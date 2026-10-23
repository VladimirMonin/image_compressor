---
id: ic-command-first-verification
title: "Command-first — проверки, ремонт и независимый ACCEPT"
kind: verification
status: accepted
created: "2026-10-23"
updated: "2026-10-23"
areas: [testing, command-first, data-safety, packaging, privacy]
summary: "Независимый ACCEPT после R1/R2: Reviewer повторил 170 тестов и исходные API/installed discriminators; docs closeout проверяется отдельно."
code_ref: "770784935c52eaa3add6a9a1ec50b5154c9f1e3c + accepted source/test inventory SHA-256 9ef5bbf6c4af8af07f3c2744212f103b6666a94568841c2fcc99aa64d541dccd"
code_verified_at: "2026-10-23"
verification_scope: "Раздельные авторские проверки, независимые Reviewer executions и ACCEPT API/CLI/filesystem/codecs/Qt/installed-wheel; последующий docs/package closeout не новая независимая приёмка."
---

# Предмет и статус

Реализованы четыре связанных среза [плана](../plans/command-first-refactoring.md). [Application API v1](../architecture/application-api.md) остаётся единым прикладным owner-ом; CLI, старый класс и QThread — адаптеры. Create-only публикация, source/foreign preservation, cancellation и отсутствие destructive fallback не изменены ремонтом image policy.

База `770784935c52eaa3add6a9a1ec50b5154c9f1e3c`, ветка `refactor/command-first`. Ниже сохранены авторские evidence и история первого NEEDS_CHANGES; отдельный раздел фиксирует последующий **независимый ACCEPT** исправленной редакции тем же Reviewer. Принятие связано с source/test bytes inventory SHA-256 `9ef5bbf6c4af8af07f3c2744212f103b6666a94568841c2fcc99aa64d541dccd`; последующий public docs closeout не меняет код/tests. Право того же accepting Reviewer на selective commit и feature-branch push отдельно дано пользователем; [development](../instructions/development.md) сохраняет точные ограничения. Feature-branch delivery не EXE/release и не merge.

## Сохранённая история

- Первоначальный API run завершился exit1: 10 failed / 30 passed из-за сравнения разных Windows path/descriptor ctime clocks. Исправление сохраняет оба snapshots и stat/fstat guards; повтор прошёл. Это дефект реализации, не основание убрать защиту.
- Предыдущая полная авторская редакция: 141 passed, 0 skips; Ruff/strict mypy/docs checks — exit0. Это не независимая приёмка и не доказательство отсутствия непокрытых случаев.
- Независимая проверка той редакции повторила 140 suite tests и собственный installed путь, но дала **NEEDS_CHANGES** по двум содержательным image-policy дефектам ниже. Эти замечания не исчезают из истории от нового авторского PASS.
- Новая авторская редакция исправляет оба findings. Полные сырые команды/выводы и исходные failing fixtures сохранены отдельно от публичной документации; старые evidence/wheels не переписаны. Здесь нет private machine/session locators или личной переписки.

# R1 / R2: дискриминаторы, controls, ремонт

## R1 — семантическая прозрачность, а не наличие A

До ремонта допустимый PNG 24×18 RGBA `(30,120,210,255)` давал `VERIFICATION_FAILED` в staging; API published=0, настоящий source CLI exit4. То же наблюдалось у opaque LA, RGB с неиспользованным transparency key и palette с неиспользованным прозрачным индексом для WebP/AVIF. Matched translucent RGBA alpha=73 проходил; JPEG/HEIF также проходили opaque case. Источник не менялся, staging очищался: отказ не был collision/fixture/environment ошибкой.

Причина: prepared alpha вычислялась по наличию канала/key до resize, verifier требовал физический A. WebP/AVIF правомерно опускали полностью opaque A.

Ремонт в [imaging.py](../../image_compressor/imaging.py):

