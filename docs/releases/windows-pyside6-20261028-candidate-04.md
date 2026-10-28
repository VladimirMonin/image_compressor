---
id: ic-release-windows-pyside6-candidate-04
title: "Курированная сборка: PySide6 GUI v2 · Windows x64 · 20261028-candidate-04"
kind: snapshot
status: superseded
created: "2026-10-28"
updated: "2026-10-28"
areas: [gui, packaging, release, windows, data-safety]
summary: "Superseded по F1 (лишний вложенный TechnicalToggle); сохранённая история: opt-in deletion после verified output, точные байты и доказанные deletion/hash факты."
snapshot_of: "dist/windows-pyside6/20261028-candidate-04/BUILD-INFO.json"
code_ref: "43554f80fb3a0650a8a3ba9dc6afcfa46464d810"
verification_scope: "Авторские проверки: core 223 passed, PySide offscreen 89 passed, tests_windows_exe 22 passed на новом EXE (включая deletion True/False/partial), ruff/mypy raw0, собственный native GUI click+deletion+journal. Независимый exact-byte ACCEPT ещё не выдан."
---

# Итог

> **Superseded in favour of `docs/releases/windows-pyside6-20261028-candidate-05.md`.** Reviewer выдал NEEDS_CHANGES по единственному F1: вложенный блок «Технические детали» дублировал существующую вкладку «Подробности». Этот бинарник не доставлялся, launcher/`.lnk` не менялись. Deletion/hash/provenance факты ниже сохранены как исторические и не переписаны; исправленный target UI — summary-only «Журнал операции» + все technical details в «Подробностях». Артефакт перемещён в Recycle Bin 2026-10-28 после ACCEPT `candidate-05` (pre-delete manifest — в reviewer evidence); сам `candidate-04` так и не был принят.

`20261028-candidate-04` — курированная сборка из **HEAD `43554f8`** + незакоммиченная bounded delta (deletion consent UX, двухуровневый журнал, packaging gates). В отличие от принятого `candidate-03` (pre-deletion база), EXE содержит `image_compressor._windows_deletion`: галочка удаления **рабочая и кликабельная**, default OFF; включение = согласие без modal; исходник удаляется безвозвратно только после verified final output на supported Windows local fixed NTFS. Статус — `proposed`: авторские gates пройдены, независимый exact-byte ACCEPT отдельно. `candidate-03` и Desktop `.lnk` не меняются и остаются fallback до ACCEPT.

# Artifact

| Поле | Значение |
|---|---|
| Путь | `dist/windows-pyside6/20261028-candidate-04/ImageCompressorV2.exe` |
| Размер | **57 011 209 bytes** |
| SHA-256 | **`f69c8832cb9acd967cdffbed1c75e36036e2ce1ba2b90a9183ec07dbfc4216e7`** |
| `BUILD-INFO.json` | 15 702 bytes, SHA-256 `de63d80786e5d9e6bfab0961502290b9c1d479ff00a07993659bee116aabea6e` |
| `source_head` | `43554f80fb3a0650a8a3ba9dc6afcfa46464d810` |
| Inputs | 42; 13 `assets/*.svg` + `tokens.json`; **обязательный** `image_compressor/_windows_deletion.py`; нет `gui/`, `classes.py`, `gui_main.py` |
| Форма | onefile, PE32+ AMD64, GUI subsystem; unsigned local artifact |

# Curated source и overlay

Staging: detached worktree HEAD `43554f8` в `.agent-work/windows-exe/staging/20261028-candidate-04/root`; junction `dist/windows-pyside6` и `.agent-work`; существующий `.agent-work/windows-exe/build-venv`. `BUILD-INFO.executable`/`build_work` записаны в staging-виде — canonical пути через junction указывают на тот же файл. Receipt: `.agent-work/windows-exe/builds/20261028-candidate-04/curated-source.json`.

| Overlay | SHA-256 |
|---|---|
| `gui_pyside6_v2/theme.py` | `ff406e269222e72997c622c3df877bc537e7f15056535a666e5f1b99a9475c7a` |
| `gui_pyside6_v2/widgets.py` | `46d93f8131972bc47a0d0076466fdd916b7b56c721e64abddd9d74fc797f7d8f` |
| `gui_pyside6_v2/controller.py` | `d6ddf987ed6bc4f469df26e425cdc6cc29679b08334d5b39f1162db7697a8bf8` |
| `gui_pyside6_v2/window.py` | `5386516d0b7d2a3225bdc9e48278e76a66e2fb21efcc3e9b0ca386ebef0123ef` |
| `gui_pyside6_v2/localization.py` | `65494c61a6cfb72d1b3e2b5dbf43097b3030dcdee12de516377019bab4022455` |
| `README.md` | `94c607e8fb1623d5aa2d219830b49d422429bf51cab4f9bf299dc59c0a87cf3c` |
| `tools/windows_exe/ImageCompressorV2.spec` | `4ea6f4b0173dffa83a6d2ea3582433be90b4ed13aa54774a75060c778ee0f33c` |
| `tools/windows_exe/build.py` | `78cc9eb622c3f0c7b64a644a6572f7b987b209ecfb0e9285afbfdbcce4bfb867` |
| `tools/windows_exe/ic_frozen_check.py` | `ab4ce06d011065743376d3cf8dcc1468eb67379d99cfff4deccdd7eadddb7188` |

