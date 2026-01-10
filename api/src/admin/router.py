"""
Адміністративні ендпоінти для управління каталогом
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pathlib import Path
import traceback

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..product.models import Product, Category, ProductPhoto
from ..product.enums import ProductPhotoDepEnum  # ← ІМПОРТ ENUM
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
    "stats": {},
    "details": []
}


def extract_docx_content(file_path: Path):
    """Витягує контент з DOCX файлу"""
    if not DOCX_AVAILABLE:
        return "Опис відсутній", [], None, False, False, 0
    
    if not file_path.exists():
        return "Файл відсутній", [], None, False, False, 0

    try:
        doc = Document(file_path)
        all_paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        
        if not all_paragraphs:
            return "Опис порожній", [], None, False, False, 0

        details = all_paragraphs
        lines_count = len(details)
        
        full_text = " ".join(all_paragraphs).lower()
        
        has_glass = any(kw in full_text for kw in ['скло', 'скла', 'glass', 'скління'])
        has_orientation = any(kw in full_text for kw in ['праве', 'ліве', 'правий', 'лівий'])
        
        covering_text = None
        for line in all_paragraphs:
            if any(kw in line.lower() for kw in ['пвх', 'шпон', 'ламінат', 'горіх', 'дуб', 'ясен', 'покриття']):
                covering_text = line
                break
        
        if not covering_text and len(all_paragraphs) > 1:
            covering_text = all_paragraphs[1]

        summary_text = " • ".join(all_paragraphs[:3]) if len(all_paragraphs) >= 3 else " • ".join(all_paragraphs)
        
        return summary_text, details, covering_text, has_glass, has_orientation, lines_count
        
    except Exception as e:
        return f"Помилка: {str(e)}", [], None, False, False, 0


async def import_doors_task(session: AsyncSession, category_id: int) -> dict:
    """Імпорт дверей"""
    base_path = Path(__file__).parent.parent.parent
    catalog_path = base_path / "static" / "catalog" / "door"
    
    import_status["details"].append(f"🔍 Шукаю каталог: {catalog_path}")
    
    if not catalog_path.exists():
        error_msg = f"Каталог не знайдено: {catalog_path}"
        import_status["details"].append(f"❌ {error_msg}")
        return {"imported": 0, "updated": 0, "skipped": 0, "photos_added": 0, "error": error_msg}
    
    imported = 0
    updated = 0
    skipped = 0
    photos_added = 0
    
    for class_dir in sorted(catalog_path.iterdir()):
        if not class_dir.is_dir():
            continue
        
        class_name = class_dir.name
        import_status["progress"] = f"Обробка: {class_name}"
        import_status["details"].append(f"📂 {class_name}")
        
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
                skipped += 1
                import_status["details"].append(f"   ⚠️ {product_folder_name} - немає фото")
                continue

            # DOCX
            desc_file = product_dir / "description.docx"
            summary, details, cover, glass, orient, doc_lines = extract_docx_content(desc_file)

            if not details:
                details = []
            
            description_json = {
                "text": summary,
                "details": details
            }
            
            if cover:
                description_json["finishing"] = {
                    "covering": {
                        "text": cover,
                        "advantages": []
                    }
                }

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
                    orientation_choice=orient,
                    material_choice=False,
                    type_of_platband_choice=False
                )
                session.add(product)
                imported += 1
                import_status["details"].append(f"   ➕ {sku} | {len(all_photos)} фото | {doc_lines} рядків")
            else:
                product.name = f"{class_name} {product_folder_name}"
                product.description = description_json
                product.have_glass = glass
                product.orientation_choice = orient
                updated += 1
                import_status["details"].append(f"   🔄 {sku} | {len(all_photos)} фото | {doc_lines} рядків")
            
            await session.flush()

            # Фото
            res_photos = await session.execute(
                select(ProductPhoto).where(ProductPhoto.product_id == product.id)
            )
            existing_photos = res_photos.scalars().all()
            existing_paths = {p.photo for p in existing_photos}
            
            new_photos_count = 0
            for idx, photo_file in enumerate(all_photos):
                web_path = f"/static/catalog/door/{class_name}/{product_folder_name}/{photo_file.name}"
                if web_path not in existing_paths:
                    has_main = any(p.is_main for p in existing_photos)
                    session.add(ProductPhoto(
                        product_id=product.id,
                        photo=web_path,
                        is_main=(idx == 0 and not has_main),
                        dependency=ProductPhotoDepEnum.COLOR  # ← ВИПРАВЛЕНО!
                    ))
                    new_photos_count += 1
            
            photos_added += new_photos_count
    
    return {
        "imported": imported,
        "updated": updated,
        "skipped": skipped,
        "photos_added": photos_added
    }


async def import_mouldings_task(session: AsyncSession, category_id: int) -> dict:
    """Імпорт лиштв"""
    base_path = Path(__file__).parent.parent.parent
    catalog_path = base_path / "static" / "catalog" / "mouldings"
    
    import_status["details"].append(f"🔍 Шукаю каталог: {catalog_path}")
    
    if not catalog_path.exists():
        error_msg = f"Каталог не знайдено: {catalog_path}"
        import_status["details"].append(f"❌ {error_msg}")
        return {"imported": 0, "updated": 0, "skipped": 0, "photos_added": 0, "error": error_msg}
    
    imported = 0
    updated = 0
    skipped = 0
    photos_added = 0
    
    import_status["progress"] = "Обробка: Лиштви"
    import_status["details"].append("📂 Лиштви")
    
    for product_dir in sorted(catalog_path.iterdir()):
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
            skipped += 1
            import_status["details"].append(f"   ⚠️ {product_folder_name} - немає фото")
            continue

        # DOCX
        desc_file = product_dir / "description.docx"
        summary, details, cover, glass, orient, doc_lines = extract_docx_content(desc_file)

        if not details:
            details = []
        
        description_json = {
            "text": summary,
            "details": details
        }
        
        if cover:
            description_json["finishing"] = {
                "covering": {
                    "text": cover,
                    "advantages": []
                }
            }

        sku = f"MOULDING-{product_folder_name}".upper()
        
        result = await session.execute(select(Product).where(Product.sku == sku))
        product = result.scalar_one_or_none()
        
        if not product:
            product = Product(
                sku=sku,
                category_id=category_id,
                price=5000,
                name=f"Лиштва {product_folder_name}",
                description=description_json,
                have_glass=False,
                orientation_choice=False,
                material_choice=False,
                type_of_platband_choice=False
            )
            session.add(product)
            imported += 1
            import_status["details"].append(f"   ➕ {sku} | {len(all_photos)} фото | {doc_lines} рядків")
        else:
            product.name = f"Лиштва {product_folder_name}"
            product.description = description_json
            updated += 1
            import_status["details"].append(f"   🔄 {sku} | {len(all_photos)} фото | {doc_lines} рядків")
        
        await session.flush()

        # Фото
        res_photos = await session.execute(
            select(ProductPhoto).where(ProductPhoto.product_id == product.id)
        )
        existing_photos = res_photos.scalars().all()
        existing_paths = {p.photo for p in existing_photos}
        
        new_photos_count = 0
        for idx, photo_file in enumerate(all_photos):
            web_path = f"/static/catalog/mouldings/{product_folder_name}/{photo_file.name}"
            if web_path not in existing_paths:
                has_main = any(p.is_main for p in existing_photos)
                session.add(ProductPhoto(
                    product_id=product.id,
                    photo=web_path,
                    is_main=(idx == 0 and not has_main),
                    dependency=ProductPhotoDepEnum.COLOR  # ← ВИПРАВЛЕНО!
                ))
                new_photos_count += 1
        
        photos_added += new_photos_count
    
    return {
        "imported": imported,
        "updated": updated,
        "skipped": skipped,
        "photos_added": photos_added
    }


async def run_import_catalog(uow: UnitOfWork):
    """Основна функція імпорту"""
    global import_status
    
    try:
        import_status["is_running"] = True
        import_status["progress"] = "Початок імпорту..."
        import_status["details"] = []
        
        async with uow:
            # Категорії
            import_status["progress"] = "Створення категорій..."
            import_status["details"].append("🔧 Перевірка категорій...")
            
            res_door = await uow.session.execute(
                select(Category).where(Category.name == "Двері")
            )
            cat_door = res_door.scalar_one_or_none()
            
            if not cat_door:
                cat_door = Category(
                    name="Двері",
                    is_glass_available=True,
                    have_material_choice=True,
                    have_orientation_choice=True,
                    have_type_of_platband_choice=False
                )
                uow.session.add(cat_door)
                await uow.session.flush()
                import_status["details"].append("✅ Створено категорію: Двері")
            else:
                import_status["details"].append("✅ Знайдено категорію: Двері")
            
            res_moulding = await uow.session.execute(
                select(Category).where(Category.name == "Лиштви")
            )
            cat_moulding = res_moulding.scalar_one_or_none()
            
            if not cat_moulding:
                cat_moulding = Category(
                    name="Лиштви",
                    is_glass_available=False,
                    have_material_choice=False,
                    have_orientation_choice=False,
                    have_type_of_platband_choice=False
                )
                uow.session.add(cat_moulding)
                await uow.session.flush()
                import_status["details"].append("✅ Створено категорію: Лиштви")
            else:
                import_status["details"].append("✅ Знайдено категорію: Лиштви")
            
            import_status["details"].append("\n" + "=" * 60)
            
            # Імпорт дверей
            import_status["progress"] = "Імпорт дверей..."
            import_status["details"].append("📦 ІМПОРТ ДВЕРЕЙ")
            import_status["details"].append("=" * 60)
            door_stats = await import_doors_task(uow.session, cat_door.id)
            
            import_status["details"].append("\n" + "=" * 60)
            
            # Імпорт лиштв
            import_status["progress"] = "Імпорт лиштв..."
            import_status["details"].append("📦 ІМПОРТ ЛИШТВ")
            import_status["details"].append("=" * 60)
            moulding_stats = await import_mouldings_task(uow.session, cat_moulding.id)
            
            await uow.commit()
            
            import_status["stats"] = {
                "doors": door_stats,
                "mouldings": moulding_stats,
                "total_imported": door_stats.get("imported", 0) + moulding_stats.get("imported", 0),
                "total_updated": door_stats.get("updated", 0) + moulding_stats.get("updated", 0),
                "total_photos": door_stats.get("photos_added", 0) + moulding_stats.get("photos_added", 0),
                "total_skipped": door_stats.get("skipped", 0) + moulding_stats.get("skipped", 0)
            }
            
            import_status["details"].append("\n" + "=" * 60)
            import_status["details"].append("🎯 ПІДСУМОК:")
            import_status["details"].append("=" * 60)
            import_status["details"].append(f"✨ Додано нових: {import_status['stats']['total_imported']}")
            import_status["details"].append(f"🔄 Оновлено: {import_status['stats']['total_updated']}")
            import_status["details"].append(f"📸 Фото додано: {import_status['stats']['total_photos']}")
            import_status["details"].append(f"⚠️ Пропущено: {import_status['stats']['total_skipped']}")
            import_status["details"].append("=" * 60)
            
            import_status["progress"] = "Завершено!"
            
    except Exception as e:
        error_msg = f"Помилка: {str(e)}"
        import_status["progress"] = error_msg
        import_status["stats"] = {"error": str(e)}
        import_status["details"].append(f"\n❌ {error_msg}")
        traceback.print_exc()
    finally:
        import_status["is_running"] = False


@router.post("/import-catalog")
async def trigger_catalog_import(
    background_tasks: BackgroundTasks,
    uow: UnitOfWork = Depends()
):
    """Запустити імпорт каталогу"""
    global import_status
    
    if import_status["is_running"]:
        raise HTTPException(status_code=409, detail="Імпорт вже виконується")
    
    import_status = {
        "is_running": True,
        "progress": "Запуск...",
        "stats": {},
        "details": []
    }
    
    background_tasks.add_task(run_import_catalog, uow)
    
    return {
        "status": "started",
        "message": "Імпорт каталогу запущено. Перевіряйте статус через /admin/import-status"
    }


@router.get("/import-status")
async def get_import_status():
    """Отримати статус імпорту"""
    return import_status


@router.post("/clear-import-status")
async def clear_import_status():
    """Очистити статус імпорту"""
    global import_status
    import_status = {
        "is_running": False,
        "progress": "",
        "stats": {},
        "details": []
    }
    return {"status": "cleared"}