---
id: ic-windows-exe-verification
title: "Windows EXE — exact-byte квалификация и независимый ACCEPT"
kind: verification
status: accepted
created: "2026-10-23"
updated: "2026-10-23"
areas: [packaging, windows, pyside6, testing]
summary: "Независимый технический и визуальный ACCEPT exact one-file EXE: native reduced-rights запуск, реальные codec/readbacks, ресурсы и owned-process teardown."
code_ref: "83c209972b731805a8b3dd97e5aba7cae48dd8ad + frozen candidate manifest SHA-256 ededba56e3e7317f13a54a9677fefd2137fd9fdc3e81a3a9b6b281308f0e44ad"
verification_scope: "Независимый exact-byte Windows11 x64/local NTFS standalone-host ACCEPT; собственный reduced-rights Medium child, не свежий аккаунт/clean unrelated machine или release. Последующий docs/package closeout — авторская проверка принимающей роли."
---

# Текущий итог

**Независимый технический и визуальный ACCEPT** выдан именно EXE/SHA из таблицы ниже, без пересборки и source/test исправлений проверяющей ролью. Свежие независимые результаты приведены отдельным продолжением после сохранённой авторской стадии.

# Artifact и авторская стадия

На момент авторского freeze: **авторские gates выполнены; независимый EXE ACCEPT — NOT_PERFORMED**. Этот исторический статус закрыт последующим независимым решением ниже, не переписан как авторская приёмка. Прежний [GUI/source/wheel ACCEPT](REPORT.md) сохранён, не выдан за приёмку этого бинарника. [Oracle план](04-windows-exe-plan.md) неизменён. Использование/сборка — [WINDOWS_EXE](WINDOWS_EXE.md).

| Поле | Фактическое значение |
|---|---|
| Путь от корня проекта | `dist/windows-pyside6/20261023-candidate-02/ImageCompressorV2.exe` |
| Build-id / mode | `20261023-candidate-02` / **onefile**, PE32+ AMD64 GUI subsystem2 |
| Размер | **56 977 108 bytes** |
| SHA-256 | `09c4b2f1fc65655d624111537d693f0971fad75787f6c3045072d5863312bb53` |
| Host | Windows11 x64/local NTFS; CPython3.14.2; native Windows QPA; DPR1.5 |
| Runtime | PySide6/Qt6.12.0, Pillow13.0.0, pillow-heif1.8.1, pillow-avif-plugin1.6.0 |
| Freezer | PyInstaller6.18.0, hooks-contrib2026.0; 16 exact build/runtime pins |
| Поставка | Локальная/неподписанная; без installer, signing, binary publication или release |

Соседние BUILD-INFO/README/notices и private source/wheel/native/payload inventories зафиксированы вместе с artifact. Для проверок копировался **только EXE**, не Python/Qt/data directory. Сборка выполнена абсолютным script path **из другого пустого cwd**; runtime также не использовал source cwd. One-file не потребовал onedir fallback; такой recipe path не квалифицирован и не выдаётся за поставленный artifact.

# Обязательства и наблюдения

