---
id: ic-figcraft-design-spec
title: "Image Compressor UI v2 — дизайн и перенос в Qt"
kind: reference
status: accepted
created: "2026-10-23"
updated: "2026-10-23"
areas: [design, gui, pyside6]
summary: "Настоящий native FigCraft, восемь экранов, связанные компоненты/переменные и правила ручного переноса в Qt Widgets."
---

# Дизайн-основа до реализации Qt

[План](02-implementation-plan.md) выполнен без нового общего исследования. Источник — [редактируемый native](../../design/figcraft/image-compressor-v2.figcraft), записанный **официальным FigCraft CLI 0.10.0**, не JSON/ZIP, изготовленным вручную. SHA-256: `440b5b8e58948d86b9c19a59e1529e51ee1cc4779e9f5cf0804b4c126fbe8dd9`.

Отдельная headless-сессия прошла read-only preflight: пустой Untitled, dirty=false. Чужое окно/PID/control не использовались. До мутаций preflight завершён и состояние сообщено. Все automation roots — только текущий проект. Скрипты [commands/](../../design/figcraft/commands/) — команды графического движка, не генератор приложения. [build_design.py](../../design/figcraft/build_design.py) только выпускает такие команды; `.figcraft` пишет сам FigCraft.

## Native readback и компоненты

Страница `00 · Foundation` (id 1): proof frame 2, библиотека 10. Страница `01 · Desktop screens` — восемь экранов ниже. Fresh process native reopen + глубокое `get_node(depth=14)` прочитали **748 узлов**, **10 masters**, **148 instances** с реальными `mainComponent` links. Editable TEXT и VECTOR присутствуют; IMAGE-слоёв нет. Это source/tree proof, а не интерактивный прототип. Прототипные клики не заявляются.

Малый proof: master 3 изменён **один**, radius 8→12, height 40→48; оба instances 5/7 унаследовали изменение, сохранив разные RU/KK labels. Root 2 расширен 800→900: Fill spacer 9 вырос 224→324 при неизменной позиции 552. Значения прочитаны до/после и после native reopen. Proof PNG просмотрен.

Основные masters: Primary 12, Secondary 14, Stop 16, Input 18, Format 20, Badge 22, Checkbox 24, Queue row 28, Section panel 33. Label/text properties действительно связаны с дочерними текстами. Checkbox имеет настоящий boolean `Checked`, привязанный к видимости VECTOR; Empty/Queue — unchecked resize, Processing — checked example, recursion — checked. Fresh native reopen отдельно подтвердил Theme Light/Dark и Locale EN/KK через `proto.evaluate`. Отдельные focus/disabled specimens; наследование цветов из Theme и подписей из Locale. Основной file row переносится в **model/view**, не в тысячи QWidget.

## Экран → экспорт

Все PNG — actual engine exports **после save/reopen**, scale 1. [Manifest с SHA-256](../../design/exports/20261023-candidate-03/manifest.json).

| Frame / id | Размер, logical px | PNG |
|---|---|---|
| RU-Light-Empty / 43 | 1120×760 | [Light Empty](../../design/exports/20261023-candidate-03/light/RU-Light-Empty.png) |
| RU-Light-Queue / 115 | 1120×760 | [Light Queue](../../design/exports/20261023-candidate-03/light/RU-Light-Queue.png) |
| RU-Light-Processing / 206 | 1120×760 | [Light Processing](../../design/exports/20261023-candidate-03/light/RU-Light-Processing.png) |
| RU-Dark-Empty / 298 | 1120×760 | [Dark Empty](../../design/exports/20261023-candidate-03/dark/RU-Dark-Empty.png) |
| RU-Dark-Queue / 370 | 1120×760 | [Dark Queue](../../design/exports/20261023-candidate-03/dark/RU-Dark-Queue.png) |
| RU-Dark-Processing / 461 | 1120×760 | [Dark Processing](../../design/exports/20261023-candidate-03/dark/RU-Dark-Processing.png) |
| EN-Light-Queue / 553 | 900×640 | [EN minimum](../../design/exports/20261023-candidate-03/light/EN-Light-Queue.png) |
| KK-Dark-Queue / 644 | 900×640 | [KK minimum](../../design/exports/20261023-candidate-03/dark/KK-Dark-Queue.png) |

Minimum copies получены из Queue только root resize/modes, без ручного reposition дочерних контролов. На minimum форма — намеренно ограниченный scroll viewport; таблица допускает elide длинного имени, footer и объяснение недоступного удаления остаются видны. Для Qt нужны настоящие scrollbars, не имитация нарисованного viewport.

## Tokens → Qt

[Сырой engine export](../../design/figcraft/variables.raw.json) отдельно от [удобной палитры](../../design/figcraft/palette.json). Theme: Light/Dark; Locale: RU/EN/KK; Metrics: Base. Это независимые оси, не шесть слепков одной системы. Основные labels привязаны к переменным. Нормализованный runtime `gui_pyside6_v2/tokens.json` содержит те же semantic values; runtime не читает native.

