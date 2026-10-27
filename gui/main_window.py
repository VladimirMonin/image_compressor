"""
Главное окно GUI компрессора изображений.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from image_compressor import ErrorCode, discover_inputs
from image_compressor.diagnostics import project

from .styles import BUTTON_STYLES, LOG_TEXT_STYLE, PROGRESS_BAR_STYLE, TITLE_STYLE
from .widgets import (
    DropZone,
    FileOptionsWidget,
    FormatWidget,
    QualityWidget,
    ResizeDimensionsWidget,
)
from .worker import DESTRUCTIVE_MODE_MESSAGE, CompressionWorker


class ImageCompressorGUI(QMainWindow):
    """Главное окно GUI компрессора изображений."""

    def __init__(self):
        super().__init__()
        self.files_to_process = []
        self.worker = None
        self._pending_result = None
        self.last_result = None
        self._close_pending = False
        self._queue_generation = 0
        self.init_ui()

    def init_ui(self):
        """Инициализация пользовательского интерфейса."""
        self.setWindowTitle("🖼️ Компрессор изображений")
        self.setMinimumSize(600, 700)
        self.resize(800, 700)

        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Заголовок
        title = QLabel("🖼️ Компрессор изображений")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(TITLE_STYLE)
        main_layout.addWidget(title)

        # Зона drag & drop
        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self.handle_dropped_files)
        main_layout.addWidget(self.drop_zone)

        # Настройки сжатия
        settings_group = QGroupBox("⚙️ Настройки сжатия")
        settings_layout = QVBoxLayout(settings_group)

        # Качество сжатия
        self.quality_widget = QualityWidget(initial_value=80)
        settings_layout.addWidget(self.quality_widget)

        # Выбор формата
        self.format_widget = FormatWidget(default_format="WEBP")
        settings_layout.addWidget(self.format_widget)

        # Настройки размеров изображений
        self.resize_widget = ResizeDimensionsWidget()
        settings_layout.addWidget(self.resize_widget)

        # Настройки обработки файлов
        file_options_group = QGroupBox("📁 Настройки обработки файлов")
        file_options_layout = QVBoxLayout(file_options_group)

        self.file_options_widget = FileOptionsWidget()
        self.file_options_widget.show()  # Принудительно показываем
        file_options_layout.addWidget(self.file_options_widget)

        settings_layout.addWidget(file_options_group)
        main_layout.addWidget(settings_group)

        # Кнопки управления
        self.setup_control_buttons(main_layout)

        # Прогресс
        self.setup_progress_section(main_layout)

        # Лог обработки
        self.setup_log_section(main_layout)

        # Статус бар
        self.statusBar().showMessage("Готов к работе")

    def setup_control_buttons(self, main_layout):
        """Создание кнопок управления."""
        buttons_layout = QHBoxLayout()

        self.start_button = QPushButton("🚀 Начать сжатие")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_compression)
        self.start_button.setStyleSheet(BUTTON_STYLES["start"])

        self.stop_button = QPushButton("⏹️ Остановить")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_compression)
        self.stop_button.setStyleSheet(BUTTON_STYLES["stop"])

        self.clear_button = QPushButton("🗑️ Очистить очередь")
        self.clear_button.setEnabled(False)
        self.clear_button.clicked.connect(self.clear_queue)
        self.clear_button.setStyleSheet(BUTTON_STYLES["clear"])

        buttons_layout.addWidget(self.start_button)
        buttons_layout.addWidget(self.stop_button)
        buttons_layout.addWidget(self.clear_button)
        buttons_layout.addStretch()

        main_layout.addLayout(buttons_layout)

    def setup_progress_section(self, main_layout):
        """Создание секции прогресса."""
        progress_group = QGroupBox("📊 Прогресс")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(PROGRESS_BAR_STYLE)
        progress_layout.addWidget(self.progress_bar)

        main_layout.addWidget(progress_group)

    def setup_log_section(self, main_layout):
        """Создание секции лога."""
        log_group = QGroupBox("📝 Лог обработки")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(200)
        self.log_text.setStyleSheet(LOG_TEXT_STYLE)
        log_layout.addWidget(self.log_text)

        main_layout.addWidget(log_group)

    def handle_dropped_files(self, files):
        """Общий discovery владеет порядком и дедупликацией выбора."""
        self._queue_generation += 1
        result = discover_inputs([*self.files_to_process, *files], recursive=True)
        self.files_to_process = [str(path) for path in result.paths]
        for issue in result.issues:
            self.log_text.append(project("item_finished", stage=issue.error.stage,
                                         reason=issue.error.code, outcome="failed"))
        for info in (*result.errors, *result.warnings):
            self.log_text.append(project("item_finished", stage=info.stage, reason=info.code))
        count = len(self.files_to_process)
        self.log_text.append(f"В очереди: {count}; дубликатов: {result.duplicates}")
        self.drop_zone.update_label(f"📁 В очереди: {count} файлов")
        self.statusBar().showMessage(f"Выбрано файлов: {count}")
        self._restore_controls()

    def start_compression(self):
        """Новый запуск ждёт реального QThread.finished предыдущего."""
        if self.worker is not None or self._close_pending:
            return
        if not self.files_to_process:
            QMessageBox.warning(self, "Предупреждение", "Сначала выберите файлы для обработки!")
            return
        quality = self.quality_widget.get_value()
        format_type = self.format_widget.get_selected_format()
        delete_original = self.file_options_widget.get_delete_original()
        postfix = self.file_options_widget.get_postfix()
        max_width = self.resize_widget.get_max_width()
        max_height = self.resize_widget.get_max_height()
        resize = self.resize_widget.is_resize_enabled()
        if resize:
            if not max_width or not max_height:
                QMessageBox.warning(
                    self, "Ошибка валидации", "Необходимо указать оба значения: ширину и высоту!"
                )
                self._restore_controls()
                return
            if max_width <= 0 or max_height <= 0:
                QMessageBox.warning(
                    self, "Ошибка валидации", "Размеры должны быть положительными числами!"
                )
                self._restore_controls()
                return
        paths = tuple(self.files_to_process)
        snapshot = (paths, quality, format_type, delete_original, postfix,
                    max_width, max_height, resize, self._queue_generation)
        if delete_original:
            answer = QMessageBox.question(
                self, "Удалить оригиналы?",
                f"Выбрано файлов: {len(paths)}. Формат: {format_type}; качество: {quality}; "
                f"размер: {max_width}×{max_height}; постфикс: {postfix}.\n\n"
                "Оригиналы будут безвозвратно удалены после проверки новых файлов. "
                "Корзины и автоматического восстановления нет. Преобразование может терять "
                "качество, уменьшать размер и удаляет метаданные. При ошибках часть оригиналов "
                "может остаться. Продолжить?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            current = (
                tuple(self.files_to_process), self.quality_widget.get_value(),
                self.format_widget.get_selected_format(),
                self.file_options_widget.get_delete_original(),
                self.file_options_widget.get_postfix(), self.resize_widget.get_max_width(),
                self.resize_widget.get_max_height(), self.resize_widget.is_resize_enabled(),
                self._queue_generation,
            )
            if (answer != QMessageBox.StandardButton.Yes or self.worker is not None
                    or self._close_pending or current != snapshot):
                self._restore_controls()
                return
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.clear_button.setEnabled(False)
        self.file_options_widget.delete_original_checkbox.setEnabled(False)
        self.progress_bar.setValue(0)
        self.log_text.clear()
        self._pending_result = None
        self.worker = CompressionWorker(
            list(paths), quality, format_type, delete_original, postfix,
            max_width, max_height,
        )
        self.worker.progress_updated.connect(self.progress_bar.setValue)
        self.worker.log_message.connect(self.log_text.append)
        self.worker.result_ready.connect(self.compression_finished)
        self.worker.finished.connect(self._thread_finished)
        self.worker.start()
        self.statusBar().showMessage("Обработка в процессе...")

    def stop_compression(self):
        """Только запрос; нет wait/terminate или выдуманного terminal результата."""
        if self.worker is not None:
            self.worker.cancel()
            self.stop_button.setEnabled(False)
            self.statusBar().showMessage("Остановка запрошена; ожидаем завершения кодека...")

    def compression_finished(self, result):
        """Результат известен; worker ещё удерживается до QThread.finished."""
        self._pending_result = result

    def _restore_controls(self):
        busy = self.worker is not None
        self.start_button.setEnabled(bool(self.files_to_process) and not busy)
        self.clear_button.setEnabled(bool(self.files_to_process) and not busy)
        self.stop_button.setEnabled(busy)
        self.file_options_widget.delete_original_checkbox.setEnabled(not busy)

    def _thread_finished(self):
        worker = self.worker
        if worker is None:
            return
        result = self._pending_result or worker.result
        self.last_result = result
        self.worker = None
        self._pending_result = None
        worker.deleteLater()
        self._restore_controls()
        if self._close_pending:
            self.close()
            return
        if result is None:
            self.statusBar().showMessage("INTERNAL_ERROR")
            return
        counts = result.counts
        message = (f"Итог: {result.status}\nУспешно: {counts.succeeded}; "
                   f"ошибок: {counts.failed + len(result.errors)}; "
                   f"отменено: {counts.cancelled}; опубликовано: {counts.published}; "
                   f"удалено оригиналов: {counts.deleted}")
        for item in result.items:
            outcome = {
                "retained": "Оригинал не удалён.",
                "deleted": "Оригинал удалён.",
                "unknown": ("Завершение удаления не подтверждено. Проверьте оригинал и результат; "
                            "автоматического повтора нет."),
            }[item.source_disposition]
            ready = ("Новый файл готов. " if item.artifact
                     and item.artifact.publication == "verified" else "")
            reasons = ", ".join(info.code.value for info in item.warnings)
            self.log_text.append(f"Файл {item.index + 1}: {ready}{outcome} {reasons}".rstrip())
        if result.options and result.options.delete_original:
            retained = sum(i.source_disposition == "retained" for i in result.items)
            unknown = sum(i.source_disposition == "unknown" for i in result.items)
            message += f"\nОригиналы: не удалено {retained}; неизвестно {unknown}."
        if any(info.code == ErrorCode.DESTRUCTIVE_MODE_UNSUPPORTED for info in result.errors):
            message = DESTRUCTIVE_MODE_MESSAGE
        self.log_text.append(message)
        self.statusBar().showMessage(f"Итог: {result.status}")
        QMessageBox.information(self, "Обработка завершена", message)

    def closeEvent(self, event):  # noqa: N802
        if self.worker is not None:
            self._close_pending = True
            self.stop_compression()
            event.ignore()
        else:
            event.accept()

    def clear_queue(self):
        """Очистка очереди файлов."""
        if self.worker is not None:
            return
        self._queue_generation += 1
        self.files_to_process = []
        self.start_button.setEnabled(False)
        self.clear_button.setEnabled(False)
        self.drop_zone.update_label("📁 Перетащите сюда файлы или папки\nили нажмите для выбора")
        self.log_text.append("🗑️ Очередь файлов очищена")
        self.statusBar().showMessage("Готов к работе")
