---
id: ic-figcraft-pyside6-report
title: "FigCraft → PySide6 — результат инженерного эксперимента"
kind: verification
status: accepted
created: "2026-10-23"
updated: "2026-10-24"
areas: [design, gui, pyside6, testing]
summary: "Редактируемый FigCraft-дизайн, отдельный работающий GUI на принятом API и фактические проверки переноса, поставки и сохранности."
code_ref: "58afb9b648ebe63bfb6fc2f5123e77165b3e0db9 + accepted source/test inventory SHA-256 7111b419752f74e9bb4fc3b7063c6771d7aea91d858f156f699e3e34a0e8793e"
code_verified_at: "2026-10-23"
verification_scope: "Отдельный независимый технический и визуальный ACCEPT: реальные Qt/API/CLI/readback, native FigCraft tree/reopen/export и installed GUI на Windows; последующий docs/package closeout — авторская проверка той же роли."
---

# Результат и граница

На существующей `refactor/command-first`, база `58afb9b648ebe63bfb6fc2f5123e77165b3e0db9`, выполнен отдельный эксперимент по [выпущенному плану](02-implementation-plan.md). Результат — настоящий FigCraft native и **opt-in `gui_pyside6_v2`**, а не замена прежнего окна или новый компрессор.

Ядро `image_compressor/`, facade, `gui/`, `gui_main.py` и PFK snapshot не изменены. Из прежних tests изменён только необходимый packaging snapshot/assertions. Старые command-first ACCEPT и ограничения остаются историческими фактами, **не приёмкой нового GUI**. Coder не stage/commit/push. Отдельный Reviewer завершил независимую техническую и визуальную приёмку: **ACCEPT**, обязательных source/test/design findings нет. Последующий docs closeout и selective доставка принадлежат той же принимающей роли, не второму независимому review.

- [Запуск и synthetic сценарий](RUNNING.md).
- [Дизайн, frame IDs, tokens и Qt mapping](03-design-spec.md).
- [Native FigCraft](../../design/figcraft/image-compressor-v2.figcraft).
- [Восемь финальных экспортов и SHA-256](../../design/exports/20261023-candidate-03/manifest.json).

# Что сделано

## 1. Основа и FigCraft

Фактические функции и API уже исследованы Oracle; повторный общий аудит не проводился. До реализации точечно синхронизированы AGENTS/роли/инструкции. Сохранены отдельные Qt-среды и один автор дизайна/экспортов.

Официальный FigCraft CLI **0.10.0**: собственный read-only headless preflight → маленький component/instance proof → компоненты/variables/layout → восемь screens → native save/fresh reopen → PNG. Чужой редактор/control/document не использовался. Ручного native JSON/ZIP, импортированного screenshot вместо компонентов или иной дизайн-программы нет.

Финальные факты:

- 2 страницы, 8 основных screens: RU Empty/Queue/Processing × Light/Dark; EN Queue Light и KK Queue Dark 900×640.
- **10 masters / 148 instances**, связанные `mainComponent`; **748 layers**, либо750 nodes с двумя PAGE в `info`. IMAGE layers0; editable TEXT/VECTOR присутствуют.
- 56 variables: независимые Theme Light/Dark, Locale RU/EN/KK, Metrics. Boolean Checked действительно управляет checkbox vector; resize-off defaults исправлены.
- Master-only изменение radius8→12/height40→48 наследуется двумя instances с сохранением разных labels. Root resize800→900 меняет Fill spacer224→324, без ручного reposition.
- Fresh native reopen подтвердил components/properties/bindings и Theme/Locale modes; `missingFonts=[]`. Сам `.figcraft` записан только движком.
- Собственный Add SVG реально экспортирован FigCraft, bounds проверены QtSvg; Segoe UI не копируется в distribution.

Native SHA-256: `440b5b8e58948d86b9c19a59e1529e51ee1cc4779e9f5cf0804b4c126fbe8dd9`.

Дизайн ограничен пятью iterations; финальные восемь PNG просмотрены индивидуально и в галерее. Старые exports/native snapshots сохранены, но не считаются дополнительными состояниями. Финальный повторный CLI-export дал те же восемь PNG hashes.

## 2. Рабочий PySide6 адаптер

