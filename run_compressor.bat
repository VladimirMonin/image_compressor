@echo off
chcp 65001 >nul
title Компрессор изображений

cd /d "C:\PY\image_compressor"

if not exist ".venv\Scripts\activate.bat" (
    echo ОШИБКА: Виртуальное окружение не найдено!
    pause
    exit /b 1
)

call .venv\Scripts\activate

if not exist "classes.py" (
    echo ОШИБКА: Файл classes.py не найден!
    pause
    exit /b 1
)

python main.py
pause