| Gate | Выполненный результат |
|---|---|
| Сохранность | Core, оба GUI, прежние tests, design, pyproject, legacy spec/bat, classes и PFK сверяются с preflight SHA inventory; Oracle plan остаётся исходным. Старые Qt environments не переустанавливались. |
| Изоляция сборки | Только новый build venv; pinned wheels сохранены с SHA, offline install/pip check — exit0. Official hooks, без UPX/strip/whole-site-packages. |
| Native closure | Верхнеуровневый `_pillow_heif` + все6 RECORD-owned wheel-root DLL; Pillow `_avif`/`_webp`, packaged pillow_avif fallback без его runtime активации. Python/VC runtime и qwindows присутствуют. |
| Ограниченный Qt | Windows/SVG plugins и dependency-checked native closure; нет QML/Quick/WebEngine/QtPdf/VirtualKeyboard, PyQt, FigCraft или bundled fonts. Точная DLL/module inventory сохранена. |
| Обычный запуск | `.exe` без аргументов → настоящее видимое `Image Compressor · PySide6 experiment`, класс Qt6120QWindowIcon, собственные HWND/PID; normal WM_CLOSE → raw exit0. |
| Ordinary user | Actual bootloader **и** Qt child: TokenIsElevated=False, integrity8192. Elevated harness безопасно создаёт только свой новый deprivileged Medium token; UAC/security/ACL не менялись, чужие tokens не использовались. |
| Standalone lookup | Новый Unicode/space EXE каталог, пустой cwd, Windows-only PATH, fresh TEMP/profile, без inherited Python/Qt/venv/`_PYI_*`. DLLs — из bundle/Windows; bundled DLL hashes сверены с exact frozen payload. |
| Настоящий GUI/API | Opt-in flag → один QApplication, существующий main/show/exec, controls/add_paths/Start, настоящие public API workers и immutable requests, delete_original=False. Нет mock converter/runpy/source injection. |
| Codec parity | JPEG/WebP/HEIF/AVIF доступны по real probes; каждый actual GUI Start создал читаемый 144×108 output из synthetic400×300 PNG. Внешний decoder независимо проверил5 опубликованных результатов, dimensions/format/digest/size и3 source hashes. |
| Provider order | AVIF provider **Pillow**, HEIF **pillow_heif**. Fallback packaged, но `pillow_avif` не импортирован во frozen runtime. Недоступных целевых encoders нет; unavailable-selector branch не объявляется выполненным negative case. |
| No-clobber / partial | Повтор WebP → OUTPUT_EXISTS, прежние bytes/hash сохранены; good+corrupt → partial,1 succeeded/1 failed/1 published, INVALID_IMAGE, исходники неизменны. |
| Ресурсы / визуал | Exact tokens/SVG hashes равны build inputs; реальный SVG rendering и Segoe UI/KK codepoints. Все6 RU/EN/KK × light/dark PNG просмотрены индивидуально, KK Dark900×640 logical; footer/safety читаемы, controls не потеряны, settings scroll намеренный. |
| Завершение | Во всех5 запусков selection: bootloader+child завершены, собственный Job Object пуст, `_MEI…` убран; timeout/forced cleanup отсутствуют. Success receipt только после настоящего event-loop exit. |
| Отказы entry | Unknown args, relative output и occupied root → raw exit2; без окна/fixtures, prior sentinel сохранён. Real Windows junction parent также отвергнут unit guard. |

# Авторские проверки

Полные argv/cwd/route/stdout/stderr/raw exits хранятся в ignored author evidence, не в Git. Сводка команд и полный obligation matrix — в авторском handoff; команды воспроизведения есть в guide.

| Selection | Итог |
|---|---|
| Новый `tests_windows_exe` | **22 passed, 0 skips**, exit0; финальный run дополнительно читает actual Medium integrity bootloader/child |
| `tests_pyside6_v2/test_entrypoint.py` + `test_window.py::test_engine_svg_is_valid_and_not_clipped` | **4 passed**, exit0, прежний PySide interpreter/отдельный процесс |
| `tests/test_packaging.py` после final README | **2 passed**, exit0, legacy interpreter; его штатный disposable no-Qt product/Pillow installation остаётся в собственном новом test root |
| Ruff Python + `.spec` новой области | exit0, `--extension spec:python` |
| Strict mypy3 новых typed helpers | exit0, build-venv dependency/stub context, `--follow-imports=silent`; без изменения типов продукта |
| Archive/provenance audit | exit0;180 CArchive entries/261 PYZ modules;18 module warnings классифицированы, unresolved native libraries нет |
| Документы / diff / окончательная сохранность | Docs checker:9 файлов,findings=[],exit0; `git diff --check`:exit0. Protected176 SHA совпали, runtime/build inputs равны текущим,16 Coder paths + исходный Oracle plan; cached diff пуст |

Полные прежние47/170 suites и FigCraft не повторялись без source drift — это исторические accepted guarantees, не новые frozen cases. Внешний packaging selector действительно собрал/установил текущий wheel; он не использовался вместо EXE проверки и не менял старые Qt environments.

# Первая ошибка и исправления

