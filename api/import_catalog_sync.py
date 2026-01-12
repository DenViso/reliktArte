import sys
import os
import time
import traceback
from pathlib import Path
from dotenv import load_dotenv
from collections import defaultdict
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker, Session

# Імпорт ваших моделей та енумів
from src.product.models import (
    Product, Category, ProductPhoto, 
    ProductSize, ProductColor, ProductGlassColor
)
from src.product.enums import ProductPhotoDepEnum

# Спроба імпорту docx
try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    print("⚠️ python-docx не встановлено. Описи не будуть зчитані.")

# Глобальна статистика
STATS = {
    'import_details': defaultdict(lambda: {
        'folders': 0, 'products_added': 0, 'products_updated': 0, 'photos_added': 0
    })
}

# --- 1. ПІДГОТОВКА БАЗИ ДАНИХ ---

def sync_references(session: Session, category: Category):
    """Гарантує наявність базових розмірів та кольорів для категорії"""
    standard_sizes = [
        {"height": 2000, "width": 600, "thickness": 40},
        {"height": 2000, "width": 700, "thickness": 40},
        {"height": 2000, "width": 800, "thickness": 40},
        {"height": 2000, "width": 900, "thickness": 40},
    ]
    
    db_sizes = []
    for s in standard_sizes:
        size = session.query(ProductSize).filter_by(**s).first()
        if not size:
            size = ProductSize(**s)
            session.add(size)
            session.flush()
        db_sizes.append(size)
    
    category.allowed_sizes = db_sizes
    
    default_color = session.query(ProductColor).filter_by(name="Стандарт").first()
    if not default_color:
        default_color = ProductColor(name="Стандарт")
        session.add(default_color)
    
    session.flush()
    return db_sizes[0], default_color

# --- 2. ОБРОБКА КОНТЕНТУ (СКЛО, SUMMARY, SKU) ---

def extract_docx_content(file_path):
    """Зчитує текст, визначає SKU, чистий опис та наявність скла"""
    if not DOCX_AVAILABLE or not file_path.exists():
        return "Опис відсутній", [{"value": "Опис відсутній"}], None, False, False, None, "UNKNOWN"

    try:
        doc = Document(file_path)
        lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        if not lines: 
            return "Опис порожній", [{"value": "Опис порожній"}], None, False, False, None, "EMPTY"

        details = [{"value": line} for line in lines]
        full_text = " ".join(lines).lower()
        
        # --- SKU: Тільки перший рядок (артикул) ---
        extracted_sku = lines[0].strip()

        # --- ПОКРИТТЯ (finishing) ---
        covering = next((line for line in lines if any(kw in line.lower() for kw in ['пвх', 'шпон', 'ламінат', 'дуб'])), None)
        
        # --- ЛОГІКА СКЛА (із запереченнями) ---
        glass_line = next((line for line in lines if any(kw in line.lower() for kw in ['скло', 'скління', 'засклена'])), None)
        has_glass = False
        glass_value = None
        negation_keywords = ['без', 'не має', 'немає', 'відсутнє', 'відсутня', 'глуха']
        
        if glass_line:
            is_negated = any(neg in glass_line.lower() for neg in negation_keywords)
            if not is_negated:
                has_glass = True
                glass_value = glass_line
        elif 'глуха' in full_text:
            has_glass = False

        # Орієнтація
        has_orient = any(kw in full_text for kw in ['праве', 'ліве', 'правий', 'лівий'])
        
        # --- ЧИСТИЙ SUMMARY (Тільки Артикул та Модель) ---
        stop_keywords = ['пвх', 'шпон', 'ламінат', 'дуб', '2000', 'х', 'праве', 'ліве', 'скла', 'скло']
        clean_parts = []
        for line in lines[:3]:
            if covering and line == covering: continue
            if any(stop in line.lower() for stop in stop_keywords): continue
            clean_parts.append(line)
            if len(clean_parts) >= 2: break
        summary = " • ".join(clean_parts)
        
        return summary, details, covering, has_glass, has_orient, glass_value, extracted_sku
    except Exception:
        return "Помилка", [], None, False, False, None, "ERROR"

