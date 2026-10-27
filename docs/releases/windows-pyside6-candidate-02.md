---
id: ic-release-windows-pyside6-candidate-02
title: "Канонический локальный релиз: PySide6 GUI v2 · Windows x64 · 20261023-candidate-02"
kind: snapshot
status: superseded
created: "2026-10-28"
updated: "2026-10-28"
areas: [gui, packaging, release, windows]
summary: "Единственная каноническая линия GUI/EXE, точные байты и происхождение выбранного локального релиза, состояние веток и границы."
snapshot_of: "dist/windows-pyside6/20261023-candidate-02/BUILD-INFO.json"
code_ref: "83c209972b731805a8b3dd97e5aba7cae48dd8ad"
verification_scope: "Ссылка на уже принятый exact-byte EXE ACCEPT и исторические source ACCEPT; новая квалификация платформ/подписи/release не заявляется."
---

> **Superseded:** заменён курированной сборкой [20261028-candidate-03](windows-pyside6-20261028-candidate-03.md); точные байты, вердикты и хеши ниже сохранены, артефакт `candidate-02` перемещён в Recycle Bin 2026-10-28 после независимого ACCEPT нового EXE.

# Назначение

Этот документ фиксирует **единственную каноническую линию** GUI и Windows-бинарника проекта, точные байты выбранного владельцем локального релиза и честную границу между принятым состоянием и текущим HEAD. Он не выдаёт новую техническую/визуальную приёмку, не объявляет публичный release/signing/installer, не переписывает исторические вердикты и не расширяет ни один принятый срез.

Основание — уже принятые документы: [FigCraft/PySide6 отчёт](../figcraft_gui_experiment/REPORT.md), [exact-byte EXE verification](../figcraft_gui_experiment/05-windows-exe-verification.md), [control-fix verification](../figcraft_gui_experiment/06-controls-verification.md), [EXE guide](../figcraft_gui_experiment/WINDOWS_EXE.md), [прикладной контракт v1](../architecture/application-api.md). Статус документа — `superseded`: он был независимо принят в docs/launcher-границе (2026-10-28) и затем заменён курированной сборкой `20261028-candidate-03`; вердикты и хеши ниже сохранены, runtime-границы — в §7.

# 1. Каноническая линия

- **GUI продукта — `gui_pyside6_v2/` (PySide6 Widgets v2).** Принятая source-граница для GUI — `68b7dc5` (включает принятый control-fix). Текущий HEAD не объявляется каноном GUI: он несёт непринятый WIP удаления исходников (§6).
- **Единственный принятый локальный бинарник — `dist/windows-pyside6/20261023-candidate-02/ImageCompressorV2.exe`**, 56 977 108 bytes, SHA-256 `09c4b2f1fc65655d624111537d693f0971fad75787f6c3045072d5863312bb53`. Собран из `83c2099`; неподписанный, не публичный release, без installer; control-fix `68b7dc5` в него **не входит**. Не пересобирать и не подменять.
- **Старая PyQt6-оболочка `gui/` + `gui_main.py` — сохранённое legacy.** Не удаляется, не правится, не рекомендуется; её bat-файлы остаются историческим маршрутом.
- **Ветка канонической разработки — `refactor/command-first`.** Только она содержит все принятые срезы и уже равна записанному `origin/refactor/command-first`. `develop`/`docs/project-foundation` — база подготовки (предки), `main` — старая расходящаяся линия; все ref'ы сохраняются как есть.
- **Вариации артефактов:** `candidate-02` — единственный принятый бинарник; `candidate-01` — superseded (не использовать); `dist/ImageCompressorGUI.exe` + `build/` — legacy; `design/exports/*` — design-evidence. Никакая чистка не выполняется.
- **Deletion-срез вне канона:** [план](../plans/gui-feedback-source-deletion.md) остаётся `proposed`, реализация в HEAD не принята и не является рабочей функцией продукта.

# 2. Артефакты и точные байты

Пересчитано по raw bytes в этом срезе (`sha256sum`, `stat`).

