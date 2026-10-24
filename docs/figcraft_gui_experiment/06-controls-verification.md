---
id: ic-pyside6-controls-verification
title: "PySide6 — различимые и удобные мелкие контролы"
kind: verification
status: accepted
created: "2026-10-24"
updated: "2026-10-24"
areas: [gui, pyside6, controls, testing]
summary: "Независимый технический и визуальный ACCEPT source-среза стрелок, списков и флажков; остальные функциональные исправления и новый EXE не включены."
code_ref: "bf9f89d8b2c877512a58f5a7ad1aea35ccf3559a + controls candidate manifest SHA-256 be84ac01de78fa48a32dd0df5b11e7a6eb52af03729802da88cc9fd586b1aa09"
verification_scope: "Только 15 frozen source/test/asset paths, Windows source Widgets/Fusion/offscreen и native Windows QPA; не удаление, новый вывод результатов или новый frozen EXE."
---

# Решение и граница

**Независимый технический ACCEPT и визуальный ACCEPT. Обязательных source/test замечаний нет.** Принято только согласованное оформление и взаимодействие мелких контролов существующего `gui_pyside6_v2/`. [Первоначальный GUI/design ACCEPT](REPORT.md) и [прежний exact-byte EXE ACCEPT](05-windows-exe-verification.md) сохраняют собственные исторические границы.

Принятый состав — `gui_pyside6_v2/theme.py`, 12 новых `gui_pyside6_v2/assets/control-*.svg`, `tests_pyside6_v2/test_controls_appearance.py` и `tests_pyside6_v2/controls_gallery.py`: **15 путей**. Theme SHA-256 `2a762f5f24228ee19f7c1a6aad95b78745dc5e30a74ed97c491d03a79c857641`; test SHA-256 `d11357cf8010d1eff259eabe109139fe15c017fcf2bda7269a65b5313dc11c06`; gallery SHA-256 `625d1e8982b534073ea8c536d9dcf77dac0f4488f6d16c35e5953f7f98b04f84`. Полный cumulative manifest и сохранённые bytes сверены до/после независимых проверок; index до решения пуст. Исторический manifest не переписывается последующим документационным коммитом.

Ядро/API/CLI, controller/window/widgets/localization, старый GUI, batch-семантика, дизайн, tokens, pyproject и freezer не менялись. 112 dependency-basis файлов, включая прежний EXE, совпали до/после приёмки. Позднее обновлены только относящиеся документы; из этого набора затронута только инструкция testing. План следующего функционального среза и его отдельный LOG не входят в controls-кандидат или его сохранение.

# Что исправлено и чем это проверяется

Частичный QSS поверх Fusion оставлял стрелки и индикаторы базовому стилю. Исправление находится в **существующем владельце темы**, без нового стиля-прокси, converter или UI framework.

| Контрол | Реальный механизм и наблюдение |
|---|---|
| Числовые поля | Полные up/down button/arrow rules, состояния enabled/hover/pressed/off/disabled. Общий канал 28 logical px плюс рамки; native Quality имеет отдельные hit rectangles **30×21 logical px**. Нажатия у внешних краёв действительно меняют значение; обе границы не переполняются. |
| Читаемость значения | `QLineEdit.setTextMargins` задаёт token-owned inset4, поскольку Fusion не применял нужный левый QSS inset к внутреннему editor. Из фактической ширины editor вычитаются margins; `2147483647` виден полностью и в minimum900×640/KK. |
| Выпадающие списки | Согласованные arrow/channel, реальные OPEN view/items/selection/hover. Отдельное top-level окно popup получает тот же stylesheet и token-derived palette: внешние поля Dark больше не остаются нативно-белыми. Выбор строки реально фиксируется, включая theme/locale. |
| Флажки | Различимы unchecked, checked с контрастной галочкой, disabled checked/unchecked и focus ring в обеих темах. Click по подписи и Space переключают настоящий виджет; disabled ввод ничего не включает. Размер индикатора20 logical px плюс рамки; отдельный buddy-label удаления сохранён. |
| Неизменённые связи | Quality↔slider, resize on/off→доступность обеих dimensions, Tab/skip disabled, options и RU/EN/KK сохраняются. Компоновка и намеренная вертикальная прокрутка settings не переделывались. |

SVG — только геометрия стрелок/галочки с цветами существующих tokens. Имена имеют форму `control-{up,down,check}[-disabled]-{light,dark}.svg`: три glyph × два enabled-state × две темы, всего12. Resolver основан на `importlib.resources.files`, не cwd; реальные vectors/ink/colors и Widgets проверены из другого рабочего каталога. Runtime не требует нового provider или FigCraft.

# Свежие независимые проверки

Среда: Windows, Python3.14.2, PySide6/Qt6.12.0, Pillow13.0.0; существующий отдельный PySide interpreter без PyQt6. До collection проверены config/import/fixtures и назначены own TEMP/TMP/TMPDIR, caches/basetemp, plugin-autoload policy. Установок и изменения старых сред/глобальных настроек нет. Каждый recorded subprocess ограничен110s.

