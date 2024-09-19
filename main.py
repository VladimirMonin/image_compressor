import os
import multiprocessing
from typing import List
from PIL import Image
from pillow_heif import register_heif_opener

QUALITY: int = 50  # Качество сжатия
FILE_THRESHOLD: int = 20  # Порог количества файлов для многопроцессорной обработки
MAX_PROCESSES: int = 20  # Максимальное количество процессов

def compress_image(input_path: str, output_path: str) -> None:
    """
    Сжимает изображение и сохраняет его в формате HEIF.

    Args:
        input_path (str): Путь к исходному изображению.
        output_path (str): Путь для сохранения сжатого изображения.
    """
    with Image.open(input_path) as img:
        img.save(output_path, "HEIF", quality=QUALITY)
    print(f"Сжато: {input_path} -> {output_path}")

def process_files(files: List[str]) -> None:
    """
    Обрабатывает список файлов.

    Args:
        files (List[str]): Список путей к файлам для обработки.
    """
    register_heif_opener()  # Регистрируем HEIF для каждого процесса
    for file in files:
        output_path = os.path.splitext(file)[0] + '.heic'
        compress_image(file, output_path)

def process_directory(directory: str) -> None:
    """
    Обрабатывает все изображения в указанной директории и её поддиректориях.

    Args:
        directory (str): Путь к директории для обработки.
    """
    files_to_process: List[str] = []
    # Собираем все подходящие файлы
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                files_to_process.append(os.path.join(root, file))
    
    if len(files_to_process) > FILE_THRESHOLD:
        # Используем многопроцессорную обработку для большого количества файлов
        num_processes = min(MAX_PROCESSES, multiprocessing.cpu_count())
        chunk_size = len(files_to_process) // num_processes
        chunks = [files_to_process[i:i + chunk_size] for i in range(0, len(files_to_process), chunk_size)]
        
        with multiprocessing.Pool(processes=num_processes) as pool:
            pool.map(process_files, chunks)
    else:
        # Обрабатываем файлы последовательно
        process_files(files_to_process)

def main(input_path: str) -> None:
    """
    Основная функция программы. Обрабатывает входной путь и запускает сжатие изображений.

    Args:
        input_path (str): Путь к файлу или директории для обработки.
    """
    input_path = input_path.strip('"')
    
    if os.path.exists(input_path):
        if os.path.isfile(input_path):
            # Обработка одного файла
            print(f"Обрабатываем файл: {input_path}")
            output_path = os.path.splitext(input_path)[0] + '.heic'
            compress_image(input_path, output_path)
        elif os.path.isdir(input_path):
            # Обработка директории
            print(f"Обрабатываем директорию: {input_path}")
            process_directory(input_path)
    else:
        print("Указанный путь не существует")

if __name__ == "__main__":
    multiprocessing.freeze_support()  # Для корректной работы на Windows
    user_input: str = input("Введите путь к файлу или директории: ")
    main(user_input)