- RED отсутствующего recipe и explicit-artifact fixture сохранены; отсутствие `IC_FROZEN_EXE` не стало skip.
- Первый build остался в `20261023-candidate-01`: archive guard отверг ненужные QML/Quick DLL от default virtual-keyboard plugins. Исправлены только новый recipe/helper: allowed Windows/SVG plugins и PE import/delay-import reachability для удаления неиспользуемых Qt engine DLL. Final artifact — новый build-id, старый не перезаписан; core/GUI/codec assertions не ослаблялись.
- Host harness оказался elevated. Первые frozen tests правильно отказали до запуска приложения. Linked limited token недоступен (Win1312); ранний restricted-token helper не имел ADJUST_DEFAULT, затем CreateProcessWithTokenW отказал Win5. Только внешний test runner исправлен на собственный LUA restricted+Medium token/CreateProcessAsUserW. Actual parent/visible-child non-elevation и integrity теперь проверяются, а не предполагаются. Платформенная защита не отключалась.
- Ранние mypy/Ruff fixture/source-format failures сохранены; финальные typed helpers и новая Python/spec область проходят. Docs checker отдельно отверг новый неканонический kind=report; исправлен только паспорт нового verification, схема/PFK не менялись. Финальный checker:9 файлов без findings. Все failed/superseded evidence остаются на месте.

18 module warnings разобраны по каждому имени: POSIX/macOS/VMS/Jython-only modules; CPython frozen-importlib/collections.abc aliases; optional numpy/olefile/defusedxml, не используемые принятой raster policy; намеренно исключённые Pillow Qt/Tk adapters. `collections.abc` в CPython3.14 — alias `_collections_abc`; настоящий frozen entry импортирует его успешно. Это не blanket признание любого warning безопасным.

# Передача авторской стадии и граница

Автор передал замороженные source/tests/docs/EXE тому же отдельному независимому Reviewer для проверки exact SHA в fresh root и принятия либо file:line finding. Кандидат во время review не пересобирался и не исправлялся. Последующий ACCEPT и docs closeout/source-only branch delivery принадлежат принимающей роли; Coder не stage/commit/push.

Не выполнены: clean unrelated machine/VM или другой аккаунт, Windows10/ARM/другие OS/Python/FS/все DPI, физический Explorer double-click/OS-dialog/drop и screen-reader certification, signing/SmartScreen/release, crash cleanup/durability. Выполненный native no-argument запуск эквивалентен double-click entry без физической mouse automation. Frozen кейсы — RGB codec path, не повтор полной alpha/precision/cancel/race qualification. Удаление/overwrite/мгновенный kill codec не добавлены. Само наличие готового artifact и author PASS — не независимый ACCEPT.

# Независимая exact-byte приёмка

**Решение: ACCEPT — технический и визуальный. Обязательных product/source/test findings нет.** До первого producer сверены17 публичных путей,176 защищённых файлов, авторский manifest SHA выше и EXE56 977 108 bytes/SHA `09c4b2f1fc65655d624111537d693f0971fad75787f6c3045072d5863312bb53`; source snapshot и оригиналы evidence сохранены в отдельном reviewer root. После всех checks эти bytes и пустой index повторно подтверждены. Прежний source GUI/core/design ACCEPT переиспользован только для неизменённых гарантий, не для frozen доказательства.

