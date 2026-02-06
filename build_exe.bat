@echo off
chcp 65001 >nul
echo ================================================
echo   Сборка ImageCompressorGUI в EXE
echo ================================================
echo.

REM Проверка виртуального окружения
if not exist ".venv\Scripts\pyinstaller.exe" (
    echo ❌ Виртуальное окружение не найдено или PyInstaller не установлен!
    echo.
    echo Запустите сначала:
    echo   uv venv
    echo   .\.venv\Scripts\Activate.ps1
    echo   uv pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo ✓ Виртуальное окружение найдено
echo.

REM Очистка старых файлов
if exist "dist\ImageCompressorGUI.exe" (
    echo 🗑️  Удаление старого exe-файла...
    del /F /Q "dist\ImageCompressorGUI.exe" 2>nul
)

echo.
echo 🔨 Начинаю сборку...
echo.

REM Сборка через PyInstaller
.venv\Scripts\pyinstaller.exe gui_compressor.spec --clean

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ================================================
    echo   ✅ Сборка завершена успешно!
    echo ================================================
    echo.
    
    if exist "dist\ImageCompressorGUI.exe" (
        for %%I in ("dist\ImageCompressorGUI.exe") do (
            set size=%%~zI
            set /a sizeMB=%%~zI/1048576
        )
        echo 📦 Файл: dist\ImageCompressorGUI.exe
        echo 📊 Размер: !sizeMB! МБ
        echo.
        echo Хотите открыть папку с exe-файлом? (Y/N)
        choice /C YN /N /M ">"
        if !ERRORLEVEL! EQU 1 (
            explorer /select,"dist\ImageCompressorGUI.exe"
        )
    )
) else (
    echo.
    echo ================================================
    echo   ❌ Ошибка при сборке!
    echo ================================================
    echo.
    echo Проверьте логи выше для деталей.
)

echo.
pause
