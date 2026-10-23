# UV в Image Compressor

Используйте уже доступный `uv`, не меняя глобальную среду ради этого проекта. Команды для PowerShell из корня, окружение — **`.venv`**, не `venv`.

```powershell
uv venv .venv
# Bare headless: Pillow, без Qt
uv pip install --python .venv/Scripts/python.exe .
.\.venv\Scripts\image-compressor.exe capabilities
.\.venv\Scripts\image-compressor.exe convert sample.png --format WEBP
# Optional providers и существующий GUI
uv pip install --python .venv/Scripts/python.exe ".[gui,codecs]"
.\.venv\Scripts\python.exe gui_main.py
# Разработка/проверки
uv pip install --python .venv/Scripts/python.exe -e ".[dev,gui,codecs]"
```

Extras: `codecs` = pillow-heif/pillow-avif-plugin, `gui` = PyQt6, `build` = PyInstaller, `dev` = pytest/timeout/Black/Ruff/mypy/build tooling. Рабочий встроенный Pillow AVIF используется без переопределения optional plugin. `capabilities` проверяет actual synthetic encode/decode, не только import.

`requirements.txt` ссылается на `.[gui,codecs,build]` — полный legacy install, **не минимальный runtime**. Версии зависимостей принадлежат pyproject. Старый `requirements_freeze.txt` — исторический snapshot, не актуальный lock и не гарантия воспроизводимости; не регенерируйте его как доказательство этой поставки. `uv pip install` не означает автоматического lock всей среды.

Если `.venv` создан без pip, `uv pip ... --python ...` работает без установки global pip. Для installed-wheel suite требуется project-local pip; при необходимости установите его только сюда: `uv pip install --python .venv/Scripts/python.exe pip`. Не используйте глобальный pip другой версии Python.

## Проверки

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m ruff check image_compressor classes.py gui/__init__.py gui/worker.py gui/utils.py gui/main_window.py tests
.\.venv\Scripts\python.exe -m mypy image_compressor classes.py
```

Runner ограничен `tests/`, не устаревшим root `test_gui.py`. Packaging test строит wheel из точной копии build inputs в disposable root, не трогает исторические `build/`/`dist/`; устанавливает wheel/Pillow в собственный venv без Qt и запускает console script вне repo. Прежний Pillow wheelhouse читается только как dependency cache: wheel копируется в новый test root; при отсутствии разрешён registry download туда же. Product wheels, venvs, temp/cache и logs создаются только в root текущего запуска; прежние wheels/evidence не перезаписываются. Все subprocess имеют конечные timeout/cleanup.

Авторские фактические selections/raw exits/версии, plugin isolation и docs checker — [testing](docs/instructions/testing.md), [verification](docs/verification/command-first-refactoring.md). Доступность команды не равна её выполнению. Сборка EXE по старому spec — отдельная непроверенная этой работой граница; `build` extra не означает новый релиз.

## Семантика

Входы: JPEG, PNG, WebP, HEIF/HEIC, AVIF. **Выходы: JPEG, WebP, HEIF, AVIF; PNG только вход.** Directory default non-recursive, для подпапок `--recursive`. Только новые проверенные файлы, без overwrite/удаления; checkbox удаления даёт явный отказ. Прозрачность/metadata/имена/partial/cancel/retry — [README](README.md) и [контракт](docs/architecture/application-api.md). Нет обещания мгновенного stop, многопроцессорности или обязательного уменьшения bytes.