Реализованы:

- один/несколько файлов, folder picker, local-file drop; HTTP URLs отвергаются;
- background discovery/stat, recursive next-add, dedup, отдельные selection issues/ignored/duplicates и явный valid subset;
- QTableView/model: имя, suffix (не обещание actual decoded format), bytes/unknown, реальные пофайловые результаты и tooltips;
- JPEG/WebP/HEIF/AVIF с фактическими capability probes; quality0..100/80, resize off/on, max width/height, exact postfix;
- один immutable request → один публичный `convert`, без CLI subprocess/дублирования naming/collision/publication policy;
- Start/Stop/Clear, indeterminate/discrete progress без выдуманного процента внутри codec; новые tokens, удержание worker до настоящего QThread.finished, отложенное close;
- succeeded/failed/rejected/partial/cancelled, отдельный published/unverified и warnings; сохранность исходных/предыдущих bytes;
- Light/Dark и RU/EN/KK без сброса ввода, очереди, результата или выполняющейся операции;
- bounded read-only technical log500 blocks, отдельный локальный result pane с допустимыми путями. Нет telemetry/persistent logging.

**Удаление оригиналов не работает и не реализовано.** Видимый unchecked/disabled control постоянно объясняет: безопасный API сохраняет исходники. Backend True по-прежнему rejected до эффектов. Это явный gap исходного запроса о работающем delete switch, а не фиктивное выполнение требования.

Код разделён на entry/window, reusable widgets, controller, QThread transport, queue model, localization и theme/tokens/assets. Runtime не требует FigCraft.

# Авторские проверки

Среды: Windows11/local NTFS, Python3.14.2. Legacy: PyQt6 6.10.2/Pillow12.1.0. Отдельная новая среда: **PySide6/Qt6.12.0/Pillow13.0.0**, без PyQt6. JPEG/WebP/HEIF/AVIF в новой среде прошли реальные probes и GUI conversions; HEIF provider — pillow_heif, остальные — Pillow. PNG остаётся только входом.

| Проверка | Фактический результат |
|---|---|
| Новый изолированный suite | **47 passed, 0 skips**, две test-side deprecation warnings QDragEnter constructor |
| Сохранённый `tests/`, другой interpreter/process | **170 passed, 0 skips** |
| Финальная README/wheel selection | **2 passed**, входит в прежние170, не172 уникальных теста |
| Ruff GUI/new tests/packaging/design helpers | exit0 |
| Strict mypy GUI | exit0, 9 modules, `--follow-imports=silent` |
| Strict mypy неизменённого ядра/facade в legacy среде | exit0, 11 modules |
| Native FigCraft save/reopen/tree/modes/exports | exit0; links/modes/PNG readback подтверждены |
| Windows visible PySide gallery | **19 PNG / 19 unique hashes**, оба theme и все языки; собственные окна закрыты |
| Legacy Windows show/resize/event-loop/close | отдельный PyQt process, exit0 |
| Installed optional wheel вне source cwd, `python -I` | настоящий module entry/event loop, keyboard Start, WebP + JPEG readback, close, exit0 |
| Bare wheel | по-прежнему Pillow-only: нет PyQt/PySide/optional providers, API/CLI/facade работают, новый optional entry даёт понятный exit2 |

Новый suite проходит настоящий MainWindow action → controller/worker → API → Pillow → файл → `Image.open().load()`: JPEG/WebP quality0/80/100, 400×300→144×108, no-upscale, HEIF/AVIF; exact empty postfix, same-format, повтор/OUTPUT_EXISTS, общая target collision, good+corrupt partial. Проверяются source/prior-output bytes, artifact digest/format/size и clear без удаления.

Cancel использует контролируемые barriers вокруг **реального** encode/link: heartbeat жив, stop быстро возвращается, результат-ready не освобождает работающий thread, post-publication файлы остаются, поздняя отмена может дать succeeded; следующий batch использует новый token. Есть incomplete discovery, close до dispatch/во время capabilities/discovery/conversion, stale generation и положительная доставка.

Unsafe outcome: fault final readback после реального link даёт unverified/partial, не зелёный success. Cleanup-warning transport проверен controlled seam после настоящей очистки — это **не доказательство физического residual** в новом GUI; файловые cleanup guarantees принадлежат неизменённому API и его regression suite. Observer failure не скрывает финальный результат.

