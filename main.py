"""
Многопроцессорная версия компрессора изображений.
Автоматически использует все доступные ядра процессора для ускорения обработки.

Зависимости:
pip install pillow pillow-heif pillow-avif-plugin
"""

import os
import time
import multiprocessing as mp
from typing import List, Tuple, Optional
from PIL import Image
from pillow_heif import register_heif_opener

# Импорт для поддержки AVIF
try:
    import pillow_avif
    AVIF_AVAILABLE = True
except ImportError:
    AVIF_AVAILABLE = False

# Конфигурация по умолчанию
QUALITY: int = 50
OUTPUT_FORMAT = "WEBP"  # "WEBP", "HEIF" или "AVIF"
SUPPORTED_FORMATS = ('.jpg', '.jpeg', '.png')
OUTPUT_EXTENSIONS = {"WEBP": ".webp", "HEIF": ".heic", "AVIF": ".avif"}


def compress_single_image(args: Tuple[str, str, str, int]) -> Optional[str]:
    """
    Сжимает одно изображение. Используется в многопроцессорной обработке.
    
    Args:
        args: Кортеж (input_path, output_path, format, quality)
        
    Returns:
        str: Сообщение о результате обработки или None при ошибке
    """
    input_path, output_path, format_type, quality = args
    
    try:
        # Инициализация кодеков в каждом процессе
        if format_type == "HEIF":
            register_heif_opener()
        elif format_type == "AVIF" and not AVIF_AVAILABLE:
            return f"ОШИБКА: AVIF не поддерживается для {input_path}"
            
        with Image.open(input_path) as img:
            img.save(output_path, format_type, quality=quality)
            
        return f"✓ Сжато: {os.path.basename(input_path)} -> {os.path.basename(output_path)}"
        
    except Exception as e:
        return f"✗ ОШИБКА при обработке {input_path}: {str(e)}"


def collect_image_files(input_path: str) -> List[str]:
    """
    Собирает все файлы изображений из указанного пути.
    
    Args:
        input_path: Путь к файлу или директории
        
    Returns:
        List[str]: Список путей к файлам изображений
    """
    image_files = []
    
    if os.path.isfile(input_path):
        if input_path.lower().endswith(SUPPORTED_FORMATS):
            image_files.append(input_path)
    elif os.path.isdir(input_path):
        for root, _, files in os.walk(input_path):
            for file in files:
                if file.lower().endswith(SUPPORTED_FORMATS):
                    image_files.append(os.path.join(root, file))
    
    return image_files


def prepare_compression_tasks(image_files: List[str], format_type: str, quality: int) -> List[Tuple[str, str, str, int]]:
    """
    Подготавливает задачи для многопроцессорной обработки.
    
    Args:
        image_files: Список путей к изображениям
        format_type: Формат вывода
        quality: Качество сжатия
        
    Returns:
        List[Tuple]: Список задач для pool.map
    """
    extension = OUTPUT_EXTENSIONS[format_type]
    tasks = []
    
    for input_path in image_files:
        output_path = os.path.splitext(input_path)[0] + extension
        tasks.append((input_path, output_path, format_type, quality))
    
    return tasks


def process_with_multiprocessing(input_path: str, format_type: str = OUTPUT_FORMAT, quality: int = QUALITY) -> None:
    """
    Многопроцессорная обработка изображений.
    
    Args:
        input_path: Путь к файлу или директории
        format_type: Формат вывода
        quality: Качество сжатия
    """
    print(f"🔍 Поиск изображений в: {input_path}")
    
    # Собираем все файлы изображений
    image_files = collect_image_files(input_path)
    
    if not image_files:
        print("❌ Не найдено изображений для обработки!")
        return
    
    print(f"📁 Найдено изображений: {len(image_files)}")
    
    # Подготавливаем задачи
    tasks = prepare_compression_tasks(image_files, format_type, quality)
    
    # Определяем количество процессов (все доступные ядра)
    num_processes = mp.cpu_count()
    print(f"🚀 Запуск обработки на {num_processes} ядрах процессора...")
    
    # Запуск многопроцессорной обработки
    start_time = time.time()
    
    with mp.Pool(processes=num_processes) as pool:
        # Используем imap для отображения прогресса
        results = []
        for i, result in enumerate(pool.imap(compress_single_image, tasks), 1):
            if result:
                print(f"[{i:4d}/{len(tasks)}] {result}")
            results.append(result)
    
    # Подсчет результатов
    successful = sum(1 for r in results if r and r.startswith("✓"))
    failed = sum(1 for r in results if r and r.startswith("✗"))
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    print("\n" + "="*60)
    print("📊 ОТЧЕТ О ОБРАБОТКЕ:")
    print(f"✅ Успешно обработано: {successful}")
    print(f"❌ Ошибок: {failed}")
    print(f"⏱️  Время обработки: {processing_time:.2f} секунд")
    print(f"⚡ Скорость: {len(image_files)/processing_time:.2f} файлов/сек")
    print("="*60)


def get_user_format_choice() -> str:
    """
    Запрашивает у пользователя выбор формата сжатия.
    
    Returns:
        str: Выбранный формат
    """
    print("\n📋 Выберите формат сжатия:")
    print("1. WEBP (.webp) - отличная совместимость и качество")
    print("2. HEIF (.heic) - высокая эффективность сжатия")
    
    if AVIF_AVAILABLE:
        print("3. AVIF (.avif) - новейший формат с максимальным сжатием")
        
    choice = input("\nВведите номер формата (1-3) или Enter для WEBP: ").strip()
    
    if choice == "2":
        return "HEIF"
    elif choice == "3" and AVIF_AVAILABLE:
        return "AVIF"
    else:
        return "WEBP"


def get_user_quality() -> int:
    """
    Запрашивает у пользователя качество сжатия.
    
    Returns:
        int: Качество сжатия (0-100)
    """
    while True:
        quality_input = input(f"\nВведите качество (0-100) или Enter для {QUALITY}: ").strip()
        
        if not quality_input:
            return QUALITY
            
        try:
            quality = int(quality_input)
            if 0 <= quality <= 100:
                return quality
            else:
                print("❌ Качество должно быть от 0 до 100!")
        except ValueError:
            print("❌ Введите корректное число!")


def main() -> None:
    """
    Основная функция программы с многопроцессорной обработкой.
    """
    print("🖼️  === МНОГОПРОЦЕССОРНЫЙ КОМПРЕССОР ИЗОБРАЖЕНИЙ ===")
    print("⚡ Автоматическое использование всех ядер процессора")
    
    # Выбор формата
    format_choice = get_user_format_choice()
    print(f"✅ Выбран формат: {format_choice}")
    
    # Выбор качества
    quality_choice = get_user_quality()
    print(f"✅ Установлено качество: {quality_choice}")
    
    # Ввод пути
    user_input = input("\n📂 Введите путь к файлу или директории: ").strip().strip('"')
    
    if not os.path.exists(user_input):
        print("❌ Указанный путь не существует!")
        return
    
    print(f"\n🎯 Параметры обработки:")
    print(f"   📁 Путь: {user_input}")
    print(f"   🎨 Формат: {format_choice}")
    print(f"   🔧 Качество: {quality_choice}")
    print(f"   💻 Процессов: {mp.cpu_count()}")
    
    # Запуск обработки
    process_with_multiprocessing(user_input, format_choice, quality_choice)
    
    input("\n✨ Обработка завершена! Нажмите Enter для выхода...")


if __name__ == "__main__":
    # Необходимо для корректной работы multiprocessing на Windows
    mp.freeze_support()
    main()