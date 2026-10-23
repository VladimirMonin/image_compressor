---
id: ic-figcraft-implementation-plan
title: "FigCraft → PySide6: исполнимый план изолированного эксперимента"
kind: plan
status: proposed
created: "2026-10-23"
updated: "2026-10-23"
areas: [gui, design, pyside6, testing]
summary: "Один законченный эксперимент: настоящий FigCraft-документ, отдельный PySide6 Widgets GUI на принятом API, сквозные проверки и честная оценка переноса."
code_ref: "58afb9b648ebe63bfb6fc2f5123e77165b3e0db9"
verification_scope: "План по исходникам и официальному интерфейсу FigCraft 0.10.0; реализация и приёмка ещё не выполнены."
---

# 1. Решение и конечный результат

**Один Coder** создаёт редактируемый FigCraft-дизайн и по нему отдельный `gui_pyside6_v2` на **PySide6 Widgets**. Новый GUI вызывает существующие `discover_inputs`, `get_capabilities`, `convert`; ядро не меняется. Старые `gui/`, `gui_main.py`, CLI и facade остаются рабочими и неизменными. Эксперимент сохраняется как opt-in модуль, не заменяет GUI по умолчанию и не становится EXE-релизом.

Итог: реальное добавление файлов/папки/drop, очередь, настройки, обработка/отмена/clear, локальный bounded log, light/dark, RU/EN/KK, настоящий файл/readback, дизайн и отчёт о пользе FigCraft. **Удаление исходников остаётся недоступным** и честно обозначается в UI/отчёте; отсутствие destructive API не обходится. Никаких Electron/React, Image Compressor MCP, новой backend-архитектуры, Job Manager или постоянной очереди.

Источник текущего поведения — [01-current-functionality.md](01-current-functionality.md) и [Application API](../architecture/application-api.md). Новые имена файлов/контроллера ниже — **целевые**, не найденные реализации.

## Первое действие Coder: синхронизировать текущую область

На **существующей** `refactor/command-first` сверить HEAD/actual delta, сохранить Oracle-документы и чужие изменения. Не создавать/переключать ветку заново. Точечно обновить `AGENTS.md`, `docs/instructions/development.md`, `.pi/agents/{oracle,coder,reviewer}.md`: новая отдельная GUI/design задача теперь разрешена; принятый command-first-срез закрыт. Сохранить исторические факты и правила сохранности/приёмки/Git. Reviewer теперь проверяет техническую **и визуальную** границу нового GUI. Описание текущего scope в `docs/README.md`, foundation/test instructions синхронизировать только там, где старое «в этой работе GUI не заказан» ошибочно выглядит действующим запретом; не переписывать historical verification.

Роли/маршруты не менять: Oracle `openai-codex/gpt-6-astra`/xhigh; отдельные Coder и Reviewer `openai-codex/gpt-6.1-sol`/max. Этот план не добавляет пользовательское согласование макета или ещё одного Oracle-принимающего. Сначала дизайн и краткая design-spec, затем GUI; один независимый Reviewer готового кандидата. Oracle/Coder не получают index/commit/push.

# 2. Минимальная архитектура и владение файлами