Technical buffer реально прочитан: непустые outcomes/codes/counts есть, synthetic filename/path/postfix/raw-exception sentinels отсутствуют. Локальные table/results — отдельный допустимый канал, весь legacy GUI privacy-certified не объявляется.

## Авторский installed artifact

Wheel SHA-256: `b97751b9ce402e71f59fbd758ca292496e28e2ab57a22f1acbd7ccd13fe54716`.

Optional extra установлен в отдельную PySide среду. Probe с cwd вне source и `-I` подтвердил import из `site-packages`, **побайтное равенство всех новых GUI source/data** текущему кандидату, отсутствие второго binding и настоящий `gui_pyside6_v2.__main__` event loop. Созданы читаемые WebP/JPEG144×108, JPEG quality0; исходный PNG неизменён. Это не editable-only запуск и не опубликованный EXE/release.

# Независимая техническая и визуальная приёмка

Reviewer в отдельной сохранённой Pi-беседе на `openai-codex/gpt-6.1-sol`, requested/observed PI reasoning `max`, прочитал полное ТЗ, Oracle plan/map, frozen Coder result и реальные bytes. До вердикта все 83 candidate paths и два Oracle-документа оставались побайтно неизменными, index пуст; core/old GUI/PFK совпали с базой. Candidate inventory SHA-256: `56d60aa7a6163b633ac415930abcc4ecea8a676096b23e13aa895af0bee42405`. Oracle research/plan остаются историческим source-only результатом, не runtime PASS.

| Независимый запуск | Raw exit / результат |
|---|---|
| Отдельный PySide Python: `-B -m pytest -p pytest_timeout -p no:cacheprovider tests_pyside6_v2 -q`, own basetemp | **0; 47 passed, 0 skips**, 2 test-side deprecation warnings |
| Legacy Python: тот же runner, selection `tests`, другой own basetemp/process | **0; 170 passed, 0 skips**, включая свежие bare-wheel build/install/API/CLI/facade |
| Ruff новой Python-области/tests/packaging/design helpers | **0** |
| GUI mypy `--follow-imports=silent gui_pyside6_v2`; отдельно legacy mypy `image_compressor classes.py` | **0 / 0**, 9/11 modules |
| Официальный CLI0.10.0: fresh native open/deep tree/modes/export | **0**, 8 экспортов побайтно совпали с final manifest |
| Windows `tests_pyside6_v2.gallery --visible` в свежем собственном root | **0**, 19 PNG/19 unique; все просмотрены individually |
| PySide-only installed Python `-I -B tests_pyside6_v2/installed_probe.py`, cwd вне source | **0**, настоящий module entry/exec, keyboard Start, WebP/JPEG144×108 и quality0; package bytes равны source |
| Собственный native connected probe | **0**, close внутри настоящего encode, heartbeat жив, cancelled/no final; invalid postfix→rejected→successful retry→OUTPUT_EXISTS, source/output bytes сохранены, clear не удаляет файлы, полезный private-free buffer |
| Настоящий legacy MainWindow/QApplication.exec в другом процессе | **0**, show/resize/action→API→WebP80×60/readback/close; только modal information заменён controlled OK |

Это **217 разных suite cases**, не сумма пересекающихся повторов/галерей. Optional installed environment разрешённо переиспользован read-only и независимо исполнен/сверен; новой установки PySide для review не было. Bare wheel Reviewer действительно собрал/установил заново, 28 package source/data файлов побайтно равны source. Точные argv/cwd/raw stdout/stderr/exits, входные hashes и PNG manifests сохранены в отдельном игнорируемом reviewer evidence root; приватные сессии/venvs/outputs не входят в публичный payload.

Независимое native inspection: 748 layers, 10 masters, 148 linked instances, editable TEXT/VECTOR, IMAGE0, 615 узлов с `boundVariables`, Theme/Locale modes и boolean Checked. На **собственной копии**, не кандидате, master3 radius12→16/height48→52 наследован instances5/7 с сохранением RU/KK labels; root900→1000 автоматически расширил Fill spacer324→424 при прежнем x552. Fresh reopen подтверждает сохранённые links/геометрию. Посмотрены все 8 design PNG, все19 current Qt PNG, 3 installed PNG и собственный live-closing/legacy кадр: композиция/палитра согласованы, EN/KK minimum fit, glyphs читаемы, footer/safety доступны, stop/cancel/partial/success различимы. Подробности адаптации ниже.

