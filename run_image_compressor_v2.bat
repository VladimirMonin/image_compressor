@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

rem Канонический локальный релиз (build-id 20261028-candidate-05).
rem Launcher только открывает уже принятый EXE: ничего не устанавливает,
rem не собирает, не удаляет и не скачивает. Точные байты и границы:
rem docs/releases/windows-pyside6-20261028-candidate-05.md

set "IC_V2_EXE=%~dp0dist\windows-pyside6\20261028-candidate-05\ImageCompressorV2.exe"

if not exist "%IC_V2_EXE%" (
  echo Не найден принятый бинарник:
  echo   %IC_V2_EXE%
  echo Сборка, установка и скачивание не выполняются.
  echo Точные байты и границы: docs\releases\windows-pyside6-20261028-candidate-05.md
  exit /b 1
)

start "" "%IC_V2_EXE%"
exit /b 0
