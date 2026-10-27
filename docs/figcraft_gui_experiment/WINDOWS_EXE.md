---
id: ic-windows-exe-running
title: "Windows x64: самостоятельный ImageCompressorV2.exe"
kind: guide
status: accepted
created: "2026-10-23"
updated: "2026-10-23"
areas: [packaging, windows, pyside6, usage]
summary: "Double-click запуск, отдельная pinned сборка и проверки именно frozen EXE без внешнего Python."
language: ru
source_revision: "r2"
---

# Готовый EXE

Готовый **PySide6 GUI v2 в самостоятельном Windows EXE**: предыдущий `dist/windows-pyside6/20261023-candidate-02/ImageCompressorV2.exe` (56 977 108 bytes) получил независимый технический и визуальный ACCEPT и теперь `superseded` (артефакт в Recycle Bin); текущая курированная сборка `20261028-candidate-03` независимо принята exact-byte 2026-10-28 — точные байты/overlay/границы в [release record](../releases/windows-pyside6-20261028-candidate-03.md). Legacy PyQt6 GUI и его build/launcher'ы удалены из рабочей копии 2026-10-23→2026-10-28 (история в Git). Точный SHA-256, авторские/независимые проверки и пределы принятия прежнего бинарника — в [EXE verification](05-windows-exe-verification.md). История прежнего source/wheel ACCEPT — в [REPORT](REPORT.md); он сам по себе не принимал бинарник. Oracle [план](04-windows-exe-plan.md) сохранён без переименования его исследования в runtime PASS.

1. Откройте указанный в verification `dist/windows-pyside6/<build-id>/ImageCompressorV2.exe` двойным щелчком. Пользователю готового EXE **не требуется устанавливать Python, Qt или кодеки**.
2. One-file EXE можно скопировать один в каталог с пробелами/Unicode. Соседние BUILD-INFO/README/notices нужны для provenance/лицензий, не для запуска. Не путать с возможным onedir fallback: у него обязательный `_internal` и portable ZIP, один EXE из него не переносим.
3. Нужны Windows x64, обычные системные DLL/Segoe UI, writable user TEMP и поддерживаемая локальная файловая система для create-only hard link. При старте one-file распаковывает своё содержимое в `_MEI…` внутри TEMP; при нормальном закрытии bootloader удаляет этот каталог. Первый старт может быть медленнее; это не обещание запуска без временных файлов.
4. Не запускайте elevated и не отключайте Defender/SmartScreen. Это локальный **неподписанный** artifact, не installer/публичный release. Если Windows блокирует запуск, сохраните отказ для проверки, не обходите системную защиту ради PASS.

Использование интерфейса и ограничения — [RUNNING](RUNNING.md). JPEG/WebP/HEIF/AVIF показываются по реальным capability probes. Удаление исходников постоянно disabled/unchecked; overwrite, обещание меньшего файла и мгновенная остановка native codec отсутствуют. EXE не расширяет принятую image policy и crash-durability guarantees.

# Собрать из исходников

Требуется **CPython 3.14.2 x64 на Windows** у сборщика, не у пользователя EXE. `build_exe.bat` удалён вместе с legacy PyQt6-маршрутом. Не пересоздавайте `.venv` или принятую PySide среду; для этой задачи выделена только `.agent-work/windows-exe/build-venv`. Все команды ниже — PowerShell из корня проекта.

```powershell
$Root = (Get-Location).Path
$Work = Join-Path $Root '.agent-work/windows-exe'
$EnvDir = Join-Path $Work 'build-venv'
# Только если новой build-среды ещё нет:
& "$Root/.venv/Scripts/python.exe" -I -B -m venv $EnvDir
$Python = Join-Path $EnvDir 'Scripts/python.exe'
$Setup = Join-Path $Work ('setup-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
New-Item -ItemType Directory $Setup -ErrorAction Stop
$env:TEMP = $Setup
$env:TMP = $Setup
$env:TMPDIR = $Setup
$env:PIP_CACHE_DIR = Join-Path $Work 'pip-cache'
$Requirements = Join-Path $Root 'tools/windows_exe/requirements-win64.txt'
$Wheelhouse = Join-Path $Work 'wheelhouse'
& $Python -I -B -m pip download --only-binary=:all: -r $Requirements --dest $Wheelhouse
& $Python -I -B -m pip install --no-index --find-links $Wheelhouse -r $Requirements
& $Python -I -B -m pip check
$BuildId = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
& $Python -I -B "$Root/tools/windows_exe/build.py" --build-id $BuildId
```

