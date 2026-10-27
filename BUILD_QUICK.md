> **Исторический материал (до command-first).** Актуальный GUI/EXE — [docs/releases/windows-pyside6-candidate-02.md](docs/releases/windows-pyside6-candidate-02.md); `dist/ImageCompressorGUI.exe` и `build_exe.bat` — legacy, не использовать для нового GUI.

# Быстрая сборка ImageCompressor в EXE

## Подготовка окружения

```powershell
# 1. Создать виртуальное окружение
python -m venv venv

# 2. Активировать
.\venv\Scripts\Activate.ps1

# 3. Установить зависимости
pip install -r requirements.txt
# или с UV (быстрее):
uv pip install -r requirements.txt
```

## Сборка EXE

```powershell
# Собрать в один exe-файл (без консоли)
pyinstaller gui_compressor.spec --clean
```

Результат: `dist\ImageCompressorGUI.exe` (~47 МБ)

## Возможности собранного приложения

✅ Один exe-файл - ничего больше не нужно  
✅ Drag & Drop файлов и папок  
✅ Поддержка WebP, HEIC, AVIF, PNG, JPEG  
✅ GUI на PyQt6  
✅ Без окна консоли  

## Тестирование

Запустите `dist\ImageCompressorGUI.exe` и перетащите на него изображения!
