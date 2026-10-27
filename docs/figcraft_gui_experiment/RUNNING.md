---
id: ic-pyside6-running
title: "Запуск отдельного PySide6 GUI v2"
kind: guide
status: accepted
created: "2026-10-23"
updated: "2026-10-28"
areas: [gui, pyside6, usage]
summary: "Изолированная optional установка, запуск, synthetic проверки и безопасная семантика экспериментального интерфейса."
language: ru
source_revision: "r4"
---

# Отдельный запуск

`gui_pyside6_v2/` — **канонический GUI продукта**; legacy PyQt6 GUI и compatibility facade удалены из рабочей копии 2026-10-28 (история в Git), не рекомендуемый путь больше не поставляется. Python distribution остаётся `image-compressor`; bare install требует только Pillow. Новый optional extra — `gui-pyside6` с PySide6 **6.12+ / <7**. Квалифицированная автором и независимым Reviewer среда: Windows 11/local NTFS, Python 3.14.2, PySide6/Qt 6.12.0. Технический и визуальный ACCEPT — в [REPORT](REPORT.md); другие ОС/версии, все DPI и физические OS-dialog/drop не квалифицированы.

PowerShell, корень проекта; среда **отдельная от старой `.venv`**:

```powershell
$EnvDir = ".agent-work\figcraft-gui-experiment\pyside6-venv"
# Только если этой экспериментальной среды ещё нет:
python -m venv $EnvDir
& "$EnvDir\Scripts\python.exe" -m pip install ".[gui-pyside6,codecs]"
& "$EnvDir\Scripts\python.exe" -m gui_pyside6_v2
```

`codecs` необязателен для JPEG/WebP; наличие optional provider не заменяет probe. Для разработки добавьте `dev` в extra. Legacy extra `gui`/PyQt6 удалён из `pyproject.toml`; не загружайте PyQt6 и PySide6 в один процесс. Отсутствующий PySide даёт короткую инструкцию установки и exit2 без traceback.

Обычная non-editable установка wheel тоже поддержана: `python -m pip install "image_compressor-1.0.0-py3-none-any.whl[gui-pyside6]"`, затем тот же `python -m gui_pyside6_v2` из любого рабочего каталога. Имя wheel здесь — имя полученного candidate artifact, не опубликованный релиз. Автор и независимый Reviewer отдельно проверили installed-wheel import из `site-packages`, настоящий module entry/event loop и outputs **вне source cwd**, не только editable import. Итог и точная граница — в [REPORT](REPORT.md).

Старый PyQt6-запуск и его launcher'ы retired вместе с source (история в Git); в рабочей копии нет `gui_main.py`.

# Без Python: отдельный Windows EXE

Курированная сборка `20261028-candidate-03` собрана из базы `68b7dc5` + принятого native-frame `theme.py` + исправленного packaging и **независимо принята exact-byte** 2026-10-28. Точные байты, overlay и границы — [release record](../releases/windows-pyside6-20261028-candidate-03.md). Ранее принятый `candidate-02` переведён в `superseded`, его артефакты перемещены в Recycle Bin. Его можно открыть без установки Python/Qt/кодеков; инструкция и пределы — [WINDOWS_EXE](WINDOWS_EXE.md), историческая exact-byte проверка прежнего бинарника — [05-windows-exe-verification](05-windows-exe-verification.md). Это Windows11 x64/local NTFS standalone-host с собственным non-elevated Medium child, не новый аккаунт/чистая unrelated machine и не все платформы/DPI. Прежний source/wheel ACCEPT не подменяется новым решением; общий GUI/API и ограничения ниже не меняются. Старый `build_exe.bat` удалён как legacy.

## Исправленные контролы — пока только source-срез

Стрелки числовых полей/списков и unchecked/checked/disabled/focus флажки исправлены в существующем владельце темы и получили отдельный [технический и визуальный ACCEPT](06-controls-verification.md). Полные области стрелок действительно кликабельны, числа имеют внутренний отступ, открытые списки согласованы с Light/Dark. RU/EN/KK, компоновка, resize gates и quality-slider сохраняются. Проверены32 адресных cases и2 дополнительных native source cases;8 HiDPI cases — повтор подмножества, не новые уникальные tests.