`image_compressor/**` (включая `_windows_deletion.py`), `pyproject.toml`, `frozen_entry.py`, `requirements-win64.txt`, 13 SVG/tokens берутся из HEAD. README заморожен до сборки.

# Что теперь работает

- **Deletion (opt-in):** видимая галочка `DeleteOriginals` встроена в текст (клик по индикатору/подписи и Space переключают), default OFF, busy-gating. Включение = согласие; per-start modal удалён. После verified final output + flush + повторной source-проверки исходник удаляется безвозвратно (no Recycle Bin/undo); failure/cancel/unknown сохраняют источник и дают retained/unknown, unsupported — явная ошибка до эффектов. `counts.deleted` — только подтверждённые удаления.
- **Журнал:** в существующем нижнем блоке человеческая summary из typed `ItemResult`/verified artifact (имя/формат, было→стало, меньше/больше/unknown, статус, deleted/retained/unknown) + раскрываемые (`▸ Технические детали`, Space/Enter) raw `event=` с selection/Ctrl+C. Локальные пути/SHA/errors — в «Подробностях»; 500 blocks/50 items — честные границы. RU/EN/KK, Light/Dark, 900×640/1120×760.
- **Packaging:** spec кладёт все `assets/*.svg` + `tokens.json`; `verify_archive()` требует 13 SVG, `python314.dll` и модуль `image_compressor._windows_deletion` в PYZ, отвергает точные legacy-имена. Frozen driver проверяет enabled/default-OFF checkbox, модуль, `forbidden_modules_absent` (только legacy) и реальные маршруты deletion-true/false/partial на synthetic files.
- **Native frame:** принятое поведение Dark↔Light сохранено (theme helper не менялся по существу).

# Авторские gates (raw)

| # | Проверка | Результат |
|---|---|---|
| core | `.venv` pytest `tests` (включая source/Windows deletion и packaging) | **223 passed**, raw exit 0, 26.45 s |
| PySide | `QT_QPA_PLATFORM=offscreen` full `tests_pyside6_v2` | **89 passed**, raw exit 0, 9.88 s |
| frozen | `tests_windows_exe` против candidate-04 (`IC_FROZEN_EXE`) | **22 passed**, raw exit 0, 15.41 s |
| ruff | `.venv` `image_compressor tests`; PySide `gui_pyside6_v2 tests_pyside6_v2 tools/windows_exe tests_windows_exe --extension spec:python` | 0 / 0 |
| mypy | core; GUI `--follow-imports=silent`; strict 3 helper с build-venv | 0 / 0 / 0 |
| frozen receipt | `--packaging-check` на том же SHA | `status=succeeded`, `platform=windows`, `resources=14`, `deletion_module_loaded=true`, `deletion_available=true`, `forbidden_modules_absent=true`, 9 starts, cases `deletion-true` (deleted=1/source absent), `deletion-false` (retained/bytes unchanged), `deletion-partial` (good deleted, bad unchanged), 6 screens RU/EN/KK × Light/Dark |
| build | curated worktree + build-venv, `--build-id 20261028-candidate-04` | raw exit 0 |

Первые два build-attempt'а этого среза сохранены как evidence в `.agent-work/deletion-journal/coder-01/failed-candidate-04-build-{1,2}/`: build-1 (`6cc4fc6d…`) отвергнут собственным frozen driver (неверный assert в deletion-true helper), build-2 (`4cf9608c…`) — из-за пользовательской детали summary (`OutputFormat.WEBP` вместо `WEBP`), найденной native visual probe. Product delta исправлена, все affected gates повторены; оба attempt'а не приняты и не перезаписаны.

# Native visual/functional факт

Собственный real-Windows QPA прогон (`.agent-work/deletion-journal/coder-01/native-3/`, PrintWindow только своего HWND): system Light, DPR 1.5. Реальный mouse-клик по галочке включил её; реальный Start через queue→worker→API создал verified `synthetic-delete.webp` (640×480 → 320×240, 220 bytes), удалил synthetic source (`deleted=1`, source absent), closed штатно; техническая зона раскрыта Space/Enter, selection работает. Кадры `01-dark-ru-1120`, `02-light-ru-1120`, `03-dark-en-900`, `04-dark-kk-900`, `05-dark-ru-again` просмотрены: summary/технический слой читаемы, `PNG→WEBP` без enum-репра, статус не только цветом, галочка и irreversible label на месте в обеих темах и всех локалях; native title bar следует теме в обе стороны.

# NOT RUN

- Независимый exact-byte ACCEPT, обновление Desktop `.lnk`/launcher, `status: accepted`, Recycle Bin cleanup, commit/push — Reviewer после ACCEPT.
- Автоматический deletion в **frozen EXE** для failure/cancel (frozen driver покрывает true/false/partial; failure/cancel проверены source tests), смена системной темы при открытом окне, другие ОС/DPI, signing/release, clean machine, reproducibility, screen reader/RTL, физические OS-dialog/drop.
- Личные/проектные файлы для deletion не использовались: только собственный synthetic disposable root.

# Будущее

После ACCEPT новые байты не пересобираются; `.lnk`/launcher переведены на принятый `candidate-05`, а `candidate-04` остаётся `superseded`/unaccepted и убран в Recycle Bin.
