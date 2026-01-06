"""
Адміністративні ендпоінти для управління каталогом
ВАЖЛИВО: Використовуйте тільки в безпечному середовищі!
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from pathlib import Path
import asyncio
from typing import Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..product.models import Product, Category, ProductPhoto
from ..core.db.unitofwork import UnitOfWork

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

router = APIRouter(prefix="/admin", tags=["Admin"])

# Глобальна змінна для статусу імпорту
import_status = {
    "is_running": False,
    "progress": "",
    "stats": {}
}


def extract_docx_content(file_path: Path):
    """Витягує контент з DOCX файлу"""
    if not DOCX_AVAILABLE:
        return "Опис відсутній", [{"value": "python-docx не встановлено"}], None, False, False
    
    if not file_path.exists():
        return "Файл відсутній", [{"value": "Файл опису відсутній"}], None, False, False

    try:
        doc = Document(file_path)
        all_paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        
        if not all_paragraphs:
            return "Опис порожній", [{"value": "Документ порожній"}], None, False, False

        details = [{"value": line} for line in all_paragraphs]
        full_text = " ".join(all_paragraphs).lower()
        
        has_glass = any(kw in full_text for kw in ['скло', 'скла', 'glass', 'скління'])
        has_orientation = any(kw in full_text for kw in ['праве', 'ліве', 'правий', 'лівий'])
        
        covering_text = None
        for line in all_paragraphs:
            if any(kw in line.lower() for kw in ['пвх', 'шпон', 'ламінат', 'горіх', 'дуб', 'покриття']):
                covering_text = line
                break
        
        if not covering_text and len(all_paragraphs) > 1:
            covering_text = all_paragraphs[1]

        summary_text = " • ".join(all_paragraphs[:3]) if len(all_paragraphs) >= 3 else " • ".join(all_paragraphs)
        
        return summary_text, details, covering_text, has_glass, has_orientation
        
    except Exception as e:
        return f"Помилка: {str(e)}", [{"value": "Помилка читання"}], None, False, False


async def import_doors_task(session: AsyncSession, category_id: int) -> Dict[str, int]:
    """Імпорт дверей"""
    catalog_path = Path("api/static/catalog/door")
    if not catalog_path.exists():
        return {"imported": 0, "skipped": 0, "error": "Каталог не знайдено"}
    
    count = 0
    skipped = 0
    
    for class_dir in sorted(catalog_path.iterdir()):
        if not class_dir.is_dir():
            continue
        
        for product_dir in sorted(class_dir.iterdir()):
            if not product_dir.is_dir():
                continue
            
            class_name = class_dir.name
            product_folder_name = product_dir.name
            
            # Збір фото
            photo_extensions = ['*.webp', '*.png', '*.jpg', '*.jpeg']
            all_photos = []
            for ext in photo_extensions:
                all_photos.extend(list(product_dir.glob(ext)))
            
            all_photos = list({f.name.lower(): f for f in all_photos}.values())
            all_photos = sorted(all_photos, key=lambda x: x.name)

            if not all_photos:
                skipped += 1
                continue

            # DOCX
            desc_file = product_dir / "description.docx"
            summary, details, cover, glass, orient = extract_docx_content(desc_file)

            if not details:
                details = [{"value": "Опис відсутній"}]
            
            description_json = {
                "text": summary,
                "details": details
            }
            
            if cover:
                description_json["finishing"] = {"covering": {"text": cover}}

            sku = f"DOOR-{class_name.replace(' ', '-')}-{product_folder_name}".upper()
            
            # БД
            result = await session.execute(select(Product).where(Product.sku == sku))
            product = result.scalar_one_or_none()
            
            if not product:
                product = Product(
                    sku=sku,
                    category_id=category_id,
                    price=50000,
                    name=f"{class_name} {product_folder_name}",
                    description=description_json,
                    have_glass=glass,
                    orientation_choice=orient
                )
                session.add(product)
            else:
                product.name = f"{class_name} {product_folder_name}"
                product.description = description_json
                product.have_glass = glass
                product.orientation_choice = orient
            
            await session.flush()

            # Фото
            res_photos = await session.execute(
                select(ProductPhoto).where(ProductPhoto.product_id == product.id)
            )
            existing_photos = res_photos.scalars().all()
            existing_paths = {p.photo for p in existing_photos}
            
            for idx, photo_file in enumerate(all_photos):
                web_path = f"/static/catalog/door/{class_name}/{product_folder_name}/{photo_file.name}"
                if web_path not in existing_paths:
                    has_main = any(p.is_main for p in existing_photos)
                    session.add(ProductPhoto(
                        product_id=product.id,
                        photo=web_path,
                        is_main=(idx == 0 and not has_main)
                    ))
            
            count += 1
    
    return {"imported": count, "skipped": skipped}


async def import_mouldings_task(session: AsyncSession, category_id: int) -> Dict[str, int]:
    """Імпорт лиштв"""
    catalog_path = Path("api/static/catalog/mouldings")
    if not catalog_path.exists():
        return {"imported": 0, "skipped": 0, "error": "Каталог не знайдено"}
    
    count = 0
    skipped = 0
    
    for class_dir in sorted(catalog_path.iterdir()):
        if not class_dir.is_dir():
            continue
        
        for product_dir in sorted(class_dir.iterdir()):
            if not product_dir.is_dir():
                continue
            
            class_name = class_dir.name
            product_folder_name = product_dir.name
            
            photo_extensions = ['*.webp', '*.png', '*.jpg', '*.jpeg']
            all_photos = []
            for ext in photo_extensions:
                all_photos.extend(list(product_dir.glob(ext)))
            
            all_photos = list({f.name.lower(): f for f in all_photos}.values())
            all_photos = sorted(all_photos, key=lambda x: x.name)

            if not all_photos:
                skipped += 1
                continue

            desc_file = product_dir / "description.docx"
            summary, details, cover, glass, orient = extract_docx_content(desc_file)

            if not details:
                details = [{"value": "Опис відсутній"}]
            
            description_json = {
                "text": summary,
                "details": details
            }
            
            if cover:
                description_json["finishing"] = {"covering": {"text": cover}}

            sku = f"MOULDING-{class_name.replace(' ', '-')}-{product_folder_name}".upper()
            
            result = await session.execute(select(Product).where(Product.sku == sku))
            product = result.scalar_one_or_none()
            
            if not product:
                product = Product(
                    sku=sku,
                    category_id=category_id,
                    price=5000,
                    name=f"{class_name} {product_folder_name}",
                    description=description_json,
                    have_glass=False,
                    orientation_choice=False
                )
                session.add(product)
            else:
                product.name = f"{class_name} {product_folder_name}"
                product.description = description_json
            
            await session.flush()

            res_photos = await session.execute(
                select(ProductPhoto).where(ProductPhoto.product_id == product.id)
            )
            existing_photos = res_photos.scalars().all()
            existing_paths = {p.photo for p in existing_photos}
            
            for idx, photo_file in enumerate(all_photos):
                web_path = f"/static/catalog/mouldings/{class_name}/{product_folder_name}/{photo_file.name}"
                if web_path not in existing_paths:
                    has_main = any(p.is_main for p in existing_photos)
                    session.add(ProductPhoto(
                        product_id=product.id,
                        photo=web_path,
                        is_main=(idx == 0 and not has_main)
                    ))
            
            count += 1
    
    return {"imported": count, "skipped": skipped}


async def run_import_catalog(uow: UnitOfWork):
    """Основна функція імпорту"""
    global import_status
    
    try:
        import_status["is_running"] = True
        import_status["progress"] = "Початок імпорту..."
        
        async with uow:
            # Категорії
            import_status["progress"] = "Створення категорій..."
            res_door = await uow.session.execute(
                select(Category).where(Category.name == "Двері")
            )
            cat_door = res_door.scalar_one_or_none()
            
            if not cat_door:
                cat_door = Category(name="Двері", is_glass_available=True)
                uow.session.add(cat_door)
                await uow.session.flush()
            
            res_moulding = await uow.session.execute(
                select(Category).where(Category.name == "Лиштви")
            )
            cat_moulding = res_moulding.scalar_one_or_none()
            
            if not cat_moulding:
                cat_moulding = Category(name="Лиштви", is_glass_available=False)
                uow.session.add(cat_moulding)
                await uow.session.flush()
            
            # Імпорт дверей
            import_status["progress"] = "Імпорт дверей..."
            door_stats = await import_doors_task(uow.session, cat_door.id)
            
            # Імпорт лиштв
            import_status["progress"] = "Імпорт лиштв..."
            moulding_stats = await import_mouldings_task(uow.session, cat_moulding.id)
            
            await uow.commit()
            
            import_status["stats"] = {
                "doors": door_stats,
                "mouldings": moulding_stats,
                "total": door_stats.get("imported", 0) + moulding_stats.get("imported", 0)
            }
            import_status["progress"] = "Завершено!"
            
    except Exception as e:
        import_status["progress"] = f"Помилка: {str(e)}"
        import_status["stats"] = {"error": str(e)}
    finally:
        import_status["is_running"] = False


@router.post("/import-catalog")
async def trigger_catalog_import(
    background_tasks: BackgroundTasks,
    uow: UnitOfWork = Depends()
):
    """
    Запустити імпорт каталогу
    
    УВАГА: Цей endpoint запускає тривалу операцію!
    """
    global import_status
    
    if import_status["is_running"]:
        raise HTTPException(status_code=409, detail="Імпорт вже виконується")
    
    # Скидаємо статус
    import_status = {
        "is_running": True,
        "progress": "Запуск...",
        "stats": {}
    }
    
    # Запускаємо в фоні
    background_tasks.add_task(run_import_catalog, uow)
    
    return {
        "status": "started",
        "message": "Імпорт каталогу запущено. Перевіряйте статус через /admin/import-status"
    }


@router.get("/import-status")
async def get_import_status():
    """Отримати статус імпорту"""
    return import_status