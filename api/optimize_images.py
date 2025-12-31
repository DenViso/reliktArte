import os
import time
from PIL import Image
from pathlib import Path
from multiprocessing import Pool

def get_dir_size(directory):
    """Рахує загальний розмір папки в байтах"""
    total_size = 0
    for root, _, files in os.walk(directory):
        for f in files:
            fp = os.path.join(root, f)
            if os.path.exists(fp):
                total_size += os.path.getsize(fp)
    return total_size

def recompress_webp(file_path):
    """Перетискає існуючий WebP файл для макс. економії місця"""
    try:
        temp_path = file_path.with_suffix('.temp.webp')
        original_size = os.path.getsize(file_path)
        
        with Image.open(file_path) as img:
            # 1. Зменшення роздільної здатності (Resize)
            # Це дає найбільший приріст в економії ваги
            max_size = 1600
            if img.width > max_size or img.height > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

            # 2. Агресивне збереження
            # quality=45 — дуже високе стиснення, ідеально для великих каталогів
            img.save(temp_path, "WEBP", quality=45, method=6, optimize=True)
            
        new_size = os.path.getsize(temp_path)
        
        # Замінюємо оригінал тільки якщо новий файл дійсно менший
        if new_size < original_size:
            os.replace(temp_path, file_path)
            return original_size, new_size, True
        else:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return original_size, original_size, False
            
    except Exception as e:
        return 0, 0, False

def run_recompression(directory):
    if not os.path.exists(directory):
        print(f"❌ Папка '{directory}' не знайдена.")
        return

    initial_size_mb = get_dir_size(directory) / (1024 * 1024)
    print(f"📊 Початковий розмір папки: {initial_size_mb:.2f} MB")

    # Шукаємо тільки .webp файли
    queue = []
    for root, _, files in os.walk(directory):
        for f in files:
            path = Path(root) / f
            if path.suffix.lower() == '.webp':
                queue.append(path)
    
    total_files = len(queue)
    if total_files == 0:
        print("✅ Файлів .webp не знайдено.")
        return

    print(f"🚀 Починаю перетискання {total_files} файлів WebP (20 процесів)...")
    start_time = time.time()

    with Pool(processes=20) as pool:
        processed = 0
        total_old_size = 0
        total_new_size = 0
        
        for old_sz, new_sz, success in pool.imap_unordered(recompress_webp, queue):
            processed += 1
            total_old_size += old_sz
            total_new_size += new_sz
            
            if processed % 10 == 0 or processed == total_files:
                elapsed = time.time() - start_time
                rem = (elapsed / processed) * (total_files - processed)
                print(f"📈 Прогрес: [{processed}/{total_files}] | Залишилось: {int(rem//60)}хв {int(rem%60)}с")

    final_size_mb = get_dir_size(directory) / (1024 * 1024)
    duration = time.time() - start_time
    reduction = 100 - (final_size_mb / initial_size_mb * 100) if initial_size_mb > 0 else 0

    print(f"\n--- ФІНАЛЬНИЙ ЗВІТ ---")
    print(f"⏱️ Час виконання: {int(duration // 60)}хв {int(duration % 60)}с")
    print(f"📉 Розмір ДО: {initial_size_mb:.2f} MB")
    print(f"✨ Розмір ПІСЛЯ: {final_size_mb:.2f} MB")
    print(f"🔥 Реальне стиснення: {reduction:.1f}%")
    print(f"----------------------")

if __name__ == "__main__":
    # Вкажіть шлях до папки зі статикою
    run_recompression("static")