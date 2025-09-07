"""
GUI пакет для компрессора изображений.

Модули:
    main_window - главное окно приложения
    worker - рабочий поток для сжатия
    widgets - UI виджеты
    styles - CSS стили
    utils - вспомогательные функции
"""

import sys

from .main_window import ImageCompressorGUI
from .worker import CompressionWorker
from .widgets import DropZone, QualityWidget, FormatWidget, FileOptionsWidget

def main():
    """Главная функция запуска GUI приложения."""
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)

    # Настройка темы приложения
    app.setStyle("Fusion")

    # Создание и показ главного окна
    window = ImageCompressorGUI()
    window.show()

    # Запуск приложения
    sys.exit(app.exec())

__all__ = ['ImageCompressorGUI', 'CompressionWorker', 'DropZone', 'QualityWidget', 'FormatWidget', 'FileOptionsWidget', 'main']
