---
id: ic-windows-exe-plan
title: "Самостоятельный Windows EXE для принятого PySide6 GUI"
kind: plan
status: proposed
created: "2026-10-23"
updated: "2026-10-23"
areas: [packaging, windows, pyside6, testing]
summary: "Отдельная one-file сборка принятого GUI, изолированные зависимости и проверка настоящего frozen EXE без изменения ядра или дизайна."
code_ref: "83c209972b731805a8b3dd97e5aba7cae48dd8ad"
verification_scope: "Read-only source/tool-documentation investigation; EXE ещё не построен и не принят."
---

# Решение и граница

По новому прямому поручению собрать **Windows x64 one-file `ImageCompressorV2.exe`**, запускаемый двойным щелчком без установки Python/Qt/кодеков. Отдельный PyInstaller recipe; без installer, signing, auto-update, GitHub Release и публикации бинарника. Принятые [GUI/дизайн](REPORT.md) и [API](../architecture/application-api.md) не переоткрывать. Старые `gui/`, `gui_main.py`, `gui_compressor.spec`, `build_exe.bat`, ядро, `design/`, PFK и предыдущие outputs остаются неизменными. Новый EXE не заменяет default GUI.

Технической причины заранее выбирать onedir не найдено: PyInstaller поддерживает one-file/PySide6 и используемый importlib.resources. One-file распаковывает библиотеки во временный `_MEI…` каталог; это всё ещё один переносимый EXE, **не** исполнение вообще без временных файлов. Нужны обычные Windows system libraries/fonts и writable user TEMP, но не внешний Python/site-packages. Не запускать elevated, не отключать antivirus/SmartScreen. Холодный старт может быть медленнее Python-запуска. Размер/время заранее не обещать.

Если после конкретной исправимой packaging ошибки one-file остаётся непригодным, допускается **один** обоснованный onedir fallback тем же recipe: `ImageCompressorV2.exe` + обязательный `_internal` в portable ZIP, с теми же frozen checks. Не отдавать EXE из onedir отдельно и не называть это one-file. Нет третьего упаковщика или нового GUI; неразрешённый blocker вернуть как blocker, не как готовность.

# Что установлено по текущим исходникам

| Источник | Значение для упаковки |
|---|---|
| Git readback | Чистая `refactor/command-first`, HEAD `83c209972b731805a8b3dd97e5aba7cae48dd8ad`; прежний ACCEPT закрыт. |
| `gui_pyside6_v2/__main__.py:10–40` | Реальный `main(argv)` создаёт/переиспользует QApplication, Fusion, настоящий MainWindow/show/exec. Entry остаётся неизменным; frozen launcher вызывает его обычным импортом. Не замораживать `__main__.py` напрямую как standalone script с относительными imports. |
| `theme.py:14–23`, `tokens.json`, `localization.py` | `importlib.resources.files()` читает `tokens.json` и `assets/add.svg`; RU/EN/KK — Python catalog, не внешние `.qm`. Segoe UI — системный Windows font, не копировать шрифт. FigCraft/native/scripts для runtime не нужны. |
| `window.py:234–258,421–426`, `controller.py`, `workers.py` | `add_paths(tuple[Path])`, settings и Start уже ведут в настоящий public API/QThread; штатный close ждёт worker. Эти owners пригодны для узкого frozen qualification без новой реализации конвертера. |
| `image_compressor/imaging.py:59–104` | HEIF регистрируется лениво; рабочий Pillow AVIF предпочитается pillow_avif. Сборка обязана сохранить этот порядок, а не импортировать fallback plugin заранее в runtime hook. |
| `pyproject.toml:30–58` | Отдельные extras `gui-pyside6`, `codecs`, `build`; data уже объявлены для wheel. Это **не** PyInstaller-конфигурация: нижняя `[tool.pyinstaller]` и старый spec называют старый GUI. Новый packaging requirements уточняет версии, runtime manifest менять не требуется. |
| Старый spec/bat | Entry `gui_main.py`, PyQt6 hidden imports; bat удаляет `dist/ImageCompressorGUI.exe`. Не запускать/исправлять/переиспользовать этот route. BUILD_README/BUILD_QUICK описывают старую Python3.12/PyQt-сборку, не evidence нового EXE. |
| Изолированная принятая PySide среда, metadata-only | Python3.14.2 x64; PySide6/Addons/Essentials/shiboken6 **6.12.0**, Pillow **13.0.0**, pillow-heif **1.8.1**, pillow-avif-plugin **1.6.0**. PyQt6, PyInstaller, hooks-contrib в ней отсутствуют. |
| Legacy build tools, только чтение | PyInstaller **6.18.0**, hooks-contrib **2026.0** уже установлены в `.venv`, но использовать смешанную legacy среду для новой сборки нельзя. Metadata PyInstaller допускает Python3.8–3.14, PySide6 metadata — Python>=3.10,<3.16. Это совместимость заявленного диапазона, не frozen PASS Qt6.12. |

