import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from collections import defaultdict
import time

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

# Глобальна статистика
STATS = {
    'catalog_analysis': {},
    'import_details': defaultdict(lambda: {
        'folders': 0,
        'photos': 0,
        'docs': 0,
        'products_added': 0,
        'products_updated': 0,
        'photos_added': 0
    })
}

def analyze_catalog_structure(base_path: Path, catalog_type: str):
    """Аналізує структуру каталогу перед імпортом"""
    print("\n" + "=" * 60)
    print(f"🔍 АНАЛІЗ СТРУКТУРИ: {catalog_type.upper()}")
    print("=" * 60)
    
    if not base_path.exists():
        print(f"❌ Каталог не знайдено: {base_path}")
        return
    
    total_folders = 0
    total_photos = 0
    total_docs = 0
    class_stats = {}
    
    for class_dir in sorted(base_path.iterdir()):
        if not class_dir.is_dir():
            continue
        
        class_name = class_dir.name
        class_folders = 0
        class_photos = 0
        class_docs = 0
        
        for product_dir in sorted(class_dir.iterdir()):
            if not product_dir.is_dir():
                continue
            
            class_folders += 1
            
            # Підрахунок фото
            photos = []
            for ext in ['*.webp', '*.png', '*.jpg', '*.jpeg']:
                photos.extend(list(product_dir.glob(ext)))
            photos = list({f.name.lower(): f for f in photos}.values())
            class_photos += len(photos)
            
            # Перевірка наявності DOCX
            desc_file = product_dir / "description.docx"
            if desc_file.exists():
                class_docs += 1
        
        if class_folders > 0:
            class_stats[class_name] = {
                'folders': class_folders,
                'photos': class_photos,
                'docs': class_docs
            }
            total_folders += class_folders
            total_photos += class_photos
            total_docs += class_docs
            
            print(f"\n📂 {class_name}:")
            print(f"   └─ Папок товарів: {class_folders}")
            print(f"   └─ Фото: {class_photos}")
            print(f"   └─ DOCX файлів: {class_docs}")
    
    print("\n" + "-" * 60)
    print(f"📊 ПІДСУМОК {catalog_type.upper()}:")
    print(f"   • Класів товарів: {len(class_stats)}")
    print(f"   • Всього папок: {total_folders}")
    print(f"   • Всього фото: {total_photos}")
    print(f"   • Всього DOCX: {total_docs}")
    print("=" * 60)
    
    STATS['catalog_analysis'][catalog_type] = {
        'classes': len(class_stats),
        'folders': total_folders,
        'photos': total_photos,
        'docs': total_docs,
        'class_details': class_stats
    }

def analyze_mouldings_structure(base_path: Path):
    """Аналізує структуру каталогу лиштв (плоска структура)"""
    print("\n" + "=" * 60)
    print(f"🔍 АНАЛІЗ СТРУКТУРИ: MOULDINGS")
    print("=" * 60)
    
    if not base_path.exists():
        print(f"❌ Каталог не знайдено: {base_path}")
        return
    
    total_folders = 0
    total_photos = 0
    total_docs = 0
    
    for product_dir in sorted(base_path.iterdir()):
        if not product_dir.is_dir():
            continue
        
        total_folders += 1
        
        # Підрахунок фото
        photos = []
        for ext in ['*.webp', '*.png', '*.jpg', '*.jpeg']:
            photos.extend(list(product_dir.glob(ext)))
        photos = list({f.name.lower(): f for f in photos}.values())
        total_photos += len(photos)
        
        # Перевірка наявності DOCX
        desc_file = product_dir / "description.docx"
        if desc_file.exists():
            total_docs += 1
    
    print(f"\n📂 Лиштви (без класів):")
    print(f"   └─ Папок товарів: {total_folders}")
    print(f"   └─ Фото: {total_photos}")
    print(f"   └─ DOCX файлів: {total_docs}")
    
    print("\n" + "-" * 60)
    print(f"📊 ПІДСУМОК MOULDINGS:")
    print(f"   • Всього товарів: {total_folders}")
    print(f"   • Всього фото: {total_photos}")
    print(f"   • Всього DOCX: {total_docs}")
    print("=" * 60)
    
    STATS['catalog_analysis']['mouldings'] = {
        'classes': 0,
        'folders': total_folders,
        'photos': total_photos,
        'docs': total_docs,
        'class_details': {}
    }

