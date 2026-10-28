---
id: ic-release-windows-pyside6-candidate-05
title: "Курированная сборка: PySide6 GUI v2 · Windows x64 · 20261028-candidate-05"
kind: snapshot
status: accepted
created: "2026-10-28"
updated: "2026-10-28"
areas: [gui, packaging, release, windows, data-safety]
summary: "Candidate-04 + F1 UX correction: «Журнал операции» — только human summary; все technical details (raw events, paths, SHA, errors) — в существующей вкладке «Подробности». Opt-in deletion и точные байты сохранены."
snapshot_of: "dist/windows-pyside6/20261028-candidate-05/BUILD-INFO.json"
code_ref: "43554f80fb3a0650a8a3ba9dc6afcfa46464d810"
verification_scope: "Авторские affected-проверки после узкой F1-коррекции: focused GUI 62 passed, full PySide 89 passed, tests_windows_exe 22 passed на новом EXE, ruff/mypy GUI raw0, native click/Space + summary-only/Details + deletion. Независимый exact-byte ACCEPT выдан этим же Reviewer'ом 2026-10-28 на этих байтах: affected GUI tests 62 passed, tests_windows_exe 22 passed на этом EXE, archive/provenance 42/42, реальный клик/Space, summary-only «Журнал операции» + technical details в «Подробностях», deletion true/false/partial с собственным disk readback."
---

# Итог

`20261028-candidate-05` — та же принятая deletion/journal delta, что candidate-04, плюс **единственная F1-коррекция**: удалён вложенный `▸/▾ Технические детали`; вкладка «Журнал операции» теперь содержит только человеческую summary, а вся техническая информация (raw `event=`, локальные пути, params, elapsed, SHA-256, errors, dispositions) живёт в существующей вкладке «Подробности» (read-only, selection/Ctrl+C). STATUS `proposed`; candidate-04 `superseded` (NEEDS_CHANGES F1, не доставлялся), candidate-03 остаётся accepted fallback. Launcher и Desktop `.lnk` не менялись.

# Artifact

| Поле | Значение |
|---|---|
| Путь | `dist/windows-pyside6/20261028-candidate-05/ImageCompressorV2.exe` |
| Размер | **57 010 633 bytes** |
| SHA-256 | **`ea1cb00fe4ca1e0d339dc9c1023d3970e9b9b3bfa0060ae8741deb0570b8476a`** |
| `BUILD-INFO.json` | 15 702 bytes, SHA-256 `a945d10246760e56e2f7202aaee87d4e51ec76b463bcc433f5d63500d9a115b7` |
| `source_head` | `43554f80fb3a0650a8a3ba9dc6afcfa46464d810` |
| Inputs | 42; 13 `assets/*.svg` + `tokens.json`; `image_compressor/_windows_deletion.py`; нет legacy/PyQt |
| Build | переиспользован staging worktree HEAD `43554f8`, новый create-only id; build raw exit 0 |

Overlay (9 файлов): `theme.py` `ff406e26…`, `widgets.py` `46d93f81…`, `controller.py` `d6ddf987…`, `window.py` `c5f25149…` (F1), `localization.py` `c4eb7216…` (F1), `README.md` `b43387be…`, spec `4ea6f4b0…`, build.py `78cc9eb6…`, ic_frozen_check.py `ab4ce06d…`. Receipt: `.agent-work/windows-exe/builds/20261028-candidate-05/curated-source.json`.

# Deletion и журнал (факты)

- Deletion не менялся: рабочая кликабельная галочка (`DeleteOriginals`, inline label, default OFF, busy-gating), Start без modal, удаление только после verified final output/flush/source-проверки, failure/cancel/unknown → retained/unknown, unsupported — explicit.
- UI журнала после F1: `Журнал операции` = summary-only (имя/формат, было→стало, меньше/больше/unknown, статус, deleted/retained/unknown; **без** `event=` и путей). `Подробности` = единственная technical-зона: raw `event=`, пути результата, params (codec/quality/bounds/postfix/mode), elapsed, SHA-256, errors, dispositions; read-only, StrongFocus, `TextSelectableByMouse|Keyboard`, no-wrap; raw-буфер ограничен 500, displayed items — 50.
- Удалены `_JournalToggle`, `journal_toggle`, `toggle_row`, `TechnicalLog`, `_toggle_technical`/`_retranslate_toggle`, ключ `journal_technical`; добавлен `technical_events` заголовок в Details. Второго technical-контейнера/вкладки/кнопки нет.

