---
id: ic-release-windows-pyside6-candidate-03
title: "Курированная сборка: PySide6 GUI v2 · Windows x64 · 20261028-candidate-03"
kind: snapshot
status: accepted
created: "2026-10-28"
updated: "2026-10-28"
areas: [gui, packaging, release, windows]
summary: "Курированная сборка из 68b7dc5 + accepted native-frame theme.py + исправленный packaging: точные байты, overlay, отсутствие legacy/deletion в EXE и границы."
snapshot_of: "dist/windows-pyside6/20261028-candidate-03/BUILD-INFO.json"
code_ref: "68b7dc57e08a61d167e5a7f629b8a078d218732a"
verification_scope: "Авторские проверки: core 223 passed, PySide 82 passed, tests_windows_exe 22 passed на новом EXE, ruff/mypy raw0, frozen --packaging-check и собственный визуальный кадр Dark→Light→Dark. Независимый exact-byte ACCEPT выдан этим же Reviewer'ом на этих байтах (core/PySide/tests_windows_exe, архив, provenance, реальный запуск, title bar и controls); других платформ/подписи/release нет."
---

# Итог

Курированная сборка `20261028-candidate-03` собрана из **pre-deletion базы `68b7dc5`** с точечным overlay: принятый native-frame `gui_pyside6_v2/theme.py` (`0d902dbc…4c0d`), frozen `pyproject.toml`/`README.md` и исправленный packaging (`tools/windows_exe/*`). Deletion-WIP `718c578` и legacy PyQt6/facade в EXE **не входят**. Статус — `accepted`: независимый exact-byte ACCEPT выдан на этих байтах; `candidate-02` переведён в `superseded`, его артефакты и старые build/caches перемещены в Recycle Bin (§ Delivery).

# Artifact

| Поле | Значение |
|---|---|
| Путь | `dist/windows-pyside6/20261028-candidate-03/ImageCompressorV2.exe` |
| Размер | **56 986 324 bytes** |
| SHA-256 | **`31fd7999f93cc54305bd39a18c9aa3c65f274ae5a8a974bafea47b7a0dd49b30`** |
| `BUILD-INFO.json` | 15 480 bytes, SHA-256 `af12e4005f04d5a0ad80d17bba2c5c8f8860abec44f17f038d9a4e31aea5ab1a` |
| `README.txt` | 378 bytes, SHA-256 `524a264ac07f535e3e7e6522f32066f518beab47fba4e0a9d624e58ff934a2f9` |
| Форма | onefile, PE32+ AMD64, GUI subsystem; unsigned local artifact |

`BUILD-INFO.status = built_not_independently_accepted` — статус момента сборки. Байты не пересобирались после сборки; hash-readback совпадает с BUILD-INFO.

# Curated source

- База: detached git-worktree на `68b7dc57e08a61d167e5a7f629b8a078d218732a` в `.agent-work/windows-exe/staging/20261028-candidate-03/root` (обратимо, без ветки/reset/истории).
- `.agent-work` и `dist/windows-pyside6` подключены junction'ами к canonical root; артефакт и build-work сразу лежат в canonical путях, а `BUILD-INFO.executable`/`build_work` записаны в staging-виде — это те же файлы (совпадают bytes/hash).
- Curated-source receipt (base commit, worktree, `git status --porcelain`, хеши overlay, EXE hash/bytes): `.agent-work/windows-exe/builds/20261028-candidate-03/curated-source.json`.

`source_head` = `68b7dc5…`; `source_delta` содержит ровно 6 overlay-файлов:

| Путь | SHA-256 | Роль |
|---|---|---|
| `gui_pyside6_v2/theme.py` | `0d902dbcef54f6712d785b034a7392c6280a6afb02df2cdd18d9a848511a4c0d` | принятый native-frame (HEAD) |
| `pyproject.toml` | `462e032de1e6ef4c27e41440fe16c00ef82ea3e7ba8fcf6ae32d8f8f33744a2a` | retired PyQt extra/package/py-modules |
| `README.md` | `e831ce189913b9ad3dcb1863a70eaf4ab32cb7b835f7d544b563e3a44eb9ffce` | актуальная навигация без legacy |
| `tools/windows_exe/ImageCompressorV2.spec` | `f90aaba2a0cf59f16faf7b29e589df527a22b568c600ba5dd54bdc1d56fb1b43` | все 13 assets + legacy/deletion excludes |
| `tools/windows_exe/build.py` | `c564814452c0c691d6707fa8d5199fae130ba1b7834d36fb3714d9952185fadd` | fail-closed assets/legacy/deletion гейты |
| `tools/windows_exe/ic_frozen_check.py` | `fa2fe9116ae029f9d276a74b5d7834127b69b081cafb966ab47091ba9a0583e1` | все SVG + forbidden-modules в receipt |

`frozen_entry.py` и `requirements-win64.txt` в overlay не менялись (совпадают с `68b7dc5`). Input-set — **41** файл: `pyproject.toml`, `README.md`, `image_compressor/**`, `gui_pyside6_v2/**` (включая `tokens.json` и все 13 `assets/*.svg`), 5 packaging-файлов. В `inputs` нет `gui/`, `classes.py`, `gui_main.py`, `image_compressor/_windows_deletion.py`.