| Роль | Light | Dark | Qt consumer |
|---|---|---|---|
| surface/window | #F3F6FB | #101827 | shell/QPalette.Window |
| surface/panel | #FFFFFF | #192537 | cards/table/log |
| surface/raised | #EAF0F8 | #243349 | secondary/status/selection |
| text/primary | #17263C | #EDF3FC | main text |
| text/secondary | #50627A | #B5C5DB | captions/help |
| border/default | #CCD7E5 | #40516B | input/card borders |
| accent/action | #245EDB | #82ACFF | primary/progress |
| accent/on-action | #FFFFFF | #10213F | primary text |
| success / warning / error | #176A4C / #875106 / #AF3444 | #79DDB1 / #F6CA79 / #FFA2AC | terminal/result states |
| focus/ring | #153F9D | #B8D0FF | keyboard focus |

Spacing 4/8/12/16/24; radius panel12/control8. Shell padding20 — геометрия композиции; панель параметров320, gap16. Body14/caption12/title24 **font px**. В Qt предпочтительно `QFont.setPixelSize`, а не ошибочное присвоение 14 points. Все layout values — logical pixels, не raw PNG pixels. Segoe UI Regular/Semibold запрошен; engine `info` сообщает missingFonts=[] и разрешает системные faces Segoe UI. Набор Ә Ғ Қ Ң Ө Ұ Ү Һ І присутствует в editable filename и KK labels. Шрифты Windows **не копируются** в поставку; альтернативная ОС/системный fallback не квалифицированы.

[Icon-Add.svg](../../design/exports/20261023-candidate-03/Icon-Add.svg) экспортирован самим FigCraft из собственного VECTOR id41 (frame40), без сторонних изображений/emoji. Собственная простая геометрия распространяется с проектом; системный Segoe UI — только ссылка на установленный шрифт, не новый лицензируемый asset. Qt использует эту SVG-геометрию через QtSvg/QIcon с monochrome tint; не full-window screenshot вместо controls.

## Структура и сознательная адаптация

- Header → QHBoxLayout; identity с растяжением, theme/locale combos.
- Left area → add/drop, QStackedWidget empty/table, QTableView+model, отдельные selection issues, bounded read-only log.
- Right → fixed-width card, **QScrollArea** формы и отдельный всегда видимый disabled/unchecked delete + объяснение. Поля/slider/spinbox — реальные widgets. Качество 0..100, resize off / 1920×1080 при включении.
- Footer → отдельный layout, status/counts/progress + Clear/Stop/Start, не исчезающий при росте очереди/log.
- Модель состояния и реальные terminal outcomes не являются частью графического движка: они реализуются вручную поверх public API.

Намеренные отличия Qt: настоящий thumb/gutter вместо дизайнерской полосы, стандартные selection/focus/keyboard/disabled semantics; table scroll вместо спрятанных строк; многострочный terminal detail вместо молчаливого зелёного badge. Running source не угадывается по batch index: API item_started не несёт source, поэтому активность показана общим status/counts; пофайловый статус обновляется по настоящему item.source после завершения. Это осознанное отличие от выделенной active row макета, без ложного сопоставления при изменении manifest. В FigCraft на minimum нижние поля формы доступны концептуально прокруткой; PNG сам по себе не доказывает scrolling. Ширины колонок/label wrapping уточняются по фактическим Qt font metrics, не абсолютным координатам макета.

## Просмотр и ограничение цикла

Пять ограниченных design iterations: (1) RU queue и small proof, (2) dark/minimum после устранения незаданных белых frame fills, (3) language selectors, короткий KK header и visible unchecked safety control, (4) исправление bounds собственных VECTOR icon/check, (5) настоящий boolean Checked и корректный resize-off default. Предыдущие exports сохранены как история; финальные — candidate-03. Восемь screen PNG просмотрены по отдельности и повторно в общей галерее, финальные изменения также сверены по native tree и свежим PNG. Наблюдения: две согласованные палитры, читаемые подписи/иерархия, footer целиком, KK glyphs присутствуют, длинное имя elide на minimum; нет растровой подложки. Design-only scroll affordance в правой форме тесен к input — Qt получает собственный scrollbar gutter. Начальный промах `node.get` дал только depth1; глубокая свежая MCP-проверка заменяет его как tree evidence, первая попытка сохранена.

Дизайн был конкретной основой до реализации, а не самостоятельным runtime proof. Затем независимый Reviewer подтвердил native tree/modes, все восемь fresh exports с теми же hashes и master-only inheritance/Auto Layout на собственной копии; технический и визуальный **ACCEPT** Qt-результата и ограничения — в [REPORT](REPORT.md), команды — в [RUNNING](RUNNING.md). Интерактивные editor-window клики не квалифицированы; официальный headless save/reopen/render подтверждён.
