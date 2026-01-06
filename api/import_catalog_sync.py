import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Додаємо шлях до кореня проекту
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session
from src.product.models import Product, Category, ProductPhoto

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    print("⚠️ python-docx не встановлено.")

def extract_docx_content(file_path):
    """Зчитує весь текст з docx"""
    if not DOCX_AVAILABLE:
        return "Опис відсутній", [{"value": "Опис відсутній"}], None, False, False
    
    if not file_path.exists():
        return "Файл опису відсутній", [{"value": "Файл опису відсутній"}], None, False, False

    try:
        doc = Document(file_path)
        lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        
        if not lines:
            return "Опис порожній", [{"value": "Опис порожній"}], None, False, False

        details = [{"value": line} for line in lines]
        print(f"  📄 Зчитано {len(details)} рядків")

        full_text = " ".join(lines).lower()
        has_glass = any(kw in full_text for kw in ['скло', 'скла', 'glass', 'скління'])
        has_orientation = any(kw in full_text for kw in ['праве', 'ліве', 'правий', 'лівий'])
        
        covering_text = None
        for line in lines:
            if any(kw in line.lower() for kw in ['пвх', 'шпон', 'ламінат', 'горіх', 'дуб', 'ясен', 'покриття']):
                covering_text = line
                break
        
        if not covering_text and len(lines) > 1:
            covering_text = lines[1]

        summary_text = " • ".join(lines[:3]) if len(lines) >= 3 else " • ".join(lines)
        
        return summary_text, details, covering_text, has_glass, has_orientation
        
    except Exception as e:
        print(f"  ❌ Помилка: {e}")
        return "Помилка читання файлу", [{"value": "Помилка"}], None, False, False

def import_doors(session: Session, category_id: int):
    """Імпорт дверей"""
    catalog_path = Path("static/catalog/door")
    if not catalog_path.exists():
        print("❌ Каталог дверей не знайдено")
        return 0
    
    count = 0
    for class_dir in sorted(catalog_path.iterdir()):
        if not class_dir.is_dir():
            continue
        
        class_name = class_dir.name
        print(f"\n📂 {class_name}")
        
        for product_dir in sorted(class_dir.iterdir()):
            if not product_dir.is_dir():
                continue
            
            product_folder_name = product_dir.name
            
            # Збір фото
            all_photos = []
            for ext in ['*.webp', '*.png', '*.jpg', '*.jpeg']:
                all_photos.extend(list(product_dir.glob(ext)))
            
            all_photos = list({f.name.lower(): f for f in all_photos}.values())
            all_photos = sorted(all_photos, key=lambda x: x.name)

            if not all_photos:
                continue

            # DOCX
            desc_file = product_dir / "description.docx"
            summary, details, cover, glass, orient = extract_docx_content(desc_file)

            if not details:
                details = [{"value": "Опис відсутній"}]
            
            description_json = {"text": summary, "details": details}
            if cover:
                description_json["finishing"] = {"covering": {"text": cover}}

            sku = f"DOOR-{class_name.replace(' ', '-')}-{product_folder_name}".upper()
            
            # БД
            product = session.query(Product).filter(Product.sku == sku).first()
            
            if not product:
                product = Product(
                    sku=sku, category_id=category_id, price=50000,
                    name=f"{class_name} {product_folder_name}",
                    description=description_json,
                    have_glass=glass, orientation_choice=orient
                )
                session.add(product)
                session.flush()
                print(f"  ➕ {sku}")
            else:
                product.name = f"{class_name} {product_folder_name}"
                product.description = description_json
                product.have_glass = glass
                product.orientation_choice = orient
                session.flush()
                print(f"  🔄 {sku}")

            # Фото
            existing_photos = session.query(ProductPhoto).filter(
                ProductPhoto.product_id == product.id
            ).all()
            existing_paths = {p.photo for p in existing_photos}
            
            new_photos = 0
            for idx, photo_file in enumerate(all_photos):
                web_path = f"/static/catalog/door/{class_name}/{product_folder_name}/{photo_file.name}"
                if web_path not in existing_paths:
                    session.add(ProductPhoto(
                        product_id=product.id, photo=web_path,
                        is_main=(idx == 0 and len(existing_photos) == 0)
                    ))
                    new_photos += 1
            
            count += 1
            
    return count

