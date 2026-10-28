---
id: ic-application-api
title: "Image Compressor — прикладной контракт v1"
kind: contract
status: accepted
created: "2026-10-23"
updated: "2026-10-28"
areas: [architecture, command-first, conversion, data-safety]
summary: "Независимо принятый синхронный API, create-only публикация, JSON CLI и совместимые потребители с явными пределами."
code_ref: "770784935c52eaa3add6a9a1ec50b5154c9f1e3c + accepted source/test inventory SHA-256 9ef5bbf6c4af8af07f3c2744212f103b6666a94568841c2fcc99aa64d541dccd"
code_verified_at: "2026-10-23"
verification_scope: "Авторские проверки и независимый ACCEPT всей API/CLI/filesystem/Qt/installed-wheel границы после ремонта R1/R2; последующий docs closeout не меняет source/tests."
---

# Область и канон

Профиль **A, синхронный прикладной сервис**: вызов возвращает окончательный результат, последовательно обрабатывая один фиксированный пакет. Нет jobs, очереди, IPC, демона, БД, MCP или общей живой сессии между процессами. План и границы решения — [Oracle](../plans/command-first-refactoring.md); фактические проверки/ограничения — [verification](../verification/command-first-refactoring.md). Технический срез независимо принят после ремонта R1/R2: Reviewer повторил 170 тестов без skips и исходные discriminator/control cases через API/source CLI/installed API+CLI. Последующий docs closeout не меняет код/контракт и проверяется автором closeout, не выдаётся за новую независимую приёмку.

**Исполняемый канон:** [models.py](../../image_compressor/models.py) (frozen DTO, defaults, validator, ErrorCode), [service.py](../../image_compressor/service.py) (сценарий), [serialization.py](../../image_compressor/serialization.py) (JSON-проекция закрытого набора DTO). Ручной JSON Schema нет. Зависимости идут от адаптеров в API, не наоборот.

| Владелец | Ответственность / реальные consumers |
|---|---|
| [Публичный API](../../image_compressor/__init__.py) | `convert`, `discover_inputs`, `get_capabilities`, DTO; без Qt/parser/input/prints и import-time codec probes |
| [Discovery](../../image_compressor/discovery.py) | Снимок, порядок, dedup, ошибки обхода; service, GUI finder/handler |
| [Imaging](../../image_compressor/imaging.py) | Lazy codecs под lock, capability cache процесса, Pillow/resize/полное декодирование; service |
| [Filesystem](../../image_compressor/filesystem.py) | Identity, имена, staging, атомарный create-only link, только своя очистка; service |
| [Diagnostics](../../image_compressor/diagnostics.py) | Закрытая техническая проекция; logging sinks host-а и CLI, Qt log signals |
| [CLI](../../image_compressor/cli.py) | argparse, сигналы, UTF-8 JSON/exit/delivery; console script, `python -m image_compressor` |
| Legacy PyQt6 GUI и compatibility facade | Удалены из рабочей копии в legacy-retirement 2026-10-28 (история сохранена в Git). Canonical GUI — [gui_pyside6_v2](../../gui_pyside6_v2/window.py); старые worker/handlers/class больше не поставляются. |

# Операции

```python
get_capabilities() -> Capabilities
# Synthetic in-memory probes; не читает пользовательские каталоги.
discover_inputs(inputs, *, recursive=False, exclude_directory=None,
                cancellation=None) -> DiscoveryResult
# Только имена/stat (на Windows также descriptor stat), без decode/записи.
convert(request: ConversionRequest, *, cancellation=None,
        on_progress=None) -> BatchResult
```

Запрос/результаты неизменяемые; sequences фиксируются tuple. Конструктор DTO не подтверждает корректность: общий runtime validator исполняется при каждом `convert`. Пути — `str`/`os.PathLike[str]`, относительно cwd начала вызова; env/`~`/glob/кавычки не раскрываются. Один str вместо sequence, bytes, NUL, пустая sequence/строка, неверный тип отвергаются.

| Поле ConversionRequest | Default и правило |
|---|---|
| `inputs` | Непустая последовательность файлов/каталогов |
| `output_format` | `WEBP`; case-insensitive JPEG/JPG, WEBP, HEIF/HEIC, AVIF → canonical JPEG/WEBP/HEIF/AVIF |
| `quality` | `80`; строго int 0..100, bool/float/str не подходят |
| `max_width`, `max_height` | Оба None — без resize; иначе оба положительные int, не bool, пиксели |
| `recursive` | Строго bool, False; старые directory consumers передают True |
| `output_directory` | None — рядом с источником; иначе существующий обычный каталог, flat layout, без создания дерева |
| `output_path` | None; точная цель для одного явно выбранного файла, не каталога; parent существует, suffix соответствует формату; несовместимо с output_directory |
| `postfix` | `_compressed`; может быть пустым, не trim; запрещены Unicode control chars, `/`, `\`, Windows `<>:"|?*`, trailing dot/space |
| `delete_original` | Строго bool, False (default OFF); True → безвозвратное удаление исходника **только после verified final output** на supported Windows local fixed NTFS; unsupported → явная ошибка до эффектов этого элемента, без тихого False; Корзины/undo нет |

