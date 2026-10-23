"""
Вспомогательные функции для GUI компрессора изображений.
"""

import os
from pathlib import Path

from image_compressor import discover_inputs


def get_image_files_from_paths(file_paths: list[str]) -> list[str]:
    """
    Получает список всех изображений из переданных путей (файлы и папки).

    Args:
        file_paths: Список путей к файлам и папкам

    Returns:
        Список путей к файлам изображений
    """
    return [str(path) for path in discover_inputs(file_paths, recursive=True).paths]


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


def get_savings_info(original_size: int, compressed_size: int) -> tuple[int, float]:
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