def import_mouldings(session: Session, category_id: int):
    """Імпорт лиштв"""
    catalog_path = Path("static/catalog/mouldings")
    if not catalog_path.exists():
        print("❌ Каталог лиштв не знайдено")
        return 0
    
    count = 0
    for class_dir in sorted(catalog_path.iterdir()):
        if not class_dir.is_dir():
            continue
        
        class_name = class_dir.name
        print(f"\n📂 {class_name}")
        
        for product_dir in sorted(class_dir.iterdir()):
            if not product_dir.is_dir():
                continue
            
            product_folder_name = product_dir.name
            
            # Фото
            all_photos = []
            for ext in ['*.webp', '*.png', '*.jpg', '*.jpeg']:
                all_photos.extend(list(product_dir.glob(ext)))
            
            all_photos = list({f.name.lower(): f for f in all_photos}.values())
            all_photos = sorted(all_photos, key=lambda x: x.name)

            if not all_photos:
                continue

            # DOCX
            desc_file = product_dir / "description.docx"
            summary, details, cover, glass, orient = extract_docx_content(desc_file)

            if not details:
                details = [{"value": "Опис відсутній"}]
            
            description_json = {"text": summary, "details": details}
            if cover:
                description_json["finishing"] = {"covering": {"text": cover}}

            sku = f"MOULDING-{class_name.replace(' ', '-')}-{product_folder_name}".upper()
            
            product = session.query(Product).filter(Product.sku == sku).first()
            
            if not product:
                product = Product(
                    sku=sku, category_id=category_id, price=5000,
                    name=f"{class_name} {product_folder_name}",
                    description=description_json,
                    have_glass=False, orientation_choice=False
                )
                session.add(product)
                session.flush()
                print(f"  ➕ {sku}")
            else:
                product.name = f"{class_name} {product_folder_name}"
                product.description = description_json
                session.flush()
                print(f"  🔄 {sku}")

            # Фото
            existing_photos = session.query(ProductPhoto).filter(
                ProductPhoto.product_id == product.id
            ).all()
            existing_paths = {p.photo for p in existing_photos}
            
            new_photos = 0
            for idx, photo_file in enumerate(all_photos):
                web_path = f"/static/catalog/mouldings/{class_name}/{product_folder_name}/{photo_file.name}"
                if web_path not in existing_paths:
                    session.add(ProductPhoto(
                        product_id=product.id, photo=web_path,
                        is_main=(idx == 0 and len(existing_photos) == 0)
                    ))
                    new_photos += 1
            
            count += 1
            
    return count

def main():
    """Головна функція"""
    print("=" * 60)
    print("🚀 ПОЧАТОК ІМПОРТУ")
    print("=" * 60)
    
    load_dotenv('.env')
    
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL не знайдено!")
        return
    
    # Використовуємо psycopg2 (синхронний)
    db_url = db_url.replace('postgresql://', 'postgresql+psycopg2://')
    
    try:
        db_host = db_url.split('@')[1].split('/')[0] if '@' in db_url else 'unknown'
        print(f"🔗 Підключення до: {db_host}\n")
    except:
        print(f"🔗 Підключення до БД...\n")
    
    engine = create_engine(db_url, echo=False, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)
    
    with SessionLocal() as session:
        # Категорії
        cat_door = session.query(Category).filter(Category.name == "Двері").first()
        if not cat_door:
            cat_door = Category(name="Двері", is_glass_available=True)
            session.add(cat_door)
            session.flush()
            print("✅ Створено категорію: Двері")
        else:
            print("✅ Знайдено категорію: Двері")
        
        cat_moulding = session.query(Category).filter(Category.name == "Лиштви").first()
        if not cat_moulding:
            cat_moulding = Category(name="Лиштви", is_glass_available=False)
            session.add(cat_moulding)
            session.flush()
            print("✅ Створено категорію: Лиштви")
        else:
            print("✅ Знайдено категорію: Лиштви")
        
        print("\n" + "=" * 60)
        print("📂 ІМПОРТ ДВЕРЕЙ")
        print("=" * 60)
        door_count = import_doors(session, cat_door.id)
        
        print("\n" + "=" * 60)
        print("📂 ІМПОРТ ЛИШТВ")
        print("=" * 60)
        moulding_count = import_mouldings(session, cat_moulding.id)
        
        session.commit()
        
        print("\n" + "=" * 60)
        print("🎉 ІМПОРТ ЗАВЕРШЕНО!")
        print("=" * 60)
        print(f"📊 Статистика:")
        print(f"   - Дверей: {door_count}")
        print(f"   - Лиштв: {moulding_count}")
        print(f"   - Всього: {door_count + moulding_count}")
        print("=" * 60)

if __name__ == "__main__":
    main()