**Важный native edge:** установленный pillow-heif1.8.1 содержит **верхнеуровневый** `_pillow_heif.cp314-win_amd64.pyd` и шесть DLL рядом с пакетом: libheif/libde265/libx265/libgcc_s_seh/libstdc++/libwinpthread (имена с wheel hashes). Его `__init__.py` добавляет родительский каталог в DLL search. Старый hidden import `pillow_heif._pillow_heif` неверен для этого wheel. В прочитанных installed freezer hooks отдельного heif/avif hook нет; одного `collect_dynamic_libs('pillow_heif')`, просматривающего лишь package directory, недостаточно.

Из installed PyInstaller подтверждены: `hook-PySide6.py` enforce single binding + shiboken; QtGui/QtSvg/QtWidgets hooks собирают Qt-зависимости, platforms/imageformats/iconengines/styles; `pyi_rth_pyside6.py` направляет Qt к bundle plugins; `hook-PIL.Image.py` собирает Pillow ImagePlugin modules; `PyiFrozenResourceReader` поддерживает filesystem package data. Установка/импорты продукта/probes/build Oracle не выполнялись.

# Конечный scope Coder

Ниже — **новые предлагаемые файлы**, не уже реализованные команды. Один Coder владеет всей packaging delta.

| Owner | Изменение |
|---|---|
| `tools/windows_exe/requirements-win64.txt` | Pinned build/runtime closure для CPython3.14.2 Windows x64; не requirements-freeze всего рабочего venv. |
| `tools/windows_exe/ImageCompressorV2.spec` | Отдельный entry/data/native collection, one-file/windowed, no UPX/strip, optimize=0, без legacy imports. |
| `tools/windows_exe/frozen_entry.py` | Тонкий entry: без аргументов → существующий `gui_pyside6_v2.__main__.main`; только один opt-in qualification flag ниже; безопасный fixed startup error без traceback/личных путей. |
| `tools/windows_exe/ic_frozen_check.py` | Маленький synthetic-only driver **в том же EXE**: Qt timer → существующее окно/actions/controller, результаты/screens/receipt. Не импортирует tests/gallery, не меняет core/window, не имеет произвольного script/config/command execution. |
| `tools/windows_exe/build.py` | stdlib wrapper: проверка Windows/x64/version/dependencies/no-PyQt, fresh work/cache/dist dirs, вызов `python -m PyInstaller` по spec, hash/inventory/receipt. Не устанавливает пакеты автоматически и не удаляет старые outputs. |
| `tests_windows_exe/test_recipe.py`, `test_frozen.py` | Packaging assertions и внешний runner exact EXE; collection без Qt, процесс приложения отдельный. Новая suite не попадает в старый `tests/`. |
| `docs/figcraft_gui_experiment/WINDOWS_EXE.md`, `05-windows-exe-verification.md` | Пользовательский double-click/build recipe, фактические artifact/hash/capabilities/commands/limits; независимый verdict отдельно от авторского результата. |
| `AGENTS.md`, `docs/instructions/{development,testing}.md`, `README.md`, `docs/README.md`, `RUNNING.md`, `LOG.md` | Только актуальный scope/ссылки/команды/запись нового follow-up. Не переписывать прошлый REPORT/Oracle plans и прежние NOT RUN как будто EXE проверялся тогда. |