Неверные общие параметры/назначение, недоступный выбранный encoder или пустой завершённый discovery → rejected, без staging/публикации. Ошибка отдельного входа после валидации не скрывает другие независимые результаты.

## Discovery и имена

- Входные suffix: `.jpg/.jpeg/.png/.webp/.heic/.heif/.avif`, case-insensitive. Явный иной suffix — поэлементный `UNSUPPORTED_INPUT_EXTENSION`; в каталоге — ignored. Actual Pillow format проверяется отдельно.
- Сначала полный immutable manifest, затем любая запись. Порядок roots сохраняется; внутри root кандидаты сортируются по `(relative_path.casefold(), relative_path)`. First-wins dedup по normalized absolute path/normcase и доступным dev/inode; независимые одинаковые байты не dedup-ятся.
- Не следуем symlink/junction/reparse, включая ancestors до нормализации `..`. Явный link — ошибка; вложенный исключается с ignored/reason. Ошибка чтения каталога — собственная failed entry, не изображение.
- Строгий потомок output_directory исключается из входного root; совпавший root не исключается целиком. Результаты текущего вызова не могут стать его входами. Старые outputs в других местах не угадываются по имени.
- Canonical выходные suffix: JPEG `.jpg`, WEBP `.webp`, HEIF `.heic`, AVIF `.avif`; exact output также допускает `.jpeg/.heif`.
- При совпадении suffix family добавляется postfix: `a.png → a.webp`, `a.webp → a_compressed.webp`, `a.jpeg → a_compressed.jpg`. Exact output не переименовывается.
- Только collision policy **fail**. Все элементы общей target-группы получают `TARGET_CONFLICT`; совпадение с любым input path/identity — `INPUT_OUTPUT_CONFLICT`. Существующее имя любого типа, включая dangling symlink, — `OUTPUT_EXISTS`. Независимые элементы продолжаются. Нет overwrite, автоматических `(1)` или silent skip.

## Кодеки и image policy

`get_capabilities()` лениво вызывает Pillow init, optional HEIF registration и реальные RGB encode → BytesIO → open/load probes формата/размеров. Для AVIF сначала проверяется встроенный Pillow; optional pillow_avif импортируется только при его отказе. Выбранный рабочий provider не переключается посреди операций. Cache живёт только в процессе.

Каждая capability содержит `decoder_registered` (не обещание всех файлов), `encoder_available`, `roundtrip_verified`, `alpha_verified`, `provider` и безопасный `reason`. PNG имеет собственный decoder probe, но `encoder_available=False`: **PNG только вход**, не output API. JPEG/WebP — обязательные возможности проверенной среды; optional HEIF/AVIF зависят от настоящего probe.

Обычный pipeline: tracked source handle → actual format/frames/mode/исходная precision → load → EXIF transpose → RGB/RGBA → shrink → семантика прозрачности → чистый raster → staging save с явным `format=`. Все raster/file handles закрываются. Правила:

- Actual source — JPEG/PNG/WEBP/HEIF/AVIF. Поддерживаемое содержимое под другим поддерживаемым suffix допустимо. Несколько кадров отвергаются, а не превращаются молча в кадр 0.
- Поддержаны обычные 8-bit `1/L/LA/P/RGB/RGBA/CMYK`; transparency (включая palette/color key) учитывается. JPEG композирует alpha на белый фон. Для иных выходов учитываются **фактически непрозрачные/прозрачные пиксели после orientation/resize**, не один лишь A-канал. Полностью opaque RGBA/LA и неиспользованные palette/color keys допустимы, opaque A нормализуется в RGB; физическое сохранение избыточного A кодеком не требуется. Для реально прозрачного prepared raster нужен alpha-verified provider, иначе `IMAGE_MODE_UNSUPPORTED`. Staging/final verifier проверяет ту же семантику: потерянная или ложно добавленная прозрачность не принимается.
- I/F/16-bit/HDR и иные неоговорённые режимы отвергаются. У PNG RGB/RGBA mode Pillow **не доказывает 8-bit source**: до `load()` через тот же tracked handle читаются фиксированные 33 bytes signature/IHDR/CRC (position восстанавливается). 16-bit RGB/RGBA/LA/grayscale получают `IMAGE_MODE_UNSUPPORTED` до pixel decode/неявного downconvert; filename suffix не определяет эту проверку. Полная проверка/decode изображения остаётся у Pillow, не заменяется чтением заголовка.
- Orientation применяется **до** геометрии. EXIF/XMP/ICC/comments не переносятся: создаётся новый raster, info очищается; staging и final проверяются. Нет ICC engine, архивной/цветометрической гарантии или HDR tone mapping.
- `r=min(1,max_width/width,max_height/height)`, стороны `max(1,floor(side*r))`, LANCZOS; без upscale/crop. 4000×3000 в 1920×1080 → 1440×1080.
- Защита Pillow от bombs/truncated data не выключается. Bomb warning/error → `IMAGE_LIMIT_EXCEEDED`; raw warnings не выводятся. Нет жёсткого RAM/CPU/time budget или изоляции native codec. Меньший итоговый файл и равная perceptual quality разных кодеков не обещаны.

