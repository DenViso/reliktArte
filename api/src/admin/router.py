import traceback
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..product.models import Product, Category, ProductPhoto
from ..product.enums import ProductPhotoDepEnum
from ..core.db.unitofwork import UnitOfWork

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

router = APIRouter(prefix="/admin", tags=["Admin"])

# Глобальний стан для моніторингу
import_status = {
    "is_running": False,
    "progress": "",
    "stats": {},
    "details": []
}

def extract_docx_content(file_path: Path):
    """Витягує чистий SKU (артикул) та метадані"""
    if not DOCX_AVAILABLE or not file_path.exists():
        return "Без опису", [{"value": "Опис відсутній"}], None, False, False, "UNKNOWN"

    try:
        doc = Document(file_path)
        lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        if not lines:
            return "Порожньо", [], None, False, False, "EMPTY"

        # SKU — тільки ПЕРШЕ СЛОВО першого рядка (тільки артикул)
        raw_sku = lines[0].split()[0].replace(',', '').strip()
        
        details = [{"value": line} for line in lines]
        full_text = " ".join(lines).lower()
        
        # Покриття (шукаємо ключові слова)
        cover = next((l for l in lines if any(kw in l.lower() for kw in ['пвх', 'шпон', 'ламінат', 'дуб', 'матовий'])), None)
        
        # Аналіз скла з урахуванням заперечень
        negation = ['без', 'не має', 'немає', 'відсутнє', 'глуха']
        glass_line = next((l for l in lines if any(kw in l.lower() for kw in ['скло', 'скла', 'скління'])), None)
        has_glass = False
        if glass_line and not any(n in glass_line.lower() for n in negation):
            has_glass = True
        elif 'глуха' in full_text:
            has_glass = False

        # Орієнтація
        has_orient = any(kw in full_text for kw in ['праве', 'ліве', 'правий', 'лівий'])
        
        # Короткий опис (Артикул + Назва моделі)
        summary = " • ".join(lines[:2])
        
        return summary, details, cover, has_glass, has_orient, raw_sku
    except:
        return "Помилка читання", [], None, False, False, "ERROR"

async def import_task_logic(session: AsyncSession, category_id: int, folder_type: str):
    """Універсальна логіка створення товарів"""
    base_path = Path(__file__).parent.parent.parent
    catalog_path = base_path / "static" / "catalog" / folder_type
    stats = {"imported": 0, "photos": 0}
    
    if not catalog_path.exists():
        return stats

    # Формуємо список папок для обробки
    target_dirs = []
    if folder_type == "door":
        for class_dir in sorted(catalog_path.iterdir()):
            if class_dir.is_dir():
                for p_dir in sorted(class_dir.iterdir()):
                    if p_dir.is_dir(): target_dirs.append((class_dir.name, p_dir))
    else:
        for p_dir in sorted(catalog_path.iterdir()):
            if p_dir.is_dir(): target_dirs.append(("Лиштви", p_dir))

    for parent_name, p_dir in target_dirs:
        summary, details, cover, glass, orient, sku = extract_docx_content(p_dir / "description.docx")
        
        if sku in ["UNKNOWN", "EMPTY", "ERROR"]:
            continue

        # Створення товару (завжди новий, бо ми робимо TRUNCATE перед цим)
        description_json = {"text": summary, "details": details}
        if cover:
            description_json["finishing"] = {"covering": {"text": cover}}

        new_product = Product(
            sku=sku,
            category_id=category_id,
            price=0,  # Ціна за запитом
            name=f"{parent_name} {p_dir.name}",
            description=description_json,
            have_glass=glass,
            orientation_choice=orient,
            material_choice=False,
            type_of_platband_choice=False
        )
        session.add(new_product)
        await session.flush()
        stats["imported"] += 1

        # Додавання фото
        photos = list(p_dir.glob('*.webp')) + list(p_dir.glob('*.jpg'))
        for idx, photo_file in enumerate(sorted(photos)):
            # Формуємо шлях для вебу
            rel_path = p_dir.relative_to(catalog_path)
            web_path = f"/static/catalog/{folder_type}/{rel_path}/{photo_file.name}"
            
            session.add(ProductPhoto(
                product_id=new_product.id,
                photo=web_path,
                is_main=(idx == 0),
                dependency=ProductPhotoDepEnum.COLOR
            ))
            stats["photos"] += 1
            
    return stats

async def run_import_catalog(uow: UnitOfWork):
    global import_status
    try:
        import_status["is_running"] = True
        import_status["details"] = ["🚀 Початок повної перезапису каталогу..."]
        
        async with uow:
            # 1. ОЧИЩЕННЯ
            import_status["progress"] = "Видалення старих даних..."
            # Рахуємо для статистики
            count_res = await uow.session.execute(text("SELECT count(*) FROM products"))
            old_count = count_res.scalar()
            
            # Повне очищення з скиданням ID (Identity)
            await uow.session.execute(text("TRUNCATE TABLE products RESTART IDENTITY CASCADE"))
            import_status["details"].append(f"🗑️ Видалено: {old_count} товарів")

            # 2. ПЕРЕВІРКА КАТЕГОРІЙ
            # Двері
            res_d = await uow.session.execute(select(Category).where(Category.name == "Двері"))
            cat_door = res_d.scalar_one_or_none()
            if not cat_door:
                cat_door = Category(name="Двері", is_glass_available=True, have_orientation_choice=True)
                uow.session.add(cat_door)
            
            # Лиштви
            res_m = await uow.session.execute(select(Category).where(Category.name == "Лиштви"))
            cat_mould = res_m.scalar_one_or_none()
            if not cat_mould:
                cat_mould = Category(name="Лиштви", is_glass_available=False)
                uow.session.add(cat_mould)
            
            await uow.session.flush()

            # 3. ІМПОРТ
            import_status["progress"] = "Імпорт дверей..."
            door_stats = await import_task_logic(uow.session, cat_door.id, "door")
            
            import_status["progress"] = "Імпорт лиштви..."
            mould_stats = await import_task_logic(uow.session, cat_mould.id, "mouldings")
            
            await uow.commit()
            
            # 4. ФІНАЛІЗАЦІЯ
            import_status["stats"] = {
                "deleted": old_count,
                "added_doors": door_stats["imported"],
                "added_mouldings": mould_stats["imported"],
                "total_photos": door_stats["photos"] + mould_stats["photos"]
            }
            import_status["progress"] = "Завершено!"
            import_status["details"].append(f"✨ Записано {door_stats['imported'] + mould_stats['imported']} нових товарів.")

    except Exception as e:
        import_status["progress"] = "Помилка"
        import_status["details"].append(f"❌ Помилка: {str(e)}")
        traceback.print_exc()
    finally:
        import_status["is_running"] = False

# --- Ендпоінти ---

@router.post("/import-catalog")
async def trigger_import(background_tasks: BackgroundTasks, uow: UnitOfWork = Depends()):
    if import_status["is_running"]:
        raise HTTPException(status_code=409, detail="Імпорт уже запущено")
    
    import_status["is_running"] = True
    background_tasks.add_task(run_import_catalog, uow)
    return {"status": "started", "message": "Очищення та імпорт почалися у фоновому режимі"}

@router.get("/import-status")
async def get_status():
    return import_status

@router.post("/clear-import-status")
async def clear_status():
    global import_status
    import_status = {"is_running": False, "progress": "", "stats": {}, "details": []}
    return {"status": "cleared"}