- Alpha-bearing source сначала корректно нормализуется; actual transparency измеряется по пикселям **подготовленного растра после orientation/resize**.
- Полностью opaque A нормализуется в RGB; alpha-capability требуется только для настоящей prepared transparency.
- Staging/final verifier проверяет ту же семантику, а не физическое наличие избыточного канала. Исчезновение настоящей прозрачности, превращение её в opaque и ложное появление прозрачности остаются отказами; guard не удалён и не стал безусловным допуском.
- Случай sparse alpha, который после 64×64→1×1 LANCZOS округляется в fully opaque raster, проверяется отдельно. Controls alpha=0/73/255 с resize проходят реальные доступные codecs.

## R2 — исходная PNG precision до decoder downconvert

До ремонта валидные PNG 12×10 с IHDR bit_depth=16, color type 2/6, samples `(0x1234,0x5678,0x9abc[,0x8000])` возвращали succeeded / artifact verified / published=1, CLI exit0. Pillow уже показывал RGB/RGBA и при load отбрасывал младшие биты. 8-bit RGB control проходил, grayscale I;16 control правильно отвергался — именно цветной 16-bit input различал дефект.

Ремонт: после распознавания actual PNG, **до `load()`**, общий imaging owner через тот же tracked handle читает фиксированные 33 bytes signature/IHDR/CRC и восстанавливает позицию. Precision>8 даёт `IMAGE_MODE_UNSUPPORTED` на decode stage, без публикации. Suffix и уже усечённые Pillow pixels не используются как доказательство bit depth. Полный parser/decode/verification остаётся Pillow; проверка заголовка не заменяет их и не отключает bomb/truncated guards.

Регрессии включают RGB/RGBA, LA и grayscale 16-bit, все соответствующие 8-bit controls, actual PNG под `.jpg` и наблюдение, что source pixel load не вызван для отказавшего 16-bit входа. Fixture generator независимо проверяет IHDR, chunk CRC и полный decompressed scanline payload; ошибочный PNG не выдаётся за policy discriminator.

## Первый RED и тот же GREEN

Первым действием ремонта оба finding + matched controls воспроизведены на настоящих API/source CLI в новом synthetic root: 8 opaque input/codec отказов и 2 silent-precision violations; CLI exits opaque=4, translucent=0, RGB8=0, gray16=4, RGB16/RGBA16=0.

Новые постоянные [policy tests](../../tests/test_imaging_policy.py) на прежнем owner-е: **exit1, 13 failed / 9 passed**, содержательный RED, не import/collection failure. После одного связного ремонта тот же selection: **exit0, 22 passed**. Повтор полного discriminator/control probe: **exit0**, violations=[], opaque/translucent/RGB8 CLI=0, все 16-bit CLI=4 с `IMAGE_MODE_UNSUPPORTED`, published=0. Новых skip/xfail/deselection для findings нет.

# Финальные авторские проверки

Selections выполнялись project Python из корня. До collection заданы собственные TEMP/TMP/TMPDIR, pytest basetemp и tool caches; third-party pytest autoload отключён, pytest-timeout включён явно. Весь `tests/`, включая packaging, выбран без deselection. Test timeout 90 s, installed tests 240 s, subprocess — finite timeout/cleanup. Все изображения синтетические, product external services/личные данные не использовались. Новое provisioning для ремонта не требовалось.

```text
python -B -m pytest -p pytest_timeout -p no:cacheprovider tests -q -ra
python -B -m ruff check image_compressor classes.py gui/__init__.py gui/worker.py gui/utils.py gui/main_window.py tests
python -B -m mypy image_compressor classes.py
```

Публично указаны selections; конкретные disposable/cache roots и полные raw argv сохраняются в локальном handoff, не являются каноном поведения. Общая [инструкция тестирования](../instructions/testing.md) описывает изоляцию и docs checker.

