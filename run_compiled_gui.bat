@echo off
cd /d "%~dp0"
echo Запуск скомпилированной GUI версии компрессора изображений...
echo.
start dist\ImageCompressorGUI.exe
echo GUI версия запущена!
pause
