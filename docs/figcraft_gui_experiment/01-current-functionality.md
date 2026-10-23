---
id: ic-figcraft-current-functionality
title: "FigCraft → PySide6: фактическая функциональность Image Compressor"
kind: research
status: proposed
created: "2026-10-23"
updated: "2026-10-23"
areas: [gui, command-first, data-safety]
summary: "Source-only карта существующих возможностей, отличий старого GUI и обязательных гарантий для отдельного PySide6-эксперимента."
code_ref: "58afb9b648ebe63bfb6fc2f5123e77165b3e0db9"
code_verified_at: "2026-10-23"
verification_scope: "Чтение исходников, manifest и тестов; не новый runtime или visual PASS."
---

# Рамка и установленная база

Новая задача — **отдельный FigCraft-дизайн и отдельный экспериментальный GUI на PySide6** на существующей ветке `refactor/command-first`. Это не повтор принятого command-first-рефакторинга. Старые task-specific запреты нового GUI заменены текущим поручением; сохранность данных, независимая проверка и ограничения полномочий остаются.

Read-only Git-проверка показала указанную ветку, HEAD выше и чистое tracked/untracked дерево до записи этих документов. Полное ТЗ прочитано из побайтной копии: 574 строки, SHA-256 `b8cdfcc394fa43f19b5f082d9bb458f17ba5d920d8819bc9b5329b11d5048d98`; хеш исходного paste совпал. Изображения пользователя, credentials, `.env` и чужие сессии не читались.

Канон поведения — [Application API v1](../architecture/application-api.md), не этот обзор. Последующая реализация описана в [плане](02-implementation-plan.md). Исторические 170 independently accepted тестов относятся к [предыдущей проверке](../verification/command-first-refactoring.md), **не запускались Oracle заново**.

## Реальные владельцы

| Вход/owner | Что существует в этой базе |
|---|---|
| `image_compressor/__init__.py:3–40` | Публичные `convert`, `discover_inputs`, `get_capabilities`, frozen DTO и token; нет Qt или parser в API. |
| `image_compressor/models.py:202–271,274–383` | Запрос, строгая валидация, результат, прогресс, capabilities и cooperative token. |
| `image_compressor/service.py:92–404` | Один синхронный последовательный batch: discovery → preflight → encode → verify → publish → readback → result. |
| `image_compressor/discovery.py:64–246` | Поиск, стабильный порядок, дедупликация, discovery issues; без decode и записи. |
| `image_compressor/imaging.py:59–104,125–248` | Lazy probes/codecs, image policy, resize, encoder и verifier. |
| `image_compressor/filesystem.py:158–167,193–294` | Имена, собственный staging, атомарная create-only публикация, ограниченная очистка. |
| `image_compressor/cli.py:46–66,119–125,145–218` | Настоящий parser, JSON/exit и signal→token адаптер. |
| `classes.py:41–114` | Совместимый `ImageCompressor`, не альтернативный backend; `classes.py ...` перенаправляет в CLI. |
| `gui_main.py:6–17`, `gui/__init__.py:30–39` | Старый отдельный запуск PyQt6 Widgets/Fusion. |
| `gui/main_window.py:157–275`, `gui/worker.py:51–124` | Старое окно → один `convert` в QThread; результат/отмена/отложенное закрытие. |

Новая оболочка может использовать API **непосредственно**, не CLI subprocess, не `classes.py` и не PyQt-worker. Профиль A уже достаточен: новая очередь — локальное представление выбранных файлов, не backend Job Manager.

# Возможности из ТЗ, подтверждённые исходниками

