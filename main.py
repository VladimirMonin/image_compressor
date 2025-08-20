"""
pip install pillow pillow-heif
"""

import os
from typing import Union
from PIL import Image
from pillow_heif import register_heif_opener

QUALITY: int = 30  # Можно настроить качество сжатия
OUTPUT_FORMAT = "WEBP"  # или "HEIF" - можно выбирать

def compress_image(input_path: str, output_path: str, format: str = OUTPUT_FORMAT) -> None:
    """
    Сжимает изображение и сохраняет его в выбранном формате.

    Args:
        input_path (str): Путь к исходному изображению.
        output_path (str): Путь для сохранения сжатого изображения.
        format (str): Формат сжатия ("WEBP" или "HEIF")

    Returns:
        None
    """
    with Image.open(input_path) as img:
        img.save(output_path, format, quality=QUALITY)
    print(f"Сжато: {input_path} -> {output_path}")


def process_directory(directory: str, format: str = OUTPUT_FORMAT) -> None:
    """
    Обрабатывает все изображения в указанной директории и её поддиректориях.

    Args:
        directory (str): Путь к директории для обработки.

    Returns:
        None
    """
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                input_path = os.path.join(root, file)
                extension = '.webp' if format == "WEBP" else '.heic'
                output_path = os.path.splitext(input_path)[0] + extension
                compress_image(input_path, output_path, format)

def main(input_path: str) -> None:
    """
    Основная функция программы. Обрабатывает входной путь и запускает сжатие изображений.

    Args:
        input_path (str): Путь к файлу или директории для обработки.

    Returns:
        None
    """
    if OUTPUT_FORMAT == "HEIF":
        register_heif_opener()
    
    input_path = input_path.strip('"')  # Удаляем кавычки, если они есть

    if os.path.exists(input_path):
        if os.path.isfile(input_path):
            print(f"Обрабатываем файл: {input_path}")
            extension = '.webp' if OUTPUT_FORMAT == "WEBP" else '.heic'
            output_path = os.path.splitext(input_path)[0] + extension
            compress_image(input_path, output_path, OUTPUT_FORMAT)
        elif os.path.isdir(input_path):
            print(f"Обрабатываем директорию: {input_path}")
            process_directory(input_path, OUTPUT_FORMAT)
    else:
        print("Указанный путь не существует")

if __name__ == "__main__":
    user_input: str = input("Введите путь к файлу или директории: ")
    main(user_input)