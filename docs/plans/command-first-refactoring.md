---
id: ic-command-first-refactoring-plan
title: "Image Compressor — command-first-рефакторинг"
kind: plan
status: proposed
created: "2026-10-23"
updated: "2026-10-23"
areas: [architecture, command-first, conversion, data-safety, testing]
summary: "Исполнимый переход к синхронному прикладному API, безопасной публикации новых файлов, headless CLI и совместимым адаптерам существующего GUI."
owner: "Автор реализации Image Compressor"
code_ref: "770784935c52eaa3add6a9a1ec50b5154c9f1e3c"
code_verified_at: "2026-10-23"
verification_scope: "Чтение исходников, потребителей, локальных инструкций и read-only Git-диагностика; продукт и тесты не запускались."
---

# 1. Поручение, статус и решение

> **Фактическое завершение и последующая власть (2026-10-23).** Ниже сохранён исходный предлагаемый план и ограничения стадий Oracle/Coder/read-only review. Все четыре среза реализованы; после первого NEEDS_CHANGES тот же Coder исправил R1/R2, тот же Reviewer независимо вынес ACCEPT (170 passed/0 skips и отдельные matched API/installed discriminators). Действующие поведение/пределы — [контракт](../architecture/application-api.md), решение/evidence — [verification](../verification/command-first-refactoring.md). Последующее прямое поручение пользователя заменяет старые запреты Git/index **только для accepting Reviewer после ACCEPT**: он завершает docs/instructions, selective commit принятого состава и branch-only push существующего origin на refactor/command-first с exact SHA readback. Coder/Oracle по-прежнему не получают Git writes; source/tests/PFK не исправляются Reviewer-ом, merge/tag/release/force не разрешены. Актуальный порядок — [development](../instructions/development.md). Ни исторические NOT RUN Oracle, ни отсутствие commit в первоначальном handoff ниже не описывают итоговую стадию сохранения.

Это **предлагаемый план**, а не описание уже работающего API. Новые пути, сигнатуры и команды ниже — целевые. Пользователь поручил последующую реализацию и проверку другим агентам; Oracle на этом шаге имеет право записать только этот файл. Принятие текста, реализация, авторские запуски и независимая приёмка — разные факты. Реализованный авторский кандидат всех четырёх срезов описан в [контракте](../architecture/application-api.md), фактические запуски/пределы — в [verification](../verification/command-first-refactoring.md); исходный замысел и критерии этого плана сохранены.

**Результат пользователя:** локально преобразовать один файл или определённый набор изображений через Python API либо настоящий неинтерактивный CLI; получить читаемые файлы, проверяемый поэлементный итог и полезную диагностику, не потеряв оригиналы и прежние результаты. Существующее окно продолжает вызывать тот же исполнитель через worker; новый интерфейс не разрабатывается.

**Выбрано:** профиль **A — прикладной сервис**. Синхронный `convert()` возвращает окончательный результат; один вызов последовательно обрабатывает пакет. Прогресс — callback, отмена — локальный потокобезопасный токен. GUI запускает вызов в существующем QThread, CLI — в своём процессе. Нет Job ID, очереди, демона, IPC, attached-сессии, БД, универсальной шины, MCP или нового GUI.

**Политика сохранности:** только создание нового результата, без overwrite и без удаления источника. `delete_original=True` явно отвергается **до файловых эффектов**, в том числе при вызове старого worker. Не игнорировать флаг и не подменять его `False`. Это намеренно несовместимое исправление опасной семантики, с сообщением существующему потребителю; подробности в §7.

**Публикация:** уникальный staging рядом с назначением → полное декодирование и проверка → атомарное создание hard link без замены → readback окончательного пути. Неподдерживаемая файловая система получает явный отказ, не небезопасный fallback. Это атомарная видимость одного нового файла, **не crash durability**.

## Границы

- Обрабатываем локальные обычные файлы в доступных процессу каталогах. Проверки — исключительно на синтетических данных в собственных временных корнях.
- Сохраняем четыре реально существующих выхода: JPEG, WebP, HEIF/HEIC, AVIF. PNG — вход, **не новый выход**. README ошибочно обещает PNG-output; это не основание расширять продукт.
- Не обещаем меньший размер файла, равенство качества между кодеками, архивное сохранение метаданных/цвета, поддержку всех вариантов HEIF/AVIF, многокадровую обработку, мгновенную остановку, восстановление после аварии, транзакцию всего пакета или exactly-once.
- GUI-дизайн, `gui/widgets.py`, `gui/styles.py`, расположение и состав виджетов не менять. Допустимы только адаптация worker/поиска/импортов и необходимое событийное подключение в `gui/main_window.py`.
- Не собирать и не выпускать EXE в этой работе. Не менять глобальный Python/Pi, исходный PFK, `tools/project-foundation/`, Git index/историю. Не читать соседний проект, credentials, личные изображения, БД и журналы.

# 2. Найденная основа — current, не target

На чтении: корень `C:/PY/image_compressor`, ветка `docs/project-foundation`, HEAD `7707849` (полный hash в metadata). `git diff --cached --stat` пуст; tracked delta — `.gitignore`; untracked `.pi/`, `AGENTS.md`, `LOG.md`, `docs/`, `tools/` — подготовленная Hermes основа. Oracle её не переписывал и не сохранял commit. Не считать untracked-документы отсутствующей работой или кандидатом на cleanup.

| Реальный owner / потребитель | Найденное поведение и риск | Что сохраняем / меняем |
|---|---|---|
| `classes.py:38–223`, `ImageCompressor` | Конструктор обходит setter-валидацию; defaults HEIF/50; поддерживаемые входные расширения не включают WebP. `compress_image()` сохраняет прямо в `output_path`, печатает пути. Resize только при двух truthy размерах, сторона может округлиться в 0. Нет readback, цветовой политики и защиты совпадения input/output. | Импорт класса, сигнатуры, свойства, defaults и успешный `None` сохраняются через мост; все эффекты переводятся в API. |
| `classes.py:120–156` | `os.walk`, цель через замену расширения; источник может быть одновременно назначением, результаты — повторно входами. Отсутствующий путь лишь печатается. | Общий discovery и фиксированный состав пакета; безопасные имена; явный структурированный отказ через исключение совместимости. |
| `classes.py:225–283` | Интерактивный `main()` с `input()`. | Скрипт становится переадресацией в новый CLI, без вопросов. Это документированная смена входа. |
| `gui/worker.py:15–152` | Реальный потребитель класса; `list(set(files))` уничтожает порядок; собственные правила имён/пакета/удаления. Проверка успеха — `exists()`, затем `unlink()` оригинала. При same-path возможна перезапись; ошибка удаления не отражается в счётчике. Глобальный сбой может завершиться `(0, 0)`. | Один вызов API, перевод прогресса/результата в сигналы, сохранение старых сигналов, явное отображение отказов. |
| `gui/utils.py:10–36` → `gui/main_window.py:153–181` | Второй recursive finder, другая таблица расширений, нет стабильной дедупликации. В `gui/widgets.py:24` есть также неиспользуемый импорт helper-а. | Совместимый helper делегирует общему discovery; main получает и показывает safe issues, не реализует обход. |
| `gui/main_window.py:183–274` | GUI defaults WEBP/80; передаёт `delete_original`, `postfix`, размеры. Собственная дедупликация, печать произвольного postfix. `stop_compression()` блокирует UI через `wait()`, затем фабрикует `(0,0,cancelled=True)` независимо от итога worker; возможно двойное завершение. | Только событийная перепроводка, корректный итог и жизненный цикл worker. Никаких новых виджетов. |
| `gui/widgets.py` | Четыре radio-формата, checkbox удаления, postfix с fallback `_compressed`; resize-getters печатают введённый текст и исключения. | Не менять по scope. Не объявлять весь неизменённый GUI privacy-certified; граница диагностики §8. |
| `gui/__init__.py`, `gui_main.py`, `run_gui.bat`, `run_dev.bat` | Пакет `gui` eager-импортирует окно/виджеты; launcher вызывает `gui.main`. | GUI-входы сохраняются; импорты пакета можно сделать lazy с сохранением exports. Новый API не импортирует `gui`. |
| `pyproject.toml`, `requirements.txt` | Runtime включает Qt и PyInstaller; setuptools упаковывает только `gui`; console entrypoint отсутствует, `classes.py` в установленный пакет явно не включён. | Отдельный пакет API, console script, правильный состав wheel; GUI/codecs/build — extras. |
| `gui_compressor.spec` | Analysis входа `gui_main.py`, hidden imports старого класса/Qt/плагинов. | Не менять без необходимости: обычные статические импорты нового пакета должны быть видимы Analysis. Frozen-путь остаётся NOT RUN, не новая цель. |
| `test_gui.py` | Ручной launcher, ищет отсутствующий `gui.py`, тестовых функций нет. | Не использовать как suite; `tests/` и явный pytest testpaths. Не превращать его в новый GUI-этап. |
| `README.md`, `UV_GUIDE.md`, `QUICK_GUIDE.txt`, `UPDATE_FEATURES.md` | README ссылается на отсутствующие `main.py`, `run_compressor.bat`, обещает PNG-output и многопроцессорность. Quick guide и update notes рекомендуют удаление/замену. | Обновить актуальные пользовательские инструкции; старые release/status-свидетельства не выдавать за проверку новой версии. |