Ошибки reviewer fixtures не скрыты: два ранних capture-launch с неверным положением argparse options завершились host exit1/WinError2 **до pytest**. Первый legacy probe создал второй QApplication через launcher и получил raw3221225477/0xC0000005; исправлен только probe, повтор с одним QApplication/настоящим MainWindow дал exit0/readback. Первый summary parser искал несуществующий `variableBindings`; фактический deep tree содержит `boundVariables`, отдельная проверка подтвердила615 узлов. Кандидат ради этих probes не менялся.

**Решение: ACCEPT — технический и визуальный.** Принят именно ограниченный opt-in эксперимент с явно недоступным удалением, а не все исходные wishlist-возможности. Физический OS-dialog/drop, интерактивные editor-window клики и screen reader не проверялись. Другие платформы/DPI/EXE и productivity benchmark не становятся PASS от этого решения.

## Документационный closeout после ACCEPT

Та же принимающая роль сохранила исходный verdict/evidence и прежние документы перед обновлением статусов/README/REPORT/инструкций/профилей. Source/tests/design/product manifest не менялись. Собственная **авторская проверка closeout**, не второе независимое review: final README packaging selection `tests/test_packaging.py` — exit0, **2 passed** (subset прежних170); bare installed API/CLI/facade и optional-missing exit2 прошли. Структурный checker — exit0, checked19/findings=[]; он не доказывает runtime. Полные неизменённые suites не повторялись ради новой даты. Применимых required branch rules нет; отсутствие CI checks не называется green CI. Selective сохранение/доставка проверяются по точным Git blobs/SHA, без публикации private evidence, environments или build outputs.

# Rendered наблюдения и отличия от макета

Qt проверен при 1120×760 и900×640 logical px, в12 language/theme/size комбинациях. Длинная очередь1000 rows и log1200 событий не растят minimumSize; таблица/форма прокручиваются, footer/safety остаются доступны. Tab/Space/Enter, focus, selection и combo popup проверены действием, не только PNG.

Финальная native gallery: Windows QPA, **DPR1.5**, main client captures1680×1140 либо1350×960; requested/resolved Segoe UI. Отдельный popup capture действительно показывает JPEG/WebP/HEIF/AVIF и selected colors. Ещё3 свежих installed-wheel captures — KK Dark minimum queue и два terminal successes. Все данные synthetic. Screens manifests содержат source/native/output hashes, renderer, DPR, logical/raw sizes, font и test barriers.

Наблюдения: общая двухколоночная композиция/палитра сохранена; ключевые подписи и KK glyphs читаются; scroll не сдвигает footer; stop-requested отличается от cancelled; partial amber/error rows не masquerade как полный success. На minimum последняя строка таблицы может быть частично видна **в scroll viewport**, что не является clipping кнопки/важного пояснения. Файлы намеренно elide с tooltip.

Осознанные отличия:

- настоящие Qt scrollbars/gutter, platform controls и table model вместо нарисованных форм/rows;
- Label/Checked — реальная Qt semantics, не автоматическое поведение FigCraft;
- log/details tabs и отдельные terminal counts, а не один декоративный status badge;
- активность показана общим progress/status: API item_started не передаёт source, поэтому active row не угадывается по index. Completed rows обновляются по actual source; это отличие от highlighted running row макета;
- сравнение ведётся в logical px, не по pixel-perfect совпадению Skia и Qt/DirectWrite при разных DPR.

# Первая ошибка и ограничения

Авторские RED сохранены, не стерты последующим PASS: stale startup error после retry; слишком длинная safety checkbox label; устаревший progress и completed row при throttling; Enter не активировал focused primary button вне QDialog. Исправления — reset error нового запроса, отдельная wrap-label рядом с disabled indicator, GUI polling latest immutable event + batched completed items и явный QPushButton autoDefault для focused Enter. Assertions не ослаблены.