# Файловая граница

1. Снимок source dev/inode/size/mtime_ns/ctime_ns, ancestors; open/fstat и повторные проверки пути. На Windows сохраняется также descriptor ctime: CPython path/descriptor stat могут отражать разные clocks, ни один guard не удалён.
2. Проверка parent/ancestors и создание уникального `.ic-*` staging-directory рядом с target, payload внутри; ownership учтён до оставшихся fallible setup-шагов. Codec никогда не получает final path.
3. Полный decode staging, actual format/size/alpha/metadata; bytes и SHA-256 подготовленного файла. Проверки source fingerprint, parent/staging identities и token непосредственно перед публикацией.
4. **Точка эффекта — успешный `os.link(payload, destination)`**. Атомарное создание нового имени без замены. При неподдерживаемых hard links — `PUBLICATION_UNSUPPORTED`, без rename/replace/эксклюзивной записи неполных final bytes как fallback.
5. Сразу записывается artifact unverified; final path полностью load/readback, digest и доступная identity сравниваются с подготовленным. Только затем verified/succeeded. Отказ после link оставляет final и возвращает `PUBLISHED_UNVERIFIED`, не удаляет его «для отката».
6. Finally удаляет только свой payload при совпавшей identity и свой пустой dir через rmdir. Никакого rmtree/glob-cleanup по output root. Подмена/foreign content/отказ cleanup оставляются с `TEMP_CLEANUP_FAILED`; успешная публикация с таким остатком — partial.

Это atomic visibility одного нового файла, **не crash durability**: нет fsync/recovery журнала, транзакции всего пакета или exactly-once. Проверена local NTFS. Прочие FS требуют своей проверки; unsupported FS безопасно отказывает. Модель — trusted local namespace без враждебной параллельной перестановки каталогов, не sandbox. Stat/fstat обнаруживают обычные изменения, не создают криптографический snapshot источника. Чужая запись после checkpoint/readback остаётся возможной.

# Результаты, управление и ошибки

`BatchResult`: status, effective options (либо null при отказе до нормализации), discovery_complete, items/errors/warnings/counts. `ItemResult`: стабильный 0-based index, absolute source/destination либо null, status, известные source format/width/height/bytes, artifact/error/warnings, `source_disposition` (`retained`/`deleted`/`unknown`) и `counts.deleted` (только подтверждённые удаления). `retained` — приложение не удаляло/не заменяло, не утверждение о чужих процессах; ошибка/отмена до destructive point оставляет исходник и не выдаётся за `deleted`.

Artifact: path, canonical format, width/height px, size_bytes, SHA-256 **подготовленных** байтов, publication `verified|unverified`. При unverified это не гарантия текущего содержимого final. Неизвестное — null, настоящий ноль — 0, пустая коллекция — `[]` в JSON. Пути только в предусмотренных result/options полях, не в error message. `ErrorInfo`: стабильный [ErrorCode](../../image_compressor/models.py), фиксированный safe message, stage, optional field закрытого набора. Raw exceptions/EXIF/cause не сериализуются.

Counts: `total = succeeded + failed + cancelled`; `published` пересекается с ними и включает unverified artifacts; duplicates/ignored вне total. Неполный discovery сообщает только найденные entries и `discovery_complete=False` и не начинает их конвертацию.

| status | Смысл |
|---|---|
| rejected | Общий отказ или завершённый пустой набор; items пусты, эффектов нет |
| succeeded | Все items succeeded; нет существенного cleanup остатка |
| failed | Ошибки без успешных/опубликованных результатов |
| partial | Есть успех/публикация и ошибка, либо успешная публикация с cleanup warning |
| cancelled | Запрос реально остановил discovery/текущий/ещё не начатый элемент; готовые artifacts и прежние ошибки сохранены |