| Планируемый owner | Единственная ответственность |
|---|---|
| `gui_pyside6_v2/__init__.py`, `__main__.py` | Lazy package и отдельный запуск `python -m gui_pyside6_v2`; понятная ошибка отсутствующего optional PySide6, без input/raw traceback. |
| `gui_pyside6_v2/window.py` | MainWindow, Qt layouts, соединение действий с controller, closeEvent, retranslate; без Pillow/файловых эффектов. |
| `gui_pyside6_v2/controller.py` | Локальный state machine, выбранный manifest/selection issues, immutable options snapshot, поколение операции, итог и доступность действий. |
| `gui_pyside6_v2/workers.py` | QThread-транспорт discovery/capabilities/conversion, queued signals с immutable данными; API остаётся единственным исполнителем. |
| `gui_pyside6_v2/queue_model.py` | QAbstractTableModel: name, suffix/format, bytes, status; dataChanged/reset только в GUI thread. |
| `gui_pyside6_v2/widgets.py` | Небольшие реальные reusable widgets: drop panel, settings panel, semantic buttons/status banner. Не отдельный QWidget на каждый файл. |
| `gui_pyside6_v2/theme.py`, `tokens.json` | Нормализованные semantic values из дизайна → QSS/QPalette/QFont/layout constants. Никакого runtime парсинга .figcraft. |
| `gui_pyside6_v2/localization.py` | RU/EN/KK catalog + formatter стабильных status/error codes; не вторая доменная валидация. |
| `gui_pyside6_v2/assets/*.svg` при необходимости | Простые собственные значки, реально экспортированные FigCraft и проверенные Qt; происхождение в design-spec. |
| `pyproject.toml` | Только optional extra `gui-pyside6` (PySide6 6.x, совместимая фактически проверенная версия), explicit новый package и package-data tokens/SVG. Runtime Pillow, старый gui extra и CLI script неизменны. |
| `tests_pyside6_v2/` | Изолированный PySide suite: `conftest.py`, `test_controller.py`, `test_window.py`, `test_entrypoint.py`, `gallery.py`; собственные synthetic fixtures. |
| `tests/test_packaging.py` | Минимальная адаптация explicit build snapshot: добавить новый package и проверить его data; сохранить все прежние no-Qt/API/CLI assertions, добавить отсутствие PySide в bare install. |
| `design/figcraft/image-compressor-v2.figcraft` | Настоящий native design, сохранённый официальным FigCraft; один редактор-владелец. |
| `design/exports/<run-id>/{light,dark}/`, `design/figcraft/commands/` | Конечные PNG и исходные официальные command scripts, если используются; старые runs не перезаписывать. |
| `docs/figcraft_gui_experiment/{03-design-spec.md,RUNNING.md,REPORT.md}` | Дизайн→Qt mapping, инструкция запуска/проверки, факты/ограничения/оценка эксперимента. |
| `README.md`, `docs/README.md`, relevant instructions, `LOG.md` | Короткие точные ссылки/optional запуск/граница новых checks; не второй канон API. |
| `.agent-work/figcraft-gui-experiment/coder-01/` | Свежие команды, raw exits, native-tree evidence, hashes, screenshot runs и handoff. Reviewer использует **свой новый root**. |

`tests_pyside6_v2/` намеренно вне existing `tests/`: обычная collection `pytest tests` уже импортирует PyQt6 (`tests/test_gui_adapter.py:7–10`). **Никогда не импортировать оба binding в одном процессе**, включая pytest collection, gallery и helper. Не добавлять глобальную autouse fixture и не чинить legacy widgets ради lint. Core/source/tests command-first, кроме названного packaging snapshot, не изменять; если обнаружен обязательный core defect — передать конкретный finding, не начинать backend repair молча.

PySide установить позже только в отдельный project-local venv, например `.agent-work/figcraft-gui-experiment/pyside6-venv`, с `.[gui-pyside6,dev,codecs]`, **без** `gui`. Текущую `.venv` оставить для PyQt/прежнего suite. Oracle установок не делал; сейчас PySide6 отсутствует. Version resolve/совместимость Python 3.14.2 — проверка Coder, не обещанный install PASS.

# 3. FigCraft: доступ установлен, начать с реального инструмента

## Наблюдённое и неизменяемая граница

Установлен официальный `figcraft-cli.exe` **0.10.0**, sibling `figcraft.exe`. Точный локальный путь и выполненные discovery-команды — в Oracle handoff. `--help`, `--version`, `commands --json` работают. **`run --help`, `export --help` и остальные subcommand --help не поддерживаются** (usage/exit2); использовать верхнеуровневую справку и command catalog.

Официальная отдельная headless MCP-сессия успешно прошла `initialize` → `tools/list` → `inspect_ui {}` → `inspect_document {depth:2}` с **read root только проекта, без write roots**: backend=headless, Untitled, dirty=false, одна пустая страница, нет layers/images/variables, exit0. После отчёта о preflight мутаций не было, сессия завершена. Это подтверждает доступ/схему, **не** создание/сохранение/render компонентов.

Чужой PID **38272**, control **7979**, roots **C:/PY/FigCraft** существует. Его документ неизвестен и не исследовался. Не attach к нему, не менять roots, не закрывать, не делать file.new/open/save в нём. Глобальные Pi/Hermes MCP/app settings не менять.

## Предпочтительный путь: официальный headless `run`

Coder сначала повторяет короткий read-only preflight **своей** headless-сессии, сообщает состояние и заканчивает preflight без open/mutations. Затем отдельным шагом создаёт новый проектный дизайн. Не требуется ждать дополнительного user approval; требуется не смешивать preflight с записью.

`FC` ниже — полный путь установленного официального `figcraft-cli.exe`; `ROOT` — абсолютный путь текущего проекта. `DESIGN` и `WORK` — заранее созданные **в проекте** каталоги `design` и собственного coder root. Примеры команд для Git Bash; это **планируемые**, ещё не выполненные design-команды:

```bash
# Read-only catalog: точный существующий синтаксис
"$FC" --version
"$FC" --help
"$FC" commands --json --filter component.
"$FC" commands --json --filter variable.
"$FC" commands --json --filter node.create

# Read-only отдельная MCP-сессия для preflight (не attach)
"$FC" mcp --automation-read-root "$DESIGN" --automation-read-root "$WORK"

# После законченного preflight — настоящий новый документ/этап через official engine
"$FC" run "$DESIGN/figcraft/commands/01-foundation.json" \
  --out "$DESIGN/figcraft/image-compressor-v2.figcraft" \
  --automation-read-root "$DESIGN" --automation-write-root "$DESIGN"

# Следующий этап читает предыдущий native; не начинать заново при потерянном ответе
"$FC" run "$DESIGN/figcraft/commands/02-screens.json" \
  --in "$DESIGN/figcraft/image-compressor-v2.figcraft" \
  --out "$DESIGN/figcraft/image-compressor-v2.figcraft" \
  --automation-read-root "$DESIGN" --automation-write-root "$DESIGN"

# Каждый вызов info/export заново открывает сохранённый файл отдельным процессом
"$FC" info "$DESIGN/figcraft/image-compressor-v2.figcraft" --json \
  --automation-read-root "$DESIGN"
"$FC" export "$DESIGN/figcraft/image-compressor-v2.figcraft" \
  --node 'RU-Light-Queue' --format png --scale 1 \
  -o "$DESIGN/exports/<new-run-id>/light/RU-Queue.png" \
  --automation-read-root "$DESIGN" --automation-write-root "$DESIGN/exports"
```

Подставить действительный новый run-id и созданные roots; не исполнять angle placeholders. Предварительно сохранять версию каждого законченного семейства в своём evidence root, затем рабочий native можно продолжать. Все scripts — **команды графического дизайна**, не кодогенератор продукта и не ручное изготовление native JSON/ZIP. Настоящий `.figcraft` пишет только FigCraft. `run` не касается PID 38272; имеет собственную новую session или `--in`.