def extract_docx_content(file_path):
    """Зчитує весь текст з docx"""
    if not DOCX_AVAILABLE:
        return "Опис відсутній", [{"value": "Опис відсутній"}], None, False, False, 0
    
    if not file_path.exists():
        return "Файл опису відсутній", [{"value": "Файл опису відсутній"}], None, False, False, 0

    try:
        doc = Document(file_path)
        lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        
        if not lines:
            return "Опис порожній", [{"value": "Опис порожній"}], None, False, False, 0

        details = [{"value": line} for line in lines]
        lines_count = len(details)

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
        
        return summary_text, details, covering_text, has_glass, has_orientation, lines_count
        
    except Exception as e:
        print(f"  ❌ Помилка: {e}")
        return "Помилка читання файлу", [{"value": "Помилка"}], None, False, False, 0

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

            photos_count = len(all_photos)
            
            if not all_photos:
                continue

            # DOCX
            desc_file = product_dir / "description.docx"
            summary, details, cover, glass, orient, doc_lines = extract_docx_content(desc_file)

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
                print(f"  ➕ {sku} | 📷 {photos_count} фото | 📝 {doc_lines} рядків")
                STATS['import_details']['door']['products_added'] += 1
            else:
                product.name = f"{class_name} {product_folder_name}"
                product.description = description_json
                product.have_glass = glass
                product.orientation_choice = orient
                session.flush()
                print(f"  🔄 {sku} | 📷 {photos_count} фото | 📝 {doc_lines} рядків")
                STATS['import_details']['door']['products_updated'] += 1

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
            
            STATS['import_details']['door']['folders'] += 1
            STATS['import_details']['door']['photos_added'] += new_photos
            if desc_file.exists():
                STATS['import_details']['door']['docs'] += 1
            
            count += 1
            
    return count

def import_mouldings(session: Session, category_id: int):
    """Імпорт лиштв (плоска структура - папки безпосередньо в mouldings/)"""
    catalog_path = Path("static/catalog/mouldings")
    if not catalog_path.exists():
        print("❌ Каталог лиштв не знайдено")
        return 0
    
    count = 0
    print(f"\n📂 Лиштви")
    
    for product_dir in sorted(catalog_path.iterdir()):
        if not product_dir.is_dir():
            continue
        
        product_folder_name = product_dir.name
        
        # Фото
        all_photos = []
        for ext in ['*.webp', '*.png', '*.jpg', '*.jpeg']:
            all_photos.extend(list(product_dir.glob(ext)))
        
        all_photos = list({f.name.lower(): f for f in all_photos}.values())
        all_photos = sorted(all_photos, key=lambda x: x.name)

        photos_count = len(all_photos)

        if not all_photos:
            print(f"  ⚠️ {product_folder_name} - немає фото, пропущено")
            continue

        # DOCX
        desc_file = product_dir / "description.docx"
        summary, details, cover, glass, orient, doc_lines = extract_docx_content(desc_file)

        if not details:
            details = [{"value": "Опис відсутній"}]
        
        description_json = {"text": summary, "details": details}
        if cover:
            description_json["finishing"] = {"covering": {"text": cover}}

        # SKU без класу
        sku = f"MOULDING-{product_folder_name}".upper()
        
        product = session.query(Product).filter(Product.sku == sku).first()
        
        if not product:
            product = Product(
                sku=sku, category_id=category_id, price=5000,
                name=f"Лиштва {product_folder_name}",
                description=description_json,
                have_glass=False, orientation_choice=False
            )
            session.add(product)
            session.flush()
            print(f"  ➕ {sku} | 📷 {photos_count} фото | 📝 {doc_lines} рядків")
            STATS['import_details']['mouldings']['products_added'] += 1
        else:
            product.name = f"Лиштва {product_folder_name}"
            product.description = description_json
            session.flush()
            print(f"  🔄 {sku} | 📷 {photos_count} фото | 📝 {doc_lines} рядків")
            STATS['import_details']['mouldings']['products_updated'] += 1

        # Фото
        existing_photos = session.query(ProductPhoto).filter(
            ProductPhoto.product_id == product.id
        ).all()
        existing_paths = {p.photo for p in existing_photos}
        
        new_photos = 0
        for idx, photo_file in enumerate(all_photos):
            # Шлях без класу
            web_path = f"/static/catalog/mouldings/{product_folder_name}/{photo_file.name}"
            if web_path not in existing_paths:
                session.add(ProductPhoto(
                    product_id=product.id, photo=web_path,
                    is_main=(idx == 0 and len(existing_photos) == 0)
                ))
                new_photos += 1
        
        STATS['import_details']['mouldings']['folders'] += 1
        STATS['import_details']['mouldings']['photos_added'] += new_photos
        if desc_file.exists():
            STATS['import_details']['mouldings']['docs'] += 1
        
        count += 1
    
    return count