| Возможность | API / CLI | Существующий GUI и существенное отличие |
|---|---|---|
| Один файл | `ConversionRequest([path])`; CLI `convert path`. | `DropZone.open_file_dialog`, `gui/widgets.py:85–96`: ExistingFiles допускает один выбор. |
| Несколько файлов | Sequence фиксируется tuple; порядок roots сохраняется. | Тот же multi-select dialog или local-file drag & drop (`widgets.py:71–96`). |
| Папка | `discover_inputs` / `convert` принимают каталоги. | **Папку можно перетащить**. Отдельной кнопки/диалога выбора папки нет; ExistingFiles — не directory picker. |
| Рекурсивный обход | API/CLI default False, CLI `--recursive`. | `main_window.py:159`, `gui/utils.py:20`, `worker.py:88`: всегда True; переключателя нет. |
| Входы | `.jpg/.jpeg/.png/.webp/.heic/.heif/.avif`, регистр неважен (`models.py:22–38`). Actual format также проверяется. | Фильтр диалога соответствует расширениям; доступность декодера не выводится. |
| Выходы | JPEG/JPG → JPEG, WebP, HEIF/HEIC → HEIF, AVIF. **PNG только вход**. | Четыре radio, default WEBP (`widgets.py:147–194`). Не отключаются по фактическим capabilities. |
| Качество | Строго integer **0..100**, default 80; bool/float/string отвергаются (`models.py:157–162`). | Slider **1..100**, default 80 (`widgets.py:112–118`): ноль через старый UI недоступен. |
| Resize on/off | Оба лимита None — выключен; иначе нужны обе положительные целые стороны. | Checkbox default False; поля сначала disabled. Placeholder 1920/1080 — **не введённые значения** (`widgets.py:203–246`). |
| Max width/height | В пикселях, fit с сохранением пропорций, без upscale/crop; LANCZOS. | Проверяет наличие обеих сторон перед worker (`main_window.py:190–203`). |
| Удаление оригиналов | **Не поддерживается.** `validate_request` отклоняет True до discovery/эффектов (`models.py:234–241`). CLI delete-флага нет. | Checkbox существует/default False (`widgets.py:307–309`), но True честно передаётся backend и вызывает отказ с объяснением (`worker.py:86–112`). Наличие checkbox не означает функцию удаления. |
| Постфикс | Default `_compressed`; добавляется только при совпадении suffix-family входа и выхода, не при любой коллизии. Пустая строка допустима как ввод, но совпавшая цель откажет. | `get_postfix` делает `strip() or "_compressed"` (`widgets.py:328–330`): пустой/whitespace ввод подменяется default, в отличие от API. |
| Прогресс | Immutable discovering/item_started/item_finished/finished; при discovery total=None; внутри native codec процентов нет. | Worker выдаёт проценты на item_finished; только `processed=succeeded+failed`, cancelled не входит (`worker.py:54–56`). |
| Лог | Закрытая безопасная техническая проекция, результат отдельно; постоянного журнала/телеметрии нет. | QTextEdit максимум 200 px (`main_window.py:145–155`), без ограничения числа блоков; по умолчанию не read-only. Старые resize getters печатают DEBUG/raw ValueError — весь старый GUI не privacy-certified. |
| Остановка | `CancellationToken.cancel()`, checkpoints; не kill/rollback. | Stop только запрашивает отмену. Worker удерживается до настоящего QThread.finished, start заблокирован, close отложен (`main_window.py:215–264`). |
| Очистка очереди | Нет удаления файлов; это локальное действие адаптера. | Сбрасывает list, только когда нет worker (`main_window.py:266–275`). |
| Совпадения имён | Только fail, без overwrite/auto-numbering/silent skip. | Через тот же API, отдельного безопасного режима разрешения коллизий UI не имеет. |
| «Тот же формат» | Допускается повторное кодирование в новый файл с postfix, включая alias-family JPEG/JPG, HEIC/HEIF. Не считается no-op. | Работает через общий worker; оригинал остаётся. |
| Каталог/точное имя результата | API и CLI имеют output_directory / output_path с ограничениями. | Старый GUI не предлагает их; результат рядом с исходником. Добавлять эти дополнительные настройки в минимальный эксперимент не требуется. |

## Настоящие defaults

