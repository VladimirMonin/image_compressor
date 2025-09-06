"""
Простой тест для проверки GUI компрессора.
Запускает GUI и показывает инструкции для тестирования.
"""

import sys
import os


def main():
    print("=" * 60)
    print("🧪 ТЕСТ GUI КОМПРЕССОРА ИЗОБРАЖЕНИЙ")
    print("=" * 60)

    # Проверяем зависимости
    try:
        import PyQt6

        print("✅ PyQt6 установлен")
    except ImportError:
        print("❌ PyQt6 не найден! Установите: pip install PyQt6")
        return

    try:
        from classes import ImageCompressor

        print("✅ Модуль classes доступен")
    except ImportError:
        print("❌ Модуль classes не найден!")
        return

    # Проверяем файлы
    current_dir = os.path.dirname(os.path.abspath(__file__))
    gui_file = os.path.join(current_dir, "gui.py")

    if os.path.exists(gui_file):
        print("✅ Файл gui.py найден")
    else:
        print("❌ Файл gui.py не найден!")
        return

    print("\n📋 ИНСТРУКЦИИ ДЛЯ ТЕСТИРОВАНИЯ:")
    print("1. Перетащите несколько PNG/JPG файлов в зону")
    print("2. Перетащите еще файлы - они должны добавиться")
    print("3. Проверьте счетчик в заголовке")
    print("4. Выберите качество и формат")
    print("5. Запустите сжатие")
    print("6. Проверьте лог на дубликаты и экономию места")
    print("7. Проверьте, что файлы созданы в той же папке")
    print("8. Используйте 'Очистить очередь' для сброса")

    print("\n🚀 Запуск GUI...")

    # Запускаем GUI
    try:
        from gui import main as gui_main

        gui_main()
    except Exception as e:
        print(f"❌ Ошибка запуска GUI: {e}")


if __name__ == "__main__":
    main()