Схема script: JSON array / `{"commands":[...]}` / JSONL строк `{"command":"id","params":{...}}`. Официальная v0.10.0 [CLI reference](https://github.com/storytold/figcraft/blob/v0.10.0/docs/cli.md#run-scriptjsonscriptjsonl---in-file---out-file) устанавливает один undo step, all-or-nothing document state, `ok:false/rolledBack:true` и exit1 при ошибке; `--out` не сохраняется при failure. `{"$step":n}` — ссылка на id результата более раннего шага, `field` выбирает иное поле. **Не угадывать node ID**, не подставлять `$step` shell-расширением. File/external effects не считать общей rollback-транзакцией: в build scripts не нужны посторонние import/export/prefs/network actions.

Достаточные реально обнаруженные команды:

| Команда | Params / назначение |
|---|---|
| `file.new` | `{name?}`; новый отдельный дизайн. |
| `page.rename`, `page.add`, `page.select` | `{id?,name}`, `{name?}`, `{id|index}`. |
| `node.create` | `{type, name?, parent?, width?, height?, text?, props?}`; props включают layout, padding, gap, fill, fontFamily/fontSize, sizingH/V. |
| `node.set` | `{ids:[...], props:{...}}`; пользоваться схемой MCP set_properties/command docs, читать свойства обратно. |
| `layout.add` | `{ids?,direction?:horizontal|vertical|grid}`. |
| `component.create` | `{ids:[frameId]}` — **настоящий component**, не GROUP с названием Button. |
| `component.addProperty` | `{id?,name,type:text|boolean|instanceSwap|variant|slot,default?,layer?}`. |
| `instance.create` | `{component:masterId,parent?,x?,y?}`. |
| `instance.setProperties` | `{ids:[instanceId],properties:{name:value}}`. |
| `component.list`, `component.properties`, `node.get` | `{}`, `{id?}`, `{id}` — evidence структуры/связей. |
| `variable.createCollection` | `{name,modes:["Light","Dark"]}`; Locale отдельно, не произведение Theme×Locale. |
| `variable.create` | `{collection,name,type:color|number|string|boolean,values:{modeName:value}}`. |
| `variable.bind` | `{ids?,field:"fill"|"characters"|"gap"|...,variable:id}`. |
| `variable.setMode` | `{ids?:[frameId],collection,mode:"Light"|"Dark"|...}`. |
| `variable.list`, `variable.set` | `{}`, `{variable,mode?,value}`. |
| `edit.duplicate` | `{ids?,dx?,dy?}`; копия main component становится instance, обычного frame — frame. |
| `file.saveVersion`, `file.save` | `{name?,description?}`, `{path?}`; native save. |

Официальный MCP использует newline-delimited JSON-RPC 2.0/stdin/stdout, protocol `2025-06-18`; доступны `run_command`, `batch`, `inspect_document {depth,allPages}`, `get_node {id,depth}`, `inspect_ui {}`, `open_file {path}`, `save_file {path}`. Можно использовать стандартный клиент к **официальному** CLI без правки MCP config. Для полного дерева reopen запустить fresh MCP с только read roots → preflight/report → open_file **только своего native** → inspect по страницам/узлам. Открытие native после preflight — отдельный разрешённый design/readback шаг. Truncated output не считать полным деревом.

Headless save → завершение процесса → fresh process open/inspect/export является native **save/reopen**. Для настоящего editor-window inspection допустим отдельный `figcraft.exe --control 7981 --automation-read-root "$DESIGN" --automation-write-root "$DESIGN"` (порт **перепроверить**, discovery не резервирует его), затем `figcraft-cli mcp --attach 7981`. Roots задаются **приложению**, с `--attach` эти flags запрещены. Сначала inspect_ui/document depth2 и отчёт; если экземпляр неожиданно открыл чужое/recovery состояние — не закрывать/discard, остановить этот путь. Не запускать отдельный editor без нужды, когда headless покрывает дизайн. Официальные ограничения roots не являются sandbox приложения: его внутренние preferences/recovery/system fonts вне этих roots; не менять их настройками.

**Остаток доступа:** материального блокера headless нет. Работоспособность создания component, render, save/reopen ещё должна быть доказана первым маленьким семейством. При конкретном failure сохранить exact call/raw error; не строить fake native, не менять глобальные settings, не уходить в бесконечный поиск инструментов.

# 4. Ограниченный дизайн: что пользователь видит, понимает и делает

## Композиция

Обычный размер **1120×760**, минимальный полезный **900×640** в logical px (предложенные, проверить фактическими Qt/PNG). Header: название, короткое объяснение «Новые файлы; исходники сохраняются», theme + locale. Body: растягиваемая очередь слева, settings panel около 320–340 px справа. Footer всегда доступен: summary/progress, Start/Stop/Clear; bounded log ниже очереди или отдельная раскрываемая область, не растущая минимальная высота окна.

- Empty: краткая drop-зона + «Добавить файлы» / «Выбрать папку»; не огромная декоративная иллюстрация.
- Queue: таблица имя / формат по расширению / размер / статус; до decode не называть suffix проверенным actual format. Длинные имена elide + локальный tooltip; размер неизвестен → «—», не 0. Selection issues отделены от runnable rows.
- Settings: format combo (четыре выхода, unavailable codecs disabled с reason), quality slider+spinbox 0..100/80, resize toggle off + реальные значения 1920/1080 при включении, max sides, postfix `_compressed`, checkbox «Включая подпапки» default True **для следующего добавления папки**. После изменения recursion уже раскрытая очередь не пересканируется молча.
- Disabled unchecked «Удалять оригиналы» + видимое пояснение «Недоступно: безопасный API всегда сохраняет исходники». Не только tooltip и не фальшиво включаемый toggle.
- Под postfix: «Для совпадающих форматов. Занятые имена не перезаписываются». Пустой ввод сохранять как пустой: отказ API показывать честно; не копировать legacy strip/fallback.
- Processing: immutable список/настройки, активная строка и item counts; stop-requested отдельный status. Нет выдуманного внутрикодекового процента/ETA.
- Done: тот же layout, сводка succeeded/failed/cancelled/published и warnings; partial/error/cancel не окрашивать как полный успех. Это runtime состояние обязательно; отдельный FigCraft Done-frame — только если недорог.

Qt: `QVBoxLayout` для shell/header/footer; `QHBoxLayout`/`QSplitter` для body; QTableView+model; QScrollArea для settings на малой высоте; QStackedWidget для empty/queue; QPlainTextEdit read-only с `maximumBlockCount` порядка 500 и bounded height. Без абсолютного размещения controls, full-window SVG/PNG вместо виджетов и minimum-size ratchet. Имена/пути допускаются в локальной очереди/results, но не в техническом log.

## Конечный набор FigCraft-экранов

**8 основных экранов**, не полный Cartesian product:

1–6. RU Empty / Queue / Processing, каждый в Light и Dark, 1120×760.
7. EN Queue Light, 900×640.
8. KK Queue Dark, 900×640.

Минимальные Queue-копии делать из существующего frame: изменить только корень, язык/режим, не подгонять дочерние координаты. Основы/компоненты — отдельная страница, не считать экраном. Опциональный Done — максимум один дополнительный пример, если основные готовы. В дизайн входят реальные editable text/vector/frame layers, собственные простые SVG без emoji как основного набора значков.

Настоящие masters/instances: primary / secondary / stop button, input, checkbox, format selector, queue row, section panel, status badge. States default/focus/disabled (+selected/running/error по месту). Варианты допустимы, но не обязательны для каждого произведения state×theme×locale; базовые компоненты и независимые variables достаточны.

Tokens: `surface/window`, `surface/panel`, `surface/raised`, `text/primary`, `text/secondary`, `border/default`, `accent/action`, `state/success`, `state/warning`, `state/error`, `focus/ring`, spacing 4/8/12/16/24, radius panel/control, body/caption/title typography. Начальная палитра спокойная slate+blue; финальные values устанавливает FigCraft-дизайн. Записать единицы: layout logical px, font px/Qt point conversion отдельно, не массовый suffix `px` на все числа. Один requested font, например Segoe UI, и **actual resolved font**/KK glyph fit проверяются в обоих renderer; не выдавать fallback за совпадение. Шрифты Windows не копировать в distributable.

Ключевые строки для fit (предложенные переводы, не native-language certification):

| RU | EN | KK |
|---|---|---|
| Добавить файлы | Add files | Файлдарды қосу |
| Выбрать папку | Choose folder | Қалтаны таңдау |
| Включая подпапки | Include subfolders | Ішкі қалталарды қосу |
| Качество | Quality | Сапа |
| Максимальная ширина | Maximum width | Ең үлкен ені |
| Максимальная высота | Maximum height | Ең үлкен биіктігі |
| Удалять оригиналы — недоступно | Delete originals — unavailable | Түпнұсқаларды жою — қолжетімсіз |
| Начать / Остановить | Start / Stop | Бастау / Тоқтату |
| Очистить очередь | Clear queue | Кезекті тазарту |

Казахские Ә Ғ Қ Ң Ө Ұ Ү Һ І должны отображаться. RU/EN/KK catalog покрывает все visible strings и terminal states; counts оформлять нейтрально «Успешно: N», не создавать отдельную plural framework. Theme/locale switch не очищает очередь, ввод, прогресс, логи как данные и worker.

## Доказательства, без которых дизайн не готов

1. Первый небольшой button/row master + два instances: inspect → изменить **только master** → inspect подтверждает наследование и сохранение индивидуальных labels; не менять instances ради PASS.
2. Auto Layout: root resize existing frame, геометрия дочерних областей до/после; отсутствие ручного reposition между снимками.
3. Official native save → fresh process reopen → tree с component/instance links, text/vector layers, variables bindings/modes и layout → PNG после reopen. `info` counts сами по себе не доказывают links.
4. В `03-design-spec.md`: native hash, страницы/frame IDs, screen→PNG manifest, token/Qt mapping, компоненты, source/licensing icons/fonts, intended deviations. **Посмотреть** PNG, не только существование файлов.
5. Qt код начинается после этой конкретной основы и design-spec, не после второго общего исследования. Не обещать automatic Python/QSS export: `inspect.code` v0.10.0 перечисляет css/html/react/leptos/swiftui/compose, не Qt.

# 5. Контроллер и настоящая работа

## State/данные

Минимальные состояния: initializing-capabilities, empty/ready, discovering, converting, stop-requested, terminal, closing-pending. Controller — GUI-thread owner view state; одновременно не более одного active worker. Ссылки/connection lifetime удерживаются до **QThread.finished**, не только result-ready. Небольшой generation counter исключает поздние callbacks после нового выбора/закрытия; это не backend Job ID.

Добавление (file dialog / directory dialog / local URL drop) идёт в **один controller method**. Не вызывать `os.walk`, encode или `get_capabilities` в GUI thread. В background вызвать `discover_inputs(existing_valid_paths + selected_roots, recursive=checkbox_snapshot)`. Сохранить order/dedup API; не unordered set в UI. При полном discovery принять реальные paths и отдельно показать issues/errors/warnings/duplicates/ignored. При cancelled/incomplete discovery прежнюю runnable очередь сохранить, новый неполный набор не запускать автоматически. Пустой/corrupt выбор не фабрикует success.

`DiscoveryResult` не содержит size/actual format/index. Не выдумывать metadata: для display-only bytes допустим короткий read-only stat **в worker** по уже возвращённым paths, ошибка → неизвестно/статус; thumbnails/decode в очереди не нужны. Issues показывать отдельно, поскольку их порядок не совпадает с индексами будущего batch. Если есть valid subset, разрешить его запуск с явным «Обработать N доступных; M ошибок добавления»; итог batch не выдавать за успешную обработку всех выбранных roots. Selection issues остаются видимыми до clear/следующего явного выбора.

Start snapshot: `ConversionRequest(tuple(valid_paths), output_format=..., quality=..., max_width=... or None, max_height=... or None, postfix=<exact text>, delete_original=False, recursive=False)`; default output рядом с source. Директории уже раскрыты; не повторять пользовательские directory roots при Start, чтобы новые outputs не подхватывались незаметно. Это **не резервирование**: API заново валидирует inputs и делает manifest. На исчезновение/замену внешним процессом ориентироваться по настоящему результату, не обещать тождество preview. Сопоставлять результаты по actual source; index — только внутри данного API batch. Не вызывать private filesystem naming/preflight из UI и не делать per-file `convert`: один batch нужен для общих TARGET_CONFLICT.

Во время discovery/conversion отключить add/drop/start/clear и изменение параметров. Theme/locale/просмотр log/Stop доступны. Capabilities query тоже в worker; не обещать мгновенную отмену synthetic probe, у `get_capabilities()` нет token. Close ждёт его окончания без блокировки event loop.

## Worker/signals/lifetime

Минимально подходит QThread subclass с вычислением только в `run()` и queued object signals; либо worker QObject при той же понятной модели. Не ставить queued cancel-slot за блокирующим convert: `CancellationToken.cancel()` вызывается GUI thread непосредственно, он thread-safe. Worker не обновляет QWidget/model. Один result-ready объект, затем настоящий finished; fallback неожиданной adapter exception — безопасный INTERNAL_ERROR status, не сырое исключение и не поддельный BatchResult успеха.

Прогресс: discovery indeterminate; при известном total использовать `(processed,total)` и считать percent лишь как долю завершённых success+failed. Cancelled не доводить искусственно до 100. API может вызывать discovering на каждый entry — не ставить тысячи queued updates: coalesce discovery/active ticks, terminal result не терять. Для больших queues batching/throttling UI updates достаточно; никаких новых параллельных конвертеров. Сводка/результат восстанавливают факты даже если callback был отключён.

Stop выставляет token и текст «Остановка запрошена; ожидаем кодек», не вызывает wait/terminate. Close во время worker: ignore event, поставить closing-pending, запросить token где есть, оставить окно/loop живым; после finished корректно disconnect/deleteLater и закрыть. Не уничтожать QThread при работающем codec. No hard timeout claim: hangs native codec остаются ограничением API; tests имеют safety-release и собственные subprocess timeout/cleanup.

`result.status`, items/artifacts/errors/warnings/counts — final truth. `publication=unverified`, OBSERVER_FAILED, TEMP_CLEANUP_FAILED видимы, published отдельно. Log — безопасные codes/stage/counts; никаких raw exceptions/DTO repr/полных путей. Нет постоянного log handler по умолчанию. Clear не удаляет source/output, новый запуск получает новый token; не retry автоматически.

# 6. Реализация и проверка — один конечный цикл

## Последовательность

1. Scope sync + один собственный evidence root; изолированная optional PySide среда.
2. FigCraft preflight/report → маленькое component proof → 8 frames/tokens → native save/reopen/exports → `03-design-spec.md`.
3. Новый runnable module: empty/queue/settings/controller → одна реальная conversion/readback → stop/close/next-run → темы/локали/terminal/error. Не заменять backend готовыми fake success objects.
4. Адресные tests + текущая Qt gallery → визуальный review → исправление root cause, **3–5 итераций максимум**. После двух итераций без прогресса пересмотреть конкретную гипотезу, а не повторять общий аудит.
5. Достаточный regression/отдельные smoke/package checks → RUNNING/REPORT → freeze → один независимый Reviewer; findings тому же Coder, delta тому же Reviewer.

## Конкретные acceptance checks

| Граница | Что должно быть реально наблюдено |
|---|---|
| Добавление | Один/несколько synthetic файлов, папка с подпапкой recursive on/off, повтор пути/hardlink где доступно, explicit unsupported path и пустая папка. Table rows из real discovery, errors не исчезли. Drop принимает только local URLs; web URL не открывается/скачивается. |
| Real conversion через GUI | Real MainWindow action/controller/worker → существующий convert → Pillow → файл → `Image.open().load()`. WEBP и JPEG, качество 0/80/100 по разумной выборке, resize 400×300→144×108 для bounds192×108, no-upscale. Source bytes/hash неизменны; artifact format/size/hash согласованы. Не просто SignalSpy/save.called. |
| Same-format/collision | `a.webp→a_custom.webp`; пустой postfix→явный conflict; repeat→OUTPUT_EXISTS; `a.png+a.jpg→WEBP` отказывает обоим, независимый файл успешен. Сохранились точные исходные/предыдущие bytes. |
| Partial/unsafe outcome | Good+corrupt→partial; readback failure после реальной публикации через ограниченный fault seam→unverified показан не как success; cleanup warning не теряется. Можно использовать существующие core seams без изменения owners. |
| Disabled delete/capabilities | Checkbox видим/unchecked/disabled, объяснение доступно всем locales; UI никогда не удаляет файлы. API regression True→DESTRUCTIVE_MODE_UNSUPPORTED остаётся. Unavailable encoder недоступен в selector с reason; реальные JPEG/WebP обязательны, HEIF/AVIF отмечать по фактическим probes, не по имени distribution. |
| Cancel/responsiveness | Реальный codec + управляемый barrier на encode/publication boundary; GUI heartbeat продолжает работать; stop быстро возвращает; нет нового worker до QThread.finished. Сохранить уже опубликованный файл, не начатые cancelled; поздний cancel после последнего checkpoint может дать succeeded. Следующий batch с новым token работает. |
| Discovery/close/stale | Cancel incomplete discovery не запускает найденную часть. Close до dispatch и во время worker не обновляет уничтоженное окно; поздний A не затирает новый B. Отдельно positive live delivery, чтобы guard не выключил всё. Teardown без `QThread destroyed while running`. |
| View/i18n | Обе темы, RU/EN/KK ключи/глифы, minimum и обычный размер, длинное synthetic имя, resize on/off, unavailable explanation, выбранный item combo popup, focus/tab/Enter/Space. Theme/locale не сбрасывают inputs/operation. |
| Geometry | Layout activated, widgets штатно видимы, rects в общей системе координат. Footer actions/scrollbars доступны; controls не перекрываются, значки целиком в viewport строк. Преднамеренный elide имён отделён от clipping кнопок/важных подписей. Длинный log/очередь не растят minimumSize. |
| Qt screenshot review | Минимум 6 RU state/theme кадров + EN/KK minimum queue; адресно stop-requested, terminal partial/cancel/success и indeterminate, если их не видно в основных. Counts actual PNG/unique images/state coverage отдельно. Fixtures галереи допустимы **как rendered**, не заменяют real behavioral run. Посмотреть individual PNG и gallery. |
| Native smoke отдельно | В двух **разных subprocess** новый PySide module и старый PyQt `gui_main.py`/настоящий MainWindow; show/event loop/resize/close, один процесс — один binding. Qt offscreen полезен для test geometry, но не выдаётся за Windows titlebar/native dialog/drag-drop smoke. Хотя бы краткий Windows visible smoke в разрешённой synthetic среде; при недоступности конкретно NOT RUN. Только свои окна/PIDs. |
| Регрессия/поставка | Existing `tests/` в старой .venv; новый suite в PySide venv. Bare installed wheel по-прежнему Pillow-only без Qt, новый package/data присутствуют, API/CLI работают вне repo. Отдельно новый module запускается из установленного candidate wheel с PySide-only environment; entry smoke не ограничивать editable import. |
| Privacy | UI technical buffer содержит непустые outcome/code/counts и не содержит sentinel file path/postfix/raw exception. Names в user-facing table/results — отдельный допустимый канал, не log. |

Не задавать желаемое число tests: сохранить фактические collection/pass/skip/fail, не складывать пересекающиеся runs как уникальные. Existing acceptance не отменяет проверку нового адаптера; старый suite не является новым visual proof.

Предлагаемые команды после создания окружения/файлов (Oracle **не запускал**):

```bash
# У каждого запуска fresh TEMP/TMP/TMPDIR, caches, --basetemp внутри его own root.
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/Scripts/python.exe -B -m pytest \
  -p pytest_timeout -p no:cacheprovider tests -q --basetemp "$RUN/legacy-tmp"
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 "$PYSIDE_PY" -B -m pytest \
  -p pytest_timeout -p no:cacheprovider tests_pyside6_v2 -q --basetemp "$RUN/pyside-tmp"
"$PYSIDE_PY" -B -m ruff check gui_pyside6_v2 tests_pyside6_v2
.venv/Scripts/python.exe -B -m ruff check tests/test_packaging.py
"$PYSIDE_PY" -B -m mypy gui_pyside6_v2
.venv/Scripts/python.exe -B -m mypy image_compressor classes.py
"$PYSIDE_PY" -B -m gui_pyside6_v2
# Legacy smoke — ДРУГОЙ процесс, без PySide imports:
.venv/Scripts/python.exe -B gui_main.py
```

Последние два интерактивных входа требуют контролируемого smoke/cleanup, не unattended вечного процесса. `PYSIDE_PY`, `RUN`, среды/commands и timings фиксируются фактически; plugins autoload off, не импортировать обе test suites в одном runner. Не перезаписывать старые `.agent-work` evidence, build/dist или control files. Gallery builder принимает явный новый output root, не имеет общего старого default. Screens manifest: native/design hash, source hashes/HEAD+dirty inventory, state/theme/locale, requested/resolved font, logical size, DPR, PNG dimensions/SHA, renderer/offscreen/native, substitutes и review notes.

## Первичные Qt references

Context7 и codebase-memory/Serena/ast-grep в этой Oracle-сессии не экспонированы; достаточное source reading выполнено штатными tools, установки не нужны. Прочитаны официальные HTTPS материалы: [QThread](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html) (thread affinity, worker-object/queued slots), [Layout Management](https://doc.qt.io/qt-6/layout.html), [QSS reference](https://doc.qt.io/qt-6/stylesheet-reference.html), [High DPI](https://doc.qt.io/qt-6/highdpi.html). Qt сайт на момент чтения показывал 6.12.0 для Widgets docs; это reference общих механизмов, **не версия установленного PySide**. Coder фиксирует реально установленную версию и проверяет используемый API на ней. CSS Flex/Grid/variables не переносить в QSS как есть.

# 7. Документы, freeze и остановка

`03-design-spec.md`: точная native редакция/дерево/frames, tokens/components, schema/exports, geometry и Qt mapping. `RUNNING.md`: отдельная optional установка и запуск, старый запуск, synthetic проверка, safe semantics, поддержанные языки/темы, минимум окна, codec/FS/отмена ограничения. README только ссылается и сохраняет старые команды.

`REPORT.md` должен различать:

- что исследовано, нарисовано, сохранено/reopened, реализовано, реально проверено и независимо принято;
- фактические tests/screens/runs, источник и freshness evidence, первая ошибка и её причина;
- что работает и что не работает: в частности **нет удаления оригиналов**, нет direct Qt exporter, нет гарантий мгновенной cancel/меньшего файла/любой FS;
- что FigCraft дал: композицию, editable components, темы/tokens, spacing/icons/states; что вручную: Qt layout policies, model/controller, сигналы/lifecycle, локализацию, доступность, интеграцию backend;
- конкретные неудобства/потери переноса, измеренное время этапов если записывалось (не придуманный выигрыш), пригодность для более крупных Qt-проектов;
- финальный отдельный блок **«Итоговая оценка пригодности связки FigCraft → PySide6»** с одним обоснованным выводом, а не утверждением code generation.

Coder freeze: список изменённых paths, hashes source/tests/manifest/native/tokens/screens, exact commands/raw exits/NOT RUN, source→design→Qt mapping, своё saved session locator, handoff единственному Reviewer. Во время review candidate/docs/native/index не менять. Reviewer независимо проверяет connected behavior, сохранность, native-tree evidence и текущие PNG; обязательные findings возвращает тому же автору. Только **после ACCEPT** тот же Reviewer выполняет уже разрешённый docs closeout/selective commit/branch-only push существующего origin на `refs/heads/refactor/command-first` с exact SHA readback. Ни merge/tag/release/force, ни новое разрешение Oracle на эти действия не появляются.

**Done:** реальный editable design + exports, отдельный работающий PySide GUI на неизменённом API, сохранённый старый GUI, достаточные независимые technical/visual checks и честный отчёт/инструкция. Нет дополнительной Oracle-acceptance/user-approval стадии. Если конкретная обязательная проверка недоступна — точный blocker/NOT RUN, не fabricated ACCEPT. После этого результата остановиться; новые UI-функции, backend deletion и бесконечная полировка не являются продолжением эксперимента.
