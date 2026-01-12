import os
import traceback
from pathlib import Path
from dotenv import load_dotenv
from collections import defaultdict
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

# Імпорт ваших моделей
from src.product.models import (
    Product, Category, ProductPhoto, 
    ProductSize, ProductColor
)
from src.product.enums import ProductPhotoDepEnum

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# Розширена статистика
STATS = {
    'total_deleted': 0,
    'import_details': defaultdict(lambda: {
        'added': 0, 
        'updated': 0, # У логіці TRUNCATE буде 0
        'photos': 0
    })
}

# --- 1. ОБРОБКА КОНТЕНТУ ---
def extract_docx_content(file_path):
    if not DOCX_AVAILABLE or not file_path.exists():
        return "Без опису", [], None, False, False, None, "UNKNOWN"

    try:
        doc = Document(file_path)
        lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        if not lines: return "Порожньо", [], None, False, False, None, "EMPTY"

        details = [{"value": line} for line in lines]
        full_text = " ".join(lines).lower()
        
        extracted_sku = lines[0].strip()
        covering = next((line for line in lines if any(kw in line.lower() for kw in ['пвх', 'шпон', 'ламінат', 'дуб'])), None)
        
        glass_line = next((line for line in lines if any(kw in line.lower() for kw in ['скло', 'скління', 'засклена'])), None)
        has_glass = False
        glass_value = None
        negation = ['без', 'не має', 'немає', 'відсутнє', 'глуха']
        
        if glass_line:
            if not any(n in glass_line.lower() for n in negation):
                has_glass = True
                glass_value = glass_line
        elif 'глуха' in full_text:
            has_glass = False

        has_orient = any(kw in full_text for kw in ['праве', 'ліве', 'правий', 'лівий'])
        
        stop_keywords = ['пвх', 'шпон', 'ламінат', 'дуб', '2000', 'х', 'скла', 'скло']
        clean_parts = []
        for line in lines[:3]:
            if covering and line == covering: continue
            if any(s in line.lower() for s in stop_keywords): continue
            clean_parts.append(line)
            if len(clean_parts) >= 2: break
        summary = " • ".join(clean_parts)
        
        return summary, details, covering, has_glass, has_orient, glass_value, extracted_sku
    except:
        return "Помилка", [], None, False, False, None, "ERROR"

# --- 2. СИНХРОНІЗАЦІЯ ДОВІДНИКІВ ---
def sync_refs(session: Session, category: Category):
    def_size = session.query(ProductSize).first()
    if not def_size:
        def_size = ProductSize(height=2000, width=800, thickness=40)
        session.add(def_size); session.flush()
    
    def_color = session.query(ProductColor).filter_by(name="Стандарт").first()
    if not def_color:
        def_color = ProductColor(name="Стандарт")
        session.add(def_color); session.flush()
    
    return def_size, def_color

# --- 3. ОСНОВНИЙ ІМПОРТ ---
def analyze_and_import(session: Session, cat_name: str):
    folder_key = "door" if cat_name == "Двері" else "mouldings"
    base_path = Path(f"static/catalog/{folder_key}")
    if not base_path.exists(): return

    cat = session.query(Category).filter_by(name=cat_name).first()
    if not cat:
        cat = Category(name=cat_name, is_glass_available=(cat_name=="Двері"))
        session.add(cat); session.flush()
    
    def_size, def_color = sync_refs(session, cat)

    product_dirs = []
    if cat_name == "Двері":
        for class_dir in sorted(base_path.iterdir()):
            if class_dir.is_dir():
                for p_dir in sorted(class_dir.iterdir()):
                    if p_dir.is_dir(): product_dirs.append((class_dir.name, p_dir))
    else:
        for p_dir in sorted(base_path.iterdir()):
            if p_dir.is_dir(): product_dirs.append(("Базова", p_dir))

    for class_name, p_dir in product_dirs:
        photos = list(p_dir.glob('*.webp'))
        summary, details, cover, glass, orient, g_val, sku = extract_docx_content(p_dir / "description.docx")
        
        desc_json = {"text": summary, "details": details}
        if cover: desc_json["finishing"] = {"covering": {"text": cover}}

        product = Product(
            sku=sku, category_id=cat.id, price=0, 
            name=f"{class_name} {p_dir.name}",
            description=desc_json,
            have_glass=glass, orientation_choice=orient
        )
        session.add(product); session.flush()
        STATS['import_details'][cat_name]['added'] += 1

        for idx, p_file in enumerate(sorted(photos)):
            web_path = f"/static/catalog/{folder_key}/{p_dir.relative_to(base_path)}/{p_file.name}"
            new_photo = ProductPhoto(
                photo=web_path, product_id=product.id, is_main=(idx == 0),
                dependency=ProductPhotoDepEnum.COLOR,
                color_id=def_color.id, size_id=def_size.id, with_glass=g_val
            )
            session.add(new_photo)
            STATS['import_details'][cat_name]['photos'] += 1

# --- 4. ЗАПУСК ТА ОЧИЩЕННЯ ---
def main():
    load_dotenv('.env')
    db_url = os.getenv('DATABASE_URL').replace('postgresql://', 'postgresql+psycopg2://')
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    
    with SessionLocal() as session:
        try:
            print("🔴 Крок 1: Аналіз та очищення бази...")
            
            # Рахуємо скільки було перед видаленням
            old_count = session.query(Product).count()
            STATS['total_deleted'] = old_count
            
            # Повне очищення
            session.execute(text("TRUNCATE TABLE products RESTART IDENTITY CASCADE"))
            print(f"✅ Видалено записів: {old_count}")

            print("🟢 Крок 2: Запис нових даних...")
            analyze_and_import(session, "Двері")
            analyze_and_import(session, "Лиштви")
            
            session.commit()
            
            print("\n" + "═"*50)
            print("📊 ПІДСУМКОВА СТАТИСТИКА")
            print("─"*50)
            print(f"🗑️  ВСЬОГО ВИДАЛЕНО СТАРИХ ТОВАРІВ: {STATS['total_deleted']}")
            print(f"🔄 ВСЬОГО ОНОВЛЕНО (перезаписано): 0 (обрано повне очищення)")
            print("─"*50)
            
            total_added = 0
            for cat, d in STATS['import_details'].items():
                print(f"📦 {cat}: Записано {d['added']} шт. (+ {d['photos']} фото)")
                total_added += d['added']
            
            print("─"*50)
            print(f"✨ РЕЗУЛЬТАТ: +{total_added} нових записів у базі")
            print("═"*50)
            print("🎉 КАТАЛОГ ПОВНІСТЮ ОНОВЛЕНО!")

        except Exception as e:
            session.rollback()
            print(f"❌ Помилка: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    main()