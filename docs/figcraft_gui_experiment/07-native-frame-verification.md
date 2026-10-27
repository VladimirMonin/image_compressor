---
id: ic-native-frame-verification
title: "Native Windows frame для ручной смены темы PySide6 GUI"
kind: verification
status: accepted
created: "2026-10-28"
updated: "2026-10-28"
areas: [gui, pyside6, windows, verification]
summary: "Root cause светлой рамки, минимальный DWM-owner в theme.py, offscreen/real-Windows проверки, оба визуальных направления и границы: source fix не исправляет candidate-02."
code_ref: "b67678860de1bad3a0688fc60d0a98177f73ba7d"
verification_scope: "Авторские проверки на текущем Windows11 x64/local NTFS хосте, system Light, DPR1.5: offscreen 82 passed, real Windows QPA probe и собственные PrintWindow-кадры обоих направлений. Независимый ACCEPT выдан этим же Reviewer'ом на тех же байтах в source/native-frame границах; новая платформенная/release квалификация не заявляется."
---

# Итог

Ручная смена темы в PySide6 GUI теперь доводит **native title bar** до выбранной темы: последний writer `apply_theme` вызывает узкий DWM-owner для собственного top-level окна. Source fix проверен на offscreen suite и реальном Windows QPA; оба визуальных направления и RU/EN/KK в Dark подтверждены собственными кадрами только своего окна. Статус документа — `accepted`: авторские числа и визуальные направления ниже независимо воспроизведены тем же Reviewer'ом на тех же байтах в source/native-frame границах; платформенная/release квалификация не расширяется.

**Source fix не исправляет `candidate-02`.** Принятый EXE `20261023-candidate-02` не пересобирался и остаётся светлым в Dark; его байты и SHA не менялись. Пользователь через `run_image_compressor_v2.bat` увидит прежнюю рамку до нового build-id и нового независимого exact-byte ACCEPT.

# Root cause

- Рамка окна — non-client область, которой владеет Windows/DWM; `QPalette`/QSS красят клиентскую область и на заголовок не действуют (Qt, «Window and Dialog Widgets»).
- Qt 6.12 `qwindows` сам вызывает `DwmSetWindowAttribute(hwnd, 20 /*19 fallback*/, &BOOL, sizeof(BOOL))`: при создании top-level окна — только если системная схема Dark и палитра темнее текста (`shouldApplyDarkFrame()`), затем на `ApplicationPaletteChange`, смену top-level состояния и смену **системной** схемы (`handleThemeChange`, обход всех окон).
- Ручная смена темы приложения не меняет системную схему, поэтому событие `colorScheme` не приходит: остаётся рамка по системе. На светлой Windows ручной Dark даёт тёмный клиент со светлым заголовком.
- `QStyleHints::setColorScheme()` — это app-level **hint** для системной интеграции, а не per-window API; он меняет глобальную подсказку приложения и в этом срезе не используется.
- `windowHandle()` до `show()` равен `None`; `winId()` создаёт native handle. Поэтому helper сам получает HWND через `winId()`, и одних трёх существующих вызовов `apply_theme` (создание окна, диалог подтверждения, ручная смена темы) достаточно — `window.py` не менялся.

# Design (минимальный owner)

Изменён только `gui_pyside6_v2/theme.py`; QSS, палитры, тексты, layout и все прочие модули — без правок.

| Элемент | Решение |
|---|---|
| Атрибут | `DWMWA_USE_IMMERSIVE_DARK_MODE = 20`; `pvAttribute → BOOL`, `cbAttribute = sizeof(BOOL) = 4`; success = `S_OK` (`hr == 0`), иначе fail-closed `False`. Attr 19, caption/border color, `SetWindowTheme`, `setColorScheme` не используются. |
| Обе темы явно | `dark → BOOL(1)`, `light → BOOL(0)`; light — реальный вызов, а не «оставить как есть». |
| Только своё окно | один `hwnd = int(window.winId())`; проверка `window.isWindow()`; никаких перечислений/чужих handle, foreground, clipboard, реестра. |
| Offscreen guard | `sys.platform == "win32"` **и** существующий `QGuiApplication` **и** `platformName() == "windows"`; на offscreen DWM не вызывается вовсе. |
| Видимое окно | `SetWindowPos` только с `NOSIZE|NOMOVE|NOZORDER|NOACTIVATE|NOOWNERZORDER|FRAMECHANGED`, `hWndInsertAfter = NULL`; без `UpdateWindow`/`RedrawWindow`/`DwmFlush`. |
| Порядок | последняя строка `apply_theme` — после палитры, QSS/шрифта, spin-inset и popup-палитры; `apply_theme` по-прежнему возвращает `None`. |
| Ошибки | любые `OSError`/`AttributeError`/`ctypes.ArgumentError` → `False`; палитра/QSS применяются в любом случае. |

