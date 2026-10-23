"""Small RU/EN/KK catalog. Stable API codes remain language-neutral, never raw exceptions."""

from __future__ import annotations

from PySide6.QtCore import QLocale

from image_compressor import ErrorCode

TEXT: dict[str, tuple[str, str, str]] = {
    "subtitle": (
        "Новые файлы. Исходники сохраняются.",
        "New files. Originals stay safe.",
        "Жаңа файлдар. Түпнұсқалар сақталады.",
    ),
    "add": ("Добавить файлы", "Add files", "Файлдарды қосу"),
    "folder": ("Выбрать папку", "Choose folder", "Қалтаны таңдау"),
    "queue": ("Очередь", "Queue", "Кезек"),
    "empty_title": (
        "Добавьте изображения",
        "Add images to begin",
        "Бастау үшін суреттерді қосыңыз",
    ),
    "drop": (
        "Перетащите файлы или папку сюда",
        "Drop files or a folder here",
        "Файлдарды не қалтаны осында сүйреңіз",
    ),
    "inputs": (
        "JPEG, PNG, WebP, HEIF, AVIF · PNG только вход",
        "JPEG, PNG, WebP, HEIF, AVIF · PNG input only",
        "JPEG, PNG, WebP, HEIF, AVIF · PNG тек кіріс",
    ),
    "settings": ("Параметры", "Settings", "Параметрлер"),
    "format": ("Выходной формат", "Output format", "Шығыс пішімі"),
    "quality": ("Качество", "Quality", "Сапа"),
    "resize": ("Уменьшить размер", "Resize to fit", "Өлшемін кішірейту"),
    "width": ("Максимальная ширина", "Maximum width", "Ең үлкен ені"),
    "height": ("Максимальная высота", "Maximum height", "Ең үлкен биіктігі"),
    "postfix": ("Постфикс", "Postfix", "Постфикс"),
    "postfix_help": (
        "Для совпадающих форматов. Занятые имена не перезаписываются.",
        "For matching formats. Existing names are never overwritten.",
        "Бірдей пішімдер үшін. Бар файлдар қайта жазылмайды.",
    ),
    "recursive": ("Включая подпапки", "Include subfolders", "Ішкі қалталарды қосу"),
    "recursive_help": (
        "Для следующего добавления папки; очередь не пересканируется.",
        "Applies to the next folder added; does not rescan the queue.",
        "Келесі қосылатын қалтаға қолданылады; кезек қайта қаралмайды.",
    ),
    "delete": (
        "Удалять оригиналы — недоступно",
        "Delete originals — unavailable",
        "Түпнұсқаларды жою — қолжетімсіз",
    ),
    "safe": (
        "Безопасный API всегда сохраняет исходники.",
        "The safe API always retains originals.",
        "Қауіпсіз API түпнұсқаларды әрқашан сақтайды.",
    ),
    "start": ("Начать", "Start", "Бастау"),
    "stop": ("Остановить", "Stop", "Тоқтату"),
    "clear": ("Очистить очередь", "Clear queue", "Кезекті тазарту"),
    "log": ("Журнал операции", "Operation log", "Әрекет журналы"),
    "details": ("Подробности", "Details", "Мәліметтер"),
    "name": ("Имя файла", "File name", "Файл атауы"),
    "suffix": ("Расш.", "Suffix", "Түрі"),
    "bytes": ("Размер", "Size", "Өлшем"),
    "status": ("Статус", "Status", "Күй"),
    "light": ("Светлая", "Light", "Ашық"),
    "dark": ("Тёмная", "Dark", "Қараңғы"),
    "theme": ("Тема", "Theme", "Тақырып"),
    "language": ("Язык", "Language", "Тіл"),
    "initializing": ("Проверяем кодеки…", "Checking codecs…", "Кодектер тексерілуде…"),
    "empty": ("Добавьте файлы для начала", "Add files to begin", "Бастау үшін файлдарды қосыңыз"),
    "ready": ("Готово к запуску", "Ready to start", "Бастауға дайын"),
    "discovering": (
        "Добавление: поиск файлов…",
        "Adding: discovering files…",
        "Қосу: файлдар ізделуде…",
    ),
    "converting": ("Обработка…", "Processing…", "Өңделуде…"),
    "stop_requested": (
        "Остановка запрошена; ожидаем кодек",
        "Stop requested; waiting for the codec",
        "Тоқтату сұралды; кодек күтілуде",
    ),
    "closing": (
        "Закрытие: ожидаем завершения операции",
        "Closing: waiting for the operation to finish",
        "Жабу: әрекеттің аяқталуы күтілуде",
    ),
    "waiting": ("Ожидает", "Ready", "Дайын"),
    "running": ("Обработка", "Processing", "Өңделуде"),
    "succeeded": ("Успешно", "Succeeded", "Сәтті"),
    "failed": ("Ошибка", "Failed", "Қате"),
    "cancelled": ("Остановлено", "Cancelled", "Тоқтатылды"),
    "partial": ("Частичный результат", "Partial result", "Ішінара нәтиже"),
    "rejected": ("Запрос отклонён", "Request rejected", "Сұрау қабылданбады"),
    "terminal": ("Операция завершена", "Operation finished", "Әрекет аяқталды"),
    "unverified": ("Опубликован, не проверен", "Published, unverified", "Жарияланды, тексерілмеді"),
    "selection_summary": (
        "Доступно: {available} · Ошибок добавления: {issues} · "
        "Повторов: {duplicates} · Пропущено: {ignored}",
        "Available: {available} · Selection issues: {issues} · "
        "Duplicates: {duplicates} · Ignored: {ignored}",
        "Қолжетімді: {available} · Қосу қатесі: {issues} · "
        "Қайталану: {duplicates} · Өткізілген: {ignored}",
    ),
    "subset": (
        "Будут обработаны только доступные файлы; ошибки добавления — в подробностях.",
        "Only available files will run; selection issues are in Details.",
        "Тек қолжетімді файлдар өңделеді; қосу қателері Мәліметтерде.",
    ),
    "counts": (
        "Успешно: {succeeded} · Ошибок: {failed} · "
        "Остановлено: {cancelled} · Опубликовано: {published}",
        "Succeeded: {succeeded} · Failed: {failed} · "
        "Cancelled: {cancelled} · Published: {published}",
        "Сәтті: {succeeded} · Қате: {failed} · Тоқтатылған: {cancelled} · Жарияланған: {published}",
    ),
    "progress": (
        "Завершено: {processed} / {total}",
        "Completed: {processed} / {total}",
        "Аяқталды: {processed} / {total}",
    ),
    "retained": (
        "Готовые файлы остаются. Исходники сохранены.",
        "Published files remain. Originals are retained.",
        "Жарияланған файлдар қалады. Түпнұсқалар сақталды.",
    ),
    "no_details": (
        "Результаты и ошибки появятся здесь. Пути показаны только локально.",
        "Results and issues will appear here. Paths are shown locally only.",
        "Нәтижелер мен қателер осында көрсетіледі. Жолдар тек жергілікті көрсетіледі.",
    ),
    "selection_issues": ("Ошибки добавления", "Selection issues", "Қосу қателері"),
    "warnings": ("Предупреждения", "Warnings", "Ескертулер"),
    "more": ("Других записей: {count}", "Additional entries: {count}", "Қосымша жазба: {count}"),
    "images_filter": (
        "Изображения (*.jpg *.jpeg *.png *.webp *.heic *.heif *.avif);;Все файлы (*)",
        "Images (*.jpg *.jpeg *.png *.webp *.heic *.heif *.avif);;All files (*)",
        "Суреттер (*.jpg *.jpeg *.png *.webp *.heic *.heif *.avif);;Барлық файлдар (*)",
    ),
    "unavailable": (
        "Кодек недоступен: {reason}",
        "Codec unavailable: {reason}",
        "Кодек қолжетімсіз: {reason}",
    ),
    "error": ("Ошибка: {code}", "Error: {code}", "Қате: {code}"),
    "output_exists": (
        "Имя результата уже занято; перезаписи нет.",
        "The output name already exists; no overwrite.",
        "Нәтиже атауы бар; қайта жазылмайды.",
    ),
    "input_conflict": (
        "Выход совпадает со входом; задайте другой постфикс.",
        "Output conflicts with input; choose another postfix.",
        "Шығыс кіріспен сәйкес келеді; басқа постфикс беріңіз.",
    ),
    "target_conflict": (
        "Несколько входов имеют одну цель. Ни один не перезаписан.",
        "Multiple inputs target the same name. None was overwritten.",
        "Бірнеше кірістің нысанасы бір. Ешқайсысы қайта жазылмады.",
    ),
    "invalid_image": (
        "Изображение повреждено или не читается.",
        "The image is invalid or unreadable.",
        "Сурет бүлінген немесе оқылмайды.",
    ),
    "published_unverified": (
        "Файл опубликован, но финальная проверка не пройдена. Проверьте результат перед повтором.",
        "A file was published but final verification failed. Inspect it before retrying.",
        "Файл жарияланды, бірақ соңғы тексеруден өтпеді. Қайталамас бұрын тексеріңіз.",
    ),
    "cleanup_failed": (
        "Остались временные данные; результат не является полным успехом.",
        "Temporary data remains; this is not full success.",
        "Уақытша деректер қалды; бұл толық сәттілік емес.",
    ),
    "observer_failed": (
        "Промежуточные обновления прерваны; ниже показан окончательный результат.",
        "Progress delivery stopped; the final result is shown below.",
        "Аралық жаңарту тоқтады; соңғы нәтиже төменде көрсетілген.",
    ),
    "internal_error": (
        "Внутренняя ошибка. Проверьте известные результаты перед повтором.",
        "Internal error. Inspect known outputs before retrying.",
        "Ішкі қате. Қайталамас бұрын белгілі нәтижелерді тексеріңіз.",
    ),
    "cancel_note": (
        "Остановка запрошена; уже опубликованные файлы не откатываются.",
        "Stop requested; already published files are not rolled back.",
        "Тоқтату сұралды; жарияланған файлдар кері қайтарылмайды.",
    ),
}
LANGUAGES = ("ru", "en", "kk")
CATALOG = {
    language: {key: values[i] for key, values in TEXT.items()}
    for i, language in enumerate(LANGUAGES)
}
ERROR_KEYS = {
    ErrorCode.OUTPUT_EXISTS: "output_exists",
    ErrorCode.INPUT_OUTPUT_CONFLICT: "input_conflict",
    ErrorCode.TARGET_CONFLICT: "target_conflict",
    ErrorCode.INVALID_IMAGE: "invalid_image",
    ErrorCode.PUBLISHED_UNVERIFIED: "published_unverified",
    ErrorCode.TEMP_CLEANUP_FAILED: "cleanup_failed",
    ErrorCode.OBSERVER_FAILED: "observer_failed",
    ErrorCode.INTERNAL_ERROR: "internal_error",
    ErrorCode.CANCELLED: "cancel_note",
    ErrorCode.DESTRUCTIVE_MODE_UNSUPPORTED: "safe",
}


class Translator:
    def __init__(self, language: str) -> None:
        self.language = language if language in CATALOG else "en"
        self.locale = QLocale({"ru": "ru_RU", "en": "en_US", "kk": "kk_KZ"}[self.language])

    def __call__(self, key: str, **values: object) -> str:
        return CATALOG[self.language].get(key, key).format(**values)

    def error(self, code: ErrorCode) -> str:
        prefix = self("error", code=code.value)
        key = ERROR_KEYS.get(code)
        return f"{prefix} — {self(key)}" if key else prefix

    def size(self, value: int | None) -> str:
        if value is None:
            return "—"
        if value < 1024:
            return self.locale.toString(value) + " B"
        unit, divisor = ("MiB", 1024**2) if value >= 1024**2 else ("KiB", 1024)
        return self.locale.toString(value / divisor, "f", 1) + " " + unit
