"""
Новая точка входа для модульного GUI компрессора изображений.
"""

import sys
from PyQt6.QtWidgets import QApplication

from gui import ImageCompressorGUI


def main():
    """Главная функция запуска GUI приложения."""
    app = QApplication(sys.argv)

    # Настройка темы приложения
    app.setStyle("Fusion")

    # Создание и показ главного окна
    window = ImageCompressorGUI()
    window.show()

    # Запуск приложения
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
