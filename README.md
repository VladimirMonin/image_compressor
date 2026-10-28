# Image Compressor

Локальное преобразование изображений через Python API, неинтерактивный CLI и GUI. Канонический GUI продукта — `gui_pyside6_v2/` (PySide6 Widgets v2); legacy PyQt6-оболочка и compatibility facade выведены из рабочей копии. Единый исполнитель последовательно обрабатывает пакет и возвращает проверяемый поэлементный итог. Точная каноническая линия, байты бинарника и границы — в [release record](docs/releases/windows-pyside6-20261028-candidate-05.md).

**Сохранность:** по умолчанию — только создание нового файла, без overwrite и удаления исходника. Opt-in `delete_original=True` (рабочая галочка, default OFF) удаляет выбранный исходник безвозвратно только после verified final output на supported Windows local fixed NTFS; ошибка/отмена/unknown сохраняют его и отражаются как retained/unknown; unsupported — явная ошибка. Корзины/undo нет. В принятом `candidate-05` удаление доступно как opt-in; `candidate-03` его не содержал, `candidate-04` — proposed без доставки ACCEPT ([release record](docs/releases/windows-pyside6-20261028-candidate-04.md)). Результат сначала кодируется/проверяется в staging, затем атомарно публикуется новым hard link и повторно читается. Неподдерживаемая файловая система получает явный отказ, не небезопасный fallback.

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
# Canonical GUI — PySide6 v2 в отдельной среде
python -m venv .agent-work\figcraft-gui-experiment\pyside6-venv
.\.agent-work\figcraft-gui-experiment\pyside6-venv\Scripts\python.exe -m pip install ".[gui-pyside6,codecs]"
.\.agent-work\figcraft-gui-experiment\pyside6-venv\Scripts\python.exe -m gui_pyside6_v2
# Разработка (editable + проверки + canonical GUI/codecs)
.\.venv\Scripts\python.exe -m pip install -e ".[dev,gui-pyside6,codecs]"
```

`requirements.txt` — удобный **canonical GUI/codecs/build install** для batch-потребителей: `python -m pip install -r requirements.txt` из корня. Owner зависимостей Python distribution — `pyproject.toml`; точные standalone build pins выделены в отдельный recipe. Build extra содержит PyInstaller для standalone EXE. Про uv — [UV_GUIDE](UV_GUIDE.md).

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

## Канонический GUI · PySide6 v2

Desktop-дизайн создан в настоящем редактируемом FigCraft; реализация — `gui_pyside6_v2/`, без изменений ядра. Legacy PyQt6 GUI и compatibility facade удалены из рабочей копии; история сохранена в Git. Две темы, RU/EN/KK, пофайловая очередь, file/folder/drop, качество/resize/postfix, настоящий batch API, stop/отложенное close и bounded journal. **Удаление оригиналов — opt-in:** рабочая галочка default OFF; включение разрешает безвозвратное удаление выбранного исходника только после verified final output на supported Windows local fixed NTFS; Корзины/undo нет, unsupported даёт явную ошибку. Журнал: вкладка «Журнал операции» — только человеческая summary (имя/формат, было→стало, статус, удалён/сохранён); все технические детали (raw events, пути, params, SHA, errors) — в существующей вкладке «Подробности». Принятый `candidate-03` этой функции не содержит; `candidate-04` — proposed до ACCEPT ([release record](docs/releases/windows-pyside6-20261028-candidate-04.md)).

Используйте отдельную среду (не заменяйте старую `.venv`):

```powershell
python -m venv .agent-work\figcraft-gui-experiment\pyside6-venv
.\.agent-work\figcraft-gui-experiment\pyside6-venv\Scripts\python.exe -m pip install ".[gui-pyside6,codecs]"
.\.agent-work\figcraft-gui-experiment\pyside6-venv\Scripts\python.exe -m gui_pyside6_v2
```

Если экспериментальная среда уже создана, пропустите создание. Не загружайте оба Qt binding в один процесс. FigCraft не нужен для runtime. Native/exports — в `design/`; [запуск и проверки](docs/figcraft_gui_experiment/RUNNING.md) · [дизайн→Qt](docs/figcraft_gui_experiment/03-design-spec.md) · [отчёт и честная оценка](docs/figcraft_gui_experiment/REPORT.md). Эксперимент независимо принят: **технический и визуальный ACCEPT**. Reviewer отдельно выполнил 47 PySide6 и 170 legacy/API/CLI/package тестов без skips, официальный native reopen/export и Windows-native/installed проверки; точная граница — в отчёте. Это отдельное принятие, не автоматическое расширение прежнего ACCEPT и не EXE-релиз. Физические OS-dialog/drop, screen reader, другие платформы и все DPI не квалифицированы.

### Самостоятельный Windows EXE · PySide6 v2

Готовый **Windows x64 one-file EXE**. Принятый `20261028-candidate-05` **независимо принят exact-byte** 2026-10-28; `candidate-03`/`candidate-04` — `superseded` и перемещены в Recycle Bin. Desktop `Image Compressor.lnk` и `run_image_compressor_v2.bat` указывают на него; точные байты/provenance — в [release record](docs/releases/windows-pyside6-20261028-candidate-05.md). До ACCEPT Desktop `.lnk` и `run_image_compressor_v2.bat` продолжают указывать на `candidate-03`. Запуск без Python/Qt/кодеков; [запуск и сборка](docs/figcraft_gui_experiment/WINDOWS_EXE.md) · [историческая exact-byte проверка](docs/figcraft_gui_experiment/05-windows-exe-verification.md). Проверка выполнена на текущем Windows11 x64/local NTFS host, не на новом аккаунте/чистой машине и не для всех DPI. One-file использует writable TEMP. Артефакт локальный, неподписанный, без installer/публикации. В `candidate-04` нет PyQt6/legacy-модулей; deletion работает только по opt-in и только после verified output.

## Политика данных и пределы

Поддерживаются обычные статические 8-bit изображения. Несколько кадров, неоговорённые 16-bit/HDR/modes, повреждённые/truncated/bomb inputs явно отвергаются. У PNG исходная разрядность проверяется по IHDR **до load**: 16-bit RGB/RGBA/LA/grayscale дают `IMAGE_MODE_UNSUPPORTED`, даже если Pillow уже показывает RGB/RGBA. Молчаливая потеря младших битов не разрешена.

Прозрачность определяется пикселями подготовленного растра **после orientation/resize**, не просто наличием A-канала или transparency key. Полностью opaque RGBA/LA и неиспользованная palette/color-key transparency допустимы; избыточный opaque A нормализуется в RGB. Кодек вправе не хранить такой A. Фактическая прозрачность требует проверенной alpha-способности provider и повторной проверки результата; исчезнувшая или ложно появившаяся прозрачность — ошибка verification. Для JPEG alpha композируется на белый.

EXIF Orientation применяется; **EXIF/XMP/ICC/comments не переносятся**. Архивная/цветометрическая точность, меньший размер файла и одинаковое качество кодеков не обещаны; оригинал остаётся для другой обработки.

Atomic no-replace hard link проверен на local NTFS. Нет unsafe fallback для FAT/exFAT/неподдерживаемой share. Это atomic visibility одного нового файла, не crash durability или транзакция пакета. Нет fsync/recovery/автоматического удаления crash-staging; cleanup удаляет только собственный учтённый payload и пустой dir. Trusted local namespace — не sandbox от враждебной подмены ancestors и не защита от последующей чужой записи. RAM/CPU/time budget и изоляция native codec не реализованы.

Нет runtime telemetry, сетевых продуктовых вызовов, daemon/MCP или постоянного журнала по умолчанию. Локальные result paths в stdout не являются разрешением копировать их в technical logs/экспорт.

## Разработка и evidence

Точные pytest/Ruff/mypy/docs commands, версии, raw exits, реальные компоненты и fault seams — [инструкция тестирования](docs/instructions/testing.md) и [verification](docs/verification/command-first-refactoring.md). Все изображения synthetic. Suite включает установку настоящего wheel вне repo в venv **без Qt**, API/CLI readback, no-clobber race, отмену/следующую операцию и QThread. Независимый Reviewer подтвердил технический результат; последующие docs/package checks closeout — author verification той же роли, не новая независимая приёмка.

Исторические build/status-материалы retired вместе с legacy PyQt6-маршрутом (история сохранена в Git). Старые EXE/build outputs не обновлялись и не выдают этот рефакторинг за выпущенный бинарник. Исторический command-first ACCEPT не включал новый GUI/visual qualification. Курированная сборка и её проверки описаны отдельно выше; её статус не переписывает историческую границу. Единственная каноническая линия GUI/EXE, состояние веток и границы — в [release record](docs/releases/windows-pyside6-20261028-candidate-04.md). Публичный release и другие платформы не квалифицированы.

Автор исходного проекта: Vladimir Monin. Версия distribution сохранена: 1.0.0; публичный release не создаётся; отдельный локальный Windows EXE относится только к курированной standalone-сборке. Source-срез и необходимая документация сохраняются вместе на `refactor/command-first`; доставка feature branch не означает merge/tag/release.
