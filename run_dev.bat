@echo off
REM Скрипт для запуска приложения в dev режиме через uv окружение
echo 🚀 Запуск Image Compressor (dev режим с uv)...
call .venv\Scripts\activate.bat
python gui_main.py
pause