| Проверка | Фактический результат |
|---|---|
| Новый controls module + адресные прежние window regressions | **32 passed,0 skips,raw0**:18 новых controls cases +14 существующих geometry/i18n/Add-SVG cases. Не полный прежний suite. |
| HiDPI-risk выборка, `QT_SCALE_FACTOR=1.5` | **8 passed,raw0** — повтор подмножества тех же32, не8 дополнительных уникальных cases. |
| Отдельный native Windows-QPA supplement | **2 passed,raw0**, обе темы: собственные HWND/PID, реальные arrow/row/keyboard commits, clicks/limits/slider, checkbox states/gates/options; окна штатно закрыты. |
| Ruff theme + два новых test/gallery modules | **raw0**, All checks passed. |
| Strict mypy theme, `--follow-imports=silent` | **raw0**,1 source module; неизменённое ядро не переоткрывалось под другими stubs. |
| Свежая source gallery | **raw0**,10 PNG + labelled contact sheet, source hashes совпали с frozen кандидатом, собственное окно закрыто. |
| Просмотр | Contact sheet и **все16 отдельных собственных PNG**:10 source/offscreen +6 native panel/popup, а не только авторская выбранная галерея. |

Положительные проверки используют production MainWindow/theme hookup и реальные Qt input/geometry/raster, не поиск QSS-строк. Offscreen использует установленные Segoe UI только в памяти своего процесса; native Windows перечисляет системный шрифт сам. Просмотренные captures имеют DPR1.5, Segoe UI; обычное окно1120×760 logical, отдельный KK minimum900×640. В disabled-предустановке отключается только представление SettingsPanel: она **не** изображает выполненную конвертацию или настоящий busy/result исход.

Ранняя дополнительная native fixture дала2 отказа: синтетический mouse release был подан40ms после mouse-arrow открытия. Bare-Fusion witness с тем же способом открытия воспроизвёл отказ без продукта/QSS;700ms проходит, системный double-click interval500ms. Исправлен только private probe — ожидание `doubleClickInterval()+50` перед тем же положительным row click; обе native проверки затем raw0. Первые failures и первый неэквивалентный diagnostic через programmatic showPopup сохранены, кандидат не менялся. Авторские RED исходных target/inset/popup и промежуточных исправлений также сохранены отдельно от независимого решения.

Точные commands/raw stdout/stderr/exits, JUnit, source/capture hashes и исходный вердикт находятся в ignored evidence. **Прежние47/170, core/codec/installed-Python и design гарантии переиспользованы только для неизменённых owners**, не названы свежими controls/frozen tests. Преобразование/удаление пользовательских изображений и broad suite здесь не выполнялись.

# Что видно на текущих кадрах

- RU Dark resize-off: активное quality80/focus, unchecked resize, disabled dimensions, checked recursive. Чёткие широкие chevrons и themed checkbox вместо светлого нативного квадрата.
- RU Light resize-on: checked/focus resize, enabled dimensions, quality100 с неактивным верхним шагом, unchecked recursive.
- Dark disabled panel и native Light/Dark disabled panels: checked и unchecked muted/dashed indicators различаются; отключённый флажок удаления остаётся отдельным недоступным действием.
- KK Dark minimum900×640: quality0, полный десятизначный width, читаемые glyphs, header/footer/safety сохранены, settings scroll намеренный.
- Реальные OPEN format Dark и language Light popup плюс native format обеих тем: читаемые строки/selection/on-action text, согласованные рамки и внешняя поверхность. Popup снят отдельно как принадлежащее проверке окно, не дорисован поверх host.

# Следующие функциональные срезы и упаковка

**Это не завершение всего исправления GUI.** Пока не реализованы новым срезом: явный default-false режим удаления через общий API/CLI/GUI; человеческий локализованный журнал и полезные пофайловые результаты; новый интегрированный standalone Windows EXE. Изменение внешнего вида disabled deletion не означает, что удаление заработало: checkbox остаётся unchecked/disabled, прежний API продолжает отвергать True.

Существующий [EXE](WINDOWS_EXE.md), SHA-256 `09c4b2f1fc65655d624111537d693f0971fad75787f6c3045072d5863312bb53`, **не изменён и не содержит эти controls-правки**. Он не является новым исправленным артефактом. Текущий frozen spec перечисляет только tokens.json/add.svg: последующий packaging-срез обязан включить все12 новых SVG в тот же package-relative путь, собрать новый build-id и независимо проверить installed/frozen controls, popup и интегрированное поведение. `pyproject.toml` уже включает `assets/*.svg`, но source alternate-cwd проверка не заменяет свежий installed-wheel/frozen запуск. Ранняя controls-приёмка не требует заранее пересобирать EXE.

Не квалифицированы все DPI/OS/шрифты, screen reader, физические OS-dialog/drop, мышь на пользовательском рабочем столе или новые conversion/deletion/cancel/filesystem гарантии. Source/native QWidget captures и синтетические события не равны такой сертификации. Бинарники, private evidence и чужие незакоммиченные plan/LOG bytes не публикуются в controls-коммите.

# Документация и сохранение

После этого ACCEPT та же принимающая роль сохранила оригиналы затронутых документов и завершила только controls verification, ближайшие RUNNING/REPORT/index и testing instruction. Проверка этой docs-only delta — авторская проверка принимающей роли, не ещё один независимый аудит. Candidate source/tests/assets остаются byte-identical; достаточные неизменённые checks не повторяются. Selective source-only commit/branch delivery проверяются полным path/blob binding и exact SHA/ref readback в итоговом receipt; это не merge/tag/release или доставка нового EXE.