| Путь от корня | Bytes | SHA-256 | Статус |
|---|---|---|---|
| `dist/windows-pyside6/20261023-candidate-02/ImageCompressorV2.exe` | 56 977 108 | `09c4b2f1fc65655d624111537d693f0971fad75787f6c3045072d5863312bb53` | **канонический локальный релиз**; независимый технический и визуальный ACCEPT |
| `dist/windows-pyside6/20261023-candidate-02/BUILD-INFO.json` | 13 797 | `2c5bbc00495ea619b40d3e6a3ca5d4a38c42145824d3242666541a4edd6a54d3` | build-record: pins, 29 входных хешей, argv, payload-hashes |
| `dist/windows-pyside6/20261023-candidate-02/README.txt` | 378 | `524a264ac07f535e3e7e6522f32066f518beab47fba4e0a9d624e58ff934a2f9` | пользовательская памятка + `notices/` (10 файлов лицензий) |
| `dist/windows-pyside6/20261023-candidate-01/ImageCompressorV2.exe` | 65 280 009 | `3cf32db20120673ba53f83c134a8b4405b93098794863cbc35baa7861126cd1e` | **superseded**: первый build, отвергнут собственным archive guard (QML/Quick); сохранить, не использовать |
| `dist/ImageCompressorGUI.exe` | 59 206 939 | `309464d8868bc9cacba6171a665d396fc1eb4842bf1f8901af17570311cbbe0d` | **legacy** PyQt6 onefile из `build_exe.bat`; не обновлялся и не квалифицирован |
| `.agent-work/windows-exe/reviewer-01/candidate-source-frozen.tar.gz` | 113 422 | `40bfb73ed92035418e0a1804fbe5caba4eae27f5751f51b224362c560e144a19` | замороженный source-snapshot принятого кандидата (untracked/ignored) |

`dist/`, `build/` и `.agent-work/` — gitignored: перечисленные байты существуют только на этой машине. Один `git clean -xdf`, сбой диска или «уборка» уничтожит единственную принятую сборку; внешняя архивная копия — решение владельца, не этого среза. Хеши таблицы относятся к build-id `20261023-candidate-02`; одноимённый каталог `design/exports/20261023-candidate-02/` — другой артефакт (PNG design run), совпадение метки.

# 3. Происхождение `candidate-02`: что доказано, а что нет

| Утверждение | Факт |
|---|---|
| База сборки | `83c2099` (`83c209972b731805a8b3dd97e5aba7cae48dd8ad`), записана в `BUILD-INFO.source_head` |
| Рабочее дерево при сборке | грязное только по docs/untracked packaging: `M AGENTS.md, README.md, docs/README.md, RUNNING.md, instructions/development.md, instructions/testing.md`; `?? 04-windows-exe-plan.md, WINDOWS_EXE.md, tests_windows_exe/, tools/windows_exe/` (`BUILD-INFO.source_delta`) |
| Runtime-входы | 29 input-hashes: **21** файл байт-в-байт равен LF-блобам `83c2099`; `gui_pyside6_v2/tokens.json` и `pyproject.toml` — его CRLF-представлению; **5** входов `tools/windows_exe/*` — блобам `bf9f89d` (packaging-дельта, в `83c2099` их нет); `README.md` — provenance-only и не равен ни одной коммитнутой редакции |
| Что исполняется | payload определяется 29 входами (`image_compressor/*`, `gui_pyside6_v2/*`, `tools/windows_exe/*`); `README.md` в payload не входит |
| Toolchain | CPython 3.14.2 x64; PyInstaller 6.18.0 + hooks 2026.0; PySide6 6.12.0; Pillow 13.0.0; pillow-heif 1.8.1; pillow-avif-plugin 1.6.0; 16 exact pins + SHA каждого wheel; venv `.agent-work/windows-exe/build-venv` |
| PE-форма | PE32+ (`0x20b`), AMD64 (`0x8664`), subsystem 2 (GUI); `TimeDateStamp` 1792779475 = 2026-10-23T18:17:55Z, совпадает с mtime файла |
| Exact-byte приёмка | ACCEPT выдан именно этим байтам: до producer'ов и после всех проверок сверены 176 protected файлов, 17 публичных путей, manifest `ededba56…`, index пуст |
| Состав архива | 180 CArchive entries / 261 PYZ modules / 58 native images; 18 actual code objects равны compile проверенных source bytes; 16 wheel-hashes; unresolved PE imports 0 |
| Bit-for-bit reproducibility | **не заявлена**: recipe воспроизводим, идентичность двух пересборок не обещана |