- API и CLI: WEBP / 80 / без resize / recursive=False / `_compressed` / delete=False / рядом с источником.
- Старый GUI: WEBP / 80 / resize off / recursive=True / `_compressed` / delete unchecked.
- Старый Python facade: **HEIF / 50**, directory/input recursive=True (`classes.py:45–57,97–101`). Не переносить эти defaults случайно в новый GUI.
- Дополнительные кодеки проверяются реальным синтетическим in-memory roundtrip, лениво и с process cache. `decoder_registered` не гарантирует прочтение любого файла; `encoder_available`, `alpha_verified`, provider/reason — отдельные факты (`imaging.py:59–104`).

# Имена, ошибки и сохранность

Примеры общего owner `filesystem.destination_for`:

- `a.png → a.webp`; `a.webp → a_compressed.webp`.
- `a.jpeg → a_compressed.jpg`; `a.heif → a_compressed.heic` при соответствующем output format.
- Постфикс **не является стратегией “если имя занято, добавь суффикс”**.
- Пустой postfix для `a.webp → WEBP` даёт `INPUT_OUTPUT_CONFLICT`, не перезапись.
- Уже существующее имя любого типа → `OUTPUT_EXISTS`.
- `a.png` и `a.jpg`, оба в WEBP в одном каталоге → оба `TARGET_CONFLICT`; независимый `ok.png` продолжает работу.
- Цель, совпавшая с любым input path/identity, → `INPUT_OUTPUT_CONFLICT`; hardlink alias также защищён.
- Exact output: только один явно выбранный файл, подходящий suffix, существующий parent. Output directory: существующий обычный каталог, flat layout, не создание дерева.

Discovery сначала фиксирует полный manifest. Сортировка внутри root по casefold + исходной строке относительного пути; first-wins dedup по normalized path и доступной dev/inode identity. Symlink/junction/reparse не обходятся; ошибки/ignored/duplicates не скрываются. Новые результаты текущего batch не становятся его входами; старые outputs не исключаются эвристикой имени. Public `DiscoveryResult` содержит **paths и issues раздельно**, без общих индексов и без metadata/размеров файлов. Предварительный UI discovery не резервирует файлы: `convert` создаёт свой новый manifest и проверяет актуальные условия.

Публикация (`service.py:133–224`, `filesystem.py:279–294`): собственный staging рядом с target → decode/проверка подготовленного результата → atomic `os.link` без замены → final readback/hash/identity. При unsupported hard links — отказ без опасного fallback. При отказе **после** link остаётся artifact `unverified` / `PUBLISHED_UNVERIFIED`; нельзя писать «ничего не создано» или удалять результат для отката. Cleanup удаляет только собственный учтённый payload и пустой dir; остаток обозначается `TEMP_CLEANUP_FAILED`. Исходники не удаляются и не заменяются.

Это не fsync/crash recovery, не транзакция всего пакета, не sandbox от враждебных гонок. Прежняя квалификация — local NTFS. Нет жёстких RAM/CPU/time budgets для кодека.

## Итог и отмена, которые UI обязан различать

- `rejected`: общая валидация/недоступный encoder/пустой набор; не подменять успехом «0 обработано».
- `failed`: ошибки без успешных/опубликованных результатов.
- `partial`: успех/публикация вместе с ошибкой либо cleanup residual.
- `cancelled`: token действительно остановил работу; уже опубликованные файлы остаются.
- `succeeded`: реальный полный успех, а не один завершившийся QThread.
- `published` не равно `succeeded`; `total=succeeded+failed+cancelled`; duplicates/ignored отдельно. Ошибки всего batch и item errors показываются обе.
- «Остановка запрошена» не означает «остановлено». Native codec может долго не возвращать управление. После последнего checkpoint текущая публикация допустима; слишком поздний cancel не превращает уже завершённый успех в cancelled.
- Каждый новый запуск — новый token/worker. Повтор — новое действие и может дать OUTPUT_EXISTS. Нет автоматического retry/overwrite.
- Callback синхронный и должен быть коротким; его exception отключает дальнейшие callbacks, добавляет OBSERVER_FAILED, не отменяя реальную обработку (`service.py:37–68`). Финальный BatchResult — авторитетнее промежуточного экрана/лога.

