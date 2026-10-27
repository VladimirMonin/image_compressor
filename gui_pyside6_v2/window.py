"""Desktop layouts and rendering; no image encode, traversal or publication policy."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .controller import Controller
from .localization import Translator
from .theme import add_icon, apply_theme
from .widgets import DropPanel, SettingsPanel, caption, card


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Image Compressor · PySide6 experiment")
        self.resize(1120, 760)
        self.setMinimumSize(900, 640)
        self.language = "ru"
        self.theme = "light"
        self.t = Translator(self.language)
        self.controller = Controller(self)
        self.shell = QWidget()
        self.shell.setObjectName("Shell")
        self.setCentralWidget(self.shell)
        shell = QVBoxLayout(self.shell)
        shell.setContentsMargins(20, 20, 20, 20)
        shell.setSpacing(12)
        header = QHBoxLayout()
        header.setSpacing(12)
        identity = QVBoxLayout()
        identity.setSpacing(2)
        self.title_label = QLabel("Image Compressor")
        self.title_label.setObjectName("Title")
        self.subtitle = caption()
        identity.addWidget(self.title_label)
        identity.addWidget(self.subtitle)
        header.addLayout(identity, 1)
        self.theme_combo = QComboBox()
        self.theme_combo.setObjectName("Theme")
        self.theme_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.theme_combo.addItem("", "light")
        self.theme_combo.addItem("", "dark")
        self.theme_combo.currentIndexChanged.connect(self._change_theme)
        self.locale_combo = QComboBox()
        self.locale_combo.setObjectName("Language")
        self.locale_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        for label, code in (("Русский", "ru"), ("English", "en"), ("Қазақша", "kk")):
            self.locale_combo.addItem(label, code)
        self.locale_combo.currentIndexChanged.connect(self._change_language)
        header.addWidget(self.theme_combo)
        header.addWidget(self.locale_combo)
        shell.addLayout(header)
        body = QHBoxLayout()
        body.setSpacing(16)
        left = QVBoxLayout()
        left.setSpacing(12)
        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.add_button = QPushButton()
        self.add_button.setObjectName("AddFiles")
        self.folder_button = QPushButton()
        self.folder_button.setObjectName("AddFolder")
        self.add_button.clicked.connect(self.choose_files)
        self.folder_button.clicked.connect(self.choose_folder)
        actions.addWidget(self.add_button)
        actions.addWidget(self.folder_button)
        actions.addStretch(1)
        left.addLayout(actions)
        self.drop_panel = DropPanel()
        self.drop_panel.paths_dropped.connect(self.add_paths)
        queue_layout = QVBoxLayout(self.drop_panel)
        queue_layout.setContentsMargins(16, 16, 16, 12)
        queue_layout.setSpacing(6)
        self.queue_heading = QLabel()
        self.queue_heading.setProperty("role", "heading")
        self.drop_hint = caption()
        queue_layout.addWidget(self.queue_heading)
        queue_layout.addWidget(self.drop_hint)
        self.pages = QStackedWidget()
        self.empty_page = QWidget()
        empty = QVBoxLayout(self.empty_page)
        empty.setContentsMargins(0, 0, 0, 0)
        empty.setSpacing(8)
        empty.addStretch(1)
        self.empty_title = QLabel()
        self.empty_title.setProperty("role", "heading")
        self.empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_title.setWordWrap(True)
        self.empty_hint = caption()
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.input_hint = caption()
        self.input_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for empty_label in (self.empty_title, self.empty_hint, self.input_hint):
            empty.addWidget(empty_label)
        empty.addStretch(1)
        self.pages.addWidget(self.empty_page)
        self.table = QTableView()
        self.table.setObjectName("QueueTable")
        self.table.setModel(self.controller.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(42)
        self.table.horizontalHeader().setMinimumSectionSize(44)
        self.table.horizontalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column, width in ((1, 58), (2, 78), (3, 140)):
            self.table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.Interactive
            )
            self.table.setColumnWidth(column, width)
        self.pages.addWidget(self.table)
        queue_layout.addWidget(self.pages, 1)
        self.selection_summary = caption()
        queue_layout.addWidget(self.selection_summary)
        self.subset_note = caption()
        queue_layout.addWidget(self.subset_note)
        left.addWidget(self.drop_panel, 1)
        self.tabs = QTabWidget()
        self.tabs.setObjectName("OperationTabs")
        self.tabs.setFixedHeight(132)
        self.log = QPlainTextEdit()
        self.log.setObjectName("TechnicalLog")
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(500)
        self.log.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.details = QPlainTextEdit()
        self.details.setObjectName("LocalResults")
        self.details.setReadOnly(True)
        self.tabs.addTab(self.log, "")
        self.tabs.addTab(self.details, "")
        left.addWidget(self.tabs)
        body.addLayout(left, 1)
        self.settings = SettingsPanel()
        self.settings.output_format.currentIndexChanged.connect(self._refresh)
        body.addWidget(self.settings)
        shell.addLayout(body, 1)
        self.footer = card("Footer")
        footer = QVBoxLayout(self.footer)
        footer.setContentsMargins(12, 10, 12, 10)
        footer.setSpacing(6)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        footer.addWidget(self.status_label)
        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self.counts_label = caption()
        action_row.addWidget(self.counts_label, 1)
        self.clear_button = QPushButton()
        self.clear_button.setObjectName("Clear")
        self.stop_button = QPushButton()
        self.stop_button.setObjectName("Stop")
        self.start_button = QPushButton()
        self.start_button.setObjectName("Start")
        self.start_button.setAutoDefault(True)  # Enter activates the focused primary control.
        self.clear_button.clicked.connect(self.controller.clear)
        self.stop_button.clicked.connect(self.controller.stop)
        self.start_button.clicked.connect(self.start)
        action_row.addWidget(self.clear_button)
        action_row.addWidget(self.stop_button)
        action_row.addWidget(self.start_button)
        footer.addLayout(action_row)
        self.progress = QProgressBar()
        self.progress.setObjectName("Progress")
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        self.progress.setRange(0, 100)
        footer.addWidget(self.progress)
        shell.addWidget(self.footer)
        self.controller.changed.connect(self._refresh)
        self.controller.log_line.connect(self.log.appendPlainText)
        self.controller.close_ready.connect(self.close)
        QWidget.setTabOrder(self.theme_combo, self.locale_combo)
        QWidget.setTabOrder(self.locale_combo, self.add_button)
        QWidget.setTabOrder(self.add_button, self.folder_button)
        QWidget.setTabOrder(self.folder_button, self.table)
        QWidget.setTabOrder(self.table, self.settings.output_format)
        QWidget.setTabOrder(self.settings.output_format, self.settings.quality)
        QWidget.setTabOrder(self.settings.quality, self.settings.quality_slider)
        QWidget.setTabOrder(self.settings.quality_slider, self.settings.resize_check)
        QWidget.setTabOrder(self.settings.resize_check, self.settings.max_width)
        QWidget.setTabOrder(self.settings.max_width, self.settings.max_height)
        QWidget.setTabOrder(self.settings.max_height, self.settings.postfix)
        QWidget.setTabOrder(self.settings.postfix, self.settings.recursive)
        QWidget.setTabOrder(self.settings.recursive, self.settings.delete_original)
        QWidget.setTabOrder(self.settings.delete_original, self.clear_button)
        QWidget.setTabOrder(self.clear_button, self.stop_button)
        QWidget.setTabOrder(self.stop_button, self.start_button)
        apply_theme(self, self.theme)
        self.retranslate()
        self.log.appendPlainText("event=ready")
        QTimer.singleShot(0, self.controller.initialize)

    @Slot()
    def choose_files(self) -> None:
        if self.controller.busy or self.controller.closing:
            return
        paths, _ = QFileDialog.getOpenFileNames(self, self.t("add"), "", self.t("images_filter"))
        self.add_paths(tuple(Path(path) for path in paths))

    @Slot()
    def choose_folder(self) -> None:
        if self.controller.busy or self.controller.closing:
            return
        path = QFileDialog.getExistingDirectory(self, self.t("folder"))
        if path:
            self.add_paths((Path(path),))

    @Slot(object)
    def add_paths(self, paths: object) -> None:
        if isinstance(paths, tuple) and all(isinstance(path, Path) for path in paths):
            if self.controller.add_paths(paths, recursive=self.settings.recursive.isChecked()):
                self.tabs.setCurrentIndex(0)

    @Slot()
    def start(self) -> None:
        if self.controller.capabilities is None:
            self.controller.initialize()
        elif self.settings.selected_available() and self.controller.can_start:
            c = self.controller
            paths, options, generation = c.paths, self.settings.options(), c.generation
            if options.delete_original:
                dialog = QMessageBox(self)
                dialog.setIcon(QMessageBox.Icon.Warning)
                dialog.setWindowTitle(self.t("delete_confirmation_title"))
                dialog.setText(self.t(
                        "delete_confirmation", count=len(paths), format=options.output_format,
                        quality=options.quality, postfix=options.postfix,
                        bounds=(f"{options.max_width}×{options.max_height}"
                                if options.resize else self.t("no_resize")),
                ))
                dialog.setStandardButtons(
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                dialog.setDefaultButton(QMessageBox.StandardButton.No)
                dialog.button(QMessageBox.StandardButton.Yes).setText(self.t("confirm_yes"))
                dialog.button(QMessageBox.StandardButton.No).setText(self.t("confirm_no"))
                # Same token/palette owner, including the new top-level surface.
                apply_theme(dialog, self.theme)
                dialog.setAutoFillBackground(True)
                try:
                    answer = dialog.exec()
                finally:
                    dialog.deleteLater()
                if answer != QMessageBox.StandardButton.Yes:
                    return
                if (not c.can_start or c.generation != generation or c.paths != paths
                        or self.settings.options() != options):
                    return  # A nested dialog event loop cannot authorize a changed request.
            if c.start(options):
                self.tabs.setCurrentIndex(0)

    @Slot()
    def _change_theme(self) -> None:
        self.theme = str(self.theme_combo.currentData())
        apply_theme(self, self.theme)
        self.add_button.setIcon(add_icon(self.theme))
        self.controller.model.retranslate(self.t, self.theme)
        self._refresh()

    @Slot()
    def _change_language(self) -> None:
        self.language = str(self.locale_combo.currentData())
        self.t = Translator(self.language)
        self.retranslate()

    def retranslate(self) -> None:
        t = self.t
        self.subtitle.setText(t("subtitle"))
        self.add_button.setText(t("add"))
        self.add_button.setIcon(add_icon(self.theme))
        self.folder_button.setText(t("folder"))
        self.queue_heading.setText(t("queue"))
        self.drop_hint.setText(t("drop"))
        self.empty_title.setText(t("empty_title"))
        self.empty_hint.setText(t("drop"))
        self.input_hint.setText(t("inputs"))
        self.settings.retranslate(t)
        self.clear_button.setText(t("clear"))
        self.stop_button.setText(t("stop"))
        self.start_button.setText(t("start"))
        self.tabs.setTabText(0, t("log"))
        self.tabs.setTabText(1, t("details"))
        self.theme_combo.blockSignals(True)
        for index, name in enumerate(("light", "dark")):
            self.theme_combo.setItemText(index, t(name))
        self.theme_combo.blockSignals(False)
        self.theme_combo.setAccessibleName(t("theme"))
        self.locale_combo.setAccessibleName(t("language"))
        self.controller.model.retranslate(t, self.theme)
        self._refresh()

    def _detail_text(self) -> str:
        c, t = self.controller, self.t
        lines: list[str] = []
        if c.failure:
            lines.append(t.error(c.failure))
        if c.selection:
            selection = c.selection
            if selection.issues or selection.errors:
                lines.append(t("selection_issues"))
            for issue in selection.issues[:50]:
                lines.append(str(issue.source) + " — " + t.error(issue.error.code))
            if len(selection.issues) > 50:
                lines.append(t("more", count=len(selection.issues) - 50))
            lines.extend(t.error(info.code) for info in selection.errors)
            if selection.warnings:
                lines.append(t("warnings"))
                lines.extend(t.error(info.code) for info in selection.warnings[:50])
                if len(selection.warnings) > 50:
                    lines.append(t("more", count=len(selection.warnings) - 50))
        if c.result:
            result = c.result
            lines.append(t(result.status))
            lines.extend(t.error(info.code) for info in (*result.errors, *result.warnings))
            for item in result.items[:50]:
                lines.append(f"{item.source.name} — {t(item.status)}")
                if item.artifact:
                    a = item.artifact
                    lines.append(
                        f"{a.path} · {a.publication} · {a.width}×{a.height} · "
                        f"{t.size(a.size_bytes)}"
                    )
                lines.append(t("source_" + item.source_disposition))
                if item.error:
                    lines.append(t.error(item.error.code))
                lines.extend(t.error(info.code) for info in item.warnings)
            if len(result.items) > 50:
                lines.append(t("more", count=len(result.items) - 50))
        return "\n".join(lines) if lines else t("no_details")

    @Slot()
    def _refresh(self) -> None:
        c, t = self.controller, self.t
        idle = not c.busy and not c.closing
        self.add_button.setEnabled(idle and c.capabilities is not None)
        self.folder_button.setEnabled(idle and c.capabilities is not None)
        self.drop_panel.drop_enabled = idle and c.capabilities is not None
        self.settings.set_busy(not idle)
        if c.capabilities is not None and self.settings._capabilities is not c.capabilities:
            self.settings.set_capabilities(c.capabilities, t)
        self.start_button.setEnabled(
            idle
            and (c.capabilities is None or (c.can_start and self.settings.selected_available()))
        )
        self.clear_button.setEnabled(idle and bool(c.paths or c.selection or c.result or c.failure))
        self.stop_button.setEnabled(
            c.busy and c.worker is not None and c.worker.kind != "capabilities" and not c.closing
        )
        self.pages.setCurrentWidget(self.table if c.paths else self.empty_page)
        self.queue_heading.setVisible(bool(c.paths))
        self.drop_hint.setVisible(bool(c.paths))
        selection = c.selection
        issue_count = len(selection.issues) + len(selection.errors) if selection else 0
        self.selection_summary.setText(
            t(
                "selection_summary",
                available=len(c.paths),
                issues=issue_count,
                duplicates=selection.duplicates if selection else 0,
                ignored=selection.ignored if selection else 0,
            )
        )
        self.selection_summary.setVisible(bool(c.paths or selection))
        self.subset_note.setText(t("subset"))
        self.subset_note.setVisible(bool(issue_count and c.paths))
        tone = ""
        status = t(c.state)
        if not c.busy:
            if c.failure:
                status, tone = (
                    t.error(c.failure),
                    "warning" if c.failure.value == "CANCELLED" else "error",
                )
            elif c.result:
                status = t(c.result.status)
                tone = (
                    "success"
                    if c.result.status == "succeeded"
                    else "error"
                    if c.result.status in ("failed", "rejected")
                    else "warning"
                )
                if c.result.options and c.result.options.delete_original:
                    status += " · " + t(
                        "deletion_summary", deleted=c.result.counts.deleted,
                        retained=sum(i.source_disposition == "retained" for i in c.result.items),
                        unknown=sum(i.source_disposition == "unknown" for i in c.result.items),
                    )
                else:
                    status += " · " + t("retained")
        self.status_label.setText(status)
        if self.status_label.property("tone") != tone:
            self.status_label.setProperty("tone", tone)
            self.status_label.style().unpolish(self.status_label)
            self.status_label.style().polish(self.status_label)
        if c.result and not c.busy:
            counts = c.result.counts
            self.counts_label.setText(
                t(
                    "counts",
                    succeeded=counts.succeeded,
                    failed=counts.failed,
                    cancelled=counts.cancelled,
                    published=counts.published,
                    deleted=counts.deleted,
                )
            )
            self.progress.setRange(0, max(1, counts.total))
            self.progress.setValue(counts.succeeded + counts.failed)
        elif c.busy:
            event = c.progress
            if event is not None and event.total is not None:
                self.progress.setRange(0, max(1, event.total))
                self.progress.setValue(event.processed)
                self.counts_label.setText(
                    t("progress", processed=event.processed, total=event.total)
                )
            else:
                self.progress.setRange(0, 0)
                self.counts_label.setText("")
        else:
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
            self.counts_label.setText("")
        detail = self._detail_text()
        if self.details.toPlainText() != detail:
            self.details.setPlainText(detail)
        if not c.busy and (
            c.failure or issue_count or (c.result and c.result.status != "succeeded")
        ):
            self.tabs.setCurrentIndex(1)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self.controller.request_close():
            event.accept()
        else:
            event.ignore()