# --- 3. АНАЛІЗ ТА ІМПОРТ ---

def analyze_and_import(session: Session, cat_name: str):
    folder_key = "door" if cat_name == "Двері" else "mouldings"
    base_path = Path(f"static/catalog/{folder_key}")
    
    if not base_path.exists():
        print(f"❌ Шлях не знайдено: {base_path}")
        return

    cat = session.query(Category).filter_by(name=cat_name).first()
    if not cat:
        cat = Category(name=cat_name, is_glass_available=(cat_name == "Двері"))
        session.add(cat)
        session.flush()
    
    def_size, def_color = sync_references(session, cat)

    print(f"\n🔍 ІМПОРТ: {cat_name.upper()}")
    print("-" * 60)

    product_dirs = []
    if cat_name == "Двері":
        for class_dir in sorted(base_path.iterdir()):
            if class_dir.is_dir():
                for p_dir in sorted(class_dir.iterdir()):
                    if p_dir.is_dir():
                        product_dirs.append((class_dir.name, p_dir))
    else:
        for p_dir in sorted(base_path.iterdir()):
            if p_dir.is_dir():
                product_dirs.append(("Базова", p_dir))

    for class_name, p_dir in product_dirs:
        photos = list(p_dir.glob('*.webp')) + list(p_dir.glob('*.jpg')) + list(p_dir.glob('*.png'))
        docx_path = p_dir / "description.docx"
        if not photos and not docx_path.exists():
            continue

        summary, details, cover, glass, orient, glass_v, extracted_sku = extract_docx_content(docx_path)
        
        # Використовуємо чистий артикул як SKU
        sku = extracted_sku 
        
        product = session.query(Product).filter_by(sku=sku).first()
        desc_json = {"text": summary, "details": details}
        if cover: desc_json["finishing"] = {"covering": {"text": cover}}

        if not product:
            product = Product(
                sku=sku, category_id=cat.id, 
                price=0,  # 0 = "Надішліть запит"
                name=f"{class_name} {p_dir.name}",
                description=desc_json,
                have_glass=glass, orientation_choice=orient
            )
            session.add(product)
            session.flush()
            STATS['import_details'][cat_name]['products_added'] += 1
            print(f"  ➕ Додано: SKU {sku}")
        else:
            product.description = desc_json
            product.have_glass = glass
            product.price = 0
            product.orientation_choice = orient
            STATS['import_details'][cat_name]['products_updated'] += 1
            print(f"  🔄 Оновлено: SKU {sku}")

        # Обробка Фото
        existing_photos = {p.photo for p in session.query(ProductPhoto).filter_by(product_id=product.id).all()}
        for idx, p_file in enumerate(sorted(photos)):
            web_path = f"/static/catalog/{folder_key}/{p_dir.relative_to(base_path)}/{p_file.name}"
            if web_path not in existing_photos:
                new_photo = ProductPhoto(
                    photo=web_path, product_id=product.id,
                    is_main=(idx == 0),
                    dependency=ProductPhotoDepEnum.COLOR,
                    color_id=def_color.id, size_id=def_size.id,
                    with_glass=glass_v
                )
                session.add(new_photo)
                STATS['import_details'][cat_name]['photos_added'] += 1

# --- 4. ЗАПУСК ---

def main():
    load_dotenv('.env')
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL не знайдено")
        return
    
    db_url = db_url.replace('postgresql://', 'postgresql+psycopg2://')
    engine = create_engine(db_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)
    
    with SessionLocal() as session:
        try:
            analyze_and_import(session, "Двері")
            analyze_and_import(session, "Лиштви")
            session.commit()
            print("\n✅ УСПІШНО ЗАВЕРШЕНО")
        except Exception as e:
            session.rollback()
            print(f"\n❌ ПОМИЛКА: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    main()