Окружение: **новое** `.agent-work/windows-exe/build-venv`; обе прежние Qt среды остаются неизменными. Requirements закрепляет runtime версии из таблицы и PyInstaller6.18.0/hooks-contrib2026.0; известные compatible build dependencies: altgraph0.17.5, packaging26.0, pefile2024.8.26, pywin32-ctypes0.2.3, setuptools80.10.2. Проверить resolved closure/pip check, сохранить hashes использованных wheels. Если требуется узкое обновление freezer/hook из-за воспроизводимой несовместимости — только здесь, с новой фиксацией версий и повтором frozen checks; не менять Python/Qt/accepted source без причины. Reproducible recipe/input inventory — не обещание bit-for-bit deterministic EXE.

## Состав spec и размещение

- Runtime imports только `gui_pyside6_v2`, `image_compressor`, Pillow, PySide6 Core/Gui/Widgets/Svg, shiboken, optional providers и их реальные зависимости. Использовать official hooks, не `collect_all(PySide6)` и не перенос всего site-packages. Не добавлять QtWebEngine/QML, PyQt, PIL.ImageQt/Tk или development/test runtime.
- `datas`: ровно package-relative `gui_pyside6_v2/tokens.json`, `gui_pyside6_v2/assets/add.svg` и применимые dependency licenses/notices. Оставить `importlib.resources` код неизменным. Executable icon может быть штатным PyInstaller: новый дизайн/`.ico` не нужен.
- HEIF: явный hidden import `_pillow_heif` + provider; DLL получить по **списку файлов соответствующей distribution**, не glob всех DLL среды, проверить принадлежность этому wheel, разместить в bundle root рядом с native extension. Включить `_avif`/`_webp` и Pillow plugins через analysis/hooks; pillow_avif fallback тоже собрать, не активируя заранее. Проверить DLL dependency closure, unresolved warnings классифицировать, не назвать все warnings безопасными.
- Проверить наличие `platforms/qwindows.dll`, QtSvg и нужных Qt DLL/plugins, bundled Python/VC runtime; не требовать отдельной установки redistributable пользователем. Не писать постоянные QT/PATH settings или custom Qt bootstrap поверх official runtime hook.
- One-file `EXE(..., console=False, upx=False, strip=False, optimize=0, runtime_tmpdir=None, disable_windowed_traceback=True)` с обычным текущим PYZ recipe. Не копировать obsolete параметры старого spec. В windowed процессе stdout/stderr могут быть None: нормальный старт и failure reporting не должны зависеть от print/flush. Fixed Windows message box при startup failure допустим, без raw exception, persistent log или telemetry.
- User-facing output: **`dist/windows-pyside6/<build-id>/ImageCompressorV2.exe`**. Рядом `BUILD-INFO.json`, краткий README и notices; они не требуются для запуска one-file. Это durable локальный результат, не только scratch. Existing `.gitignore` уже исключает dist/build; никаких binary commits/uploads.
- Work/cache: `.agent-work/windows-exe/builds/<build-id>/`; manifest записывает source hashes/base+delta, interpreter/dependency versions, exact argv, inputs/wheel hashes, EXE size/SHA и mode. `<build-id>`/все output roots создаются exclusively; повтор в занятое имя отказывает, не чистит его. Не использовать старый `build/` или EXE filename, общий `--clean` cache, массовый copy/glob проекта.

# Проверка именно frozen артефакта

## Один ограниченный встроенный qualification mode

Выбран **`ImageCompressorV2.exe --packaging-check <ABSOLUTE_NEW_OUTPUT_DIR>`**. Он нужен потому, что существующий `tests_pyside6_v2/installed_probe.py` запускается Python/runpy и проверяет site-packages: это wheel evidence, не frozen EXE. Не расширять пользовательский CLI и не добавлять тестовый backend.

Flag реализуется только в packaging entry; без flag не создаёт fixtures/reports и не импортирует/запускает driver. Единственная разрешённая форма arguments; invalid args → ненулевой exit без writes. Output dir должен отсутствовать, иметь безопасный существующий parent, не совпадать с bundle/EXE dir и не идти через reparse/symlink; создаётся как новый owned root. Никаких входных пользовательских изображений, сетевых calls, произвольных форматов JSON requests, запуска script или cleanup чужих каталогов.