Поиск import/call в разрешённых исходных `*.py` подтвердил worker и ручной launcher как потребителей `ImageCompressor`; иных локальных вызовов `validate_write_permissions` и подписок на `file_processed` не найдено. Это не утверждение об отсутствии внешних пользователей Python-класса. `get_savings_info` и `format_file_size` — представление, не альтернативный конвертер.

Исходная среда **по подготовленным инструкциям Hermes**, не по запуску Oracle: `.venv` Python 3.14.2; PIL/heif/avif/PyQt6 найдены; pytest/Ruff/mypy отсутствуют. Найденный `requirements_freeze.txt` — старый snapshot, не свежий lock или доказательство доступности кодеров. Codebase-memory/Serena/ast-grep в данном наборе tools не предоставлены; достаточные связи установлены штатными read/grep и read-only Git.

# 3. Целевая структура и владельцы

Все перечисленные новые модули — планируемые, сейчас их нет.

```text
image_compressor/
  __init__.py       # публичные DTO, convert/discover_inputs/get_capabilities; без CLI/Qt
  models.py         # frozen dataclass, enum/literal, коды, общая валидация
  service.py        # единственный owner сценария, результатов, прогресса и отмены
  discovery.py      # раскрытие/снимок входов, сортировка, дедупликация
  imaging.py        # Pillow, lazy codecs, преобразование, проверка изображения
  filesystem.py     # имена, идентичности, staging, publish-new, cleanup
  diagnostics.py    # безопасные поля/события; не глобальная настройка logging
  cli.py            # argparse, сигнал отмены, JSON, exit mapping
  __main__.py       # только вызов cli.main
classes.py          # совместимый Python-адаптер и forwarding CLI
 gui/worker.py      # QThread-адаптер → convert()
 gui/utils.py       # discovery facade + существующие presentation helpers
 gui/main_window.py # существующий GUI; только wiring
```

Модули допустимо объединить, если обязанности и тестовые границы не размываются; не добавлять интерфейс на каждую функцию. Канон данных — `models.py`, поведения — `service.py` и вызываемые им owners. Сериализация CLI явно отражает эти типы, не вводит свой набор правил. Долговечное описание после реализации — один `docs/architecture/application-api.md` (kind `contract`) с картой текущей архитектуры, ссылками на код и API/CLI-семантикой, без второй ручной JSON Schema.

| Ресурс | Кто вправе менять | Время жизни |
|---|---|---|
| Состав, порядок, результаты и счётчики запуска | Локальный вызов `service.convert` | До возврата `BatchResult`; затем immutable данные вызывающего |
| Staging и создание конечного имени | Только `filesystem` по запросу service | Один элемент; никаких записей из adapter/codec в конечный путь |
| Растр и зарегистрированный провайдер | `imaging`; инициализация однократно под небольшим lock | Растр — элемент; выбранные codecs/capability cache — процесс |
| Запрос отмены | Созданный adapter/caller-ом `CancellationToken` | Один вызов; новый запуск получает новый token |
| Qt thread/window state | Существующий GUI-адаптер | До реального окончания QThread; это не публичная job |

Права ОС наследуются от локального процесса; отдельная аутентификация, sandbox и произвольные `allowed_root` не вводятся. Общая библиотека не создаёт общей сессии между CLI и GUI. Пересмотреть A только при реальном требовании адресуемой работы после возврата/закрытия клиента (B), общего несохранённого workspace (C), восстановления зависимых этапов через сбои/ожидания (D).

# 4. Прикладной контракт v1

## 4.1 Операции и вход

Публичные операции:

```python
get_capabilities() -> Capabilities
# Только synthetic in-memory probes, без чтения пользовательских каталогов.

discover_inputs(inputs, *, recursive=False, exclude_directory=None,
                cancellation=None) -> DiscoveryResult
# Читает имена/stat; не декодирует и ничего не записывает.

convert(request: ConversionRequest, *, cancellation=None,
        on_progress=None) -> BatchResult
# Синхронный окончательный результат, не accepted/job.
```

`CancellationToken` предоставляет `cancel()` и `is_cancelled()` на основе `threading.Event`; без reset/reuse. Входной DTO не содержит QWidget, logger, parser, signal handler или исполняемые shell-строки. Объекты запроса/результата неизменяемые; вложенные списки фиксируются tuple, `Path` не подменяется открытым файловым дескриптором наружу.

| Поле `ConversionRequest` | Семантика/default/валидация общего API |
|---|---|
| `inputs` | Непустая последовательность `str`/`os.PathLike[str]`, снимок в tuple. Один str не трактовать как список символов. Пустая строка, bytes, NUL и неверный тип — отказ. Относительно cwd, зафиксированного в начале вызова. Не раскрывать env, `~`, glob и кавычки автоматически. |
| `output_format` | Default `WEBP`; case-insensitive `JPEG/JPG`, `WEBP`, `HEIF/HEIC`, `AVIF`; канонические значения JPEG/WEBP/HEIF/AVIF. PNG-output и неизвестное имя — отказ, не fallback. |
| `quality` | Default `80`, строго int 0..100 включительно, bool/float/string отвергаются. Число передаётся кодеку как quality; равная perceptual quality не обещана. |
| `max_width`, `max_height` | Оба `None` — без resize. Иначе **оба** строго положительные int (не bool), пиксели. Одна сторона, 0, отрицательное, строка — отказ. |
| `recursive` | Строго bool, default `False`; старые recursive consumers явно передают `True`. |
| `output_directory` | Default `None`: рядом с каждым источником. Иначе существующий обычный каталог, flat layout; не создавать дерево каталогов и не сохранять иерархию неявно. |
| `output_path` | Default `None`. Точная цель только для одного явно переданного файла, не каталога/результата раскрытия. Взаимоисключается с `output_directory`. Родитель существует; suffix должен принадлежать запрошенному формату. |
| `postfix` | Default `_compressed`; применяется по §5.2. Строка может быть пустой, но не может содержать `/`, `\\`, NUL, control chars и Windows `<>:"|?*`; не допускаются trailing dot/space. Пустой postfix допустим, но совпавшая цель затем отвергается. Не trim произвольный текст в ядре. |
| `delete_original` | Строго bool, default `False`; `True` → `DESTRUCTIVE_MODE_UNSUPPORTED` до discovery/создания staging. Поле сохраняет явность миграции, не разрешает удаление. |

Вся runtime-валидация выполняется и при прямом вызове. DTO-конструктор сам по себе не подтверждает корректность. Общий чистый validator используется legacy setters/constructor, но API повторно проверяет запрос. Неверные параметры/неподдерживаемый выход/недоступный encoder/невалидное общее назначение возвращают `BatchResult(status="rejected", errors=...)` без записи файлов. После валидации ошибка одного входа не отменяет остальные.

## 4.2 Форматы, кодеки и обработка растра

