"""Reusable real controls corresponding to the editable FigCraft components."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QMimeData, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QStandardItemModel
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from image_compressor import Capabilities

from .controller import Options
from .localization import Translator


def card(name: str = "") -> QFrame:
    widget = QFrame()
    widget.setProperty("role", "card")
    if name:
        widget.setObjectName(name)
    return widget


def caption() -> QLabel:
    label = QLabel()
    label.setProperty("role", "caption")
    label.setWordWrap(True)
    return label


class DropPanel(QFrame):
    paths_dropped = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.setProperty("role", "card")
        self.setAcceptDrops(True)
        self.drop_enabled = True

    @staticmethod
    def local_paths(mime: QMimeData) -> tuple[Path, ...]:
        urls = mime.urls()
        if not urls or any(not url.isLocalFile() or not url.toLocalFile() for url in urls):
            return ()
        return tuple(Path(url.toLocalFile()) for url in urls)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if self.drop_enabled and self.local_paths(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        paths = self.local_paths(event.mimeData())
        if self.drop_enabled and paths:
            event.acceptProposedAction()
            self.paths_dropped.emit(paths)
        else:
            event.ignore()


class SettingsPanel(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setProperty("role", "card")
        self.setFixedWidth(320)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        self.heading = QLabel()
        self.heading.setProperty("role", "heading")
        layout.addWidget(self.heading)
        self.scroll_area = QScrollArea()
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.form = QWidget()
        self.form.setObjectName("SettingsForm")
        form_layout = QVBoxLayout(self.form)
        form_layout.setContentsMargins(
            0, 0, 8, 0
        )  # real scrollbar gutter, unlike the design stripe
        form_layout.setSpacing(8)
        self.labels: dict[str, QLabel] = {}

        def add_label(key: str) -> QLabel:
            label = caption()
            self.labels[key] = label
            form_layout.addWidget(label)
            return label

        self.output_format = QComboBox()
        self.output_format.setObjectName("OutputFormat")
        for display, data in (
            ("JPEG", "JPEG"),
            ("WebP", "WEBP"),
            ("HEIF / HEIC", "HEIF"),
            ("AVIF", "AVIF"),
        ):
            self.output_format.addItem(display, data)
        self.output_format.setCurrentIndex(1)
        self.labels["format"] = add_label("format")
        self.labels["format"].setBuddy(self.output_format)
        form_layout.addWidget(self.output_format)
        self._capabilities: Capabilities | None = None
        self.codec_note = caption()
        form_layout.addWidget(self.codec_note)
        self.quality = QSpinBox()
        self.quality.setObjectName("Quality")
        self.quality.setRange(0, 100)
        self.quality.setValue(80)
        quality_layout = QHBoxLayout()
        label = caption()
        self.labels["quality"] = label
        label.setBuddy(self.quality)
        quality_layout.addWidget(label, 1)
        quality_layout.addWidget(self.quality)
        form_layout.addLayout(quality_layout)
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(0, 100)
        self.quality_slider.setValue(80)
        self.quality_slider.valueChanged.connect(self.quality.setValue)
        self.quality.valueChanged.connect(self.quality_slider.setValue)
        form_layout.addWidget(self.quality_slider)
        self.resize_check = QCheckBox()
        self.resize_check.setObjectName("Resize")
        self.resize_check.toggled.connect(self._resize_toggled)
        form_layout.addWidget(self.resize_check)
        dimensions = QGridLayout()
        dimensions.setSpacing(8)
        self.max_width = QSpinBox()
        self.max_height = QSpinBox()
        for column, (key, field, value) in enumerate(
            (("width", self.max_width, 1920), ("height", self.max_height, 1080))
        ):
            field.setObjectName(key)
            field.setRange(1, 2_147_483_647)
            field.setValue(value)
            field.setEnabled(False)
            label = caption()
            label.setBuddy(field)
            self.labels[key] = label
            dimensions.addWidget(label, 0, column)
            dimensions.addWidget(field, 1, column)
        form_layout.addLayout(dimensions)
        self.postfix = QLineEdit("_compressed")
        self.postfix.setObjectName("Postfix")
        add_label("postfix").setBuddy(self.postfix)
        form_layout.addWidget(self.postfix)
        add_label("postfix_help")
        self.recursive = QCheckBox()
        self.recursive.setObjectName("Recursive")
        self.recursive.setChecked(True)
        form_layout.addWidget(self.recursive)
        add_label("recursive_help")
        form_layout.addStretch(1)
        self.scroll_area.setWidget(self.form)
        layout.addWidget(self.scroll_area, 1)
        self.safety = card("Safety")
        safety_layout = QVBoxLayout(self.safety)
        safety_layout.setContentsMargins(8, 8, 8, 8)
        safety_layout.setSpacing(4)
        self.delete_original = QCheckBox()
        self.delete_original.setObjectName("DeleteUnavailable")
        self.delete_original.setChecked(False)
        self.delete_original.setEnabled(False)
        self.delete_original.setFixedWidth(32)
        self.delete_label = caption()
        self.delete_label.setBuddy(self.delete_original)
        delete_row = QHBoxLayout()
        delete_row.setSpacing(4)
        delete_row.addWidget(self.delete_original, 0, Qt.AlignmentFlag.AlignTop)
        delete_row.addWidget(self.delete_label, 1)
        self.safety_explanation = caption()
        safety_layout.addLayout(delete_row)
        safety_layout.addWidget(self.safety_explanation)
        layout.addWidget(self.safety)
        self.retranslate(Translator("ru"))

    def _resize_toggled(self, enabled: bool) -> None:
        self.max_width.setEnabled(enabled)
        self.max_height.setEnabled(enabled)

    def options(self) -> Options:
        return Options(
            str(self.output_format.currentData()),
            self.quality.value(),
            self.resize_check.isChecked(),
            self.max_width.value(),
            self.max_height.value(),
            self.postfix.text(),  # Exact empty/whitespace remains the API's responsibility.
        )

    def set_busy(self, busy: bool) -> None:
        self.form.setEnabled(not busy)
        self.delete_original.setEnabled(False)

    def set_capabilities(self, capabilities: Capabilities, t: Translator) -> None:
        self._capabilities = capabilities
        model = self.output_format.model()
        assert isinstance(model, QStandardItemModel)
        for index in range(self.output_format.count()):
            capability = capabilities.for_format(str(self.output_format.itemData(index)))
            item = model.item(index)
            item.setEnabled(capability.encoder_available)
            item.setToolTip(
                t("unavailable", reason=capability.reason or "FORMAT_UNAVAILABLE")
                if not capability.encoder_available
                else capability.provider or ""
            )
        self._codec_note(t)

    def _codec_note(self, t: Translator) -> None:
        unavailable = (
            []
            if self._capabilities is None
            else [
                item.format
                for item in self._capabilities.formats
                if item.format != "PNG" and not item.encoder_available
            ]
        )
        self.codec_note.setText(
            t("unavailable", reason=", ".join(unavailable)) if unavailable else ""
        )
        self.codec_note.setVisible(bool(unavailable))

    def selected_available(self) -> bool:
        return bool(
            self._capabilities
            and self._capabilities.for_format(
                str(self.output_format.currentData())
            ).encoder_available
        )

    def retranslate(self, t: Translator) -> None:
        self.heading.setText(t("settings"))
        for key, label in self.labels.items():
            label.setText(t(key))
        self.resize_check.setText(t("resize"))
        self.resize_check.setAccessibleName(t("resize"))
        self.quality_slider.setAccessibleName(t("quality"))
        self.recursive.setText(t("recursive"))
        self.recursive.setToolTip(t("recursive_help"))
        self.delete_label.setText(t("delete"))
        self.delete_original.setAccessibleName(t("delete"))
        self.delete_original.setAccessibleDescription(t("safe"))
        self.safety_explanation.setText(t("safe"))
        if self._capabilities is not None:
            self.set_capabilities(self._capabilities, t)
