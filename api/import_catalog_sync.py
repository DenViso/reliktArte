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
    'catalog_analysis': {},
    'import_details': defaultdict(lambda: {
        'folders': 0, 'photos': 0, 'docs': 0,
        'products_added': 0, 'products_updated': 0, 'photos_added': 0
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

# --- 2. ОБРОБКА КОНТЕНТУ ---

def extract_docx_content(file_path):
    """Зчитує текст, визначає скло, орієнтацію та покриття"""
    if not DOCX_AVAILABLE or not file_path.exists():
        return "Опис відсутній", [{"value": "Опис відсутній"}], None, False, False, None

    try:
        doc = Document(file_path)
        lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        if not lines: 
            return "Опис порожній", [{"value": "Опис порожній"}], None, False, False, None

        details = [{"value": line} for line in lines]
        full_text = " ".join(lines).lower()
        
        # Визначаємо покриття
        covering = next((line for line in lines if any(kw in line.lower() for kw in ['пвх', 'шпон', 'ламінат', 'дуб'])), None)
        
        # --- ЛОГІКА СКЛА ---
        # Шукаємо рядок про скло
        glass_line = next((line for line in lines if any(kw in line.lower() for kw in ['скло', 'скління', 'засклена'])), None)
        
        has_glass = False
        glass_value = None
        
        if glass_line:
            if "без скла" in glass_line.lower():
                has_glass = False
                glass_value = None # Якщо "Без Скла" -> null
            else:
                has_glass = True
                glass_value = glass_line # Якщо назва скла є -> передаємо значення
        
        has_orient = any(kw in full_text for kw in ['праве', 'ліве', 'правий', 'лівий'])
        
        # --- ФОРМУВАННЯ SUMMARY (без покриття) ---
        # Беремо перші 2 рядки, ігноруючи рядок з покриттям
        summary_parts = []
        for line in lines[:2]:
            if covering and line == covering:
                continue
            summary_parts.append(line)
        summary = " • ".join(summary_parts)
        
        return summary, details, covering, has_glass, has_orient, glass_value
    except Exception:
        return "Помилка файлу", [{"value": "Помилка читання"}], None, False, False, None

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

    print(f"\n🔍 АНАЛІЗ ТА ІМПОРТ: {cat_name.upper()}")
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
        if not photos and not (p_dir / "description.docx").exists():
            continue

        STATS['import_details'][cat_name]['folders'] += 1
        
        # Отримуємо оновлені дані з docx
        summary, details, cover, glass, orient, glass_v = extract_docx_content(p_dir / "description.docx")
        
        sku = f"{folder_key[:3]}-{class_name}-{p_dir.name}".upper().replace(' ', '-')
        product = session.query(Product).filter_by(sku=sku).first()

        desc_json = {"text": summary, "details": details}
        if cover: desc_json["finishing"] = {"covering": {"text": cover}}

        if not product:
            product = Product(
                sku=sku, category_id=cat.id, price=5000,
                name=f"{class_name} {p_dir.name}",
                description=desc_json,
                have_glass=glass, orientation_choice=orient
            )
            session.add(product)
            session.flush()
            STATS['import_details'][cat_name]['products_added'] += 1
            print(f"  ➕ Додано: {sku}")
        else:
            product.description = desc_json
            product.have_glass = glass
            product.orientation_choice = orient
            STATS['import_details'][cat_name]['products_updated'] += 1
            print(f"  🔄 Оновлено: {sku}")

        # Фото
        existing_photos = {p.photo for p in session.query(ProductPhoto).filter_by(product_id=product.id).all()}
        for idx, p_file in enumerate(sorted(photos)):
            web_path = f"/static/catalog/{folder_key}/{p_dir.relative_to(base_path)}/{p_file.name}"
            if web_path not in existing_photos:
                new_photo = ProductPhoto(
                    photo=web_path, 
                    product_id=product.id,
                    is_main=(idx == 0),
                    dependency=ProductPhotoDepEnum.COLOR,
                    color_id=def_color.id, 
                    size_id=def_size.id,
                    with_glass=glass_v # Записуємо назву скла або None
                )
                session.add(new_photo)
                STATS['import_details'][cat_name]['photos_added'] += 1

# --- 4. ЗАПУСК ---

def main():
    load_dotenv('.env')
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ Помилка: DATABASE_URL не знайдено")
        return
    
    db_url = db_url.replace('postgresql://', 'postgresql+psycopg2://')
    engine = create_engine(db_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)
    
    print("🚀 СТАРТ УНІВЕРСАЛЬНОГО ІМПОРТУ (V2)")
    print("=" * 60)
    
    with SessionLocal() as session:
        try:
            analyze_and_import(session, "Двері")
            analyze_and_import(session, "Лиштви")
            session.commit()
            
            print("\n" + "=" * 60)
            print("📊 ПІДСУМКОВА СТАТИСТИКА")
            for cat, data in STATS['import_details'].items():
                print(f"📦 {cat}: {data['products_added']} нових, {data['products_updated']} оновлено, {data['photos_added']} фото")
            print("=" * 60)
            print("🎉 ВСЕ УСПІШНО ЗАВЕРШЕНО!")
            
        except Exception as e:
            session.rollback()
            print(f"\n❌ КРИТИЧНА ПОМИЛКА: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    main()