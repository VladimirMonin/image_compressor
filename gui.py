"""
GUI версия компрессора изображений с использованием PyQt6.

Возможности:
- Drag & Drop зона для файлов и папок
- Слайдер качества сжатия (0-100)
- Радиокнопки выбора формата (HEIF, WebP, AVIF)
- Индикатор прогресса
- Многопоточная обработка без зависания интерфейса
- Логирование процесса в реальном времени

Зависимости:
    pip install PyQt6 Pillow pillow-heif pillow-avif-plugin
"""

import os
import sys
from typing import List, Optional
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QLabel,
    QSlider,
    QRadioButton,
    QButtonGroup,
    QProgressBar,
    QTextEdit,
    QPushButton,
    QFrame,
    QGroupBox,
    QFileDialog,
    QMessageBox,
    QSpacerItem,
    QSizePolicy,
    QLineEdit,
    QCheckBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMimeData, QUrl, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor, QDragEnterEvent, QDropEvent

# Импортируем наш компрессор
from classes import ImageCompressor
from pillow_heif import register_heif_opener
from pillow_heif import register_heif_opener


class CompressionWorker(QThread):
    """Рабочий поток для сжатия изображений без блокировки UI."""

    progress_updated = pyqtSignal(int)  # Прогресс в процентах
    file_processed = pyqtSignal(str)  # Имя обработанного файла
    log_message = pyqtSignal(str)  # Сообщение для лога
    finished_processing = pyqtSignal(int, int)  # успешных, ошибок

    def __init__(self, files: List[str], quality: int, format_type: str, delete_original: bool = False, postfix: str = "_compressed"):
        super().__init__()
        # Удаляем дубликаты из списка файлов
        self.files = list(set(files))
        self.quality = quality
        self.format_type = format_type
        self.delete_original = delete_original
        self.postfix = postfix
        self.is_cancelled = False

    def run(self):
        """Основной метод обработки в отдельном потоке."""
        successful = 0
        errors = 0

        # Проверяем дубликаты еще раз и сообщаем об этом
        original_count = len(self.files)
        unique_files = list(dict.fromkeys(self.files))  # Сохраняем порядок
        total_files = len(unique_files)

        if original_count != total_files:
            duplicates_count = original_count - total_files
            self.log_message.emit(f"⚠️ Найдено и удалено дубликатов: {duplicates_count}")

        try:
            # Инициализируем HEIF для чтения входных файлов
            register_heif_opener()

            # Создаем компрессор
            compressor = ImageCompressor(
                quality=self.quality, output_format=self.format_type
            )

            for i, file_path in enumerate(unique_files):
                if self.is_cancelled:
                    break

                try:
                    # Определяем выходной путь
                    input_path = Path(file_path)
                    extension = compressor.output_formats[self.format_type]
                    
                    # Проверяем, совпадает ли расширение входного и выходного файла
                    input_extension = input_path.suffix.lower()
                    output_extension = extension.lower()
                    
                    if input_extension == output_extension and not self.delete_original:
                        # Добавляем постфикс при совпадении расширений
                        base_name = input_path.stem
                        output_path = input_path.parent / f"{base_name}{self.postfix}{extension}"
                    else:
                        output_path = input_path.with_suffix(extension)

                    # Отладочная информация
                    self.log_message.emit(f"🔄 Обрабатываем: {input_path}")
                    self.log_message.emit(f"📁 Выходной путь: {output_path}")

                    # Проверяем права на запись в папку
                    output_dir = output_path.parent
                    if not os.access(output_dir, os.W_OK):
                        raise PermissionError(
                            f"Нет прав на запись в папку: {output_dir}"
                        )

                    # Сжимаем изображение
                    compressor.compress_image(str(input_path), str(output_path))

                    # Проверяем, что файл действительно создался
                    if output_path.exists():
                        original_size = input_path.stat().st_size
                        compressed_size = output_path.stat().st_size
                        saved_bytes = original_size - compressed_size
                        saved_percent = (
                            (saved_bytes / original_size) * 100
                            if original_size > 0
                            else 0
                        )

                        if saved_percent > 0:
                            self.log_message.emit(
                                f"✅ {input_path.name} -> {output_path.name}"
                            )
                            self.log_message.emit(
                                f"   💾 Экономия: {saved_bytes:,} байт ({saved_percent:.1f}%)"
                            )
                        else:
                            self.log_message.emit(
                                f"✅ {input_path.name} -> {output_path.name} (размер увеличился)"
                            )

                        # Удаляем оригинальный файл, если это требуется
                        if self.delete_original and input_path != output_path:
                            try:
                                input_path.unlink()
                                self.log_message.emit(f"🗑️ Удален оригинальный файл: {input_path.name}")
                            except Exception as e:
                                self.log_message.emit(f"⚠️ Не удалось удалить оригинал {input_path.name}: {str(e)}")

                        successful += 1
                    else:
                        raise FileNotFoundError(
                            f"Выходной файл не создался: {output_path}"
                        )

                    self.file_processed.emit(input_path.name)

                except Exception as e:
                    errors += 1
                    self.log_message.emit(f"❌ Ошибка {Path(file_path).name}: {str(e)}")

                # Обновляем прогресс
                progress = int(((i + 1) / total_files) * 100)
                self.progress_updated.emit(progress)

        except Exception as e:
            self.log_message.emit(f"❌ Критическая ошибка: {str(e)}")

        self.finished_processing.emit(successful, errors)

    def cancel(self):
        """Отменяет обработку."""
        self.is_cancelled = True