- Входные кандидаты discovery: `.jpg`, `.jpeg`, `.png`, `.webp`, `.heic`, `.heif`, `.avif`, без учёта регистра. Реальный распознанный Pillow format должен входить в JPEG/PNG/WEBP/HEIF/AVIF; расширение не доказывает содержимое. Поддерживаемое содержимое под другим **поддерживаемым** расширением допустимо; результат сообщает actual source format. Явный файл с иным suffix получает `UNSUPPORTED_INPUT_EXTENSION`, в каталогах такие файлы учитываются как ignored.
- Выходы: JPEG `.jpg`, WEBP `.webp`, HEIF `.heic`, AVIF `.avif`. Точный `output_path` также допускает `.jpeg`/`.heif` как aliases. Всегда передавать `format=` явно в Pillow; проверять actual result format и размеры при readback.
- Инициализация lazy, без Qt и без probe при простом импорте API. `Pillow.Image.init()`; HEIF регистрируется при доступности optional `pillow_heif`. Для AVIF сначала использовать встроенный Pillow provider, если его реальный probe работает; иначе однократно проверить optional `pillow_avif`. Не переопределять уже выбранный рабочий provider случайным вторым импортом и не переключать provider посреди операции.
- `get_capabilities()` возвращает policy input extensions/formats, `decoder_registered` (это **не** обещание чтения любого файла), и для каждого из четырёх выходов `encoder_available`, `roundtrip_verified`, `alpha_verified`, `provider`, безопасный `reason`. `encoder_available=True` только после encode небольшого synthetic RGB → BytesIO → open/load → actual format/size; отдельно RGBA для не-JPEG. PNG decoder проверяется собственным PNG in-memory образцом, хотя PNG-output в API не предлагается. Ошибка probe — фиксированный код, не traceback. Cache только в процессе, без дискового реестра. Конкретный вход всё равно проверяется при обработке.
- Обычный путь: открыть источник через учтённый handle → определить формат/кадры/размеры → `load()` → `ImageOps.exif_transpose()` → нормализовать режим/alpha → shrink → кодировать staging. Закрывать все handles/новые raster objects через контекст/finally.
- Статическое изображение: `n_frames > 1` → `MULTIFRAME_UNSUPPORTED`, не молчаливый кадр 0. Для HEIF не обещать произвольные primary/auxiliary/HDR-контейнеры.
- Поддержать обычные 8-bit `1/L/LA/P/RGB/RGBA/CMYK` через определённое Pillow-преобразование в RGB/RGBA; palette transparency учитывать. Для JPEG RGBA/LA/палитровая прозрачность композируется **на белый фон**. Для остальных выходов alpha сохраняется только при проверенной способности provider, иначе `IMAGE_MODE_UNSUPPORTED`, не молчаливое удаление alpha. `I`, `F`, 16-bit/HDR и иные неоговорённые режимы отвергать. Не добавлять tone mapping или ICC engine.
- EXIF Orientation применяется перед вычислением геометрии. EXIF/XMP/ICC/comments и прочие metadata не переносить в выход: перед save очищать переносимые info, не только опускать kwargs. Это намеренная privacy-политика; цветометрическая/архивная точность не обещается, ICC-преобразование не выполняется. Оригинал остаётся для иной обработки.
- Resize: `r = min(1, max_width / width, max_height / height)`; размеры `max(1, floor(width*r))`, `max(1, floor(height*r))`. Никакого upscale/crop; LANCZOS. Проверять положительность и fit после округления. При отсутствии resize сохраняются ориентированные размеры.
- Не отключать защиту Pillow от decompression bombs и truncated files. Bomb warning/error трактовать как `IMAGE_LIMIT_EXCEEDED` до дорогого полного decode; не печатать raw warning. Последовательная обработка ограничивает число активных растров одним элементом; жёсткий RAM/CPU/time budget и изоляция native codec не обещаны.

## 4.3 Результат, ошибки и счётчики

`BatchResult`: `status`, нормализованные effective options, `discovery_complete`, `items`, `errors` уровня запроса, `warnings`, `counts`. Никакого успеха только по отсутствию исключения.

`ItemResult`: стабильный `index` (0-based), абсолютный `source`, `destination` либо null, `status` (`succeeded|failed|cancelled`), `source_format`/размеры/`source_size_bytes` по известности, `artifact` либо null, `error` либо null, warnings. `source_disposition="retained"` означает «приложение не удаляло/не заменяло», не утверждение о поведении чужого процесса.

`artifact`: конечный path, canonical format, width/height px, `size_bytes`, SHA-256 подготовленных байтов, `publication` (`verified|unverified`). `verified` требует окончательного readback; при публикации и последующей ошибке проверок artifact остаётся с `unverified`, item не считается succeeded. Размеры/байты неизвестны → null, настоящий ноль → 0. Не включать raw exceptions/EXIF в ответ.

`ErrorInfo`: стабильный `code`, фиксированное безопасное `message`, `stage`, необязательный `field` из закрытого набора. Пути принадлежат явным полям результата, не message/details. Не сериализовать произвольный exception/cause. Возвращаемая локальному caller-у информация о выбранных входах и выходах не разрешена автоматически для technical log.

Минимальный закрытый каталог кодов (можно объединять близкие коды, но не терять различимые условия):

| Граница | Коды |
|---|---|
| Запрос | `INVALID_REQUEST`, `INVALID_FORMAT`, `INVALID_QUALITY`, `INVALID_DIMENSIONS`, `INVALID_POSTFIX`, `INVALID_DESTINATION`, `FORMAT_UNAVAILABLE`, `DESTRUCTIVE_MODE_UNSUPPORTED`, `NO_INPUTS` |
| Discovery/read | `INPUT_NOT_FOUND`, `INPUT_NOT_REGULAR`, `UNSUPPORTED_INPUT_EXTENSION`, `UNSAFE_PATH`, `INPUT_ACCESS_DENIED`, `DIRECTORY_READ_FAILED`, `SOURCE_CHANGED` |
| Изображение | `INVALID_IMAGE`, `INPUT_FORMAT_UNSUPPORTED`, `MULTIFRAME_UNSUPPORTED`, `IMAGE_MODE_UNSUPPORTED`, `IMAGE_LIMIT_EXCEEDED`, `ENCODE_FAILED`, `VERIFICATION_FAILED` |
| Файлы | `INPUT_OUTPUT_CONFLICT`, `TARGET_CONFLICT`, `OUTPUT_EXISTS`, `OUTPUT_ACCESS_DENIED`, `WRITE_FAILED`, `DESTINATION_CHANGED`, `PUBLICATION_UNSUPPORTED`, `PUBLICATION_FAILED`, `PUBLISHED_UNVERIFIED`, `TEMP_CLEANUP_FAILED` |
| Управление/внутреннее | `CANCELLED`, `INTERNAL_ERROR`; warning `OBSERVER_FAILED` |

Ожидаемые OS/codec failures переводятся на границе владельца. Неожиданный `Exception` внутри обработки становится `INTERNAL_ERROR`, с уже известными эффектами; не продолжать рискованный внутренний сценарий вслепую. `SystemExit`/фатальный native crash не маскируются как сохранённый результат. Legacy facade может поднимать специальное `CompressionError(result)`; прямой API не требует ловить transport-specific исключения.

`counts`: `total`, `succeeded`, `failed`, `cancelled`, `published`, `duplicates`, `ignored`. `total = succeeded + failed + cancelled` для окончательного снимка items; published — отдельное пересекающееся число, включая unverified artifact. Duplicates/ignored не входят в total. Ошибка чтения корня/подкаталога занимает собственную failed entry с path, но не притворяется сконвертированным изображением. При незавершённом discovery total означает только обнаруженные entries и `discovery_complete=False`.

Итоги:

1. `rejected`: общий невалидный запрос/недоступный выбранный encoder, либо завершённый пустой discovery без ошибок (`NO_INPUTS`); items пусты, эффектов нет.
2. `succeeded`: все items succeeded, нет существенного residual warning.
3. `failed`: есть ошибки, ни одного успешного/опубликованного результата, отмена не прекратила оставшуюся работу.
4. `partial`: есть успешные или опубликованные результаты и ошибки; также успешная публикация с `TEMP_CLEANUP_FAILED`. Не маскировать опубликованный, но непроверенный файл как отсутствие эффекта.
5. `cancelled`: отмена реально остановила discovery/текущий или ещё не начатый элемент. Уже завершённые результаты и ошибки остаются в items/counts. Поздний token после полного завершения не превращает успех в отмену.

Ошибки наблюдателя/диагностики не меняют продуктовый итог. Ошибка callback отключает его дальнейшие вызовы в этом запуске, может добавить `OBSERVER_FAILED`; не повторять конвертацию. Повтор `convert()` — новое действие, не replay: прежние outputs дадут collision. После сбоя/потери stdout сначала смотреть известные назначения; не предлагать автоматический retry с overwrite.