`BUILD-INFO.json.status = built_not_independently_accepted` — статус **момента сборки**; он перекрыт последующим независимым ACCEPT тех же байтов, а не опровергает его. Ничего в EXE не пересобиралось после приёмки.

**Чего в EXE нет:** принятого control-fix `68b7dc5` (§4), WIP удаления исходников `718c578` (в `BUILD-INFO.inputs` нет `image_compressor/_windows_deletion.py`), нового человеческого журнала/итогового вывода. Отсутствие этих возможностей — не дефект принятой сборки, а её точная граница.

# 4. Известная дельта EXE относительно принятой source-границы

Runtime-часть `68b7dc5` — только `gui_pyside6_v2/theme.py` и 12 control SVG (коммит также содержит 5 docs и 2 новых test/артефакта вне runtime): `control-check-{light,dark}`, `control-check-disabled-{light,dark}`, `control-down-{light,dark}`, `control-down-disabled-{light,dark}`, `control-up-{light,dark}`, `control-up-disabled-{light,dark}`. Это **косметическая** дельта отображения стрелок/флажков, не функциональная:

- EXE `candidate-02` рисует прежний вид контролов; RU/EN/KK, компоновка, resize gates, quality-slider, конвертация и безопасность совпадают с принятым поведением.
- Пересобрать бинарник ради этой дельты в этом срезе нельзя. Новый интегрированный EXE — отдельная задача: новый build-id, собственный build/qualification и **новый независимый exact-byte ACCEPT**; прежний вердикт на новые байты не переносится.
- Последующий source-fix native title bar (ручная смена темы) **в `candidate-02` отсутствует**: source-исправление не меняет байты EXE, и пользователь через `run_image_compressor_v2.bat` продолжит видеть прежнюю рамку до нового build-id и нового независимого exact-byte ACCEPT ([native frame verification](../figcraft_gui_experiment/07-native-frame-verification.md)).

# 5. Ref'ы и правило сохранения чужой работы