Первый Windows offscreen PNG содержал tofu: этот QPA не перечисляет system fonts. Test helpers загружают установленные Segoe UI faces **только в память своего процесса**; нормальный Windows QPA использует system fonts сам. Неоднозначный `inFont(str)` QChar overload давал ложный отказ KK; заменён точным Unicode codepoint API и actual-face coverage. Первое mypy в новой среде также показало ошибки неизменённого ядра под Pillow13 stubs: ядро не менялось; его strict gate выполнен отдельно в сохранённой среде, GUI проверен полностью в своей области. Эти ошибки окружения/fixture не объявляются дефектами принятого backend.

**NOT RUN / не обещано:** физический native file-dialog selection/OS drag-drop, screen-reader certification; иные ОС/Python/FS, все DPI/remote shares, hard codec timeout/RAM budget/crash durability, меньший размер файла, сохранение metadata/цветометрии, EXE/release. RU/EN/KK — рабочие каталоги и visual fit, не профессиональная native-language certification. Полного comparative benchmark времени FigCraft против ручного Qt-дизайна нет; durations отдельных команд не доказательство экономии времени.

# Что дал FigCraft, а что осталось вручную

| Реально перенесено | Вручную в PySide6 |
|---|---|
| композиция header/queue/settings/footer | Qt layouts/size policies/scroll/focus |
| 9 основных component contracts + proof master, instances/properties | QPushButton/inputs/model-view и доступность |
| semantic palette, Theme/Locale, spacing/radius/type metrics | normalization → QSS/QPalette/QFont, popup/selection states |
| SVG geometry, editable text/vector, state references | QtSvg tint/resources/package-data |
| оба theme и языковые fit-пробы | catalog/runtime retranslate, API error/count formatting |
| native/exports как воспроизводимый reference | controller, signals/thread lifetime, cancellation, backend integration и tests |

Неудобства конкретны: CLI требует точных схем/ID и отдельного deep tree inspection; обычный node.get недостаточно глубок. Default frame fills нужно задавать явно. VECTOR bounds проверяются экспортом, иначе icon может быть clipped. Auto Layout не реализует настоящий scroll/model; native fonts/DPR проверяются заново. Экспортеров Python/QSS/QML/.ui в FigCraft0.10.0 нет. Нормализованные tokens — поддерживаемый проектный слой, не произвольное переименование CSS в QSS.

Для больших PySide6-проектов полезно сохранять эту границу: FigCraft владеет графической спецификацией/состояниями, приложение — поведением и API. Components/tokens снимают часть угадывания, но не создают lifecycle, accessibility, model/view и приемочные tests. Эксперимент не доказывает автоматическое масштабирование или измеренный выигрыш скорости.

## Итоговая оценка пригодности связки FigCraft → PySide6

**Годится с оговорками:** FigCraft полезен как настоящий редактируемый источник структуры, components, тем, tokens, SVG и visual references. Для Qt Widgets перенос остаётся разумной ручной инженерной работой. В этом эксперименте получился реальный установленный GUI на прежней логике; автоматической генерации работающего Python-интерфейса не было и не заявляется.

## 2026-10-24 · отдельное исправление мелких контролов

Последующий source-only срез получил собственный [технический и визуальный ACCEPT](06-controls-verification.md): полные Fusion subcontrol rules, полезные hit areas стрелок, читаемые numeric insets, согласованные открытые combo lists и различимые checkbox states обеих тем. Свежие независимые32 адресных cases плюс2 native source cases прошли;8 HiDPI cases повторяют подмножество. Просмотрены contact sheet и16 собственных отдельных PNG. Общая компоновка/RU/EN/KK и прикладное поведение сохранены.

Исходные результаты/ограничения этого отчёта выше остаются исторической приёмкой своего inventory, не доказательством удобства всех последующих состояний. Controls-кандидат —15 source/test/asset paths, не новый FigCraft-дизайн и не весь feedback repair. Действующее удаление и человеческий журнал/полезные детали пока не реализованы новым функциональным срезом; прежний EXE не изменён и **не содержит controls-исправлений**. Их будущая installed/frozen проверка и новый интегрированный EXE имеют отдельный gate. Точная область, механизм, фактические capture/input проверки и packaged-resource handoff — в новом verification.