**Курированный EXE `20261028-candidate-03` включает эти исправления:** база `68b7dc5` уже содержит control-fix, а исправленный spec кладёт все 13 `assets/*.svg` в frozen-поставку (проверяется fail-closed recipe и frozen driver). Прежний `candidate-02` этих исправлений не содержал и остаётся fallback до ACCEPT нового EXE. Текущее изменение оформления не включает рабочее удаление исходников или новый человеческий журнал/результаты. Deletion-WIP в HEAD не входит в собранный EXE: disabled deletion там по-прежнему не работающий switch. Installed/frozen proof прежней версии не переносится автоматически на новые assets.

# Что делать в окне

1. «Добавить файлы» допускает один/несколько файлов; «Выбрать папку» — отдельный directory picker. Локальные file URLs можно перетащить в queue card. Web URLs не загружаются.
2. «Включая подпапки» default True относится к **следующему добавлению папки**, не пересканирует уже раскрытую очередь. Discovery и display-only stat выполняются в worker. Ошибки добавления, ignored/duplicates показаны отдельно от доступных файлов; при valid subset обрабатывается только явно показанная доступная очередь.
3. Выберите JPEG/WebP/HEIF/AVIF, quality **0..100** (default80), при необходимости resize (default off; реальные значения 1920×1080 при включении). Пропорции сохраняются, увеличения/crop нет. Недоступный encoder отключён и имеет reason.
4. Постфикс default `_compressed`, **только для совпадающей suffix-family**. Явная пустая строка не подменяется default. Уже занятое имя даёт ошибку, не overwrite/auto-numbering.
5. «Начать» фиксирует один immutable request и запускает один batch публичного API. До настоящего окончания thread нельзя менять очередь/параметры или начать второй batch. Тема и язык RU/EN/KK меняются без потери ввода/операции.
6. «Остановить» — кооперативный запрос, не kill/rollback. Текущий native codec может ещё работать; готовые файлы остаются. Закрытие во время worker ждёт его окончания **без блокировки event loop**. Жёсткий timeout кодека не реализован.
7. Итог отличает succeeded/failed/partial/rejected/cancelled; published считается отдельно. Опубликованный, но не проверенный файл не зелёный success. Локальные пути/артефакты/коды доступны в «Подробностях» и tooltips строк. После ошибки проверьте результаты перед повтором.
8. «Очистить очередь» очищает только UI — не source/output. Повторный Start — новая операция; прошлые outputs могут дать OUTPUT_EXISTS.

**В собранном EXE и на базе `68b7dc5` удаление исходников недоступно.** Видимый disabled/unchecked control и постоянное объяснение не являются реализованным switch. Вызов backend там получает delete_original=False, и API True отвергается до эффектов. В текущем HEAD есть непринятый WIP удаления: он не входит ни в курированную базу/EXE, ни в принятую границу и не должен использоваться как рабочая функция ([release record](../releases/windows-pyside6-20261028-candidate-03.md)). Это явный gap исходного ТЗ, не скрытое удаление.

Минимальный useful размер — **900×640 logical px**, обычный — 1120×760. На minimum таблица и форма прокручиваются; footer и safety explanation остаются видны. Имя файла намеренно elide, полный путь — в tooltip. Log read-only, максимум500 blocks, без путей/постфикса/raw exceptions; локальный result pane — отдельный разрешённый канал. Постоянного журнала, telemetry или CLI-subprocess backend нет.

# Самостоятельная синтетическая проверка

Создайте новый project-local каталог и PNG без личных изображений:

```powershell
$Python = (Resolve-Path "$EnvDir\Scripts\python.exe").Path
$Probe = ".agent-work\synthetic-" + (Get-Date -Format "yyyyMMdd-HHmmss")
New-Item -ItemType Directory $Probe -ErrorAction Stop
& $Python -c "from PIL import Image; import sys; Image.new('RGB',(400,300),(20,140,200)).save(sys.argv[1])" "$Probe\synthetic.png"
```