`CancellationToken` — threading.Event с cancel/is_cancelled, без reset. Проверки между directory entries, до следующего элемента, после decode/encode и перед link. Native codec может не возвращать управление долго; cancel — запрос, не мгновенный kill. После последнего checkpoint текущий link/readback может завершиться; поздний token после последнего готового файла не меняет успех на cancelled. Новый вызов получает новый token.

ProgressEvent — immutable discovering/item_started/item_finished/finished с index, total (null при discovery), processed/succeeded/failed/cancelled и optional completed ItemResult. `processed=succeeded+failed`, не включая cancelled. Callback синхронный/короткий; исключение отключает дальнейшие callbacks, добавляет OBSERVER_FAILED и не меняет факт конвертации. Ошибка logging также не меняет outcome/не вызывает retry.

Повтор convert — **новое действие**, не replay: прошлый output даст collision. При потерянном ответе/сбое доставки сначала сверять известные назначения; никакого автоматического overwrite/retry. Опубликованные файлы не откатываются при ошибке следующего элемента или stdout.

# CLI и совместимость

`image-compressor = image_compressor.cli:main`, эквивалент `python -m image_compressor`; legacy facade/`classes.py` retired. Синтаксис и примеры — [README](../../README.md). Capabilities/convert всегда выдают один UTF-8 JSON object + newline: schema_version=1, command, status, result, errors. `--json` — no-op явного выбора этого режима. Help/version — текст/0. Некорректный синтаксис не отражает raw argv, выдаёт CLI_USAGE/2 и подсказку --help. `--` отделяет пути с ведущим дефисом. Есть явный opt-in `--delete-original` (default off) с тем же guarded deletion; overwrite flags отсутствуют.

| Exit | Значение |
|---|---|
| 0 | succeeded / capabilities / help / version |
| 2 | usage / rejected |
| 3 | partial, в том числе published-unverified/cleanup residual |
| 4 | failed без успеха/публикации |
| 5 | INTERNAL_ERROR (приоритет над обычным итогом) или delivery failure |
| 130 | применённая cooperative cancellation, возможно с готовыми файлами |

CLI ставит SIGINT/SIGBREAK handlers на время convert, только запрашивает token, затем восстанавливает прежние handlers. Повторный сигнал не force-kill. Вне main thread выдаётся безопасное SIGNAL_UNAVAILABLE ограничение. Broken stdout не откатывает файлы; JSON невозможен при физически закрытом канале, exit5 без raw traceback.

Legacy `ImageCompressor`: import/constructor defaults HEIF/50, свойства/методы/таблицы сохранены; None при полном успехе, last_result и CompressionError(result)/code при ином исходе. Constructor/setters используют общий validator (TypeError для типа, ValueError для значения); codecs окончательно проверяет convert. Старое снятие внешних двойных кавычек остаётся только в process_input. WebP входит в supported inputs; silent missing/overwrite больше не сохраняются.

Worker сохраняет старые сигналы, добавляет result_ready(object)/result; terminal signals ровно один раз. delete_original передаётся в immutable request как выбранный bool; рабочая галочка default OFF, включение = согласие на безвозвратное удаление после verified output. Unsupported backend даёт явный отказ, а не тихий False. Stop не вызывает wait/terminate и не фабрикует `(0,0)`: reference/start gating/отложенное close живут до QThread.finished. Настоящий итог отображается один раз; следующая операция — новый worker/token.

# Диагностика и проверка границы

Закрытые события conversion_started/item_finished/conversion_finished/cleanup_failed, безопасные codes/stages/canonical format/quality/counts/bytes/duration_ms и случайный operation id. Именованный logger не настраивает root/постоянный файл/телеметрию. Реальные host formatters/handlers используются с изоляцией raw handleError fallback; CLI временно добавляет свой stderr sink и восстанавливает host-настройки. Технические данные не включают paths, argv, arbitrary postfix, exception/traceback или DTO целиком. Политика — [наблюдаемость](../foundation/observability-policy.md).

Гарантия privacy этой дельты относится к новым API/CLI и emitters canonical `gui_pyside6_v2/`. Legacy PyQt6 GUI и compatibility facade удалены из рабочей копии 2026-10-28 (история — в Git), их старый debug/raw вывод больше не поставляется; **весь GUI не privacy-certified**. Нет visual qualification, EXE/release, native Windows console-signal delivery, другой ОС/Python runtime проверки или MCP. Фактический suite проходит настоящие owners/readback, fault injection только на обозначенных краях; installed wheel без Qt — отдельная проверка, не editable-only PASS. Независимый Reviewer подтвердил достаточность для этой ограниченной поставки; точное решение и сохранённая история — в [verification](../verification/command-first-refactoring.md).