Остановитесь при любом ненулевом exit; команды не должны продолжаться как будто сборка успешна. Повтор установки допустим только в новой build-среде; для другого dependency набора нужны новые фиксация и qualification, не молчаливый upgrade. Сохраняется hash каждого использованного wheel. Wrapper сам ничего не устанавливает.

`build.py` работает и из другого cwd с абсолютным путём к script. Он проверяет платформу/версию/pins/no-PyQt, snapshot-ит только runtime sources и recipe, использует official hooks и RECORD-owned HEIF DLL, создаёт свежие `.agent-work/windows-exe/builds/<build-id>/` и `dist/windows-pyside6/<build-id>/`. Занятый build-id отвергается, старые outputs не чистятся. Нет UPX/strip, глобальных QT/PATH settings или копирования всего Qt/site-packages/design/tests. `BUILD-INFO.json` содержит exact input/wheel hashes, argv, Python/dependency versions, исходный HEAD+delta и EXE hash. Recipe воспроизводим; bit-for-bit идентичность двух пересборок не обещана. Принятый EXE сохраняется без пересборки: его BUILD-INFO описывает исходный snapshot, а не более поздний docs-коммит. После приёмки меняются только разрешённые документы; runtime source/data, recipe/spec/requirements не меняются. README входит в provenance snapshot, но не в runtime payload EXE; его более поздняя редакция отдельно проверяется affected wheel/package test и не приписывается прежнему build.

Актуальный spec кладёт в frozen-поставку `tokens.json` и **все** `gui_pyside6_v2/assets/*.svg`; `verify_archive()` fail-closed требует каждый ассет и `python314.dll`, а `denied` точно отсекает legacy/deletion-имена (`gui/`, `classes`, `gui_main`, `image_compressor._windows_deletion`), не трогая `gui_pyside6_v2/`. Frozen driver в том же прогоне проверяет `QSvgRenderer.isValid()` для каждого SVG и отсутствие legacy/deletion-модулей в `sys.modules`.

# Курированная сборка `68b7dc5` + overlay

Новый EXE собирается **не из HEAD**: HEAD содержит принятый native-frame `theme.py`, но также непринятый deletion-WIP. Курированный источник — detached git-worktree на `68b7dc5` (pre-deletion, controls+packaging) + точечный overlay: `gui_pyside6_v2/theme.py` из HEAD, `pyproject.toml`/`README.md` из рабочего дерева, `tools/windows_exe/*` из исправленного packaging. `image_compressor/**` берётся из `68b7dc5` — `_windows_deletion.py` в input-set не входит. Worktree/junctions — обратимая staging-операция без ветки, reset или истории.

```powershell
$Root = 'C:\PY\image_compressor'
$BuildId = '20261028-candidate-03'   # фиксируется ДО запуска; занятый id не переиспользовать
$Stage = Join-Path $Root ".agent-work/windows-exe/staging/$BuildId/root"
New-Item -ItemType Directory -Force -Path (Split-Path $Stage) | Out-Null
git -C $Root worktree add --detach $Stage 68b7dc5
New-Item -ItemType Directory -Force -Path (Join-Path $Stage 'dist') | Out-Null
New-Item -ItemType Junction -Path (Join-Path $Stage 'dist/windows-pyside6') -Target (Join-Path $Root 'dist/windows-pyside6')
New-Item -ItemType Junction -Path (Join-Path $Stage '.agent-work') -Target (Join-Path $Root '.agent-work')
Copy-Item -Force (Join-Path $Root 'gui_pyside6_v2/theme.py') (Join-Path $Stage 'gui_pyside6_v2/theme.py')
Copy-Item -Force (Join-Path $Root 'pyproject.toml') $Stage
Copy-Item -Force (Join-Path $Root 'README.md') $Stage
Copy-Item -Force -Recurse (Join-Path $Root 'tools/windows_exe/*') (Join-Path $Stage 'tools/windows_exe')
& "$Root/.agent-work/windows-exe/build-venv/Scripts/python.exe" -I -B "$Stage/tools/windows_exe/build.py" --build-id $BuildId
```