# Состав EXE

- Все 13 `gui_pyside6_v2/assets/*.svg` + `tokens.json` упакованы; `verify_archive()` fail-closed требует каждый ассет, `python314.dll` и `qwindows.dll`, а точные имена `gui/…`, `classes`, `gui_main`, `image_compressor/_windows_deletion.py` отвергает как `LEGACY_RUNTIME_BUNDLED`/`DELETION_WIP_BUNDLED`.
- Frozen `--packaging-check` на этом SHA: `status=succeeded`, `frozen=true`, `platform=windows`, `resources=14` (tokens + 13 SVG), `forbidden_modules_absent=true`, `fallback_imported=false`, 6 synthetic conversion cases, 6 screen captures (RU/EN/KK × Light/Dark) с `svg_visible=true`.
- **Deletion-WIP отсутствует.** В собранном EXE удаление исходников недоступно (disabled/unchecked, backend получает `delete_original=False`), как на базе `68b7dc5`. Legacy PyQt6 GUI/facade в EXE нет.

# Сборка

```powershell
git -C C:\PY\image_compressor worktree add --detach <stage>\root 68b7dc5
# junction dist/windows-pyside6 и .agent-work; overlay 6 файлов
& .agent-work\windows-exe\build-venv\Scripts\python.exe -I -B <stage>\root\tools\windows_exe\build.py --build-id 20261028-candidate-03
```

Raw exit сборки — 0; `BUILD_FAILED` не возникал. Никаких installs/downloads/новых build-id; `dist/windows-pyside6/20261023-candidate-01`/`-02` и legacy `dist/ImageCompressorGUI.exe` не трогались. README/pyproject заморожены **до** сборки и после неё не менялись.

# Legacy retirement (tracked source)

Удалены из рабочей копии **только через Recycle Bin** (`Microsoft.VisualBasic.FileIO.FileSystem` + `SendToRecycleBin`, по одному объекту; evidence — `.agent-work/final-clean-build/coder-01/deleted-evidence-before.json` и `recycled-after.json`): `gui/` (6 файлов), `gui_main.py`, `classes.py`, `test_gui.py`, `gui_compressor.spec`, `build_exe.bat`, `run_compiled_gui.bat`, `install_and_run_gui.bat`, `run_gui.bat`, `run_dev.bat`, `BUILD_README.md`, `BUILD_QUICK.md`, `PROJECT_STATUS.md`, `RELEASE_NOTES.md`, `UPDATE_FEATURES.md`, `tests/test_gui_adapter.py`, `tests/test_compatibility.py`. История сохранена в Git; hard delete/`del`/`rmdir`/`git clean` не применялись.

`pyproject.toml` больше не содержит extra `gui`, package `gui` и `py-modules`; `requirements.txt` = `.[gui-pyside6,codecs,build]`; `tests/test_packaging.py` проверяет wheel без `classes.py`/`gui_main.py`/`gui/**` и со всеми 13 SVG. `dist/ImageCompressorGUI.exe`, `build/`, `requirements_freeze.txt`, старые caches и `candidate-01/02` на момент сборки **не удалялись**; их обратимая уборка выполнена только после независимого ACCEPT (§ Delivery).

# Delivery (phase 2, после независимого ACCEPT)

