"""A bounded-cost model/view queue; local paths are results, never technical logs."""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, QPersistentModelIndex, Qt
from PySide6.QtGui import QColor

from image_compressor import ItemResult

from .localization import Translator
from .theme import colors


@dataclass(frozen=True)
class Row:
    path: Path
    size: int | None
    status: str = "waiting"
    item: ItemResult | None = None


def path_key(path: Path) -> str:
    return os.path.normcase(os.path.abspath(path))


class QueueModel(QAbstractTableModel):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.rows: list[Row] = []
        self._indices: dict[str, int] = {}
        self.translator = Translator("ru")
        self.theme = "light"

    def replace_selection(self, paths: tuple[Path, ...], sizes: tuple[int | None, ...]) -> None:
        self.beginResetModel()
        self.rows = [Row(path, size) for path, size in zip(paths, sizes)]
        self._indices = {path_key(row.path): index for index, row in enumerate(self.rows)}
        self.endResetModel()

    def reset_statuses(self) -> None:
        self.beginResetModel()
        self.rows = [replace(row, status="waiting", item=None) for row in self.rows]
        self.endResetModel()

    def _set_item(self, item: ItemResult) -> int | None:
        number = self._indices.get(path_key(item.source))
        if number is not None:
            status = (
                "unverified"
                if item.artifact and item.artifact.publication == "unverified"
                else item.status
            )
            self.rows[number] = replace(self.rows[number], status=status, item=item)
        return number

    def apply_item(self, item: ItemResult) -> None:
        number = self._set_item(item)
        if number is not None:
            self.dataChanged.emit(self.index(number, 0), self.index(number, 3))

    def apply_items(self, items: tuple[ItemResult, ...]) -> None:
        indices = [number for item in items if (number := self._set_item(item)) is not None]
        if indices:
            self.dataChanged.emit(self.index(min(indices), 0), self.index(max(indices), 3))

    def retranslate(self, translator: Translator, theme: str) -> None:
        self.translator = translator
        self.theme = theme
        self.headerDataChanged.emit(Qt.Orientation.Horizontal, 0, 3)
        if self.rows:
            self.dataChanged.emit(self.index(0, 0), self.index(len(self.rows) - 1, 3))

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else 4

    def headerData(  # noqa: N802
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ) -> object:
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.translator(("name", "suffix", "bytes", "status")[section])
        return None

    def data(  # noqa: N802
        self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> object:
        if not index.isValid() or not 0 <= index.row() < len(self.rows):
            return None
        row = self.rows[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return (
                row.path.name,
                row.path.suffix.lstrip(".").upper(),
                self.translator.size(row.size),
                self.translator(row.status),
            )[index.column()]
        if role == Qt.ItemDataRole.ToolTipRole:
            lines = [str(row.path), self.translator(row.status)]
            if row.item:
                if row.item.destination:
                    lines.append(str(row.item.destination))
                if row.item.error:
                    lines.append(self.translator.error(row.item.error.code))
                lines.extend(self.translator.error(info.code) for info in row.item.warnings)
                if row.item.artifact:
                    artifact = row.item.artifact
                    lines.append(
                        f"{artifact.format.value} · {artifact.width}×{artifact.height} · "
                        f"{self.translator.size(artifact.size_bytes)} · {artifact.publication}"
                    )
                    lines.append(f"SHA-256: {artifact.sha256}")
            return "\n".join(lines)
        if role == Qt.ItemDataRole.ForegroundRole and index.column() == 3:
            palette = colors(self.theme)
            key = (
                "state/success"
                if row.status == "succeeded"
                else "state/error"
                if row.status == "failed"
                else "state/warning"
                if row.status in ("unverified", "cancelled")
                else "text/secondary"
            )
            return QColor(palette[key])
        return None