class DropZone(QFrame):
    """Виджет зоны drag & drop для файлов."""

    files_dropped = pyqtSignal(list)  # Сигнал со списком файлов

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.init_ui()

    def init_ui(self):
        """Инициализация интерфейса зоны."""
        self.setFrameStyle(QFrame.Shape.Box)
        self.setLineWidth(2)
        self.setMinimumHeight(150)

        # Настройка стиля
        self.setStyleSheet(
            """
            QFrame {
                border: 2px dashed #cccccc;
                border-radius: 10px;
                background-color: #f9f9f9;
            }
            QFrame:hover {
                border-color: #0078d4;
                background-color: #f0f8ff;
            }
        """
        )

        # Лейбл с инструкцией
        layout = QVBoxLayout()
        self.label = QLabel(
            "📁 Перетащите сюда файлы или папки\nили нажмите для выбора"
        )
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont("Arial", 12))
        self.label.setStyleSheet(
            "color: #666666; border: none; background: transparent;"
        )

        layout.addWidget(self.label)
        self.setLayout(layout)

        # Обработка клика для открытия диалога
        self.mousePressEvent = self.open_file_dialog

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Обработка начала перетаскивания."""
        if event.mimeData().hasUrls():
            event.accept()
            self.setStyleSheet(
                """
                QFrame {
                    border: 2px dashed #0078d4;
                    border-radius: 10px;
                    background-color: #e6f3ff;
                }
            """
            )
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """Обработка выхода из зоны перетаскивания."""
        self.setStyleSheet(
            """
            QFrame {
                border: 2px dashed #cccccc;
                border-radius: 10px;
                background-color: #f9f9f9;
            }
        """
        )

    def dropEvent(self, event: QDropEvent):
        """Обработка отпускания файлов."""
        files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.exists(file_path):
                files.append(file_path)

        if files:
            self.files_dropped.emit(files)
            # НЕ обновляем label здесь - это сделает handle_dropped_files

        # Возвращаем обычный стиль
        self.dragLeaveEvent(event)

    def open_file_dialog(self, event):
        """Открытие диалога выбора файлов."""
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter(
            "Изображения (*.jpg *.jpeg *.png *.heic *.heif *.avif);;Все файлы (*)"
        )

        if file_dialog.exec():
            files = file_dialog.selectedFiles()
            if files:
                self.files_dropped.emit(files)
                # НЕ обновляем label здесь - это сделает handle_dropped_files


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
        title.setStyleSheet("color: #2c3e50; margin: 10px;")
        main_layout.addWidget(title)

        # Зона drag & drop
        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self.handle_dropped_files)
        main_layout.addWidget(self.drop_zone)

        # Настройки сжатия
        settings_group = QGroupBox("⚙️ Настройки сжатия")
        settings_layout = QVBoxLayout(settings_group)

        # Качество сжатия
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("🎛️ Качество:"))

        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(80)
        self.quality_slider.valueChanged.connect(self.update_quality_label)

        self.quality_label = QLabel("80")
        self.quality_label.setMinimumWidth(30)
        self.quality_label.setStyleSheet("font-weight: bold; color: #2c3e50;")

        quality_layout.addWidget(self.quality_slider)
        quality_layout.addWidget(self.quality_label)
        settings_layout.addLayout(quality_layout)

        # Выбор формата
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("📋 Формат:"))

        self.format_group = QButtonGroup()
        self.heif_radio = QRadioButton("HEIF (.heic)")
        self.webp_radio = QRadioButton("WebP (.webp)")
        self.avif_radio = QRadioButton("AVIF (.avif)")
        self.jpeg_radio = QRadioButton("JPEG (.jpg)")

        self.webp_radio.setChecked(True)  # По умолчанию WebP

        self.format_group.addButton(self.heif_radio, 0)
        self.format_group.addButton(self.webp_radio, 1)
        self.format_group.addButton(self.avif_radio, 2)
        self.format_group.addButton(self.jpeg_radio, 3)

        format_layout.addWidget(self.heif_radio)
        format_layout.addWidget(self.webp_radio)
        format_layout.addWidget(self.avif_radio)
        format_layout.addWidget(self.jpeg_radio)
        format_layout.addStretch()

        settings_layout.addLayout(format_layout)

        # Настройки обработки файлов
        file_options_group = QGroupBox("📁 Настройки обработки файлов")
        file_options_layout = QVBoxLayout(file_options_group)

        # Чекбокс удаления оригинальных файлов
        self.delete_original_checkbox = QRadioButton("🗑️ Удалять оригинальные файлы")
        self.keep_original_checkbox = QRadioButton("💾 Сохранять оригинальные файлы")
        self.keep_original_checkbox.setChecked(True)  # По умолчанию сохраняем

        # Группа для радиокнопок
        self.file_action_group = QButtonGroup()
        self.file_action_group.addButton(self.delete_original_checkbox, 0)
        self.file_action_group.addButton(self.keep_original_checkbox, 1)

        file_options_layout.addWidget(self.delete_original_checkbox)
        file_options_layout.addWidget(self.keep_original_checkbox)

        # Настройка постфикса для одинаковых расширений
        postfix_layout = QHBoxLayout()
        postfix_layout.addWidget(QLabel("📝 Постфикс при совпадении расширений:"))
        
        self.postfix_input = QLineEdit("_compressed")
        self.postfix_input.setPlaceholderText("_compressed")
        self.postfix_input.setToolTip("Добавляется к имени файла при совпадении входного и выходного расширения")
        
        postfix_layout.addWidget(self.postfix_input)
        file_options_layout.addLayout(postfix_layout)

        settings_layout.addWidget(file_options_group)
        main_layout.addWidget(settings_group)

        # Кнопки управления
        buttons_layout = QHBoxLayout()

        self.start_button = QPushButton("🚀 Начать сжатие")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_compression)
        self.start_button.setStyleSheet(
            """
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """
        )

        self.stop_button = QPushButton("⏹️ Остановить")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_compression)
        self.stop_button.setStyleSheet(
            """
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """
        )

        self.clear_button = QPushButton("🗑️ Очистить очередь")
        self.clear_button.setEnabled(False)
        self.clear_button.clicked.connect(self.clear_queue)
        self.clear_button.setStyleSheet(
            """
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """
        )

        buttons_layout.addWidget(self.start_button)
        buttons_layout.addWidget(self.stop_button)
        buttons_layout.addWidget(self.clear_button)
        buttons_layout.addStretch()

        main_layout.addLayout(buttons_layout)

        # Прогресс
        progress_group = QGroupBox("📊 Прогресс")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 3px;
            }
        """
        )
        progress_layout.addWidget(self.progress_bar)

        main_layout.addWidget(progress_group)

        # Лог обработки
        log_group = QGroupBox("📝 Лог обработки")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(200)
        self.log_text.setStyleSheet(
            """
            QTextEdit {
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 1px solid #34495e;
                border-radius: 5px;
                padding: 5px;
                font-family: 'Consolas', 'Monaco', monospace;
            }
        """
        )
        log_layout.addWidget(self.log_text)

        main_layout.addWidget(log_group)

        # Статус бар
        self.statusBar().showMessage("Готов к работе")

    def update_quality_label(self, value):
        """Обновление отображения качества."""
        self.quality_label.setText(str(value))

    def handle_dropped_files(self, files):
        """Обработка перетащенных файлов."""
        # Добавляем новые файлы к существующим (не заменяем!)
        new_files = []

        for file_path in files:
            if os.path.isfile(file_path):
                # Проверяем, что это изображение
                if file_path.lower().endswith(
                    (".jpg", ".jpeg", ".png", ".heic", ".heif", ".avif")
                ):
                    # Проверяем, что файл еще не добавлен
                    if file_path not in self.files_to_process:
                        new_files.append(file_path)
                        self.files_to_process.append(file_path)
            elif os.path.isdir(file_path):
                # Сканируем папку
                for root, _, files_in_dir in os.walk(file_path):
                    for file in files_in_dir:
                        if file.lower().endswith(
                            (".jpg", ".jpeg", ".png", ".heic", ".heif", ".avif")
                        ):
                            full_path = os.path.join(root, file)
                            if full_path not in self.files_to_process:
                                new_files.append(full_path)
                                self.files_to_process.append(full_path)

        if new_files:
            self.start_button.setEnabled(True)
            self.clear_button.setEnabled(True)  # Активируем кнопку очистки
            self.log_text.append(f"📁 Добавлено новых изображений: {len(new_files)}")
            self.log_text.append(f"📊 Всего в очереди: {len(self.files_to_process)}")
            self.statusBar().showMessage(
                f"Готово к обработке {len(self.files_to_process)} файлов"
            )

            # Обновляем текст в зоне
            self.drop_zone.label.setText(
                f"📁 В очереди: {len(self.files_to_process)} файлов"
            )
        else:
            if not self.files_to_process:
                self.start_button.setEnabled(False)
                self.clear_button.setEnabled(False)
                self.log_text.append("❌ Не найдено новых подходящих изображений")
                self.statusBar().showMessage("Файлы не выбраны")
            else:
                self.log_text.append("ℹ️ Выбранные файлы уже в очереди")

    def get_selected_format(self) -> str:
        """Получение выбранного формата."""
        if self.heif_radio.isChecked():
            return "HEIF"
        elif self.webp_radio.isChecked():
            return "WEBP"
        elif self.avif_radio.isChecked():
            return "AVIF"
        elif self.jpeg_radio.isChecked():
            return "JPEG"
        return "WEBP"

    def start_compression(self):
        """Начало процесса сжатия."""
        if not self.files_to_process:
            QMessageBox.warning(
                self, "Предупреждение", "Сначала выберите файлы для обработки!"
            )
            return

        # Получаем настройки
        quality = self.quality_slider.value()
        format_type = self.get_selected_format()
        delete_original = self.delete_original_checkbox.isChecked()
        postfix = self.postfix_input.text().strip() or "_compressed"

        # Блокируем интерфейс
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setValue(0)

        # Очищаем лог
        self.log_text.clear()

        # Подсчитываем уникальные файлы
        unique_files = list(dict.fromkeys(self.files_to_process))
        duplicate_count = len(self.files_to_process) - len(unique_files)

        self.log_text.append(f"🚀 Начинаем сжатие {len(unique_files)} файлов...")
        if duplicate_count > 0:
            self.log_text.append(f"⚠️ Удалено дубликатов: {duplicate_count}")
        self.log_text.append(f"📋 Формат: {format_type}, Качество: {quality}")
        self.log_text.append(f"🗑️ Удалять оригиналы: {'Да' if delete_original else 'Нет'}")
        if not delete_original:
            self.log_text.append(f"📝 Постфикс: {postfix}")
        self.log_text.append("=" * 50)

        # Запускаем рабочий поток с уникальными файлами
        unique_files = list(dict.fromkeys(self.files_to_process))
        self.worker = CompressionWorker(unique_files, quality, format_type, delete_original, postfix)
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

    def compression_finished(
        self, successful: int, errors: int, cancelled: bool = False
    ):
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
            self.statusBar().showMessage(
                f"Готово! Обработано: {successful}, ошибок: {errors}"
            )

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
        self.drop_zone.label.setText(
            "📁 Перетащите сюда файлы или папки\nили нажмите для выбора"
        )
        self.log_text.append("🗑️ Очередь файлов очищена")
        self.statusBar().showMessage("Готов к работе")


def main():
    """Главная функция запуска GUI приложения."""
    app = QApplication(sys.argv)

    # Настройка темы приложения
    app.setStyle("Fusion")

    # Создание и показ главного окна
    window = ImageCompressorGUI()
    window.show()

    # Запуск приложения
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