Driver использует **один QApplication**, QTimer и настоящий `main([sys.executable])`/его event loop. После появления настоящего MainWindow ждёт завершения capabilities; устанавливает реальные controls, вызывает `add_paths`, затем **нажимает Start**. Использует уже имеющиеся signals/state/result, без monkeypatch API/Pillow и без второго converter. Deadline и исключения дают safe failed receipt/nonzero exit; success receipt только после actual result/readback и штатного окончания event loop. Нельзя повторять старый fixture-дефект с двумя QApplication. Можно взять идею phase machine из installed_probe, но не его source/site-packages assertions, runpy-запуск или sys.path injection.

## Обязательная конечная выборка

1. **No-argument cold launch:** скопировать только final EXE в свежий каталог с пробелами/Unicode внутри собственного evidence root; cwd — отдельный пустой каталог, не source cwd. Child environment allowlist: Windows essentials + fresh TEMP/TMP + PATH только Windows system dirs; убрать Python/PYTHONPATH/PYTHONHOME/PYTHONUSERBASE/venv/conda, inherited Qt/plugin/QML и `_PYI_*` влияния. Для native прогона Windows QPA, не offscreen. Запустить именно `.exe`, без shell/Python launcher, ordinary user. Видимое настоящее новое окно/заголовок и нормальное закрытие; никаких runtime packages рядом. Зафиксировать собственный HWND/PID/наблюдение, не снимать чужие окна.
2. **Тот же SHA, cold qualification launch:** `--packaging-check` в такой же изоляции. Внутри подтвердить `sys.frozen`, executable identity, module/data/native paths из bundle, отсутствие PyQt; tokens/SVG hashes равны candidate inputs. Сохранить Windows-QPA/DPR/font и просмотреть компактный набор **6 кадров RU/EN/KK × Light/Dark**, с одним minimum900×640; SVG виден, KK glyphs и safety explanation читаются. Не повторять FigCraft и всю state-gallery.
3. **Фактические кодеки:** сохранить настоящие capabilities/provider/reason. Целевой bundle сохраняет JPEG/WebP/HEIF/AVIF принятой среды: для каждого доступного encoder реальный GUI Start → synthetic400×300 PNG → output144×108 → load/format/dimensions/hash/source retention; HEIF/AVIF не считать пройденными по package/import presence. Для заявленного available, но неработающего кодека — FAIL. Не скрывать unavailable optional codec: записать reason, проверить disabled selector и сначала исправить native collection. Если parity добиться не удалось — конкретная незакрытая граница, не молчаливое урезание поставки. Alpha capability не равна проверке всех image modes; неизменённая image policy сохраняет прежнюю qualification.
4. **Безопасный исход:** повтор WebP → OUTPUT_EXISTS с прежними bytes; good+corrupt synthetic batch → partial, source bytes сохраняются. Проверка не должна переписывать исходник/сбрасывать коллизию ради green. Внешний runner самостоятельно повторно открывает outputs и сверяет bytes/hash (его тестовый Python не предоставляется EXE как runtime).
5. **Shutdown:** qualification и no-argument окно закрываются штатно после завершения workers, parent bootloader и child уходят, собственная `_MEI…` extraction штатно убрана. У каждого subprocess finite timeout; timeout cleanup касается только созданного PID/tree и означает FAIL, не успешный close. Нельзя kill-by-image-name или остановку чужих процессов. Прежние source cancel/close/race tests переиспользуются только как source guarantees; не выдавать их за выполненные frozen cases.

Outer runner хранит exact EXE SHA, argv/cwd/sanitized environment policy (не env dump), raw exits, own process IDs, capabilities, fixtures/output hashes, PNG manifest, first failure и outcome. Для one-file учитывать parent+child, не объявлять exit одного процесса всей проверкой. Reviewer независимо запускает **тот же frozen SHA** в своём fresh root; авторский receipt не его ACCEPT. Не пересобирать и не редактировать candidate во время review.

