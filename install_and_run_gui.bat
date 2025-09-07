@echo off
chcp 65001 >nul
title Установка и запуск GUI компрессора

cd /d "C:\PY\image_compressor"

echo ===== Проверка виртуального окружения =====

if not exist ".venv\Scripts\activate.bat" (
    echo Создаем виртуальное окружение...
    python -m venv .venv
    if errorlevel 1 (
        echo ОШИБКА: Не удалось создать виртуальное окружение!
        pause
        exit /b 1
    )
)

echo ===== Активация виртуального окружения =====
call .venv\Scripts\activate

echo ===== Установка зависимостей =====
pip install --upgrade pip
pip install -r requirements.txt

if errorlevel 1 (
    echo ОШИБКА: Не удалось установить зависимости!
    pause
    exit /b 1
)

echo ===== Запуск GUI =====
python gui_main.py

echo.
echo Программа завершена.
pause
