---
id: ic-testing-instruction
title: "Image Compressor — тестирование"
kind: instruction
status: accepted
created: "2026-10-23"
updated: "2026-10-23"
areas: [testing, quality]
summary: "Изолированные изображения, проверка настоящего API/CLI, сохранности и честный учёт фактически выполненных команд."
read_when: "Перед написанием/запуском теста, изменением runner/fixture или выбором проверки."
---

# Порядок тестирования

Основания — [стратегия](../foundation/testing-strategy.md), [архитектурные принципы](../foundation/architecture-principles.md), [качество PFK](../../tools/project-foundation/references/quality.md). Автор проверяет свой срез; один независимый Reviewer принимает замороженный результат. Проверки не дают разрешения на личные файлы, внешние сервисы и публикацию.

1. Назвать проверяемый исход, важный отказ, владельца и потребителя. Выбрать тест, способный отличить правильное поведение от конкретной ошибки; не проверять только `save.called`.
2. **До** collection/import проверить pyproject, плагины/ранние эффекты и назначить собственные временные корни. Использовать синтетические Pillow-изображения и `tmp_path`/`TemporaryDirectory`. Не сканировать личные изображения и не читать `.env`, credentials, рабочие БД/логи. Для subprocess указать cwd, таймаут, окружение и cleanup; не оставлять открытые окна/потоки.
3. Проверить прямой API без Qt/терминального ввода и нужный адаптер. Для CLI запустить настоящий разбор аргументов, прочитать serialized stdout/stderr и raw exit; повторно открыть созданное изображение и проверить его содержательные свойства. Реальный кодек нельзя заменить фиктивным ответом в тесте, заявленном как интеграционный.
4. Для файловых эффектов проверить исходные байты, коллизию/совпадение пути, сохранность прежнего результата при сбое, очистку своих временных файлов. Политику удаления проверять на отдельно созданных копиях и только в явно разрешённом контрактом режиме. Для batch — успешный, ошибочный и частичный исходы; отмена проверяется по заявленной силе, а не по одному выставленному флагу.
5. Начать с affected случая/модуля, затем выполнить достаточный общий набор для рефакторинга единого пути. Допустимы подмены сбоя записи, callback/отмены и недоступности кодека, но не самого проверяемого Application API. Отдельно указать доступные/недоступные форматы.
6. Выполнить статические проверки новой/затронутой области: lint, типы и отсутствие запретных зависимостей ядра. Не расползаться в полную переработку старых виджетов ради общего lint, но новая/изменённая граница должна пройти свои gates. Точный scope и команда фиксируются в результате.
7. Сохранить selection/command, raw exit, среду/версию, реальные компоненты и подмены, skips/NOT RUN и наблюдение. Первая ошибка не исчезает из истории после PASS. Ошибка окружения, теста и продукта различаются. После правки контракта/fixture повторить affected проверки; достаточные неизменённые результаты переиспользовать.

## Фактическая исходная среда и команды

На базе `7707849`, проверено при подготовке 2026-10-23:

| Команда/средство | Установленный факт |
|---|---|
| `.venv/Scripts/python.exe --version` | выполнено: Python 3.14.2 |
| Pillow, pillow_heif, pillow_avif, PyQt6 в `.venv` | модули найдены; это не проверка преобразования |
| pytest, Ruff, mypy в `.venv` | отсутствуют; автоматические проверки ещё не выполнены |
| `test_gui.py` | ручной устаревший launcher; не запускать как автоматизированный suite |
| Существующие `pyproject.toml` dev extras | pytest, Black, Ruff заявлены; наличие не доказано установкой |

Разработчик может установить необходимые инструменты только в окружение этого проекта, добавив используемые dev-зависимости в manifest. Не использовать несогласованные глобальные `pip`/Python и не менять глобальную среду.

## Реализованный кандидат: действительные команды

Baseline выше сохранён как исторический факт. Объявленные dev/extras и pip установлены только в `.venv` проекта; повторная установка для ремонта image policy не потребовалась. Setuptools/wheel/build входят в dev для настоящей проверки поставки; runtime по-прежнему только Pillow.