Добавьте `synthetic.png`; выберите WebP, resize192×108 и Start. Ожидается новый `synthetic.webp` 144×108 рядом с исходником; PNG остаётся. Повтор даст OUTPUT_EXISTS. Для same-format используйте созданный WebP: с `_small` получится отдельный `synthetic_small.webp`, с пустым postfix — INPUT_OUTPUT_CONFLICT. Не используйте личные фотографии для fault/cancel эксперимента.

# Автоматизированные проверки

Перед collection назначьте **свои свежие** TEMP/TMP/TMPDIR и caches/basetemp внутри `.agent-work/`; third-party autoload выключен. Не используйте уже занятый evidence root.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
& "$EnvDir\Scripts\python.exe" -B -m pytest -p pytest_timeout -p no:cacheprovider tests_pyside6_v2 -q
& "$EnvDir\Scripts\python.exe" -B -m ruff check gui_pyside6_v2 tests_pyside6_v2
& "$EnvDir\Scripts\python.exe" -B -m mypy --follow-imports=silent gui_pyside6_v2
# Другой interpreter/process; не collect оба suite вместе:
.\.venv\Scripts\python.exe -B -m pytest -p pytest_timeout -p no:cacheprovider tests -q
```

GUI strict mypy проверяет все новые модули; `--follow-imports=silent` не переоткрывает неизменённое ядро под новыми Pillow13 stubs. Strict gate ядра выполняется отдельно в сохранённой legacy среде. В Windows offscreen renderer нет автоматического system-font enumeration: только test helpers подключают установленные Segoe UI faces через QFontDatabase **в память своего процесса**, без установки/копирования шрифтов и изменения продукта. Проверка Unicode идёт через codepoint overload/actual face coverage.

Fresh gallery (пути выбирает выполняющий):

```powershell
$Run = ".agent-work\pyside-gallery-" + (Get-Date -Format "yyyyMMdd-HHmmss")
& "$EnvDir\Scripts\python.exe" -B -m tests_pyside6_v2.gallery --output $Run
# Контролируемые СВОИ видимые Windows окна, отдельный процесс:
& "$EnvDir\Scripts\python.exe" -B -m tests_pyside6_v2.gallery --visible --output ($Run + "-native")
```

Gallery создаёт только synthetic images и ждёт safety-release собственных barriers, вызывает настоящий API и сохраняет manifest source/native/PNG hashes, platform, DPR, requested/resolved font. Это авторская rendered/behavioral проверка, не независимый ACCEPT. Native dialogs/физический OS drag/drop и screen-reader compatibility отдельно не квалифицированы.

# FigCraft

Открываемый native и точная screen/component/token карта — [03-design-spec](03-design-spec.md). Final PNG — `design/exports/20261023-candidate-03/`; ранние runs сохранены как история. Официальный CLI 0.10.0 поддерживает `info`, `run`, `export`, headless MCP. Global MCP settings не требуются; к чужому редактору/control не подключаться.

Для свежего экспорта укажите путь **уже установленного официального** CLI в `$FigCraftCli`, новый run name и собственный private evidence root:

```powershell
$RunId = Get-Date -Format "yyyyMMdd-HHmmss"
& "$EnvDir\Scripts\python.exe" design\figcraft\export_screens.py --cli $FigCraftCli --run $RunId --evidence (".agent-work\figcraft-export-" + $RunId)
```

Только движок пишет native; command JSON — рецепт графики, не собственный native serializer. Source scripts/пошаговые scripts рассчитаны на сохранённую редакцию/ID и исходный project root; при переносе репозитория абсолютные export paths в исторических scripts требуют адаптации. Runtime GUI **не читает** `.figcraft` и не требует FigCraft. Автоматического экспортера Python/QSS/.ui в этой версии нет.
