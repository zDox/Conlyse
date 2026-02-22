from __future__ import annotations
from typing import TYPE_CHECKING
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QListWidget, QStackedWidget,
    QLabel, QScrollArea, QWidget, QFrame
)
from PySide6.QtCore import Qt

from conlyse.pages.page import Page
from conlyse.pages.settings_page.settings_fields import ToggleField, SliderField, ComboField, KeybindingField
from conlyse.widgets.mui.icon_button import CIconButton
from conlyse.managers.keybinding_manager.key_action import KeyAction
from conlyse.utils.enums import Theme

if TYPE_CHECKING:
    from conlyse.app import App

class SettingsPage(Page):
    HEADER = True

    def __init__(self, app: App, parent=None):
        super().__init__(app, parent)
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header area for back button
        self.header_container = QWidget()
        self.header_container.setObjectName("settingsHeader")
        header_layout = QHBoxLayout(self.header_container)
        header_layout.setContentsMargins(10, 10, 10, 10)

        self.back_btn = CIconButton("fa5s.arrow-left", size=20, parent=self)
        self.back_btn.setObjectName("settings_back_button")
        self.back_btn.setToolTip("Back")
        self.back_btn.clicked.connect(self.app.page_manager.go_back)
        header_layout.addWidget(self.back_btn)
        header_layout.addStretch()

        main_layout.addWidget(self.header_container)

        # Content horizontal layout
        content_h_layout = QHBoxLayout()
        content_h_layout.setContentsMargins(0, 0, 0, 0)
        content_h_layout.setSpacing(0)

        # Sidebar for categories
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setObjectName("settingsSidebar")
        self.sidebar.currentRowChanged.connect(self._on_category_changed)

        # Content area
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("settingsContent")

        content_h_layout.addWidget(self.sidebar)
        content_h_layout.addWidget(self.content_stack, 1)

        main_layout.addLayout(content_h_layout)

        self._create_sections()

    def _create_sections(self):
        # UI Section
        self._add_section("UI", [
            ("ui.theme", "Dark Mode", ToggleField, {}),
        ])

        # Graphics Section
        self._add_section("Graphics", [
            ("graphics.frame_rate_limit", "FPS Limit", SliderField, {"min_val": 0, "max_val": 240}),
            ("graphics.fullscreen", "Fullscreen", ToggleField, {}),
            ("graphics.anti_aliasing", "Anti-Aliasing", ToggleField, {}),
            ("graphics.vsync", "VSync", ToggleField, {}),
        ])

        # Debug Section
        self._add_section("Debug", [
            ("debug.verbose", "Verbose Logging", ToggleField, {}),
            ("debug.style_sheet_hot_loading", "CSS Hot Loading", ToggleField, {}),
        ])

        # Simulation Section
        self._add_section("Simulation", [
            ("simulation.ups", "Updates per Second", SliderField, {"min_val": 10, "max_val": 120}),
        ])

        # Keybindings Section
        self._add_keybindings_section()

    def _add_keybindings_section(self):
        fields = []
        for action in KeyAction:
            fields.append((f"actions.{action.value}", action.value.replace("_", " ").title(), KeybindingField, {}))
        
        self._add_section("Keybindings", fields, config_type="keybindings")

    def _add_section(self, name: str, fields: list, config_type: str = "main"):
        self.sidebar.addItem(name)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        container = QWidget()
        container.setObjectName("settingsContentContainer")
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel(name)
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        for config_key, label, field_class, kwargs in fields:
            field = field_class(label, **kwargs)
            val = self.app.config_manager.get(config_key, config_type=config_type)
            
            # Special case for theme toggle initialization
            if config_key == "ui.theme" and field_class == ToggleField:
                val = (val == "DARK")
            
            field.set_value(val)
            
            # Connect value_changed
            field.value_changed.connect(lambda new_val, key=config_key, ct=config_type: self._on_setting_changed(key, new_val, ct))
            
            layout.addWidget(field)

        layout.addStretch()
        scroll.setWidget(container)
        self.content_stack.addWidget(scroll)

    def _on_category_changed(self, index: int):
        self.content_stack.setCurrentIndex(index)

    def _on_setting_changed(self, key: str, value: any, config_type: str = "main"):
        # Special case for theme toggle value conversion
        if key == "ui.theme":
            value = Theme.DARK if value else Theme.LIGHT

        self.app.config_manager.set(key, value, config_type=config_type)
        # Some settings might need immediate application
        if config_type == "main":
            if key == "ui.theme":
                self.app.style_manager.set_theme(value)
                self.app.style_manager.update_style()
        elif config_type == "keybindings":
            # Update the keybinding in the manager
            from conlyse.managers.keybinding_manager.key_action import KeyAction
            action_str = key.split('.')[-1]
            try:
                action = KeyAction(action_str)
                self.app.keybinding_manager.set_keybinding(action, value)
            except ValueError:
                pass

    def setup(self, context):
        pass

    def page_update(self, delta_time: float):
        pass

    def clean_up(self):
        pass