Проверяемые selections (Git Bash в корне проекта):

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/Scripts/python.exe -B -m pytest -p pytest_timeout -p no:cacheprovider tests -q
.venv/Scripts/python.exe -B -m ruff check image_compressor classes.py gui/__init__.py gui/worker.py gui/utils.py gui/main_window.py tests
.venv/Scripts/python.exe -B -m mypy image_compressor classes.py
```

До запуска назначить собственные TEMP/TMP/TMPDIR, tool caches и pytest basetemp; не переиспользовать чужой root/evidence. Точные локальные argv/overrides/raw exits сохраняются у выполняющего, без машинных private locators в публичных docs. Runner выбирает только tests/, third-party autoload отключён, pytest-timeout загружается явно. Каждый тест имеет finite timeout (90 s, packaging 240 s), subprocess — собственный конечный timeout/cleanup. Только synthetic изображения, прочие данные проекта не сканируются. Реальные components/fault seams, актуальные результаты/версии и первая ошибка — в [verification](../verification/command-first-refactoring.md). Не считать отдельный ранний зелёный запуск финальным после изменения его owners.

`tests/test_packaging.py` собирает wheel настоящим pip/setuptools из точной разрешённой копии build inputs в disposable test root, не изменяет старые корневые build/dist. Устанавливает его и Pillow wheel в отдельный venv без Qt/codecs, запускает console script и facade вне source cwd без PYTHONPATH. Все создаваемые wheel/venv/log/temp/cache остаются внутри собственного disposable root этого запуска. Прежний dependency wheelhouse используется только read-only: Pillow wheel копируется в новый root (если отсутствует — разрешённый registry download туда же для isolated dependencies, не live product service). Прежние product wheels и evidence не перезаписываются. Установленный путь проверяется, editable-only smoke не заменяет тест.

Структурная проверка документов — полный [checker](../../tools/project-foundation/tools/README.md), project-local isolated docs environment с PyYAML **6.0.3**, без доступа к среде соседнего source-проекта. Существующую согласованную local tooling-среду можно использовать read-only, не устанавливая PyYAML в runtime приложения. Запускать tooling Python с `-I -B`, `--project` с корнем репозитория и `--corpus` со своим explicit JSON. Corpus — конкретные authoring/native Markdown owners, не весь диск/pack. QUICK_GUIDE.txt проверяется содержательно, не поддерживаемым checker-ом форматом. Структурный PASS не доказывает runtime или независимое принятие.

## Диагностика и достаточность

По [правилам логирования](logging.md) проверять одновременно полезный непустой вывод и отсутствие запрещённого синтетического содержимого. Если добавлен файловый handler — flush и readback байтов обязательны; один `caplog` недостаточен.

Exit0 с пропуском обязательного случая его не подтверждает. Написано, static, выполнено, отменено и принято отмечаются раздельно. Срез закончен, когда критерии реально наблюдаются и независимый Reviewer подтвердил достаточность; ограничения Windows/кодеков/совместимости называются точно. Историческая command-first-проверка не квалифицировала новый GUI. В отдельно принятом [FigCraft → PySide6 эксперименте](../figcraft_gui_experiment/REPORT.md) Reviewer выполнил 47 новых и 170 прежних тестов без skips, официальный native reopen/export, просмотр текущих individual design/Qt PNG, synthetic Windows-native smoke и installed-wheel запуск. Это ограниченная проверка Windows/local NTFS/Python3.14.2, не qualification всех DPI/платформ/OS-dialog/drop. При изменении этой границы сохранять отдельные `tests_pyside6_v2/`, актуальные PNG и native/installed proof; при docs-only closeout повторять лишь затронутую проверку документов/упаковки. Новый suite — только в отдельной project-local PySide среде; старый `tests/` — в сохранённой PyQt среде, никогда не collect/import оба binding в одном процессе. MCP и EXE не квалифицировались тем source/wheel ACCEPT.

## Отдельный Windows EXE follow-up

Новый [план](../figcraft_gui_experiment/04-windows-exe-plan.md) разрешает реальную сборку и frozen checks, не изменение принятого GUI. Новая `tests_windows_exe/` collect-ится без Qt; сам EXE — отдельный native Windows процесс. Нужен explicit `IC_FROZEN_EXE`, не glob старого artifact и не skip при его отсутствии. До import/collection назначить own temp/cache/output roots; subprocess child получает Windows-only runtime lookup без Python/venv/Qt env. Normal no-argument launch и узкий `--packaging-check` проверяются на одном SHA; external runner независимо читает outputs и учитывает bootloader+child/свою extraction cleanup. Timeout означает FAIL, аварийная очистка только собственного PID tree.

Новые pinned build/runtime dependencies ставятся только в `.agent-work/windows-exe/build-venv`, не в `.venv` и не в предыдущую PySide среду. Старый build_exe.bat не запускать. Каждый build/output root fresh/exclusive. Повторять только новые packaging gates и selectors из плана: прежние47/170 остаются source evidence, а не frozen proof. Штатный `tests/test_packaging.py` проверяет product/Pillow installation только в собственном disposable no-Qt fixture venv, не устанавливает tooling в старые среды.

Работающие recipe/команды — [WINDOWS_EXE](../figcraft_gui_experiment/WINDOWS_EXE.md), авторские и независимые exact-byte результаты/пределы — [EXE verification](../figcraft_gui_experiment/05-windows-exe-verification.md). `ruff check --extension spec:python tools/windows_exe tests_windows_exe`; strict mypy — три `.py` helper из `tools/windows_exe`, `--python-executable .agent-work/windows-exe/build-venv/Scripts/python.exe --follow-imports=silent`. При elevated harness проверяется не его привилегия как будто это приложение, а actual suspended bootloader и видимый Qt child: TokenIsElevated=False/Medium8192. Допустим только собственный ограниченный token; нельзя брать foreign process token, отключать UAC/ACL/security или снимать gate. Для нового process-supervision harness нужен отдельный внешний watchdog с live native identities/handles: его собственный release flag не доказывает teardown. Успешные normal launches отделять от ожидаемого timeout-control; принудительный kill не является normal-close PASS и может оставить собственный `_MEI`.

Независимая проверка принятого SHA:22 новых теста,4 прежних PySide selector и2 legacy packaging selector — exit0, без skips; Ruff и strict mypy3 helpers — exit0. Шесть текущих frozen PNG просмотрены отдельно, ресурсы/кодеки и bootloader+child/readbacks/штатный extraction teardown подтверждены на Windows11 x64/local NTFS. Прежние47/170 не запускались заново и остаются исходной source-границей. При последующем docs closeout повторять только affected final-byte package/docs check, не неизменённую EXE-галерею или весь baseline.