`BUILD-INFO.source_head` обязан быть `68b7dc5…`; `source_delta` — ровно overlay. `executable`/`build_work` записываются в staging-виде, а canonical пути — `dist/windows-pyside6/<build-id>/` и `.agent-work/windows-exe/builds/<build-id>/` через junction (тот же файл: совпадают bytes/hash). README/pyproject входят в input-set, поэтому все их правки выполняются **до** сборки и после неё не меняются. При отказе worktree/junction, падении сборки, неверном `source_head`, legacy/deletion-входе или красном gate — остановиться, сохранить evidence, не пересобирать на месте. Curated-source receipt (`base commit`, worktree, `git status --porcelain`, хеши overlay, EXE hash/bytes) сохраняется в `.agent-work/windows-exe/builds/<build-id>/curated-source.json`.

Внешний `notices/` и встроенный `licenses/` сохраняют тексты применимых зависимостей, включая CPython, Qt/PySide/shiboken, Pillow, HEIF/AVIF providers и PyInstaller bootloader exception. Это не отдельная юридическая сертификация публикации бинарника.

# Проверить тот же artifact

Назначьте **свои свежие** TEMP/TMP/TMPDIR/caches/basetemp под `.agent-work/windows-exe/` до collection. Внешние tests используют старый tooling interpreter, но никогда не предоставляют его пакеты дочернему EXE. Не собирайте PyQt/PySide suites вместе.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
$env:IC_FROZEN_EXE = (Resolve-Path "$Root/dist/windows-pyside6/$BuildId/ImageCompressorV2.exe").Path
& "$Root/.venv/Scripts/python.exe" -B -m pytest -p pytest_timeout -p no:cacheprovider tests_windows_exe -q --basetemp "$Setup/pytest"
```

Нет fallback на первый найденный EXE: отсутствие явного `IC_FROZEN_EXE` даёт FAIL, не skip. Внешний runner копирует только EXE в собственный новый Unicode/space каталог, запускает `.exe` напрямую с пустым cwd, Windows-only PATH, fresh TEMP/profile и без inherited Python/Qt/venv/`_PYI_*`. Он наблюдает только собственные HWND/PID, обычное no-argument окно закрывает WM_CLOSE, проверяет parent/child и extraction teardown. На timeout — FAIL и cleanup только собственного Job Object/tree, не kill-by-image-name.

Runner отдельно проверяет **actual bootloader и видимый Qt child**: TokenIsElevated=False и Medium integrity (RID8192). Если сам harness уже elevated, он не запускает EXE с этим токеном: использует только свой linked limited token либо собственный новый LUA restricted token с пониженным Medium integrity через CreateProcessAsUserW. Чужие процессы/tokens, credentials, изменение UAC/ACL или отключение защит не нужны. Отсутствие безопасного способа создать non-elevated child — FAIL, не повод снять assertion. Это ограниченный standalone-host, не доказательство на другом аккаунте/машине.

Встроенный **opt-in** режим `ImageCompressorV2.exe --packaging-check <ABSOLUTE_NEW_OUTPUT_DIR>` предназначен лишь для synthetic qualification. Каталог должен отсутствовать, parent существовать и не быть reparse/symlink; runtime/EXE directory не подходят. Unknown/invalid args отказывают без fixtures. Без flag driver не запускается. Нет произвольных scripts/config/requests, пользовательских изображений или network режима.

Режим использует один QApplication и настоящий GUI main/event loop, controls/add_paths/Start/API workers: 4 codec readbacks, no-clobber повтор WebP, good+corrupt partial и шесть RU/EN/KK × light/dark PNG. Receipt появляется как success только после реальных результатов и нормального выхода event loop; внешний тест самостоятельно проверяет outputs/source hashes, provenance и teardown. Просмотр PNG человеком/моделью и независимый Reviewer verdict — отдельные обязанности, не следствие pytest PASS.

Независимо выполнены22 новых packaging теста,4 адресных PySide и2 legacy packaging selector без skips, статические/doc gates и просмотр шести собственных frozen PNG. Отдельный внешний watchdog удерживал native identities/handles bootloader и Qt child; штатные запуски завершились без оставшихся процессов/extraction. Контроль намеренного timeout правильно дал failure и завершил только собственные процессы; оставшийся тестовый `_MEI` после forced kill не является успешным cleanup или crash-durability гарантией.

Граница проверки: Windows 11 x64/local NTFS на текущем standalone-host с исключёнными из lookup внешними runtime packages. При elevated harness использован собственный reduced-rights Medium child; это не новая standard-user logon session и не другой аккаунт. Чистая unrelated VM/Windows10/ARM/другие OS, все DPI, signing/SmartScreen/release qualification, физические OS-dialog/drop и screen reader этим не сертифицируются.