| Проверка | Фактический результат | Граница доказательства |
|---|---|---|
| Полный suite исправленной редакции | **exit0, 170 passed, 0 skips, 20.24 s** | Настоящие API/CLI/Qt/filesystem/installed пути; не независимый verdict |
| Ruff всего нового/изменённого Python scope | **exit0, All checks passed** | Нет ослабления lint rules ради findings |
| Strict mypy package + facade | **exit0, no issues in 11 files** | Не runtime/codec доказательство |
| Project-local docs checker | **exit0, checked=19, findings=[]** | Только explicit Markdown corpus; не product/independent PASS |
| `git diff --check` | **exit0** | Только штатные LF→CRLF предупреждения, global settings не менялись |
| Постоянный policy selection RED→GREEN | **1: 13 failed/9 passed → 0: 22 passed** | Тот же public API/условия/controls |
| Source CLI policy regressions | **0** для opaque/translucent/RGB8, **4** для PNG16 | Один UTF-8 JSON, safe stderr; error/code/artifact/bytes/readback сверены |
| Installed API/console policy paths | Оpaque **succeeded**; PNG16 **failed**, console **exit4** | Настоящий новый wheel, no-Qt venv, вне source cwd/PYTHONPATH |

## Сохранённые общие гарантии

Полный suite повторил, а не просто перенёс прежние PASS:

- Import hook запрещает Qt/gui/argparse/CLI/input/print для прямого API/facade; настоящие файлы/readback создаются, import-time probes отсутствуют.
- Stable root/relative order, recursive False/True, relative/absolute/physical hardlink dedup, output-child exclusion и frozen manifest. Missing/read failures/reparse branches и реальные symlink cases прошли без skip.
- Single/batch/partial, параметры/defaults/quality 0/100, 4000×3000→1440×1080, no upscale/1-px, orientation/metadata и объявленные raster modes.
- Source/foreign bytes, все target collision группы, late foreign destination и два настоящих процесса с настоящим no-replace `os.link`: ровно одна публикация. Source/parent stale, partial staging setup, save/verify/link/readback/cleanup faults. Published-unverified остаётся artifact/partial, не откатывается и не теряется в counts.
- Cooperative cancellation до/во время discovery, до/после link и поздний последний checkpoint, закрытие handles, следующий fresh token/worker. CLI signal harness проходит handler→token→реальную конвертацию; это не native console delivery.
- Реальный legacy class и QCoreApplication/QThread, signals/counts/явный delete refusal; production handlers с заменёнными только views/messagebox/delay: stop не wait/terminate, start/close ждут finished. Не visual E2E.
- Настоящий FileHandler/formatter/flush/read bytes содержит полезные события/reasons/counts без synthetic private path/postfix/raw-exception sentinels. CLI stderr и worker buffer отдельно; observer/formatter failures не повторяют конвертацию.

Подмены только на fault/capability/observer/view/synchronization границах. Ни API, ни service/codec/FS не заменены готовым succeeded/failed DTO. Дополнительные transparency fault tests меняют лишь encoder edge и проверяют реальный staging verifier.

# Независимая приёмка исправленной редакции

**Verdict: ACCEPT, R1/R2 CLOSED; обязательных source/test findings не осталось.** Решение вынесено отдельно от Coder в той же Reviewer-беседе после возвращённого ремонта, без self-fix исходников и без нового review-контура. Прежние failures и NEEDS_CHANGES сохраняются выше, а не переименовываются в PASS.

Reviewer независимо сверил 129/129 inventory sizes/hashes и полный modified/untracked path set; index был пуст. Delta к прежней редакции: 2 новых / 9 изменённых / 118 byte-identical; единственная application source delta — imaging.py. После всех executions повторная сверка не выявила drift. Source/tests/product manifests и PFK оставались read-only.