# 5. Discovery, имена и граница файловых эффектов

## 5.1 Состав и порядок

1. Сначала полностью раскрыть входы и построить внутренний неизменяемый manifest, затем начинать запись. Это локальная структура вызова, не публичный persisted plan/job.
2. Сохранять порядок явно переданных roots. Внутри каждого directory сортировать кандидатов по относительному пути `(casefold, original)`; recursive=False — только непосредственные файлы, True — вложенные. `os.walk` без сортировки недостаточен. Каталог не декодируется как изображение.
3. Дедупликация first-wins: нормализованный абсолютный path (`normcase` по платформе), затем доступная физическая идентичность `(st_dev, st_ino)` для hardlink aliases. Не дедуплицировать по байтам: два независимых одинаковых изображения остаются двумя входами. Считать повторные roots/пересечения directory+file. При ненадёжной inode-информации использовать нормализованный path и не обещать physical dedup на такой FS.
4. Не следовать symlink/junction/reparse entries. Явно выбранный link/необычный файл — ошибка; обнаруженные ссылки — исключение с безопасным reason/count, без traversal. Проверять тип без предварительного `resolve()`, которое скрыло бы ссылку. Ошибки доступа не подавлять.
5. Если `output_directory` — строгий потомок входного каталога, исключить эту ветвь до обхода; если он совпадает с входным root, не исключать весь вход. Фиксированный manifest не включает созданные текущим вызовом outputs/staging. Ранее существовавшие результаты в иных местах не угадываются по postfix: они могут быть обычными входами нового запуска.
6. Discovery callback/token проверяются между directory entries; отмена discovery **не** запускает конвертацию неполного списка. Следующий вызов раскрывает входы заново.

## 5.2 Имена и коллизии

- Без точного output_path: basename исходника + canonical extension; parent — source parent либо flat output_directory.
- Если семейство suffix источника совпадает с выходом (в том числе `.jpeg`/`.jpg`, `.heif`/`.heic`, разный регистр), вставить postfix перед extension. Это небольшое безопасное расширение старого правила точного сравнения расширений. Имена рассчитываются по suffix, а корректность actual формата проверяется отдельно.
- Примеры: `a.png → a.webp`; `a.webp → a_compressed.webp`; `a.jpeg → a_compressed.jpg`; пользовательский postfix `_small` даёт `a_small.webp`. Точный output_path не переписывается автоматически.
- Единственная collision policy v1 — **fail**, без overwrite, silent skip, автоматических `(1)` и перенумерации. Существующая цель любого типа, включая dangling symlink, не заменяется.
- До записи сравнить все запланированные targets между собой и со всеми input paths/доступными identities. Все элементы группы с одной целью получают `TARGET_CONFLICT` (не «первый выигрывает»); совпадение с любым входом — `INPUT_OUTPUT_CONFLICT`. Прочие независимые элементы продолжаются.
- Empty postfix, explicit same path, case alias/hardlink цели не обходят запрет. На case-insensitive FS нормализация и атомарный primitive защищают фактическое имя; не заявлять универсального распознавания всех Unicode/сетевых aliases ранним планом.

## 5.3 Последовательность одного элемента

**Обязательное разделение prepare / publish.** `Image.save(final_path)` и `exists() → os.replace()` запрещены.

1. Снять identity/fingerprint обычного источника: dev/inode, size, `mtime_ns`, `ctime_ns`; открыть для чтения, сравнить fstat с manifest. Зафиксировать identity родителя цели. Не использовать `os.access` как доказательство права последующей записи.
2. Непосредственно перед чтением/созданием staging проверить типы и ссылки, доступные ancestor/parent identities. Модель предполагает локальное пространство имён без враждебной параллельной подмены каталогов; это не sandbox. При обнаруженном изменении — fail closed.
3. Создать уникальный staging-каталог через `tempfile.mkdtemp(prefix=".ic-", dir=target_parent)` и файл внутри него, на той же FS. Учитывать точные пути/identities своей попытки. Не использовать имя, производное только от private source basename. Codec получает только staging target.
4. Decode/transform/save; закрыть encoder/file handle. Повторно открыть staging, полностью `load()`; проверить actual canonical format, ориентированные/рассчитанные размеры, ожидаемые каналы/alpha, отсутствие переносимых metadata. Измерить bytes и SHA-256. Не считать `verify()` без полноценного load достаточным.
5. Перед эффектом повторить проверки исходника (fingerprint/path identity), родителя назначения/staging и cancellation. Изменение → `SOURCE_CHANGED`/`DESTINATION_CHANGED`, очистить только свою staging-область, результат не публиковать.
6. Публикация нового имени: **`os.link(staging_file, destination)`** в той же файловой системе. Успешное атомарное создание ссылки — точка эффекта. Уже существующее имя даёт `OUTPUT_EXISTS`, даже если появилось после preflight. Не применять replace/rename-overwrite или эксклюзивную запись неполных final bytes как fallback. Если hard links не поддерживаются — `PUBLICATION_UNSUPPORTED`; права/диск/прочие ошибки различать по доступному errno/winerror, без raw текста.
7. Сразу учитывать известный факт публикации. Открыть конечный путь и полностью readback/decode; сравнить формат, размеры, digest с подготовленным файлом и доступную identity. Только после этого item succeeded. При ошибке после `os.link` оставить конечный файл, сообщить `PUBLISHED_UNVERIFIED` и artifact; не удалять/перезаписывать его для «отката».
8. В finally удалить только учтённый staging file при совпадающей identity, затем собственный пустой staging dir через `rmdir`. Не применять recursive glob/rmtree по пользовательскому output root, не удалять final/source. Если свой файл/каталог уже подменён или занят чужим содержимым — оставить, дать `TEMP_CLEANUP_FAILED`. Собственные оставшиеся пути можно вернуть caller-у отдельно, но не писать в technical log.

Защита от обычного изменения входа — stat/fstat-revalidation, не криптографический snapshot всего входа и не атомарная compare-and-unlink. Поскольку удаления/замены нет, источник не повреждается самим приложением даже при выявленном stale input. Хеш результата связывает проверенные и опубликованные байты, но не предотвращает последующую чужую запись.

**Пределы:** local NTFS — первая фактически проверяемая платформа; другие FS требуют реальной проверки hard-link semantics. FAT/exFAT/неподдерживаемая share безопасно отказывают. Нет fsync/directory-sync durability обещания, журнала восстановления или автоматического удаления оставшегося staging после crash. Процесс может погибнуть между публикацией и ответом; источник и чужие outputs не трогаются, уже опубликованное может остаться без доставленного отчёта. Нет автоматического rollback всего пакета.

# 6. Прогресс, отмена и CLI

## 6.1 Локальное выполнение

`ProgressEvent` — immutable факт: phase (`discovering|item_started|item_finished|finished`), индекс если известен, total либо null во время discovery, processed/succeeded/failed/cancelled counts, необязательный completed `ItemResult`. `processed = succeeded + failed`; cancelled не изображаются выполненным кодированием. Итоговый BatchResult авторитетнее callbacks. Пути в ItemResult — локальный результат, не поля technical event.

Callbacks синхронны в выполняющем потоке и должны быть короткими; Qt adapter только emit-ит сигналы. Не вводить шину или собственный dispatcher. Не печатать каждый resize/codec tick.

Token проверяется до discovery, во время обхода, до следующего элемента, после decode/encode и непосредственно перед публикацией. Отмена до публикационного checkpoint удаляет собственный staging и помечает незавершённые entries cancelled. Уже опубликованные outputs сохраняются. Если cancel пришёл **после последней проверки перед `os.link`**, текущий файл может опубликоваться и завершить readback; это допустимая гонка кооперативной модели. Следующие элементы не начинаются после наблюдения token. Нельзя писать «после вызова cancel не появится ни одного файла».

`cancel()` лишь запрашивает остановку; окончание — возврат API/реальное завершение QThread. Native encode/load может блокировать до возврата библиотеки; latency не ограничена. Нельзя использовать `QThread.terminate()` или насильственно завершать codec ради зелёного теста. После возврата handles закрыты, следующий вызов с новым token работает независимо.

## 6.2 Настоящий headless entrypoint

В `pyproject.toml`:

```toml
[project.scripts]
image-compressor = "image_compressor.cli:main"
```

Эквивалентный module entry: `python -m image_compressor`. `cli.main(argv=None) -> int`; `__main__` делает `SystemExit(main())`. `python classes.py ...` передаёт argv этому же main. Импорт API/класса не импортирует CLI/parser/Qt и не вызывает `input()`.

Целевые команды (ещё **NOT RUN**):

```text
image-compressor capabilities
image-compressor convert INPUT [INPUT ...] [--recursive]
    [--format WEBP|JPEG|HEIF|AVIF] [--quality 0..100]
    [--max-width PX --max-height PX]
    [--output FILE | --output-dir DIRECTORY] [--postfix TEXT]
    [--json] [--progress]
```

- `capabilities` и `convert` всегда возвращают JSON; `--json` — явный совместимый no-op выбора этого режима, не переключатель предметных правил. `--help`/`--version` — обычный текст, exit0, без конвертации. Без команды или при неверных аргументах — безопасная usage error, не интерактивный prompt.
- Отдельного флага удаления/overwrite нет. Попытка `--delete-original`/`--overwrite` — `CLI_USAGE`, exit2. `--` поддерживает пути, начинающиеся с дефиса. Пути передаются как argv data, не через shell construction.
- Argparse делает только синтаксический разбор; значения и defaults сверяются общим API. Не печатать стандартный raw argparse message с отражением private argv: overriden error path выдаёт фиксированный `CLI_USAGE`, допустимый field/option из списка и предложение `--help`, без пользовательского значения. Ошибки int parsing также безопасны.
- stdout: ровно один UTF-8 JSON object + newline (кроме help/version), `schema_version: 1`, `command`, `status`, `result` (BatchResult/Capabilities либо null), `errors`. JSON serializer один, code-first; optional неизвестное → null, коллекции → `[]`, числа не строки. Не dump dataclass через произвольный repr. Additive поля допустимы; неизвестный status consumer не считает успехом.
- stderr: непустая безопасная диагностика начала/итога, причины отказов; `--progress` добавляет item progress. Никаких путей/argv/tracebacks и неожиданного ввода. Результат с выбранными путями в stdout допустим как локальный ответ и не копируется в log.
- На время конвертации установить обработчик SIGINT и, где есть, SIGBREAK: только запросить token, не выбрасывать KeyboardInterrupt посреди publish. Повторный сигнал повторяет cancel, не force-kill. После завершения восстановить прежние handlers. Если signal handler не может быть установлен вне main thread, CLI сообщает ограничение безопасно; обычный entrypoint работает в main thread. Library API сигналами не управляет.
- Закрытый stdout/ошибка доставки ответа не откатывают опубликованные файлы и не запускают retry. Завершиться ненулевым delivery/internal кодом без traceback; контракт JSON не обещается для физически закрытого канала.

| Exit | Значение |
|---|---|
| `0` | Полный `succeeded`; capabilities query успешно выполнен даже если отдельные optional codecs недоступны; help/version |
| `2` | CLI usage или API `rejected`: параметры, недоступный выбранный формат, пустой завершённый набор |
| `3` | `partial`, включая опубликованный unverified результат/остаток cleanup |
| `4` | `failed` без успеха/публикации: ошибки всех входов/элементов |
| `5` | Непредвиденный внутренний/доставочный сбой; известные эффекты не отрицаются |
| `130` | Применённая кооперативная отмена (`cancelled`), возможно с готовыми outputs |

При `INTERNAL_ERROR` exit5 имеет приоритет над обычной partial/failed, но JSON сохраняет реальные items/artifacts/status. Exit130 не обещает нулевых эффектов. Потерянный ответ не означает «ничего не создано».

# 7. Совместимость и подключение существующих потребителей

## 7.1 `ImageCompressor`

Сохранить `from classes import ImageCompressor`, constructor `(quality=50, output_format="HEIF", max_width=None, max_height=None)`, свойства quality/output_format, class-level supported/output formats и методы `compress_image(input_path, output_path)`, `process_directory(directory)`, `process_input(input_path)`. Таблицы берутся из общего owner-а; WebP добавляется к входным расширениям. Constructor/setters используют общую строгую валидацию (тип → TypeError, значение → ValueError с безопасным сообщением); codec availability окончательно проверяет convert, не имя импортированного плагина.

Методы строят ConversionRequest, `process_directory` рекурсивный; `process_input` сохраняет старое снятие внешних двойных кавычек только в этом legacy adapter. Методы возвращают `None` при полном успехе, сохраняют `last_result`; при rejected/failed/partial/cancelled поднимают `CompressionError` с code и BatchResult, без raw exception в строке. Старое молчаливое отсутствие пути становится явным отказом. Existing outputs/same-path больше не перезаписываются. `AVIF_AVAILABLE` не использовать как критерий; известных consumers этой внутренней константы не найдено.

Никаких Pillow/save/walk/prints в facade. Интерактивный `main` заменяется forwarding CLI; README явно объясняет переход и сохраняемый Python import. Не создавать параллельный legacy codec путь.

## 7.2 `delete_original` и postfix

Разрушительный режим **не поддерживается во всём объёме этой поставки**, а не только временно внутри первого среза. Причина: source fingerprint/hash → unlink всё равно содержит TOCTOU; старый checkbox не даёт механизма подтверждённого conditional delete/replace, а crash-safe replacement/backup выходит за минимальную цель. Пользователь разрешил выбрать консервативный отказ; незаметно сохранить опасное удаление было бы хуже явной несовместимости.

- Worker принимает прежний аргумент и передаёт его без изменения в общий API; получает `DESTRUCTIVE_MODE_UNSUPPORTED`, ноль созданных файлов.
- Существующий GUI, где checkbox остаётся на месте по запрету менять виджеты, получает **понятный неуспех**: «Удаление/замена оригиналов недоступны в безопасном режиме. Снимите флажок “Удалять оригинальные файлы”». Это сообщение в уже существующих log/dialog, не новый экран/checkbox.
- Не выводить «успешно 0, ошибок 0». Старый signal получает ненулевой error count; новый typed результат точно говорит rejected. После снятия флажка тот же consumer реально создаёт безопасный результат.
- Postfix не удаляется и не игнорируется; именами владеет API. Применение к aliases JPEG/HEIF, пустому postfix и коллизиям проверяется. GUI getter по-прежнему подставляет `_compressed` за пустую строку как presentation default; прямой API сохраняет явную пустую строку.
- Нет deferred обязательства «потом вернуть unlink». Возврат удаления — отдельное разрешённое изменение с подтверждением последствий, защищённой точкой удаления/замены и тестами после readback.

## 7.3 Worker, finder и минимальный main-window wiring

- `CompressionWorker.run()` делает один `convert()`; без `set(files)`, собственного цикла save/unlink, `os.access`, повторной регистрации codecs и собственного именования. Сохранить constructor и сигналы `progress_updated(int)`, `file_processed(str)`, `log_message(str)`, `finished_processing(int,int)`.
- Добавить `result_ready(object)` для BatchResult и `result` для последнего итога; emit ровно один раз. Legacy `finished_processing` также ровно один раз: successful = succeeded, errors = failed + число общих errors (при глобальном отказе минимум 1); cancelled не считаются ошибочно success. Предметный итог хранит точные counts, включая публикацию без успеха.
- `cancel()` выставляет общий token; старый `is_cancelled` при необходимости — читаемая проекция запроса, не источник terminal status. Progress переводится в процент только когда total известен; cancellation не дорисовывается до 100%. `file_processed` — basename успешного элемента как локальный result signal, не diagnostic log.
- `gui.utils.get_image_files_from_paths()` сохраняет list[str] interface, делегирует discovery(recursive=True); не содержит таблицу расширений/walk. Main-window handler может вызывать discovery напрямую, чтобы не терять safe issues. Объединение предыдущего выбора и нового проходит ту же стабильную дедупликацию, не собственный set.
- `gui/__init__.py`: lazy import GUI-классов/экспортов и main; сохранить известные public names. Это позволяет проверять finder без неявного создания GUI и не смешивать core import с Qt.
- В `gui/main_window.py` менять только handlers/wiring: убрать предметную дедупликацию/ложный итог отмены; отобразить общий результат; не писать raw postfix/paths/exception в log. Существующая UI-проверка заполненности resize остаётся удобством, окончательная валидация всегда в API. Ветки раннего отказа восстанавливают start/stop состояние.
- Stop больше не вызывает блокирующий `wait()` и fabricated `compression_finished(0,0,...)`: запросить cancel, показать ожидание в существующем status/log, дождаться result и **QThread.finished**. До finished не разрешать новый запуск; удерживать worker reference. Не выводить два terminal dialog по legacy и новому сигналу.
- Закрытие окна при активном worker: запросить cancel, отложить close до QThread.finished; не разрушать работающий thread. Использовать существующие closeEvent/сигналы без новых виджетов. Не обещать bound времени закрытия native codec. Повторный запуск после ошибки/отмены получает новый worker/token.