**Предел доказательства:** это standalone-host check на Windows11 x64/local NTFS с внешним Python исключённым из runtime lookup, не чистая unrelated machine/VM, не Windows10/ARM/другая ОС/все DPI, не installer/signing/SmartScreen/release qualification. System Segoe UI/Windows DLL допустимы; незаявленный внешний codec/Qt/Python DLL — нет. One-file не добавляет гарантии crash durability, мгновенного cancel или удаления исходников.

# Исполняемая последовательность и gates

1. Coder читает этот план, проверяет scope/base и вносит только названную packaging delta. Создаёт recipe/entry/driver/tests/docs и fresh build venv. No Git writes. Зависимости только из объявленного project-local recipe, не shared venv.
2. Выполняет commands ниже (они **предложены, ещё не исполнены Oracle**), первый build и bounded frozen cases. На missing-resource/DLL failure исправляет spec/helper, не GUI/core. Каждый новый artifact получает новый build-id. При невозможности закончить — точная ошибка/остаток, а не новое общее исследование.
3. Targeted regression: новая `tests_windows_exe/`; existing `tests_pyside6_v2/test_entrypoint.py` и `test_window.py::test_engine_svg_is_valid_and_not_clipped` в прежнем PySide interpreter, отдельно `tests/test_packaging.py` в legacy interpreter после final README bytes. Ruff новой Python/spec области; mypy новых typed helpers (build-time PyInstaller API stub exception точечно, не blanket ignore продукта). Existing docs checker по explicit affected corpus. Не повторять 47/170 полные suites или design qualification без source regression.
4. Freeze manifest/EXE/source/tests/docs → один независимый Sol Reviewer → findings тому же Coder → affected recheck. После ACCEPT тот же Reviewer завершает docs/selective **source-only** commit и branch push существующего origin на `refs/heads/refactor/command-first`; binaries/private evidence исключены. Финальный ответ пользователю содержит **точный локальный путь EXE**, SHA, как запустить и существенные ограничения.

Пример будущего воспроизводимого build command, PowerShell из корня; build recipe обязан работать и с absolute paths/иным cwd, не зашивать каталог разработчика:

```powershell
$EnvDir = '.agent-work\windows-exe\build-venv'
# Только если каталога ещё нет; существующую среду не пересоздавать:
& .\.venv\Scripts\python.exe -I -B -m venv $EnvDir
$Python = (Resolve-Path "$EnvDir\Scripts\python.exe").Path
$env:PIP_CACHE_DIR = Join-Path (Get-Location) '.agent-work\windows-exe\pip-cache'
& $Python -I -B -m pip install --only-binary=:all: -r tools\windows_exe\requirements-win64.txt
& $Python -I -B -m pip check
$BuildId = Get-Date -Format 'yyyyMMdd-HHmmss'
& $Python -I -B tools\windows_exe\build.py --build-id $BuildId
# build.py: python -m PyInstaller <absolute-new-spec> --workpath <fresh-own-work> --distpath <fresh-output>
# Внутри wrapper — process-local PYINSTALLER_CONFIG_DIR/TEMP/TMP, без legacy --clean.
```

`test_frozen.py` получает **обязательный явный** artifact path через `IC_FROZEN_EXE` (не glob первого старого EXE); fixture fail, а не skip, если он отсутствует. Runner сам формирует чистое child environment:

```powershell
$env:IC_FROZEN_EXE = (Resolve-Path "dist\windows-pyside6\$BuildId\ImageCompressorV2.exe").Path
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
# Назначить fresh own TEMP/TMP/caches/basetemp до collection.
& .\.venv\Scripts\python.exe -B -m pytest -p pytest_timeout -p no:cacheprovider tests_windows_exe -q
```

Tests могут использовать существующие project-local tooling среды; они **не** bundled dependencies. Build/install и frozen probes имеют собственные конечные timeouts, actual logs/counts, без фиктивных PASS. User build instructions объясняют, что Python требуется **сборщику**, не пользователю готового EXE.

**Stop condition:** существует final local standalone artifact, обычный запуск и frozen GUI conversion/readback реально проверены, ресурсы/кодеки/teardown квалифицированы, независимый Reviewer принял exact bytes, инструкция/verification и разрешённое source сохранение завершены. Затем остановиться. План не является implementation или ACCEPT; дополнительных FigCraft, пользовательского approval или Oracle-acceptance gates нет.
