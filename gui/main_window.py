"""
Главное окно GUI компрессора изображений.
"""

import sys
from PyQt6.QtWidgets import (
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QLabel,
    QProgressBar,
    QTextEdit,
    QPushButton,
    QGroupBox,
    QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from .widgets import (
    DropZone,
    QualityWidget,
    FormatWidget,
    FileOptionsWidget,
    ResizeDimensionsWidget,
)
from .worker import CompressionWorker
from .styles import BUTTON_STYLES, PROGRESS_BAR_STYLE, LOG_TEXT_STYLE, TITLE_STYLE
from .utils import get_image_files_from_paths


class ImageCompressorGUI(QMainWindow):
    """Главное окно GUI компрессора изображений."""

    def __init__(self):
        super().__init__()
        self.files_to_process = []
        self.worker = None
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
        """Обработка перетащенных файлов."""
        # Получаем все изображения из переданных путей
        image_files = get_image_files_from_paths(files)

        # Добавляем новые файлы к существующим (не заменяем!)
        new_files = []
        for file_path in image_files:
            if file_path not in self.files_to_process:
                new_files.append(file_path)
                self.files_to_process.append(file_path)

        if new_files:
            self.start_button.setEnabled(True)
            self.clear_button.setEnabled(True)  # Активируем кнопку очистки
            self.log_text.append(f"📁 Добавлено новых изображений: {len(new_files)}")
            self.log_text.append(f"📊 Всего в очереди: {len(self.files_to_process)}")
            self.statusBar().showMessage(f"Готово к обработке {len(self.files_to_process)} файлов")

            # Обновляем текст в зоне
            self.drop_zone.update_label(f"📁 В очереди: {len(self.files_to_process)} файлов")
        else:
            if not self.files_to_process:
                self.start_button.setEnabled(False)
                self.clear_button.setEnabled(False)
                self.log_text.append("❌ Не найдено новых подходящих изображений")
                self.statusBar().showMessage("Файлы не выбраны")
            else:
                self.log_text.append("ℹ️ Выбранные файлы уже в очереди")

    def start_compression(self):
        """Начало процесса сжатия."""
        if not self.files_to_process:
            QMessageBox.warning(self, "Предупреждение", "Сначала выберите файлы для обработки!")
            return

        # Получаем настройки
        quality = self.quality_widget.get_value()
        format_type = self.format_widget.get_selected_format()
        delete_original = self.file_options_widget.get_delete_original()
        postfix = self.file_options_widget.get_postfix()
        max_width = self.resize_widget.get_max_width()
        max_height = self.resize_widget.get_max_height()

        # Блокируем интерфейс
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setValue(0)

        # Очищаем лог
        self.log_text.clear()

        # Валидация resize параметров
        if self.resize_widget.is_resize_enabled():
            if not max_width or not max_height:
                QMessageBox.warning(
                    self, "Ошибка валидации", "Необходимо указать оба значения: ширину и высоту!"
                )
                self.start_button.setEnabled(True)
                return
            if max_width <= 0 or max_height <= 0:
                QMessageBox.warning(
                    self, "Ошибка валидации", "Размеры должны быть положительными числами!"
                )
                self.start_button.setEnabled(True)
                return

        # Подсчитываем уникальные файлы
        unique_files = list(dict.fromkeys(self.files_to_process))
        duplicate_count = len(self.files_to_process) - len(unique_files)

        self.log_text.append(f"🚀 Начинаем сжатие {len(unique_files)} файлов...")
        if duplicate_count > 0:
            self.log_text.append(f"⚠️ Удалено дубликатов: {duplicate_count}")
        self.log_text.append(f"📋 Формат: {format_type}, Качество: {quality}")
        if max_width and max_height:
            self.log_text.append(f"📐 Макс. размеры: {max_width}x{max_height} пикс.")
        self.log_text.append(f"🗑️ Удалять оригиналы: {'Да' if delete_original else 'Нет'}")
        if not delete_original:
            self.log_text.append(f"📝 Постфикс: {postfix}")
        self.log_text.append("=" * 50)

        # Запускаем рабочий поток с уникальными файлами
        self.worker = CompressionWorker(
            unique_files, quality, format_type, delete_original, postfix, max_width, max_height
        )
        self.worker.progress_updated.connect(self.progress_bar.setValue)
        self.worker.log_message.connect(self.log_text.append)
        self.worker.finished_processing.connect(self.compression_finished)
        self.worker.start()

        self.statusBar().showMessage("Обработка в процессе...")

    def stop_compression(self):
        """Остановка процесса сжатия."""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()  # Ждем завершения потока

        self.compression_finished(0, 0, cancelled=True)

    def compression_finished(self, successful: int, errors: int, cancelled: bool = False):
        """Завершение процесса сжатия."""
        # Разблокируем интерфейс
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

        if cancelled:
            self.log_text.append("⏹️ Обработка отменена пользователем")
            self.statusBar().showMessage("Обработка отменена")
        else:
            self.log_text.append("=" * 50)
            self.log_text.append(f"✅ Обработка завершена!")
            self.log_text.append(f"📊 Успешно: {successful}, Ошибок: {errors}")
            self.statusBar().showMessage(f"Готово! Обработано: {successful}, ошибок: {errors}")

            # Показываем результат
            QMessageBox.information(
                self,
                "Обработка завершена",
                f"Успешно обработано: {successful} файлов\nОшибок: {errors}",
            )

    def clear_queue(self):
        """Очистка очереди файлов."""
        self.files_to_process = []
        self.start_button.setEnabled(False)
        self.clear_button.setEnabled(False)
        self.drop_zone.update_label("📁 Перетащите сюда файлы или папки\nили нажмите для выбора")
        self.log_text.append("🗑️ Очередь файлов очищена")
        self.statusBar().showMessage("Готов к работе")