| Обязанность | Свежий независимый результат |
|---|---|
| Packaging/security/entry contract | Прочитаны все5 recipe/helper inputs и оба tests; прямой GUI main, opt-in-only driver, fresh-root/reparse/argument guards, exclusive build roots, pinned/RECORD-owned native collection. Нет нового converter, произвольного исполнения, source injection или обхода image safety. |
| Submitted suite на explicit same SHA | **22 passed,0 skips,raw exit0**. Только EXE скопирован в Unicode/space каталог, cwd пустой/вне source, runtime lookup Windows-only, fresh TEMP/profile. Реальный заголовок/собственный HWND, distinct bootloader+Qt child, штатный no-argument WM_CLOSE/raw0; три invalid-argument/root случая raw2. |
| Реальные операции/внешнее чтение | Тот же `--packaging-check`: один QApplication/main/show/exec,6 реальных Start/API worker действий. JPEG/WebP/HEIF/AVIF144×108; внешний decoder независимо проверил digest/format/size пяти outputs и hashes трёх исходников. OUTPUT_EXISTS сохраняет прежние bytes; good+corrupt даёт partial1/1/1. AVIF=Pillow, HEIF=pillow_heif, fallback не активирован. |
| Archive/source/native closure | **Raw0**:180 CArchive entries/261 PYZ modules,58 native images,16 wheel hashes/версий и29 build inputs.18 actual frozen product/entry/driver code objects равны compile проверенных source bytes; неиспользуемые CLI-only inputs не требуются GUI. Exact tokens/SVG, все6 HEIF DLL равны RECORD/payload. PE import/delay-import closure разрешается bundle/Windows/API-set, unresolved0.18 module warnings разобраны по именам. |
| Native token/provenance/shutdown | Независимый outer watchdog не импортирует submitted supervisor; собственный Job назначен до resume, сохранены10 live EXE handles/creation times и QPA module paths. Все bootloader+child tokens **TokenIsElevated=False/RID8192**. Пять требуемых запусков unforced, normal tree exit, пустой Job и удалённый `_MEI`. Это собственный reduced-rights child elevated host, не свежий другой аккаунт/машина. |
| Timeout-supervisor control | После readiness настоящего Qt child намеренно не посылался close. Inner deadline правильно дал **failed/timed_out/forced cleanup**; внешний owner по удержанным обоим handles подтвердил exit124/termination и отсутствие оставшихся процессов. Собственный `_MEI` после forced death остался в evidence: это ожидаемый предел crash cleanup, не normal-close PASS. |
| Визуальная parity | Все6 **собственных текущих** ru/en/kk×light/dark PNG просмотрены individually, hashes уникальны. Windows QPA/DPR1.5/Segoe UI, actual KK glyphs, SVG, readable footer/safety. KK Dark900×640 logical сохраняет действия, form scroll намеренный; принятый дизайн не переоткрывался. |
| Адресная регрессия/static/docs | Отдельный preserved PySide/offscreen процесс: **4 passed**; legacy `tests/test_packaging.py`: **2 passed** в собственном disposable root; Ruff Python/spec и strict mypy3 helpers с build-venv dependency context — **exit0**. Explicit docs corpus9/findings[]/exit0. Полные47/170 и FigCraft не повторялись. |

Каждый запуск имел независимый конечный внешний watchdog и собственные temp/cache/output destinations. Старые среды, EXE, source/tests/spec/requirements оставались read-only. Принятые авторские raw failures сохранены. Два собственных audit-fixture отказа также сохранены: сравнение raw Windows CArchive separators с нормализованным inventory и ошибочное ожидание CLI `image_compressor.__main__` в GUI-only archive. Исправлен только private reviewer observer по фактическому составу; все18 требуемых code objects, полный member set и native hashes затем прошли. Это не product defects и не исправление кандидата.

NOT RUN остаётся ровно прежняя материальная граница: physical Explorer click/OS-dialog/drop/screen reader, unrelated clean VM/другой аккаунт, Windows10/ARM/другие OS/Python/FS/все DPI, signing/SmartScreen/installer/release; RGB frozen выборка не переименовывается в новую full alpha/precision/cancel/race qualification. Нет crash-durability/instant codec kill/deletion/overwrite гарантий. Бинарник не публиковался.

## Пост-ACCEPT документация и build identity

Исходный отчёт и независимый verdict сохранены до closeout. Меняются только разрешённые docs/instructions/guide/LOG; retained EXE не пересобирается. Его BUILD-INFO и frozen candidate manifest продолжают описывать исходный build snapshot, а не последующий docs-коммит. Все runtime source/data, recipe/spec/requirements inputs сохранены; единственное затронутое provenance input — более поздний README, не входящий в runtime payload EXE. Авторская проверка final-byte docs/package delta и selective source-only доставка отмечаются отдельно от этого независимого решения. Private evidence, binaries/dist/build/venvs/caches не входят в commit. Авторская final-byte проверка принимающей роли: `tests/test_packaging.py` после итогового README — **2 passed,raw0** (повтор того же subset, не новые уникальные cases); docs checker — **9 файлов/findings[]/raw0**. Полные исходные suites и frozen GUI не повторялись без drift. Для существующего remote ref проверены protected=false и пустые applicable rules; отсутствие настроенных CI checks не называется green CI. Exact source commit/remote readback фиксируются в итоговом receipt вне публичного payload.