# Первичные источники

Проверены Oracle при выпуске контракта; в этом прогоне повторно не скачивались.

| Источник | URL | Вывод |
|---|---|---|
| MS `DwmSetWindowAttribute` | https://learn.microsoft.com/en-us/windows/win32/api/dwmapi/nf-dwmapi-dwmsetwindowattribute | `HRESULT`, success = `S_OK`; тип/размер значения задаёт атрибут |
| MS `DWMWINDOWATTRIBUTE` | https://learn.microsoft.com/en-us/windows/win32/api/dwmapi/ne-dwmapi-dwmwindowattribute | `DWMWA_USE_IMMERSIVE_DARK_MODE = 20`, значение BOOL, `TRUE` — dark, `FALSE` — always light; Win11 22000+ |
| MS `SetWindowPos` | https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowpos | `SWP_FRAMECHANGED` шлёт `WM_NCCALCSIZE`; документированная комбинация `NOMOVE|NOSIZE|NOZORDER|FRAMECHANGED` |
| Qt `QWidget::winId()` | https://doc.qt.io/qt-6/qwidget.html#winId | создаёт native handle у non-native виджета; значение может меняться (`WinIdChange`) |
| Qt `QGuiApplication::platformName()` | https://doc.qt.io/qt-6/qguiapplication.html#platformName | имя QPA-плагина; `windows`, `offscreen` |
| Qt «Window and Dialog Widgets» | https://doc.qt.io/qt-6/application-windows.html | рамка/заголовок — зона оконного менеджера, не клиентская |
| Qt 6.12 QPA Windows source | https://code.qt.io/cgit/qt/qtbase.git/plain/src/plugins/platforms/windows/qwindowswindow.cpp?h=6.12 | Qt вызывает тот же атрибут 20; `handleThemeChange` обходит окна при смене системной схемы |
| Qt `QStyleHints` | https://doc.qt.io/qt-6/qstylehints.html | `setColorScheme` — hint для системной темы приложения, не per-window |

Decision rule контракта: на светлой системе Dark обязан визуально потемнеть, иначе BLOCKER. Хост в этом прогоне — **system Light**, и потемнение подтверждено кадрами ниже; BLOCKER не сработал.

# Изменённые файлы

- `gui_pyside6_v2/theme.py` — `ctypes`/`sys`/`QGuiApplication`, константы, четыре private helper'а (`_native_frame_supported`, `_set_dark_frame`, `_redraw_frame`, `_apply_native_frame`) и один последний вызов в `apply_theme`. QSS/палитры/тексты не тронуты.
- `tests_pyside6_v2/test_native_frame.py` — 6 offscreen-тестов (routing обеих тем, explicit light FALSE, child/unknown-theme, fail-closed, redraw только для видимого, offscreen не вызывает DWM).
- `tests_pyside6_v2/native_frame_probe.py` — explicit real-Windows QPA проба с JSON-receipt.

# Команды и raw результаты

Окружение: закреплённая PySide6-only среда `.agent-work/figcraft-gui-experiment/pyside6-venv` (PySide6 6.12.0, pytest 9.1.1, Ruff 0.17.2, mypy 2.4.0); свои TEMP/TMP/TMPDIR и basetemp под `.agent-work/native-frame/coder-01/`; Git Bash из корня.

| # | Команда | Raw результат |
|---|---|---|
| G1 | `sha256sum gui_pyside6_v2/theme.py` до правки | `2a762f5f24228ee19f7c1a6aad95b78745dc5e30a74ed97c491d03a79c857641` — принятый controls-хеш, дрейфа не было |
| G2 | `QT_QPA_PLATFORM=offscreen <PySide> -B -m pytest -p pytest_timeout -p no:cacheprovider tests_pyside6_v2 -q --basetemp <own>/pytest2` | **exit 0, 82 passed, 0 failed, 0 skipped** (8.40 s); 2 deprecation warnings test-side `QDragEnterEvent` |
| G3 | `<PySide> -B -m ruff check gui_pyside6_v2/theme.py tests_pyside6_v2/test_native_frame.py tests_pyside6_v2/native_frame_probe.py` | exit 0, `All checks passed!` |
| G4 | `<PySide> -B -m mypy --follow-imports=silent gui_pyside6_v2` | exit 0, `Success: no issues found in 9 source files` |
| G5 | `QT_QPA_PLATFORM=windows <PySide> -B -m tests_pyside6_v2.native_frame_probe --output <own>/native-1` | exit 0; `platform=windows`, DPR 1.5, `hwnd_stable=true`, `all_ok=true`; receipt — `.agent-work/native-frame/coder-01/native-1/receipt.json` |
| G6 | собственный native визуальный прогон (своё окно, PrintWindow только своего HWND) | exit 0; 5 собственных кадров + `visual-facts.json` под `.agent-work/native-frame/coder-01/visual-1/` |
| G7 | `.agent-work/foundation-venv/Scripts/python.exe -I -B tools/project-foundation/tools/check_foundation.py --project . --corpus <own>/docs-corpus.json` | exit 0, `findings: []` |
| G8 | `git diff --check` | exit 0 (только штатные `LF will be replaced by CRLF`) |
| G9 | `sha256sum` candidate-02 + `git status --short` | `09c4b2f1…2bb53`, 56 977 108 bytes; в статусе только A1–A8 |

