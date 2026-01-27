# Использование UV для управления проектом

## Установка UV

```powershell
# Windows
pip install uv
# или через pipx
pipx install uv
```

## Быстрый старт с UV

```powershell
# Создать виртуальное окружение
uv venv

# Активировать окружение
.\venv\Scripts\Activate.ps1  # PowerShell
# или
.\venv\Scripts\activate.bat  # CMD

# Установить зависимости из pyproject.toml
uv pip install -e .

# Или установить только runtime зависимости
uv pip install -r requirements.txt

# Установить с dev зависимостями
uv pip install -e ".[dev]"
```

## Управление зависимостями

```powershell
# Добавить новую зависимость
uv pip install <package>

# Обновить зависимости
uv pip install --upgrade -r requirements.txt

# Создать lock-файл (freeze)
uv pip freeze > requirements_freeze.txt

# Синхронизировать окружение с pyproject.toml
uv pip sync requirements.txt
```

## Сборка exe-файла

```powershell
# Активировать окружение
.\venv\Scripts\Activate.ps1

# Собрать exe
pyinstaller gui_compressor.spec --clean

# Результат в ./dist/ImageCompressorGUI.exe
```

## Преимущества UV

- ⚡ **Скорость**: В 10-100 раз быстрее pip
- 🔒 **Надежность**: Детерминированная установка пакетов
- 🎯 **Совместимость**: Полная совместимость с pip и PyPI
- 📦 **Кэширование**: Умное кэширование пакетов

## Структура проекта

```
image_compressor/
├── gui/                    # GUI модули
│   ├── __init__.py
│   ├── main_window.py
│   ├── widgets.py
│   ├── worker.py
│   ├── styles.py
│   └── utils.py
├── classes.py              # Основные классы
├── gui_main.py            # Точка входа GUI
├── pyproject.toml         # Конфигурация проекта (UV)
├── requirements.txt       # Зависимости (минимальные)
├── requirements_freeze.txt # Полный freeze (для воспроизводимости)
├── gui_compressor.spec    # PyInstaller конфигурация
└── .gitignore
```

## Разработка

```powershell
# Запуск GUI версии
python gui_main.py

# Форматирование кода (если установлен black)
black .

# Линтинг (если установлен ruff)
ruff check .
```

## Поддерживаемые форматы

### Входные форматы

- JPEG (.jpg, .jpeg)
- PNG (.png)
- **WebP (.webp)** ⭐ Новый!
- HEIC (.heic)
- HEIF (.heif)
- AVIF (.avif)

### Выходные форматы

- WebP (по умолчанию)
- PNG
- AVIF
- JPEG

## Примечания

- Используйте `requirements.txt` для основных зависимостей
- `requirements_freeze.txt` содержит полный снимок окружения
- `pyproject.toml` - это современный стандарт конфигурации Python проектов
- Exe-файл собирается как **один файл** без консоли
- Поддерживается drag & drop файлов и папок
