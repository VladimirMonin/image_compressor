"""
Точка входа для GUI версии компрессора изображений.
Простой запуск графического интерфейса.
"""

if __name__ == "__main__":
    try:
        from gui import main

        main()
    except ImportError as e:
        print("❌ Ошибка импорта GUI модулей!")
        print("Убедитесь, что установлены зависимости: pip install PyQt6")
        print(f"Подробности: {e}")
        input("Нажмите Enter для выхода...")