| Собственная Reviewer execution | Факт | Граница |
|---|---|---|
| Весь `tests/` с pytest-timeout и отключённым third-party autoload | **exit0, 170 passed, 0 skips, 19.38 s** | Включая реальные Qt/CLI/filesystem/новый installed wheel, без deselection |
| Ruff того же нового/изменённого Python scope | **exit0** | All checks passed |
| Strict mypy package + facade | **exit0**, 11 source files | Не runtime/codec доказательство |
| Docs checker explicit corpus + diff-check | **exit0**, 19 документов, findings=[] / **exit0** | Структура/whitespace, не runtime PASS |
| Исходные reviewer fixtures, не новый авторский generator | **36** source API input/format pairs и по **9** source CLI, installed CLI, installed API cases | Кодек/API/FS настоящие; targets свежие; не складываются с suite как уникальный test count |

Read-only копии прежних discriminator/control PNG использованы в новом root. Opaque RGBA/LA/unused color-key/palette alpha теперь дают succeeded/verified на JPEG/WebP/HEIF/AVIF; matched alpha=73 сохраняется для non-JPEG. RGB/RGBA PNG16 теперь IMAGE_MODE_UNSUPPORTED на decode, artifact=null/published=0/no final (CLI exit4); RGB8 control succeeds, grayscale I;16 control по-прежнему refused. Проверены final open/load/size/alpha, artifact digest/bytes, cleanup и source bytes. Permanent negative verifier regressions реально выполнены: потеря/ложное появление прозрачности не стали допустимыми.

Reviewer заново собрал и установил wheel **43164 bytes**, SHA-256 **6d6b18341a52bb3c7196770bdeb97ad8571b1093ad9b28cf6b7c0121bc04e730**. Все 19 source/typed module bytes wheel совпали с frozen working tree. Из outside cwd без source PYTHONPATH API/classes загружены из site-packages; PyQt6/pillow_heif/pillow_avif физически отсутствуют. Installed direct API дополнительно запрещал Qt/gui/argparse/CLI/input/print, но создавал реальные файлы. Это собственное execution Reviewer, не авторский wheel, не релиз и не обещание byte-reproducible zip.

Полный первый source review и прежние достаточные проверки неизменённых owners переиспользованы по применимости; новый полный suite дополнительно повторил общие preservation/collision/cancel/legacy/QThread/privacy guarantees. Native Windows console delivery, visual GUI, EXE/другие платформы не требовались как новые ворота.

## Документационный closeout после ACCEPT

По отдельной пользовательской власти тот же Reviewer завершает затронутые public docs/instructions/свой профиль, затем selective commit и branch-only push существующего origin с exact commit/ref readback. На этой стадии source/tests/product manifests и PFK не редактируются; перед Git они сверяются с принятым inventory. Новый исходный дефект потребовал бы возврата тому же Coder, не ремонта Reviewer-ом.

Проверка новой документации/финальной упаковки — **author verification closeout**, не ещё одно независимое принятие. Исходные 170 passed переиспользуются только для byte-identical source/tests. После изменения README отдельно выполнен `python -B -m pytest -p pytest_timeout -p no:cacheprovider tests/test_packaging.py -q -ra` в свежем isolated root: **exit0, 2 passed, 6.78 s**. Новый wheel **43421 bytes**, SHA-256 **f322ebf7f4177d4493fd61d8da0ac4ddc78aa494205705c9b8aab83899854764**, содержит final README в METADATA и те же 19 source/typed modules; installed no-Qt API/CLI/readback/policy cases прошли. Отдельная проверка payload bytes — exit0: установлена точная LF→CRLF MIME-сериализация README, без иных различий; первый отказ собственного helper-а из-за сравнения этих разных EOL-представлений сохранён и классифицирован как fixture error, не дефект приложения. Project-local docs checker: **exit0, checked=19, findings=[]**. Точные Git/remote receipts принадлежат локальному handoff; этот документ не пытается встроить SHA собственного будущего commit или выдать delivery за release.

# Среда, codecs и установленный wheel