Проверка этой дельты — headless Qt/QCoreApplication и adapter/controller harness; новое окно, screenshot, визуальная приёмка и переоформление не нужны. Для проверки существующих handler-ов допустим harness с заменёнными представлениями/messagebox, но настоящими worker/API/filesystem; такой тест не называется visual E2E.

# 8. Диагностика и приватность

Следовать [политике наблюдаемости](../foundation/observability-policy.md) и [инструкции](../instructions/logging.md). API-результат, Qt result signal, stderr diagnostic и `LOG.md` разработки — разные каналы.

- Core использует именованный logger, не root/basicConfig и не print. Formatter/emit получает **закрытый whitelist**: event, stage, reason, outcome, индекс, canonical format, quality, pixel dimensions, counts, size_bytes, duration_ms. Не передавать DTO целиком, filename, argv, exception, `exc_info`, stack/cause или произвольные extra.
- Достаточно `conversion_started`, `item_finished` (при ошибке обязательно), `conversion_finished`, `cleanup_failed`; `--progress` может включить дополнительные неперсональные counts. Terminal event не теряется. Operation correlation — один случайный локальный id, без нового tracing framework.
- Ошибка handler/formatter не меняет outcome и не создаёт raw fallback. CLI настраивает только свой logging sink; no persistent runtime log/rotation/export/telemetry. Не менять глобальные handlers host-приложения при импорте библиотеки.
- Worker `log_message` использует тот же safe projector; не вставлять даже basename в technical log. Поэлементная связь идёт через индекс и BatchResult. Main-window не пишет произвольный postfix. Result messages для rejected/delete — фиксированный текст.
- Legacy `gui/widgets.py` по scope остаётся неизменённым: его resize-getters сейчас печатают введённый текст/ValueError. `gui_main.py` тоже имеет старую raw import-error ветку. Не объявлять их защищёнными новой цепочкой и не расширять текущую работу в переработку виджетов/launcher. Проверяемая privacy-гарантия этой поставки — **новые API/CLI/compatibility facade и изменённые worker/main-window emitters**, не весь старый GUI. Этот известный предел явно записать в финальный отчёт; не использовать неизменённые debug prints как диагностический путь API.

Тест privacy обязан видеть полезные непустые события после реального formatter → handler → flush/readback. Sentinel в synthetic private path допускается в локальном JSON path-поле, но не в stderr/log buffer. Sentinel в raw exception и произвольном postfix не допускается в message/log. Тесты caplog-only или пустого вывода не достаточны.

# 9. Packaging и инструменты

1. Сохранить distribution `image-compressor`, requires-python `>=3.10`; новый код не должен случайно требовать Python 3.11-only API. Целевой runtime dependency — `Pillow>=12.0.0`. Extras: `codecs` (pillow-heif и pillow-avif-plugin с существующими lower bounds), `gui` (PyQt6), `build` (PyInstaller). В dev сохранить существующие pytest/Black/Ruff, добавить mypy с совместимой с проверяемой Python 3.14 версией; фактические версии записать по установке.
2. Setuptools явно включает `image_compressor`, `gui`, `py-modules=["classes", "gui_main"]`; без auto-discovery `tools`, `.agent-work`, build/dist. При необходимости `py.typed` — package data для публичных типов. Не создавать второй nested repository.
3. `requirements.txt` остаётся удобным полным GUI/build install для существующего bat-потребителя: заменить дубли runtime списков на ссылку `.[gui,codecs,build]` с пояснением запуска из корня. Pyproject — единственный owner зависимостей. README/UV_GUIDE различают bare headless install и GUI extras.
4. Не регенерировать старый requirements_freeze как якобы lock. Не обновлять весь runtime без причины; после установки dev-инструментов зафиксировать реальные versions. Глобальный pip/Python/Pi и source-pack не используются.
5. Pytest: `testpaths=["tests"]`, собственные synthetic fixtures, без root `test_gui.py`. Ruff gate по новым и реально изменённым Python-модулям; mypy строго по новому пакету и legacy facade. Узкие overrides для нетипизированных optional codec imports допустимы; не blanket `ignore_errors` и не массовая правка старого UI ради lint.

# 10. Четыре связных среза для Coder

Один автор реализации последовательно владеет общими DTO, filesystem и adapter-файлами. Это не четыре независимых параллельных писателя и не четыре новых микроплана. Каждый срез включает свои tests/docs delta; целиком задача Done только после всех четырёх.

| Срез | Scope / owner | Наблюдаемый результат и передача |
|---|---|---|
| **1. Один безопасный файл через API** | Coder: `image_compressor/{__init__,models,service,imaging,filesystem,diagnostics}.py`, `tests/conftest.py`, `tests/test_api.py`, `tests/test_filesystem.py`, manifest dev/test setup. | Прямой convert JPEG/WebP без Qt, runtime validation, resize, staging/readback/no-clobber, явный delete refusal. Реальный source/destination bytes и ошибки. Не выставлять ещё отсутствующий CLI как готовый. Этот owner затем принимает batch. |
| **2. Определённый пакет, codecs и отмена** | Coder: `discovery.py`, расширение тех же owners, `tests/test_discovery.py`, `tests/test_codecs.py`, `tests/test_cancellation.py`. | Recursive/dedup/order, frozen manifest, групповые collisions, доступные HEIF/AVIF roundtrips, error/partial/cancelled и следующая операция. API полный по §4–6; никаких Job/queue. |
| **3. CLI и устанавливаемая headless-поставка** | Coder: `cli.py`, `__main__.py`, `pyproject.toml`, `requirements.txt`, `tests/test_cli.py`, `tests/test_packaging.py`, `tests/test_privacy.py`. | Реальный subprocess parser → API → Pillow → final readback, JSON/exit/stderr, signal adapter, console entrypoint вне cwd репозитория. Packaging отделяет Qt; не только запуск из source tree. README получает настоящие команды после запуска. |
| **4. Сохраняемые consumers и закрытие знания** | Coder: `classes.py`, `gui/worker.py`, `gui/utils.py`, `gui/__init__.py`, только handlers `gui/main_window.py`; `tests/test_compatibility.py`, `tests/test_gui_adapter.py`; документы ниже. | Нет второй предметной реализации; старый класс и реальный QThread создают проверяемые файлы, delete даёт понятный отказ, stop не фабрикует итог. Полный suite/static gates, документация и freeze кандидата для одного независимого Reviewer. |

Путь `gui/widgets.py`, стили, старые bat/spec и `test_gui.py` не входят в implementation delta. При обнаруженной технической необходимости изменить их не расширять план задним числом: сначала точная причина Oracle/Hermes; это не повод блокировать независимый headless срез.

# 11. Достаточные проверки и границы подмен

Все runtime-проверки ниже **NOT RUN Oracle**. Coder создаёт изображения программно в tmp_path; source bytes и прежний output имеют различимые sentinels. До collection проверяет ранние imports/config; не запускает legacy launcher и не сканирует личные каталоги. Подпроцессы имеют timeout, cwd, закрытие pipes и cleanup с момента acquire.

