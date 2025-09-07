"""
Вспомогательные функции для GUI компрессора изображений.
"""

import os
from typing import List, Tuple
from pathlib import Path


def get_image_files_from_paths(file_paths: List[str]) -> List[str]:
    """
    Получает список всех изображений из переданных путей (файлы и папки).
    
    Args:
        file_paths: Список путей к файлам и папкам
        
    Returns:
        Список путей к файлам изображений
    """
    image_files = []
    supported_extensions = (".jpg", ".jpeg", ".png", ".heic", ".heif", ".avif")
    
    for file_path in file_paths:
        if os.path.isfile(file_path):
            # Проверяем, что это изображение
            if file_path.lower().endswith(supported_extensions):
                image_files.append(file_path)
        elif os.path.isdir(file_path):
            # Сканируем папку рекурсивно
            for root, _, files_in_dir in os.walk(file_path):
                for file in files_in_dir:
                    if file.lower().endswith(supported_extensions):
                        full_path = os.path.join(root, file)
                        image_files.append(full_path)
    
    return image_files


def validate_write_permissions(file_path: str) -> bool:
    """
    Проверяет права на запись в директорию файла.
    
    Args:
        file_path: Путь к файлу
        
    Returns:
        True если есть права на запись, False иначе
    """
    try:
        directory = Path(file_path).parent
        return os.access(directory, os.W_OK)
    except Exception:
        return False


def format_file_size(size_bytes: int) -> str:
    """
    Форматирует размер файла в человекочитаемый вид.
    
    Args:
        size_bytes: Размер в байтах
        
    Returns:
        Отформатированная строка размера
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def get_savings_info(original_size: int, compressed_size: int) -> Tuple[int, float]:
    """
    Вычисляет экономию места при сжатии.
    
    Args:
        original_size: Исходный размер в байтах
        compressed_size: Сжатый размер в байтах
        
    Returns:
        Кортеж (экономия в байтах, процент экономии)
    """
    saved_bytes = original_size - compressed_size
    saved_percent = (saved_bytes / original_size) * 100 if original_size > 0 else 0
    
    return saved_bytes, saved_percent
