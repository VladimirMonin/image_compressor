@echo off
chcp 65001 >nul
title Компрессор изображений - GUI

cd /d "C:\PY\image_compressor"

if not exist ".venv\Scripts\activate.bat" (
    echo ОШИБКА: Виртуальное окружение не найдено!
    pause
    exit /b 1
)

call .venv\Scripts\activate

if not exist "gui_main.py" (
    echo ОШИБКА: Файл gui_main.py не найден!
    pause
    exit /b 1
)

python gui_main.py