| Компонент | Фактическая версия |
|---|---|
| ОС / FS / Python | Windows 11 `10.0.26200`, local NTFS, Python **3.14.2** AMD64 |
| Pillow / pillow-heif / pillow-avif-plugin | **12.1.0 / 1.2.0 / 1.5.5** |
| PyQt6 / Qt | **6.10.2 / 6.10.2** |
| pytest / pytest-timeout | **9.1.1 / 2.4.0** |
| Ruff / mypy | **0.17.2 / 2.4.0** |
| pip / setuptools / wheel / build | **26.2.2 / 80.10.2 / 0.48.0 / 1.6.1** |
| Docs tooling | Отдельное project-local environment, PyYAML **6.0.3**, read-only использование |

JPEG/WebP/HEIF/AVIF реальные probes и file roundtrips прошли в основной среде, включая opaque и фактически прозрачные cases по применимости. AVIF provider — встроенный Pillow, optional plugin не переопределял его. PNG — только decoder/input. Доступные optional codecs не пропущены.

Новый `image_compressor-1.0.0-py3-none-any.whl`: **43164 bytes**, SHA-256 **80ce84156ac434ec51b7eac326c74d2b3ee014c3d0f63a9c3791b61d319dd488**. Это локальный build artifact, не release и не обещание byte-reproducible zip сборки.

Packaging fixture теперь создаёт **все** wheels/venv/log/temp/cache только внутри собственного disposable root. Прежний Pillow wheelhouse — read-only dependency cache, прежний product wheel не перезаписывается. Настоящие pip/setuptools собирают явную копию build inputs, не старый root build/dist; offline install ставит новый wheel и Pillow в fresh venv без PyQt6/pillow_heif/pillow_avif. Проверены site-packages imports, entrypoint, состав wheel и единственный bare runtime Requires-Dist — Pillow.

В installed outside cwd без source PYTHONPATH реальные API/console создают readable opaque WebP 24×18 и resized 12×9, translucent alpha=73 сохраняется. 8-bit RGB/RGBA controls создают readable 12×10 WebP; соответствующие 16-bit получают `IMAGE_MODE_UNSUPPORTED`, artifact=null, published=0, final отсутствует. Source bytes и staging cleanup проверены. Старый installed facade создаёт JPEG, healthy console resize 80×60→40×30 сохранён. Build/venv/offline install/healthy child processes — raw exit0; отказавшие PNG16 console children — raw exit4, не orchestrator error.

# Дельта и пределы

Ремонт относительно предыдущего кандидата: `image_compressor/imaging.py`; новые `tests/image_fixtures.py` и `tests/test_imaging_policy.py`; regressions/isolation в `tests/test_cli.py`, `tests/test_packaging.py`; актуализация README/UV_GUIDE/этого verification/Application API/testing instruction и краткой записи LOG. DTO/CLI schema/defaults, filesystem publication guards и GUI не перепроектированы. Foundation/pack/agent profiles не изменялись этим ремонтом.

**NOT RUN / вне границы:** native Windows Ctrl-C/CTRL_BREAK console delivery; GUI visual/layout, EXE/frozen/release; Python 3.10 runtime и другие ОС/FS; external viewers/все HEIF/HDR variants; crash/power-loss durability. Прежний Python 3.10 AST check не называется runtime PASS. Trusted local namespace/cooperative cancel/stat guards — не sandbox или zero-effects barrier, RAM/CPU/codec latency не ограничены.

Privacy-гарантия по-прежнему только для новых API/CLI/facade и изменённых worker/main-window emitters; неизменённые widgets resize debug и gui_main import-error raw ветка не объявляются защищёнными. MCP/daemon/новый GUI не добавлены. После авторского freeze тот же независимый Reviewer проверил ремонт и вынес ACCEPT; авторские и независимые executions выше разделены. Docs closeout/feature-branch publication не расширяют технических гарантий.
