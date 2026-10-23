# Image Compressor

Локальное преобразование изображений через Python API, неинтерактивный CLI и существующий GUI на PyQt6. Единый исполнитель последовательно обрабатывает пакет и возвращает проверяемый поэлементный итог.

**Сохранность:** только создание нового файла, без overwrite и удаления исходника. Результат сначала кодируется/проверяется в staging, затем атомарно публикуется новым hard link и повторно читается. Неподдерживаемая файловая система получает явный отказ, не небезопасный fallback.

Command-first-срез независимо принят (**ACCEPT**) после ремонта R1/R2: Reviewer повторил 170 тестов без skips и исходные image-policy discriminators через API и установленный CLI без Qt. Это не новый EXE-релиз; точная граница и история проверок — ниже по ссылкам. [Контракт API v1](docs/architecture/application-api.md) · [фактические проверки и ограничения](docs/verification/command-first-refactoring.md) · [карта документации](docs/README.md).

## Установка

Python **3.10+**. Авторские и независимые runtime-проверки выполнены на Windows 11 / local NTFS, Python 3.14.2; другие ОС/версии Python здесь не квалифицированы. Команды ниже для PowerShell из корня исходников; примеры `sample.png`/`samples` замените своими выбранными путями.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\image-compressor.exe capabilities
```

Bare install требует только Pillow, **не Qt**. Если среда создана uv без pip, используйте уже установленный uv: `uv pip install --python .venv/Scripts/python.exe .`. Устанавливать глобальные инструменты для запуска приложения не требуется.

Дополнительно:

```powershell
# Optional HEIF/AVIF providers; фактическую доступность покажет capabilities
.\.venv\Scripts\python.exe -m pip install ".[codecs]"
# Существующий GUI и optional codecs
.\.venv\Scripts\python.exe -m pip install ".[gui,codecs]"
.\.venv\Scripts\python.exe gui_main.py
# Разработка (editable + проверки + GUI/codecs)
.\.venv\Scripts\python.exe -m pip install -e ".[dev,gui,codecs]"
```

`requirements.txt` — удобный **полный GUI/codecs/build install** для старых batch-потребителей: `python -m pip install -r requirements.txt` из корня. Единственный owner зависимостей — `pyproject.toml`. Build extra содержит PyInstaller; EXE в этой работе не собирался. Про uv — [UV_GUIDE](UV_GUIDE.md).

## CLI

```powershell
.\.venv\Scripts\image-compressor.exe convert sample.png --format WEBP --quality 80
.\.venv\Scripts\python.exe -m image_compressor convert samples --recursive --max-width 1920 --max-height 1080
# Каталог назначения уже должен существовать; flat layout
.\.venv\Scripts\image-compressor.exe convert sample.png --output-dir converted
# Точное имя — только для одного явно выбранного файла
.\.venv\Scripts\image-compressor.exe convert sample.png --format JPEG --output result.jpg
# Пути с ведущим дефисом, пробелами и Unicode передаются как argv data
.\.venv\Scripts\image-compressor.exe convert -- "-пример с пробелом.png"
```

- По умолчанию WEBP, quality 80; quality — integer **0..100**, не обещание одинакового perceptual quality разных кодеков. При resize обязательны обе положительные стороны, без увеличения/crop. Orientation применяется до расчёта размеров.
- Directory по умолчанию **нерекурсивный**, `--recursive` включает подпапки. Порядок roots сохраняется; внутри каталога — стабильная сортировка. Повторные пути/доступные physical hardlink aliases учитываются один раз, не через unordered set.
- Входные расширения JPEG/JPG, PNG, WebP, HEIF/HEIC, AVIF. Выходы **JPEG, WebP, HEIF, AVIF**. PNG только вход. Список расширений не доказывает читаемость конкретного файла.
- `capabilities` делает реальные synthetic in-memory roundtrip probes и возвращает для формата decoder_registered, encoder_available, roundtrip_verified, alpha_verified, provider, safe reason. Встроенный рабочий AVIF предпочитается optional plugin. HEIF/AVIF могут быть недоступны в конкретной установке.
- Рядом с source: `a.png → a.webp`, `a.webp → a_compressed.webp`, `a.jpeg → a_compressed.jpg`. `--postfix _small` меняет postfix при совпадении suffix family. Явная пустая строка в API не подменяется default; совпавшая цель отвергается.
- `--output-dir` — существующий обычный каталог, без неявного создания/сохранения иерархии. Строгий output-потомок исключается из входного обхода. Состав фиксируется до записи; новые результаты не включаются в текущий пакет. Ранее существовавшие outputs в других местах могут стать обычными входами нового запуска.
- Существующая цель любого типа, совпадение с любым входом или общая цель нескольких inputs — ошибка. Все члены collision-группы отказывают, независимые файлы продолжаются. Нет auto-numbering/overwrite/silent skip.

### Ответ и коды завершения

`capabilities`/`convert` всегда возвращают **один UTF-8 JSON object + newline** в stdout (`--json` — явный no-op этого режима). Поля: `schema_version: 1`, `command`, `status`, `result`, `errors`. Result содержит effective options, discovery_complete, items с absolute source/destination/artifact/error и counts. Неизвестное — null; ноль/false/пустые массивы не теряются. Help/version — обычный текст, exit0. Диагностика начала/итога и safe reason/counts — отдельно в stderr; `--progress` добавляет поэлементные counts, не private paths/argv/tracebacks.

| Exit | Значение |
|---|---|
| 0 | Полный succeeded; capabilities/help/version |
| 2 | CLI usage или rejected: параметры, недоступный encoder, пустой завершённый набор |
| 3 | partial: есть успех/публикация и ошибка либо cleanup residual |
| 4 | failed без успеха/публикации |
| 5 | INTERNAL_ERROR или ошибка доставки stdout |
| 130 | Применённая cooperative cancellation; готовые файлы могут остаться |

`published` отдельно от `succeeded`: опубликованный, но не подтверждённый final readback файл получает artifact `publication="unverified"` и не считается успехом. `total=succeeded+failed+cancelled`; duplicates/ignored вне total. При неполном discovery total — только найденная часть, конвертация её не начинается.

Ctrl-C/SIGBREAK **запрашивает** остановку. Native codec может ещё работать; прошедший последний checkpoint файл может опубликоваться. Уже готовые outputs сохраняются. Нативная доставка Windows console Ctrl-C/CTRL_BREAK в этой работе NOT RUN; handler→token→реальная конвертация проверены отдельным signal harness. Повторный сигнал не force-kill.

Повтор вызова — новое действие: прошлые outputs дадут collision. После потери ответа/ошибки stdout сначала проверьте известные назначения; не запускайте слепой retry с overwrite. Закрытый stdout не откатывает публикацию.

## Python API без Qt и CLI-парсера

```python
from image_compressor import ConversionRequest, convert, get_capabilities