After-хеши исходников среза: `theme.py` = `0d902dbcef54f6712d785b034a7392c6280a6afb02df2cdd18d9a848511a4c0d`, `test_native_frame.py` = `cb4ce3af2c953b785015009d580544bac514b0fd8df8b7869e408444b7875d79`, `native_frame_probe.py` = `dac7a18744441a98bb8c807eecf33b6f76251a9f5c951503f8c7fb5c080164b9`.

Real-Windows receipt (G5): `system_color_scheme = Light`; `direct_dwm_results = {dark: true, light: true}`; три переключения `dark→light→dark` через настоящий `theme_combo` — по одному вызову с `result: true`, `int(winId())` неизменен (`54726664` до/после), окно видимо во время переключений и закрыто штатно (`closed: true`). DPR 1.5, logical geometry 1120×760, frame 1120×790.

# Визуальный факт (собственное окно, system Light, DPR 1.5)

Кадры получены `PrintWindow` только по HWND собственного окна; чужие окна, рабочий стол, фокус и clipboard не захватывались. Просмотрены индивидуально.

| Кадр | Тема / язык | Наблюдение |
|---|---|---|
| `01-dark-ru.png` | dark / RU | заголовок тёмный, светлый текст; клиент тёмный, контролы читаемы |
| `02-light-ru.png` | light / RU | заголовок светлый, тёмный текст; клиент светлый |
| `03-dark-ru-again.png` | dark / RU | заголовок снова тёмный — light не «залипает» |
| `04-dark-en.png` | dark / EN | тёмный заголовок, EN-тексты без обрезки |
| `05-dark-kk.png` | dark / KK | тёмный заголовок, KK-тексты и disabled deletion объяснение на месте |

`visual-facts.json` фиксирует `system_color_scheme: Light`, `dpr: 1.5`, `geometry [720,290,1120,760]`, `frame_geometry [720,290,1120,790]`, стабильный HWND во всех пяти кадрах и `palette_matches: true` для каждой темы. PrintWindow — способ получить только своё окно; HRESULT и unit-тесты сами по себе визуальным PASS не считаются, факт — просмотр кадров.

# NOT RUN и границы

- `candidate-02` не пересобирался и не запускался; его байты/SHA не менялись. Source fix **не** исправляет существующий EXE.
- Packaging/spec: 12 `control-*.svg` в `datas` не входят (известный gap `ImageCompressorV2.spec`); пересборка без правки spec даст EXE без тематизированных стрелок/галочек. Отдельный out-of-scope факт, здесь не исправлялся.
- Не проверялись: смена **системной** темы при открытом окне (Qt `handleThemeChange` может вернуть рамку к системной схеме до следующего ручного переключения), high-contrast mode, Windows 10/ARM, Linux/macOS, все DPI, screen reader, RTL, сценарии `WinIdChange` (в GUI нет `setWindowFlags`).
- Не запускались: legacy `tests/` (170), `tests_windows_exe/`, сборка/EXE, gallery-наборы, installs; новых зависимостей/скачиваний кода нет.
- Не выполнялись: registry/system settings, чужие окна/фокус/clipboard, deletion/layout/text/control-поведение; stage/commit/push/branch/reset/stash; ничего не удалялось.

# Будущий интегрированный бинарник

Новый EXE с этим исправлением требует **нового build-id**, собственного build/qualification и **нового независимого exact-byte ACCEPT**. Прежний ACCEPT `candidate-02` на новые байты не переносится; [release record](../releases/windows-pyside6-candidate-02.md) сохраняет границу принятого бинарника.
