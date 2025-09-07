"""
Виджеты для GUI компрессора изображений.
"""

import os
from typing import List
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QRadioButton, 
    QButtonGroup, QGroupBox, QFileDialog, QLineEdit, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QDragEnterEvent, QDropEvent

from .styles import DROPZONE_STYLES, DROPZONE_LABEL_STYLE, QUALITY_LABEL_STYLE
from .utils import get_image_files_from_paths


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
        self.setStyleSheet(DROPZONE_STYLES['normal'])

        # Лейбл с инструкцией
        layout = QVBoxLayout()
        self.label = QLabel(
            "📁 Перетащите сюда файлы или папки\nили нажмите для выбора"
        )
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont("Arial", 12))
        self.label.setStyleSheet(DROPZONE_LABEL_STYLE)

        layout.addWidget(self.label)
        self.setLayout(layout)

        # Обработка клика для открытия диалога
        self.mousePressEvent = self.open_file_dialog

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Обработка начала перетаскивания."""
        if event.mimeData().hasUrls():
            event.accept()
            self.setStyleSheet(DROPZONE_STYLES['active'])
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """Обработка выхода из зоны перетаскивания."""
        self.setStyleSheet(DROPZONE_STYLES['normal'])

    def dropEvent(self, event: QDropEvent):
        """Обработка отпускания файлов."""
        files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.exists(file_path):
                files.append(file_path)

        if files:
            self.files_dropped.emit(files)

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

    def update_label(self, text: str):
        """Обновляет текст в лейбле."""
        self.label.setText(text)


class QualityWidget(QWidget):
    """Виджет для выбора качества сжатия."""
    
    value_changed = pyqtSignal(int)
    
    def __init__(self, initial_value: int = 80):
        super().__init__()
        self.init_ui(initial_value)
    
    def init_ui(self, initial_value: int):
        """Инициализация виджета качества."""
        layout = QHBoxLayout()
        layout.addWidget(QLabel("🎛️ Качество:"))

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(1, 100)
        self.slider.setValue(initial_value)
        self.slider.valueChanged.connect(self.on_value_changed)

        self.label = QLabel(str(initial_value))
        self.label.setMinimumWidth(30)
        self.label.setStyleSheet(QUALITY_LABEL_STYLE)

        layout.addWidget(self.slider)
        layout.addWidget(self.label)
        self.setLayout(layout)
    
    def on_value_changed(self, value: int):
        """Обновление отображения при изменении значения."""
        self.label.setText(str(value))
        self.value_changed.emit(value)
    
    def get_value(self) -> int:
        """Получить текущее значение качества."""
        return self.slider.value()


class FormatWidget(QWidget):
    """Виджет для выбора формата сжатия."""
    
    def __init__(self, default_format: str = "WEBP"):
        super().__init__()
        self.init_ui(default_format)
    
    def init_ui(self, default_format: str):
        """Инициализация виджета формата."""
        layout = QHBoxLayout()
        layout.addWidget(QLabel("📋 Формат:"))

        self.format_group = QButtonGroup()
        self.heif_radio = QRadioButton("HEIF (.heic)")
        self.webp_radio = QRadioButton("WebP (.webp)")
        self.avif_radio = QRadioButton("AVIF (.avif)")
        self.jpeg_radio = QRadioButton("JPEG (.jpg)")

        # Устанавливаем формат по умолчанию
        if default_format == "HEIF":
            self.heif_radio.setChecked(True)
        elif default_format == "WEBP":
            self.webp_radio.setChecked(True)
        elif default_format == "AVIF":
            self.avif_radio.setChecked(True)
        elif default_format == "JPEG":
            self.jpeg_radio.setChecked(True)
        else:
            self.webp_radio.setChecked(True)

        self.format_group.addButton(self.heif_radio, 0)
        self.format_group.addButton(self.webp_radio, 1)
        self.format_group.addButton(self.avif_radio, 2)
        self.format_group.addButton(self.jpeg_radio, 3)

        layout.addWidget(self.heif_radio)
        layout.addWidget(self.webp_radio)
        layout.addWidget(self.avif_radio)
        layout.addWidget(self.jpeg_radio)
        layout.addStretch()

        self.setLayout(layout)
    
    def get_selected_format(self) -> str:
        """Получить выбранный формат."""
        if self.heif_radio.isChecked():
            return "HEIF"
        elif self.webp_radio.isChecked():
            return "WEBP"
        elif self.avif_radio.isChecked():
            return "AVIF"
        elif self.jpeg_radio.isChecked():
            return "JPEG"
        return "WEBP"


class FileOptionsWidget(QWidget):
    """Виджет для настроек обработки файлов."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """Инициализация виджета настроек файлов."""
        layout = QVBoxLayout()

        # Чекбоксы удаления оригинальных файлов
        self.delete_original_radio = QRadioButton("🗑️ Удалять оригинальные файлы")
        self.keep_original_radio = QRadioButton("💾 Сохранять оригинальные файлы")
        self.keep_original_radio.setChecked(True)  # По умолчанию сохраняем

        # Группа для радиокнопок
        self.file_action_group = QButtonGroup()
        self.file_action_group.addButton(self.delete_original_radio, 0)
        self.file_action_group.addButton(self.keep_original_radio, 1)

        layout.addWidget(self.delete_original_radio)
        layout.addWidget(self.keep_original_radio)

        # Настройка постфикса для одинаковых расширений
        postfix_layout = QHBoxLayout()
        postfix_layout.addWidget(QLabel("📝 Постфикс при совпадении расширений:"))
        
        self.postfix_input = QLineEdit("_compressed")
        self.postfix_input.setPlaceholderText("_compressed")
        self.postfix_input.setToolTip("Добавляется к имени файла при совпадении входного и выходного расширения")
        
        postfix_layout.addWidget(self.postfix_input)
        layout.addLayout(postfix_layout)

        self.setLayout(layout)
    
    def get_delete_original(self) -> bool:
        """Получить настройку удаления оригинальных файлов."""
        return self.delete_original_radio.isChecked()
    
    def get_postfix(self) -> str:
        """Получить постфикс для файлов."""
        return self.postfix_input.text().strip() or "_compressed"