## Image policy, которую нельзя обещать иначе

`imaging.py:125–248`: статические обычные 8-bit изображения; multiframe, неподдерживаемые modes, 16-bit PNG/HDR, повреждённые/truncated/bomb inputs отвергаются. EXIF orientation применяется до fit. Для 4000×3000 в 1920×1080 результат 1440×1080. JPEG композирует прозрачность на белый; для иных выходов важна реальная прозрачность подготовленного растра и alpha capability. EXIF/XMP/ICC/comments не сохраняются. Меньший размер файла, lossless и цветометрическая идентичность не гарантируются.

# Ограничения старого интерфейса и must-preserve flows

Старая раскладка — вертикальная форма, минимум 600×700, обычный размер 800×700 (`main_window.py:46–104`). Очередь — внутренний list и число в drop zone, **не пофайловый список** с format/bytes/status. Нет новой темы, locale catalog, отдельного folder picker, recursive switch и capability-aware selector. Discovery выполняется синхронно в UI handler: для большой папки возможна блокировка окна. Во время работы настройки/drop zone не полностью блокируются; worker уже использует snapshot, а отображаемая очередь может измениться. Это source finding, не измеренный runtime дефект. Старое окно сохраняется без исправлений в этом эксперименте.

В новой оболочке обязательны:

1. Выбрать один/несколько файлов или папку/drop → увидеть **реальный discovery**, valid files и отдельные selection issues, duplicates/ignored.
2. WEBP/80 по умолчанию → изменить формат/качество/resize/границы → один batch общего API → читаемые реальные outputs рядом с исходниками.
3. Same-format + postfix → новый файл; коллизия → явная ошибка без порчи источника/прежнего output.
4. Смешанный корректный/повреждённый набор → partial и поэлементные исходы, не общий зелёный success.
5. Stop / close во время discovery или conversion → запрос, отзывчивое ожидание, фактический итог, безопасный teardown; затем новый запуск.
6. Clear очищает только UI; theme/locale switch не меняет выбранные файлы, options snapshot и текущую операцию.
7. **Удаление оригиналов недоступно**: показать disabled unchecked control и постоянное объяснение. Backend не расширять, deletion в UI не реализовывать. Требование ТЗ о включении удаления остаётся явно названным gap, а не выполненной функцией.

# Проверочная основа и границы этого исследования

Изучены настоящие tests: `test_api.py:14–95` (readback/validation), `test_filesystem.py:19–104` (same-format/collision/alias), `test_cancellation.py:7–127`, `test_discovery.py`, `test_gui_adapter.py:56–292` (QCoreApplication + реальные QThreads, но lightweight views), `test_packaging.py:55–166` (wheel в disposable root без Qt), test_codecs/imaging_policy/privacy. Прочитанный тест не новый PASS; старые controller tests не доказывают геометрию QWidget.

`pyproject.toml:27–57`: runtime только Pillow; optional `gui` — PyQt6, codecs/build/dev отдельно; explicit packages `[image_compressor, gui]`, `gui_main` сохранён. `requirements.txt` указывает `.[gui,codecs,build]`. PySide6 не заявлен и **не установлен в текущей .venv**. Read-only distribution metadata: Python 3.14.2, Pillow 12.1.0, PyQt6 6.10.2, pillow-heif 1.2.0, pillow-avif-plugin 1.5.5, pytest 9.1.1, pytest-timeout 2.4.0, Ruff 0.17.2, mypy 2.4.0. Это наличие distribution, не codec probe и не compatibility claim.

**NOT RUN:** приложение, конвертация, suite/lint/types, установка PySide6, новый/старый GUI smoke, скриншоты, создание/сохранение FigCraft-дизайна. Выполнены только source/tooling discovery и read-only preflight отдельной пустой официальной FigCraft headless-сессии. План следующего владельца — [02-implementation-plan.md](02-implementation-plan.md).