- **ACCEPT:** независимый exact-byte ACCEPT выдан этим же Reviewer'ом 2026-10-28 на байтах `31fd7999…9b30` / 56 986 324; до и после всех действий phase 2 EXE hash и bytes не менялись. Независимо перепроверены core/PySide/`tests_windows_exe`, состав архива (13 SVG + tokens, без legacy/deletion/PyQt/QML/WebEngine/Pdf), provenance 41 входа, реальный запуск и visual-факты (title bar в оба направления, controls RU/EN/KK при 1120×760 и 900×640, deletion disabled).
- **Desktop shortcut (create-only):** `C:\Users\User\Desktop\Image Compressor.lnk` → target `C:\PY\image_compressor\dist\windows-pyside6\20261028-candidate-03\ImageCompressorV2.exe`, WorkingDirectory — каталог артефакта, Icon — `ImageCompressorV2.exe,0`, Description — `local unsigned build 20261028-candidate-03`; readback цели/каталога/иконки совпал, существующие ярлыки не перезаписывались. Запуск **именно через `.lnk`**: процессы bootloader+child с точным canonical path, окно `Image Compressor · PySide6 experiment`, штатное закрытие, дерево процессов пусто, `_MEI*` удалён, hash EXE не изменён. Два сторонних прежних ярлыка `ImageCompressorGUI.exe.lnk` и `ImageCompressorGUI.lnk` не тронуты и после C3 указывают на уже отсутствующий legacy EXE.
- **Recycle Bin (C1–C7, по одному, `Microsoft.VisualBasic.FileIO` + `SendToRecycleBin`):** `dist/windows-pyside6/20261023-candidate-01/`, `dist/windows-pyside6/20261023-candidate-02/`, `dist/ImageCompressorGUI.exe`, `build/`, `image_compressor.egg-info/`, `requirements_freeze.txt`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/` — каждый объект после операции проверен как отсутствующий; hard delete/`del`/`rmdir`/`git clean` не применялись. Pre-delete байты/хеши и manifest каждого объекта — в reviewer evidence (`.agent-work/final-clean-build/reviewer-02/cleanup-evidence-before.json`).
- **Сохранено:** новый `candidate-03` (EXE/BUILD-INFO/notices), `.agent-work/**` (staging, builds, evidence, venvs), `.venv`, source/tests/design/docs/PFK. `requirements_freeze.txt` не отслеживался Git (ignored), поэтому в commit нет path-deletion.
- **Границы:** публикации бинарника, signing/installer/public release, других платформ/DPI и reproducibility нет — как в NOT RUN ниже.

# Авторские проверки (raw)

| # | Проверка | Результат |
|---|---|---|
| G1 | `git status --short --branch` | только allowlist: 22 `D` (17 объектов, `gui/` — 6 файлов), modified docs/config/packaging/tests, новые release record; `dist/`, `.agent-work/` не видны |
| G2 | отсутствие legacy на диске (`test -e` по каждому пути) + `git status` `D` | ни одного legacy-файла на диске; в index они ещё tracked до closeout Reviewer'а (Coder не stage'ит) |
| G3 | `.venv` pytest `tests` | **223 passed**, raw exit 0, 27.78 s |
| G4 | PySide pytest `tests_pyside6_v2` (offscreen) | **82 passed**, raw exit 0, 10.75 s |
| G5 | `tests_windows_exe` против нового EXE | **22 passed**, raw exit 0, 13.41 s |
| G6 | `.venv` ruff `image_compressor tests` | exit 0 |
| G7 | PySide ruff `gui_pyside6_v2 tests_pyside6_v2 tools/windows_exe tests_windows_exe --extension spec:python` | exit 0 |
| G8 | mypy `image_compressor`; PySide mypy `gui_pyside6_v2` | оба exit 0 |
| G9 | strict mypy 3 helper (`build`, `frozen_entry`, `ic_frozen_check`) с `--python-executable build-venv` | exit 0 |
| G10 | docs checker, собственный corpus | exit 0, `findings: []` |
| G11 | `git diff --check` | exit 0 (штатные CRLF-предупреждения) |
| G12 | hash/size нового EXE + `BUILD-INFO` | `31fd7999…9b30` / 56 986 324; `source_head=68b7dc5…`; 41 input; legacy/deletion отсутствуют |
| G13 | собственный native кадр Dark→LIGHT→Dark (PrintWindow только своего окна) | заголовок тёмный → светлый → снова тёмный; стрелки spinbox/combo и checkbox видны в обеих темах; RU/EN/KK и min 900×640 подтверждены замороженными кадрами EXE |

`G2` сформулирован как «пусто» в плане для уже сохранённого closeout; в авторской фазе удаления неизбежно видны как `D` в `git status` (index не пишется), а на диске их нет. Это ограничение фазы, не расхождение кандидата.

# Визуальные факты

- **Frozen EXE** (`--packaging-check`, собственный output `.agent-work/final-clean-build/coder-01/frozen-check-2/`): `ru-light.png`, `ru-dark.png`, `en-light.png`, `en-dark.png`, `kk-light.png`, `kk-dark.png` — все 6 просмотрены: стрелки spinbox, chevron combo и checkbox отрисованы в обеих темах; KK Dark при 900×640 без обрезки ключевых контролов; deletion — disabled/unchecked.
- **Native frame** (source-run того же accepted `theme.py`, PrintWindow только своего HWND, `.agent-work/final-clean-build/coder-01/frame-1/`): `dark.png` — тёмный заголовок; `light.png` — светлый; `dark-again.png` — снова тёмный. Система Windows — Light, DPR 1.5, окно 1120×760; штатное закрытие, процессов не осталось.
- Автоматическая смена темы **внутри frozen EXE** не производилась: driver снимает только client area. Это NOT RUN для автоматизации; рамка в EXE использует те же байты `theme.py` (input hash совпадает), а ручная проверка обоих направлений на EXE — Reviewer R6.

# NOT RUN

- Другие ОС/архитектуры (Windows 10/ARM, Linux/macOS), все DPI, screen reader, RTL, физические OS-dialog/drop.
- Signing/SmartScreen/installer/публичный release; bit-for-bit reproducibility; чистая VM/другой аккаунт; crash durability; смена системной темы при открытом окне.
- Пересборка после любых правок; cleanup `candidate-01/02`, legacy `dist/ImageCompressorGUI.exe`, `build/`, `requirements_freeze.txt`, caches; Desktop shortcut — всё это post-ACCEPT Reviewer-стадия (C1–C7), не выполнено.
- Визуальная проверка обоих направлений рамки именно в frozen EXE (см. выше).

# Будущее

После независимого ACCEPT новые байты не пересобираются; `candidate-02` может быть помечен `superseded`, старые EXE/cache убираются только через Recycle Bin, ярлык создаётся create-only. До этого `candidate-02` — fallback.