# Gates (raw)

| Проверка | Результат |
|---|---|
| focused `test_operation_journal` + `test_source_deletion` + `test_window` + `test_controller` | **62 passed**, exit 0, 14.51 s |
| full PySide offscreen `tests_pyside6_v2` | **89 passed**, exit 0, 16.58 s |
| Ruff GUI/tests | exit 0 |
| mypy `gui_pyside6_v2` (`--follow-imports=silent`) | exit 0 |
| `tests_windows_exe` против candidate-05 | **22 passed**, exit 0, 13.45 s |
| frozen receipt | `succeeded`; `deletion_module_loaded/available=true`; `forbidden_modules_absent=true`; resources 14; 9 starts; deletion-true (deleted=1/source absent), deletion-false (retained/bytes unchanged), deletion-partial (good deleted, bad retained); 6 screens RU/EN/KK × Light/Dark — Start True прошёл без modal |
| docs checker (свой corpus) | exit 0, `findings: []` |
| `git diff --check` | exit 0 (CRLF warnings only) |

# Native visual/functional (own HWND, system Light, DPR 1.5)

`.agent-work/deletion-journal/coder-01/native-c05/`: реальный mouse-клик и Space включают/выключают галочку; real Start через queue/worker/API создал verified `synthetic-delete.webp` (640×480→320×240, 220 B) и удалил synthetic source (`deleted=1`); `Журнал операции` — только summary (без `event=`/путей), `Подробности` — params/elapsed/path/SHA/raw events с selection (выделено >0 символов). Кадры `01-dark-ru-summary-1120`, `02-dark-ru-details-1120`, `03-light-ru-details-1120`, `04-dark-en-details-900`, `05-dark-kk-details-900`, `06-dark-ru-again` просмотрены: RU/EN/KK, Light/Dark, 900×640/1120×760 читаемы, вложенного toggle нет, native title bar следует теме в обе стороны.

# Delivery (phase 2, после независимого ACCEPT)

- **ACCEPT:** независимый exact-byte ACCEPT выдан этим же Reviewer'ом 2026-10-28 на байтах `ea1cb00f…476a` / 57 010 633; до и после всех действий phase 2 EXE hash/bytes не менялись.
- **Desktop shortcut:** существующий `C:\Users\User\Desktop\Image Compressor.lnk` перезаписан на `C:\PY\image_compressor\dist\windows-pyside6\20261028-candidate-05\ImageCompressorV2.exe` (WorkingDirectory/Icon/Description — этот build-id), readback цели/каталога/иконки совпал; сторонние `ImageCompressorGUI*.lnk` не тронуты. Запуск **именно через `.lnk`**: процессы bootloader+child с точным canonical path, собственное окно, штатное закрытие, дерево процессов пусто, `_MEI*` удалён, hash EXE не изменён.
- **Launcher:** `run_image_compressor_v2.bat` переведён на `20261028-candidate-05` (только `start`, без install/build/delete/network).
- **Recycle Bin:** прежний принятый fallback `dist/windows-pyside6/20261028-candidate-03/` и unaccepted `dist/windows-pyside6/20261028-candidate-04/` перемещены по одному через `Microsoft.VisualBasic.FileIO` + `SendToRecycleBin`; оба объекта проверены как отсутствующие, hard delete/`del`/`rmdir`/`git clean` не применялись. Pre-delete байты/размеры/manifest обоих каталогов — в reviewer evidence (`.agent-work/deletion-journal/reviewer-c05/cleanup-evidence-before.json`).
- **Сохранено:** `candidate-05` (EXE/BUILD-INFO/notices), `.agent-work/**` (staging, builds, evidence, failed attempts, venvs), `.venv`, source/tests/design/docs/PFK.
- **Границы:** публикации бинарника, signing/installer/public release, других платформ/DPI и reproducibility нет — как в NOT RUN ниже.

# NOT RUN и сохранность

- Независимый exact-byte ACCEPT, `.lnk`/launcher update, accepted/superseded closeout, Recycle Bin cleanup, commit/push — Reviewer после ACCEPT.
- Frozen failure/cancel deletion (покрыто source tests); системная смена темы при открытом окне; другие ОС/DPI; signing/release; clean machine; reproducibility; screen reader/RTL; физические OS-dialog/drop.
- `candidate-04` сохранён как unaccepted evidence и не доставлялся; `candidate-03` (SHA `31fd7999…9b30`) и Desktop `.lnk` не тронуты; deletion проверялся только на synthetic disposable root.
