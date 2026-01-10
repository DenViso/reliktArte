import sys
import os
import time
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

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# Глобальна статистика
STATS = {
    'import_details': defaultdict(lambda: {
        'folders': 0, 'products_added': 0, 'products_updated': 0, 
        'photos_added': 0, 'docs': 0
    })
}

# --- НОВА ЛОГІКА СИНХРОНІЗАЦІЇ ---

def sync_references(session: Session, category: Category):
    """Створює базові розміри та кольори для уникнення Foreign Key Error"""
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
    
    # Прив'язуємо розміри до категорії
    category.allowed_sizes = db_sizes
    
    default_color = session.query(ProductColor).filter_by(name="Стандарт").first()
    if not default_color:
        default_color = ProductColor(name="Стандарт")
        session.add(default_color)
    
    session.flush()
    return db_sizes[0], default_color

# --- ОСНОВНІ ФУНКЦІЇ ---

def extract_docx_content(file_path):
    if not DOCX_AVAILABLE or not file_path.exists():
        return "Опис відсутній", [{"value": "Опис відсутній"}], None, False, False

    try:
        doc = Document(file_path)
        lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        if not lines: return "Опис порожній", [{"value": "Опис порожній"}], None, False, False

        details = [{"value": line} for line in lines]
        full_text = " ".join(lines).lower()
        has_glass = any(kw in full_text for kw in ['скло', 'скла', 'glass', 'скління'])
        has_orientation = any(kw in full_text for kw in ['праве', 'ліве', 'правий', 'лівий'])
        
        covering_text = next((line for line in lines if any(kw in line.lower() for kw in ['пвх', 'шпон', 'ламінат', 'горіх'])), None)
        summary_text = " • ".join(lines[:3]) if len(lines) >= 3 else " • ".join(lines)
        
        return summary_text, details, covering_text, has_glass, has_orientation
    except Exception:
        return "Помилка файлу", [{"value": "Помилка"}], None, False, False

def import_products(session: Session, category_id: int, catalog_type: str):
    """Універсальна функція імпорту з відстеженням прогресу"""
    path_map = {"двері": "door", "лиштви": "mouldings"}
    catalog_path = Path(f"static/catalog/{path_map.get(catalog_type.lower())}")
    
    if not catalog_path.exists():
        print(f"⚠️ Шлях не знайдено: {catalog_path}")
        return 0
    
    category = session.get(Category, category_id)
    default_size, default_color = sync_references(session, category)
    
    # Визначаємо глибину вкладеності (двері мають класи, лиштви - ні)
    is_door = catalog_type.lower() == "двері"
    product_dirs = []
    
    if is_door:
        for class_dir in catalog_path.iterdir():
            if class_dir.is_dir(): product_dirs.extend([(class_dir.name, d) for d in class_dir.iterdir() if d.is_dir()])
    else:
        product_dirs = [("Лиштви", d) for d in catalog_path.iterdir() if d.is_dir()]

    for class_name, p_dir in product_dirs:
        STATS['import_details'][catalog_type]['folders'] += 1
        
        summary, details, cover, glass, orient = extract_docx_content(p_dir / "description.docx")
        if (p_dir / "description.docx").exists(): STATS['import_details'][catalog_type]['docs'] += 1
        
        sku = f"{catalog_type[:4]}-{class_name}-{p_dir.name}".upper().replace(' ', '-')
        product = session.query(Product).filter(Product.sku == sku).first()
        
        if not product:
            product = Product(
                sku=sku, category_id=category_id, price=5000,
                name=f"{class_name} {p_dir.name}",
                description={"text": summary, "details": details},
                have_glass=glass, orientation_choice=orient
            )
            session.add(product)
            session.flush()
            STATS['import_details'][catalog_type]['products_added'] += 1
        else:
            STATS['import_details'][catalog_type]['products_updated'] += 1
        
        # Імпорт фото
        all_photos = list(p_dir.glob('*.webp')) + list(p_dir.glob('*.jpg'))
        for p_file in all_photos:
            existing_photo = session.query(ProductPhoto).filter_by(photo=str(p_file)).first()
            if not existing_photo:
                photo = ProductPhoto(
                    photo=str(p_file), product_id=product.id,
                    is_main=(p_file == all_photos[0]),
                    dependency=ProductPhotoDepEnum.COLOR, # FIX ENUM
                    color_id=default_color.id, size_id=default_size.id
                )
                session.add(photo)
                STATS['import_details'][catalog_type]['photos_added'] += 1

    return STATS['import_details'][catalog_type]['products_added']

def print_report():
    print("\n" + "=" * 60)
    print("📊 ПІДСУМКОВИЙ ЗВІТ ІМПОРТУ")
    print("=" * 60)
    for cat, data in STATS['import_details'].items():
        print(f"\n📦 {cat.upper()}:")
        print(f"   • Оброблено папок: {data['folders']}")
        print(f"   • Нових товарів:   {data['products_added']}")
        print(f"   • Оновлено:        {data['products_updated']}")
        print(f"   • Додано фото:     {data['photos_added']}")
    print("=" * 60)

def main():
    load_dotenv('.env')
    db_url = os.getenv('DATABASE_URL').replace('postgresql://', 'postgresql+psycopg2://')
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    
    with SessionLocal() as session:
        try:
            # Створення категорій
            categories = {"Двері": True, "Лиштви": False}
            for name, glass in categories.items():
                cat = session.query(Category).filter_by(name=name).first()
                if not cat:
                    cat = Category(name=name, is_glass_available=glass)
                    session.add(cat)
                    session.flush()
                
                print(f"📂 Обробка категорії: {name}...")
                import_products(session, cat.id, name)
            
            session.commit()
            print_report()
            print("🎉 ІМПОРТ ЗАВЕРШЕНО УСПІШНО!")
        except Exception as e:
            session.rollback()
            print(f"❌ КРИТИЧНА ПОМИЛКА: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()