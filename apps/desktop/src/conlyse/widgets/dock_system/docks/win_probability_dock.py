"""Win-probability dock for the MapPage sidebar — live per-player predictions."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame
from PySide6.QtWidgets import QGridLayout
from PySide6.QtWidgets import QLabel
from PySide6.QtWidgets import QProgressBar
from PySide6.QtWidgets import QScrollArea
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QWidget
from conflict_interface.hook_system.replay_hook_event import ReplayHookEvent
from conflict_interface.hook_system.replay_hook_tag import ReplayHookTag
from conflict_interface.interface.replay_interface import ReplayInterface
from ml.predict import Predictor

from conlyse.logger import get_logger
from conlyse.utils.win_probability import build_snapshots
from conlyse.widgets.dock_system.docks.dock import Dock

logger = get_logger()


class WinProbabilityDock(Dock):
    """Dock displaying each player's live win probability, predicted by the
    bundled LightGBM model from the current replay tick's game state."""

    subscribed_tags = {ReplayHookTag.ProvinceChanged, ReplayHookTag.PlayerChanged}

    def __init__(self, ritf: ReplayInterface, model_path: Path | None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ritf = ritf
        self.setObjectName("win_probability_dock")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._predictor: Predictor | None = None
        if model_path is not None:
            try:
                self._predictor = Predictor(model_path)
            except Exception:
                logger.exception("Failed to load win-probability model from %s", model_path)

        self._rows: dict[int, tuple[QLabel, QProgressBar]] = {}
        self._content_layout: QVBoxLayout | None = None
        self._setup_ui()
        self._update_predictions()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Win Probability")
        title.setObjectName("dock_title")
        layout.addWidget(title)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("dock_separator")
        layout.addWidget(separator)

        if self._predictor is None:
            layout.addWidget(QLabel("Win-probability model unavailable."))
            layout.addStretch()
            return

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setSpacing(8)
        self._content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _row_widget(self, nation_name: str, is_ai: bool) -> tuple[QWidget, QLabel, QProgressBar]:
        widget = QWidget()
        widget.setObjectName("win_probability_item")

        grid = QGridLayout(widget)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setSpacing(6)

        label = f"{nation_name} (AI)" if is_ai else nation_name
        name_label = QLabel(label)
        name_label.setObjectName("dock_item_title")

        bar = QProgressBar()
        bar.setObjectName("win_probability_bar")
        bar.setRange(0, 100)
        bar.setTextVisible(True)
        bar.setFormat("%p%")

        grid.addWidget(name_label, 0, 0)
        grid.addWidget(bar, 1, 0)

        return widget, name_label, bar

    def _update_predictions(self) -> None:
        if self._predictor is None or self._content_layout is None:
            return

        snapshots = build_snapshots(self.ritf)
        if not snapshots:
            return

        probabilities = self._predictor.predict(snapshots)
        by_player = {s["player_id"]: s for s in snapshots}
        ranking = sorted(probabilities.items(), key=lambda item: item[1], reverse=True)

        # Remove rows for players no longer present (e.g. defeated since last update)
        for player_id in list(self._rows):
            if player_id not in probabilities:
                _name_label, bar = self._rows.pop(player_id)
                row_widget = bar.parentWidget()
                self._content_layout.removeWidget(row_widget)
                row_widget.deleteLater()

        for index, (player_id, probability) in enumerate(ranking):
            snapshot = by_player[player_id]
            if player_id not in self._rows:
                row_widget, name_label, bar = self._row_widget(snapshot["nation_name"], bool(snapshot["is_ai"]))
                self._rows[player_id] = (name_label, bar)
                self._content_layout.insertWidget(index, row_widget)
            else:
                name_label, bar = self._rows[player_id]
                row_widget = name_label.parentWidget()
                self._content_layout.removeWidget(row_widget)
                self._content_layout.insertWidget(index, row_widget)

            percent = max(0, min(100, round(probability * 100)))
            bar.setValue(percent)

    def process_events(self, events: dict[ReplayHookTag, list[ReplayHookEvent]]) -> None:
        self._update_predictions()