def print_final_report():
    """Виводить фінальний звіт про імпорт"""
    print("\n" + "=" * 60)
    print("📊 ДЕТАЛЬНИЙ ЗВІТ ПРО ІМПОРТ")
    print("=" * 60)
    
    # Аналіз структури
    print("\n🔍 ПОЧАТКОВИЙ АНАЛІЗ КАТАЛОГУ:")
    print("-" * 60)
    for catalog_type, data in STATS['catalog_analysis'].items():
        print(f"\n📁 {catalog_type.upper()}:")
        if data['classes'] > 0:
            print(f"   • Класів товарів: {data['classes']}")
        print(f"   • Всього папок: {data['folders']}")
        print(f"   • Всього фото: {data['photos']}")
        print(f"   • DOCX файлів: {data['docs']}")
        
        if data['class_details']:
            print(f"\n   Деталі по класах:")
            for class_name, stats in data['class_details'].items():
                print(f"      └─ {class_name}: {stats['folders']} папок, {stats['photos']} фото, {stats['docs']} DOCX")
    
    # Результати імпорту
    print("\n" + "=" * 60)
    print("✅ РЕЗУЛЬТАТИ ІМПОРТУ:")
    print("-" * 60)
    
    total_products_added = 0
    total_products_updated = 0
    total_photos_added = 0
    
    for catalog_type, data in STATS['import_details'].items():
        print(f"\n📦 {catalog_type.upper()}:")
        print(f"   • Оброблено папок: {data['folders']}")
        print(f"   • Додано нових товарів: {data['products_added']}")
        print(f"   • Оновлено товарів: {data['products_updated']}")
        print(f"   • Додано фото: {data['photos_added']}")
        print(f"   • Оброблено DOCX: {data['docs']}")
        
        total_products_added += data['products_added']
        total_products_updated += data['products_updated']
        total_photos_added += data['photos_added']
    
    print("\n" + "=" * 60)
    print("🎯 ЗАГАЛЬНА СТАТИСТИКА:")
    print("=" * 60)
    print(f"   ✨ Додано нових товарів: {total_products_added}")
    print(f"   🔄 Оновлено товарів: {total_products_updated}")
    print(f"   📸 Завантажено фото на сервер: {total_photos_added}")
    print(f"   📂 Всього товарів оброблено: {total_products_added + total_products_updated}")
    
    # Категорії
    print("\n" + "-" * 60)
    print("📋 КАТЕГОРІЇ:")
    categories_processed = list(STATS['import_details'].keys())
    for cat in categories_processed:
        print(f"   • {cat.capitalize()}")
    
    print("=" * 60)

def test_connection(db_url: str, max_retries: int = 3):
    """Тестує підключення до БД з повторними спробами"""
    for attempt in range(1, max_retries + 1):
        try:
            print(f"🔌 Спроба підключення {attempt}/{max_retries}...")
            
            engine = create_engine(
                db_url,
                echo=False,
                pool_pre_ping=True,
                pool_size=1,
                max_overflow=0,
                pool_timeout=30,
                connect_args={
                    'connect_timeout': 10,
                    'keepalives': 1,
                    'keepalives_idle': 30,
                    'keepalives_interval': 10,
                    'keepalives_count': 5,
                }
            )
            
            # Тестове підключення
            with engine.connect() as conn:
                conn.execute(select(1))
            
            print("✅ Підключення успішне!")
            return engine
            
        except Exception as e:
            print(f"❌ Спроба {attempt} невдала: {e}")
            if attempt < max_retries:
                wait_time = attempt * 2
                print(f"⏳ Очікування {wait_time} секунд перед наступною спробою...")
                time.sleep(wait_time)
            else:
                raise

def main():
    """Головна функція"""
    print("=" * 60)
    print("🚀 ПОЧАТОК ІМПОРТУ КАТАЛОГУ")
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
        print(f"🔗 Підключення до: {db_host}")
    except:
        print(f"🔗 Підключення до БД...")
    
    # Аналіз структури перед імпортом
    analyze_catalog_structure(Path("static/catalog/door"), "door")
    analyze_mouldings_structure(Path("static/catalog/mouldings"))  # Окрема функція для лиштв
    
    # Підключення до БД з повторними спробами
    try:
        engine = test_connection(db_url)
    except Exception as e:
        print(f"\n❌ Не вдалося підключитися до БД після всіх спроб!")
        print(f"Помилка: {e}")
        return
    
    SessionLocal = sessionmaker(bind=engine)
    
    try:
        with SessionLocal() as session:
            # Категорії
            cat_door = session.query(Category).filter(Category.name == "Двері").first()
            if not cat_door:
                cat_door = Category(name="Двері", is_glass_available=True)
                session.add(cat_door)
                session.flush()
                print("\n✅ Створено категорію: Двері")
            else:
                print("\n✅ Знайдено категорію: Двері")
            
            cat_mouldings = session.query(Category).filter(Category.name == "Лиштви").first()
            if not cat_mouldings:
                cat_mouldings = Category(name="Лиштви", is_glass_available=False)
                session.add(cat_mouldings)
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
            mouldings_count = import_mouldings(session, cat_mouldings.id)
            
            session.commit()
            print("\n✅ Зміни збережено в БД")
            
    except Exception as e:
        print(f"\n❌ Помилка під час імпорту: {e}")
        import traceback
        traceback.print_exc()
        return
    finally:
        engine.dispose()
    
    # Фінальний звіт
    print_final_report()
    
    print("\n🎉 ІМПОРТ УСПІШНО ЗАВЕРШЕНО!")
    print("=" * 60)

if __name__ == "__main__":
    main()