| Критерий | Достаточный тест и обязательное наблюдение |
|---|---|
| Независимость | В отдельном Python-процессе запретить импорт `PyQt6`/`gui`/CLI для прямого API и facade через import hook; import + настоящий convert работают. Проверить отсутствие input/print и Qt/parser dependency в core. Наличие установленного Qt не считается доказательством независимости. |
| Один настоящий файл | Synthetic RGB JPEG/PNG → WEBP и JPEG через API, open/load final: actual format, exact размеры, ожидаемые пиксельные свойства; исходные bytes неизменны. Не требовать, чтобы lossy bytes совпадали или размер обязательно уменьшился. |
| Параметры/геометрия | Defaults, q=0/100 и -1/101/bool/float; invalid format/postfix; одна/две/нулевые стороны; 4000×3000 fit 1920×1080 → 1440×1080, маленькое изображение без upscale, узкое 1-px after shrink без нуля. EXIF orientation меняет расчёт до resize. |
| Image policies | Palette/RGBA alpha → WebP/доступный alpha codec; JPEG white background; EXIF/metadata sentinel отсутствует в output. Corrupt/truncated data, несколько кадров, bomb threshold (подмена лимита на маленький для test), неподдерживаемый режим → поэлементный отказ без публикации. |
| Codecs | Реальный probe и file roundtrip для каждого доступного JPEG/WEBP/HEIF/AVIF, actual format проверен не по suffix/import. PNG input отдельно. JPEG и WebP — обязательный PASS в текущей поставке. Optional HEIF/AVIF нельзя молча skip при успешно объявленной capability; несоответствие probe/convert — дефект. Недоступность имитируется только на codec-boundary для `FORMAT_UNAVAILABLE`, без подмены service. Реально недоступный optional codec отмечается reason/NOT RUN; другие форматы работают. |
| Discovery | Ordered mixed roots, directory+explicit file, repeated path, relative/absolute aliases, nested directory, recursive False/True, uppercase extensions, WebP, physical hardlink alias. Проверить **непустой точный** порядок/duplicates. Output child directory исключён; same root не исключён; новые результаты не становятся текущими inputs. |
| Links/отказы discovery | Missing path, readable+missing mixed package, inaccessible directory через controlled filesystem seam; explicit symlink/reparse отвергнут, nested link не обойдён. Реальные symlink tests зависят от OS privileges; отказ branch дополнительно тестируется без privileges. Hardlink тест на целевой NTFS обязателен как часть публикации. |
| Collisions | Same-path, empty postfix, JPEG/HEIF aliases, существующий чужой output, цель-другой-input, два разных входа с одной целью. Все конфликтующие entries failed, независимый файл succeeded, источники и чужие bytes неизменны. Repeat даёт collision, не overwrite. |
| No-clobber у точки эффекта | Hook между preflight и publish создаёт настоящий foreign destination; вызов реального os.link не затирает его. Дополнительно два процесса состязаются за одну цель: ровно одна publication, проигравший OUTPUT_EXISTS, валидный итоговый файл. Не подменять сам no-clobber primitive успешным mock. |
| Source/parent stale | В контролируемой паузе заменить/изменить source или destination parent до publish; получить SOURCE_CHANGED/DESTINATION_CHANGED, без новой публикации; чужая изменённая версия не удалена. Не обещать защиту от враждебной подмены после последнего checkpoint. |
| Fault boundaries | Реальный pipeline, подменён только край: ошибка save после частичных staging bytes; fail verification; link unsupported/access denied; readback fail **после** реального link; cleanup failure. Проверить отсутствие преждевременного final, cleanup только своего, существующий foreign temp не удалён, published-unverified остаётся и отражён в результате. |
| Отмена и повтор | Token до старта; cancel во время discovery; после первого item callback; после encode до publish через контролируемый seam; cancel после публикации текущего файла. Реальные байты и counts, новые элементы не стартуют после наблюдения token, late success допустим по контракту, staging убран. Следующая операция с новым token реально succeeds. Не подменять convert готовым cancelled DTO. |
| CLI E2E | Настоящий `python -m image_compressor convert ...` и установленный `image-compressor` subprocess: один файл, recursive batch+resize, partial с corrupt input, existing output, invalid quality/flag/empty dir, capabilities. stdout строго один JSON, stderr отдельно, raw exits 0/2/3/4; final open/load и source checks. Syntax/path с пробелом/Unicode/начальным дефисом как argv list, без shell. |
| CLI cancellation | Проверить signal handler → token → реальный API → JSON/130. Где поддерживается — реальный SIGINT/CTRL_BREAK дочернему процессу. Для Windows без доступной console delivery допустим отдельный subprocess harness, который входит в настоящий cli.main и в контролируемой точке вызывает `signal.raise_signal(SIGINT)`; подменён только источник сигнала/синхронизация, не API/codec. Нативную Ctrl-C доставку тогда честно отметить NOT RUN, не GUI E2E. |
| Старый Python consumer | Реальный ImageCompressor (не fake service) → output/readback; defaults HEIF/50 проверены при capability, WebP explicit всегда; directory recursive, setters, ошибки/last_result, explicit output collision. Import/методы не печатают paths. `classes.py convert ...` как subprocess forwarding CLI. |
| Qt adapter | Настоящий QThread с QCoreApplication, синтетический batch → outputs, реальные counts/signals ровно один раз. Cancel из callback/контролируемой паузы, global rejection и следующий новый worker. Delete True даёт rejected/ненулевой legacy errors/ноль outputs, False работает. Headless harness main handlers исключает double finish и start до QThread.finished; stop не делает wait/terminate. |
| Privacy | Реальный CLI stderr и собственный logging Stream/FileHandler sink в tmp с flush/read bytes; полезные event/reason/counts есть. Private-path/filename/raw-exception/postfix sentinels отсутствуют в diagnostics. Пути допустимы только JSON result path fields. Worker log_message buffer проверяется отдельно; отказ observer/handler не повторяет конвертацию и не меняет факт публикации. |
| Installed boundary | Собрать wheel project-local, проверить его состав и entry_points; установить в project-local disposable headless venv с Pillow, **без Qt**, запускать вне repo cwd. Console script → настоящий файл/readback; импорт classes присутствует. Optional codecs/GUI ставятся отдельно для полного consumer-набора в основной .venv. Editable/source-only PASS не заменяет этот тест. |

Достаточные целевые команды после подготовки окружения (выполняет **Coder**, не Oracle; реальные raw exits/versions фиксируются отдельно):

```text
.venv/Scripts/python.exe -m pip install -e ".[dev,gui,codecs]"
.venv/Scripts/python.exe -m pytest tests -q
.venv/Scripts/python.exe -m ruff check image_compressor classes.py gui/__init__.py gui/worker.py gui/utils.py gui/main_window.py tests
.venv/Scripts/python.exe -m mypy image_compressor classes.py
.venv/Scripts/python.exe -m pip wheel . --no-deps --wheel-dir .agent-work/wheels
```

Использовать project-local pip cache/tool environments. Wheel smoke fixture создаёт disposable venv под `.agent-work/`/своим test root, устанавливает конкретный полученный wheel и проверяет stdout/файл вне исходного дерева; не полагаться на PYTHONPATH cwd. Установка зависимостей разрешена только на implementation-шаге. Если pip отсутствует — восстановить его только в этом project venv, не менять глобальный Python. Не устанавливать UV/ast-grep/Serena ради ритуала.

Для docs checker использовать **отдельное локальное** `.agent-work/foundation-venv` с PyYAML 6.0.3 из локального pack, explicit corpus `.agent-work/foundation-corpus.json` и команду `...python.exe -I -B tools/project-foundation/tools/check_foundation.py --project C:/PY/image_compressor --corpus .agent-work/foundation-corpus.json`. Corpus содержит конкретные изменённые authoring docs и native AGENTS/README при необходимости, не весь диск/pack. Не читать tooling-venv соседнего source-проекта. Структурная проверка docs не заменяет runtime.

# 12. Знания и точечная коррекция основы Hermes

Oracle не редактирует инструкции; следующие необходимые изменения выполняются с реализацией, без массовой смены metadata/status:

1. `docs/README.md`: заменить ещё не существующий назначенный путь настоящей ссылкой на этот план; после реализации добавить `docs/architecture/application-api.md` и `docs/verification/command-first-refactoring.md`. Не делать план каноном уже реализованной функции.
2. `docs/foundation/architecture-principles.md`: вместо «Oracle выберет профиль/сигнатуры» сослаться на реализованный контракт A; old/current base оставить явно историческим. Уточнить create-only publication, отсутствие удаления и предел trusted local namespace/cooperative cancellation.
3. `AGENTS.md` и `docs/foundation/project-philosophy.md`: уточнить input/output различие — PNG только вход; сохранить приоритет сохранности. Не объявлять новый контракт accepted автоматически от записи кода.
4. `docs/instructions/testing.md`: заменить target placeholders фактическими scope/commands/raw evidence ссылкой; сохранить исходный факт отсутствия tools как baseline. В `docs/foundation/testing-strategy.md` убрать вариант использования tooling-среды source-проекта: нынешнее поручение запрещает дополнительное чтение соседа; только project-local isolated docs tooling.
5. `docs/foundation/observability-policy.md`: назвать реально защищённые emitters и известный неизменённый widgets/launcher debug предел из §8; не заявлять privacy всего GUI. `docs/instructions/logging.md` уже задаёт правильный whitelist/channel принцип, no-impact если реализация не требует иной политики. `docs/instructions/development.md` не менять роли/права: она уже достаточна.
6. Создать **один** `docs/architecture/application-api.md`: фактические операции/defaults/статусы/error/exit, владельцы, публикация, политика image data, совместимость и ограничения; code-first schema owner, не дублирующий реестр JSON. Не создавать отдельные ADR/паспорт/сценарий только ради шаблона — достаточный сценарий здесь и в контракте.
7. `README.md`: реальные headless/API/GUI installation recipes, canonical entrypoint, JSON/exit/retry/cancel, directory recursion default, имена/no-overwrite/delete refusal, формат capabilities, минимум Python и проверенная Windows-среда. Удалить отсутствующие main.py/run_compressor.bat, неверные PNG-output/многопроцессорность/«остановить в любой момент»/гарантированный коэффициент сжатия. EXE секцию обозначить отдельной непроверенной этой работой поставкой, не выдавать старый бинарник за новую реализацию.
8. `UV_GUIDE.md`: обновить extras, пути `.venv`, реальные форматы и ссылку на pytest/static scope вместо `ruff check .`; не предписывать глобальную установку tooling как условие новой работы. `QUICK_GUIDE.txt`: заменить рекомендации удаления/замены явным отказом и безопасными сценариями. `UPDATE_FEATURES.md`: сохранить исторический текст, добавить заметное предупреждение, что destructive режим старой версии не действует, и ссылку на README/контракт. `RELEASE_NOTES.md`, `PROJECT_STATUS.md`, `BUILD_*` не переписывать как новые проверки; актуальный README не должен опираться на их старые PASS. При прямой ссылке обозначить историческую/сборочную границу.
9. `docs/verification/command-first-refactoring.md` (kind verification) — Coder записывает actual changed paths/base, команды/versions/raw exits, параметры synthetic fixtures, реальные компоненты/подмены, первую ошибку и причину, кодек/FS/OS limits, NOT RUN. Reviewer дополняет своим verdict или Hermes прикрепляет ссылку на отдельный review handoff, не превращая авторский PASS в независимый.
10. `LOG.md` — краткая запись implementation/проверок по факту от текущего владельца; native sessions/evidence остаются в `.agent-work/`. Русский README/существующие русские guides — текущая пользовательская редакция; заказанных переводов нет, новых переводных деревьев не создавать. Скриншоты не нужны.

# 13. Риски, достаточность и handoff

| Риск / неизвестное | Решение без дополнительного материального выбора пользователя |
|---|---|
| Hard links не работают на выбранной FS | Fail closed, `PUBLICATION_UNSUPPORTED`; на локальной test NTFS проверить настоящий primitive. Не ослаблять no-clobber ради переносимости. |
| Наличие pillow_avif не говорит о native AVIF/HEIF encode | Проверить probe/real file pipeline в implementation; capability отражает факт, optional unavailable не валит остальные форматы. |
| Отказ от удаления заметен GUI-потребителю | Явный общий refusal до эффектов + существующее сообщение + documented migration + тест False после True. Не молчаливое исчезновение функции. |
| Изменения namespace сторонним процессом | Повторные проверки типов/fingerprint/parent identity, атомарное no-replace. Нет обещания защиты от враждебной перестановки ancestors, особенно remote FS. Удаления нет. |
| Native codec не отдаёт управление | Только cooperative stop; ждать thread completion без блокирования UI. Процессная изоляция/таймауты — отдельное новое требование. |
| Metadata/color/frame policies меняют случайное старое поведение | Явные правила §4.2, source retained; отказ при неоговорённом, без скрытой деградации/кадра 0. |
| Класс возвращал None и молчал при ошибке | None success сохранён; errors теперь явны, last_result даёт подробности; реальные callers переключены атомарно на общий контракт. |
| Widgets/launcher остаются с raw debug | Прямой запрет менять widgets соблюдается; приватность всей старой оболочки не заявляется. Новый pipeline/затронутые emitters проверяются; предел обозначен, не скрытая обязательная UI-переработка. |
| Python 3.14/dev tools/packaging | Локальная установка и настоящие gates/wheel smoke; failed tooling run не product PASS. Python 3.10 совместимость сохранять в коде, но не объявлять runtime PASS без отдельного запуска этой версии. |

**Существенных пользовательских blockers для начала нет.** Консервативная файловая политика выбрана явно; неопределённость кодеков/FS разрешается конечными synthetic тестами, не новым архитектурным исследованием. Если фактическая ошибка противоречит выбранной гарантии, вернуть тому же Oracle точные input/command/exit/file:line и вопрос, не навязанный диагноз и не просьбу заменить гарантию зелёным assertion.

## Передача Hermes → Coder → Reviewer

1. Hermes передаёт этот план целиком Coder в отдельной сохраняемой Pi-беседе (`openai-codex/gpt-6.1-sol`, запрошенный max), без второго автора архитектуры. Сверить root/dirty state; создать `refactor/command-first` без перезаписи одноимённой ветки. Oracle ветку не создавал. Незакоммиченная основа переходит как working-tree changes, не как docs commit.
2. Coder начинает с среза 1 и доводит все четыре. Один писатель общих файлов. Никаких stage/commit/merge/push, установок глобально, доступа к source-pack или личным данным. План можно уточнять фактическими ссылками в назначенном документе, но не менять смысл safety/объём без согласования.
3. До freeze Coder показывает actual committed/staged/unstaged/untracked delta относительно `7707849`; явно отличает Hermes foundation от своих application/tests/docs изменений. Перечисляет commands/raw exits/limitations и session locator; обновляет knowledge owners.
4. Один независимый Reviewer в отдельной Pi-беседе той же назначенной Sol/max роли проверяет замороженный candidate, весь связный API/CLI/filesystem/consumer scope и достаточность evidence. Не редактирует код. Обязательные замечания file:line — тому же Coder; архитектурные вопросы — тому же Oracle. Повторная проверка affected delta у того же Reviewer, без проверяющего проверяющего.
5. **Done:** реальный прямой API без Qt и установленный CLI создают проверенные файлы; batch/dedup/resize/codecs/errors/collisions/source preservation/cancellation/следующая операция доказаны в выбранной среде; реальные старые consumers используют единственный owner; privacy затронутых каналов и static gates пройдены; документация соответствует фактам; обязательных review замечаний нет. Недоступные optional codecs/нативная доставка console signal/другие OS/EXE/visual/MCP отмечены точным пределом, а не PASS.
6. Итог Hermes пользователю: полезный результат, реальные проверки и NOT RUN, ветка и отсутствие commit, конкретный обязательный остаток либо его отсутствие. После выполнения исходной цели остановиться.

## Что Oracle фактически сделал

Полностью прочитаны AGENTS, карта docs, все четыре foundation и три instruction документа, оба назначенных SKILL и cli-first-delivery; использованы общие lifecycle/metadata/quality, contract-evolution/change-impact и нужные первичные разделы [02](../../tools/project-foundation/references/architecture/command-first/02_Command_First_Architecture_and_Contracts.md) (§3–9, 14–17, 19–20), [03](../../tools/project-foundation/references/architecture/command-first/03_Command_First_Architecture_Variants.md) (§3–9, 14–16, 21, 23–25), [04](../../tools/project-foundation/references/architecture/command-first/04_Command_First_Image_Converter_Architecture.md) (§6, 11–13, 16–18, 25–27). Схемы учебного конвертера не перенесены как требования: его Job/журнал/MCP/attached/опасные режимы здесь не нужны.

Прочитаны реальные исходники и потребители, перечисленные в §2; выполнены только read-only Git/root/date diagnostics. **Приложение, GUI, pytest, линтеры, кодеки, checker, сборка и установки Oracle не запускал.** Единственная проектная запись — этот план. Это достаточный handoff для реализации, не самопринятая реализация или независимое заключение.