Записанное состояние Git на момент выпуска этого документа (remote-tracking ref'ы прочитаны без сетевого `fetch`):

| Ref | SHA | Замечание |
|---|---|---|
| `HEAD` / `refs/heads/refactor/command-first` | `a91e7cee1d5677f5da32cf0e18b4d9297f7633f7` | каноническая линия; upstream у локальной ветки не настроен |
| `refs/remotes/origin/refactor/command-first` | `a91e7cee1d5677f5da32cf0e18b4d9297f7633f7` | совпадает с локальным (записанное состояние) |
| `refs/heads/develop` | `770784935c52eaa3add6a9a1ec50b5154c9f1e3c` | предок канона; локально на 1 commit впереди `origin/develop` |
| `refs/remotes/origin/develop` | `c7fb234b1be0f9abd656c1212c917db279985f79` | база подготовки |
| `refs/heads/docs/project-foundation` | `770784935c52eaa3add6a9a1ec50b5154c9f1e3c` | тот же коммит, что `develop`; отдельного docs-коммита не было |
| `refs/heads/main` | `681c4f75a8d3fd5b49ef253e4257d5f22368eede` | `= origin/main = origin/HEAD`; независимая старая squashed-линия, **не предок** канона |
| Теги | — | тегов нет |
| Worktrees | 1 | `C:/PY/image_compressor a91e7ce [refactor/command-first]` |
| Stash | — | пуст |
| Remote | — | один `origin` → `https://github.com/VladimirMonin/image_compressor.git` |

История канонической линии: `7707849` (база) → `58afb9b` (command-first API/CLI, ACCEPT) → `83c2099` (FigCraft-дизайн + PySide6 GUI v2, ACCEPT; **база EXE**) → `bf9f89d` (standalone Windows packaging, ACCEPT) → `68b7dc5` (control appearance fix, ACCEPT source-only) → `718c578` (deletion WIP, **не принято**) → `a91e7ce` (docs к proposed-плану).

Правило: **не мержить, не переименовывать, не удалять и не пушить чужие ref'ы**. `main`, `develop`, `docs/project-foundation` сохраняются как есть; ничего не теряется, потому что `develop`/`docs/project-foundation` — предки канона, а `main` остаётся отдельной исторической линией. Любое изменение ref'ов/истории — только по отдельному прямому поручению владельца и по правилам [разработки](../instructions/development.md).

# 6. Статус deletion-среза (WIP в HEAD)

- `718c578` (`wip: preserve guarded source deletion implementation`) реализует opt-in удаление исходников: новый `image_compressor/_windows_deletion.py`, правки `service/models/cli/diagnostics/filesystem/imaging`, wiring в обоих GUI и новые deletion-тесты. У коммита **нет verification-документа, нет независимого ACCEPT**, и он не описан в LOG как принятая возможность.
- `a91e7ce` добавляет docs к [плану](../plans/gui-feedback-source-deletion.md) со `status: proposed`; план остаётся предложением, а не разрешением считать функцию готовой.
- Поэтому в текущем HEAD checkbox удаления включён (`gui_pyside6_v2/widgets.py`, `setEnabled(True)`) и service отказывает только при недоступности deletion-владельца; source-запуск GUI идёт по этой **непринятой** ветке кода.
- Действующим продуктовым контрактом остаётся [Application API v1](../architecture/application-api.md): `delete_original=True` отвергается до эффектов (`DESTRUCTIVE_MODE_UNSUPPORTED`). Это утверждение верно для **принятой границы `68b7dc5` и EXE `candidate-02`**, но не для source HEAD.
- Судьба среза (завершить, принять или откатить) — отдельное поручение. В этом docs/launcher-срезе код, тесты и оба GUI не меняются, WIP не «дочиняется» и не откатывается.

# 7. Что в этой границе не проверялось (NOT RUN)

Ни этот документ, ни launcher не добавляют новых технических гарантий. За пределами проверенного остаются:

- чистая виртуальная машина и другой пользовательский аккаунт;
- Windows 10, Windows ARM, Linux/macOS и другие Python/FS-комбинации;
- все DPI/multi-monitor и нестандартные темы ОС;
- физические системные диалоги выбора файлов/папок и реальный OS drag & drop;
- screen reader/accessibility-сертификация;
- signing, SmartScreen-репутация, installer, публикация бинарника;
- crash durability, восстановление после аварийного завершения и отсутствие `_MEI` после forced kill;
- bit-for-bit воспроизводимость сборки;
- сетевые сценарии: продуктовых сетевых вызовов нет, и они не проверялись.

# 8. Как проверить байты

Git Bash из корня проекта:

```bash
sha256sum dist/windows-pyside6/20261023-candidate-02/ImageCompressorV2.exe
# 09c4b2f1fc65655d624111537d693f0971fad75787f6c3045072d5863312bb53
stat -c '%s' dist/windows-pyside6/20261023-candidate-02/ImageCompressorV2.exe
# 56977108
git status --short --branch
# ## refactor/command-first  (артефакты gitignored и в diff не появляются)
```

Совпадение обоих значений (bytes и SHA-256) — единственное доказательство «тот же бинарник». Запуск без Python: `run_image_compressor_v2.bat` открывает именно этот путь; при отсутствии файла launcher завершается с exit 1 и ничего не устанавливает, не собирает и не скачивает.

# 9. Сохранённые исторические границы

Не переписаны и остаются в силе: [Oracle-план EXE](../figcraft_gui_experiment/04-windows-exe-plan.md), [exact-byte verification](../figcraft_gui_experiment/05-windows-exe-verification.md), [control-fix verification](../figcraft_gui_experiment/06-controls-verification.md), [FigCraft/PySide6 отчёт](../figcraft_gui_experiment/REPORT.md), [прикладной контракт](../architecture/application-api.md), [план](../plans/command-first-refactoring.md) и [verification](../verification/command-first-refactoring.md) command-first. Их выводы и таблицы хешей — исходные; этот документ только ссылается на них.