capabilities = get_capabilities()
result = convert(ConversionRequest(
    inputs=["sample.png"], output_format="WEBP", quality=80,
    max_width=1920, max_height=1080,
))
# result.status и поэлементные result.items — авторитетный итог.
# Для cooperative stop передайте новый CancellationToken;
# on_progress получает короткие синхронные immutable события.
```

Импорт ничего не конвертирует и не probe-ит. DTO immutable; runtime validation выполняется и при прямом вызове. API не печатает/не спрашивает ввод/не управляет сигналами. Входы — непустая sequence str/PathLike[str], не один str; не раскрываются `~`, env/glob или кавычки.

Сохранён `from classes import ImageCompressor`: defaults **HEIF/50** (в отличие от нового API WEBP/80), свойства и методы. Методы возвращают None только при полном успехе, сохраняют last_result; иначе поднимают `CompressionError` с code/result. Directory/input методы рекурсивны; старое снятие внешних двойных кавычек осталось только в process_input. `python classes.py convert ...` теперь вызывает тот же CLI; прежних интерактивных вопросов больше нет.

## Существующий GUI

Оформление/виджеты не перепроектированы. Worker вызывает тот же API один раз, показывает настоящий результат и ждёт QThread.finished перед новым запуском/закрытием окна. Stop не блокирует UI через wait/terminate и не выдумывает нулевой итог.

**Снимите флажок “Удалять оригинальные файлы”.** Удаление/замена в безопасном режиме недоступны: `delete_original=True` явно отвергается **до эффектов**, в том числе старым worker, с понятным сообщением. Флаг не игнорируется; CLI delete/overwrite flags отсутствуют. Возврат destructive режима — отдельная задача, не скрытое обещание.

Старые resize-getters `gui/widgets.py` и import-error ветка `gui_main.py` оставлены неизменными по границе задачи и имеют debug/raw вывод. Проверенная privacy-цепочка — новые API/CLI/facade и изменённые worker/main-window emitters, **не весь старый GUI**. Qt/controller tests не являются визуальной приёмкой.

## Политика данных и пределы

Поддерживаются обычные статические 8-bit изображения. Несколько кадров, неоговорённые 16-bit/HDR/modes, повреждённые/truncated/bomb inputs явно отвергаются. У PNG исходная разрядность проверяется по IHDR **до load**: 16-bit RGB/RGBA/LA/grayscale дают `IMAGE_MODE_UNSUPPORTED`, даже если Pillow уже показывает RGB/RGBA. Молчаливая потеря младших битов не разрешена.

Прозрачность определяется пикселями подготовленного растра **после orientation/resize**, не просто наличием A-канала или transparency key. Полностью opaque RGBA/LA и неиспользованная palette/color-key transparency допустимы; избыточный opaque A нормализуется в RGB. Кодек вправе не хранить такой A. Фактическая прозрачность требует проверенной alpha-способности provider и повторной проверки результата; исчезнувшая или ложно появившаяся прозрачность — ошибка verification. Для JPEG alpha композируется на белый.

EXIF Orientation применяется; **EXIF/XMP/ICC/comments не переносятся**. Архивная/цветометрическая точность, меньший размер файла и одинаковое качество кодеков не обещаны; оригинал остаётся для другой обработки.

Atomic no-replace hard link проверен на local NTFS. Нет unsafe fallback для FAT/exFAT/неподдерживаемой share. Это atomic visibility одного нового файла, не crash durability или транзакция пакета. Нет fsync/recovery/автоматического удаления crash-staging; cleanup удаляет только собственный учтённый payload и пустой dir. Trusted local namespace — не sandbox от враждебной подмены ancestors и не защита от последующей чужой записи. RAM/CPU/time budget и изоляция native codec не реализованы.

Нет runtime telemetry, сетевых продуктовых вызовов, daemon/MCP или постоянного журнала по умолчанию. Локальные result paths в stdout не являются разрешением копировать их в technical logs/экспорт.

## Разработка и evidence

Точные pytest/Ruff/mypy/docs commands, версии, raw exits, реальные компоненты и fault seams — [инструкция тестирования](docs/instructions/testing.md) и [verification](docs/verification/command-first-refactoring.md). Все изображения synthetic. Suite включает установку настоящего wheel вне repo в venv **без Qt**, API/CLI readback, no-clobber race, отмену/следующую операцию и QThread. Независимый Reviewer подтвердил технический результат; последующие docs/package checks closeout — author verification той же роли, не новая независимая приёмка.

[BUILD_QUICK](BUILD_QUICK.md), [BUILD_README](BUILD_README.md), [UPDATE_FEATURES](UPDATE_FEATURES.md), RELEASE_NOTES и PROJECT_STATUS — исторические/сборочные материалы, не evidence новой версии. Старые EXE/build outputs не обновлялись и не выдают этот рефакторинг за выпущенный бинарник. Новый GUI, visual qualification, EXE-сборка/релиз и другие платформы — вне текущего результата.

Автор исходного проекта: Vladimir Monin. Версия distribution сохранена: 1.0.0; отдельный release/EXE этой работой не создаётся. Source-срез и необходимая документация сохраняются вместе на `refactor/command-first`; доставка feature branch не означает merge/tag/release.
