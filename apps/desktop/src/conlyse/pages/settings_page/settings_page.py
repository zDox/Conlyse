from __future__ import annotations
from typing import TYPE_CHECKING
from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QStackedWidget,
    QLabel,
    QScrollArea,
    QWidget,
    QFrame,
    QPushButton,
    QLineEdit,
)
from PySide6.QtCore import Qt

from conlyse.pages.page import Page
from conlyse.pages.settings_page.settings_fields import ToggleField, SliderField, ComboField, KeybindingField, TextField
from conlyse.utils.downloads import download_to_file
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

        # API Section
        self._add_section("API", [
            ("api.base_url", "API Base URL", TextField, {}),
            ("api.timeout_seconds", "API Timeout (seconds)", SliderField, {"min_val": 1, "max_val": 60}),
        ])

        # Simulation Section
        self._add_section("Simulation", [
            ("simulation.ups", "Updates per Second", SliderField, {"min_val": 10, "max_val": 120}),
        ])

        # Keybindings Section
        self._add_keybindings_section()

        # Account / Authentication Section
        self._add_account_section()

        # Static map data Section
        self._add_static_map_section()

        # Updates Section
        self._add_update_section()

    def _add_keybindings_section(self):
        categories = {
            "Global": [
                KeyAction.TOGGLE_DRAWER,
                KeyAction.RELOAD_STYLES,
                KeyAction.TOGGLE_THEME,
                KeyAction.TOGGLE_PERFORMANCE_WINDOW,
            ],
            "Replay List": [
                KeyAction.OPEN_REPLAY_FILE_DIALOG,
            ],
            "Map Page - Camera": [
                KeyAction.CAMERA_MOVE_UP,
                KeyAction.CAMERA_MOVE_DOWN,
                KeyAction.CAMERA_MOVE_LEFT,
                KeyAction.CAMERA_MOVE_RIGHT,
                KeyAction.CAMERA_ZOOM_IN,
                KeyAction.CAMERA_ZOOM_OUT,
            ],
            "Map Page - Views": [
                KeyAction.SWITCH_TO_POLITICAL_MAP_VIEW,
                KeyAction.SWITCH_TO_TERRAIN_MAP_VIEW,
                KeyAction.SWITCH_TO_RESOURCE_MAP_VIEW,
            ],
            "Map Page - Overlays": [
                KeyAction.TOGGLE_CONNECTIONS_OVERLAY,
                KeyAction.TOGGLE_PROVINCE_LABELS,
                KeyAction.TOGGLE_NATION_LABELS,
            ],
            "Debug": [
                KeyAction.DEBUG_TOGGLE_MOUSE_CLICK_LOGGING,
            ]
        }
        
        self.sidebar.addItem("Keybindings")
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        container = QWidget()
        container.setObjectName("settingsContentContainer")
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Keybindings")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        for cat_name, actions in categories.items():
            cat_label = QLabel(cat_name)
            cat_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 15px; color: #888;")
            layout.addWidget(cat_label)
            
            for action in actions:
                config_key = f"actions.{action.value}"
                label = action.value.replace("_", " ").title()
                field = KeybindingField(label)
                val = self.app.config_manager.get(config_key, config_type="keybindings")
                field.set_value(val)
                field.value_changed.connect(lambda new_val, key=config_key: self._on_setting_changed(key, new_val, "keybindings"))
                layout.addWidget(field)

        layout.addStretch()
        scroll.setWidget(container)
        self.content_stack.addWidget(scroll)

    def _add_account_section(self):
        self.sidebar.addItem("Account")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        container.setObjectName("settingsContentContainer")
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Account")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        # Status label
        self.account_status_label = QLabel()
        layout.addWidget(self.account_status_label)

        # Username field
        username_label = QLabel("Username")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        layout.addWidget(username_label)
        layout.addWidget(self.username_input)

        # Password field
        password_label = QLabel("Password")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Enter your password")
        layout.addWidget(password_label)
        layout.addWidget(self.password_input)

        # 2FA code field (shown only when needed)
        self.two_fa_code_label = QLabel("2FA Code")
        self.two_fa_code_input = QLineEdit()
        self.two_fa_code_input.setPlaceholderText("Enter 2FA code")
        layout.addWidget(self.two_fa_code_label)
        layout.addWidget(self.two_fa_code_input)

        # Buttons row
        button_row = QHBoxLayout()
        self.login_button = QPushButton("Log In")
        self.two_fa_button = QPushButton("Verify 2FA")
        self.logout_button = QPushButton("Log Out")

        self.login_button.clicked.connect(self._on_login_clicked)
        self.two_fa_button.clicked.connect(self._on_two_fa_clicked)
        self.logout_button.clicked.connect(self._on_logout_clicked)

        button_row.addWidget(self.login_button)
        button_row.addWidget(self.two_fa_button)
        button_row.addWidget(self.logout_button)
        button_row.addStretch()
        layout.addLayout(button_row)

        layout.addStretch()
        scroll.setWidget(container)
        self.content_stack.addWidget(scroll)

        # Initialize UI state based on current auth status
        self._refresh_account_section()

    def _add_static_map_section(self):
        """Settings section for downloading static map data from the API."""
        self.sidebar.addItem("Maps")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        container.setObjectName("settingsContentContainer")
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Static Map Data")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        description = QLabel(
            "Download static map data files from the Conlyse API.\n"
            "These files are stored locally under app_data/static_maps for future use."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        map_id_label = QLabel("Map ID")
        self.static_map_id_input = QLineEdit()
        self.static_map_id_input.setPlaceholderText("Enter map ID (e.g. main_world)")
        layout.addWidget(map_id_label)
        layout.addWidget(self.static_map_id_input)

        self.static_map_status_label = QLabel()
        layout.addWidget(self.static_map_status_label)

        download_button = QPushButton("Download Static Map Data")
        download_button.clicked.connect(self._on_download_static_map_clicked)
        layout.addWidget(download_button)

        layout.addStretch()
        scroll.setWidget(container)
        self.content_stack.addWidget(scroll)

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
            elif key == "graphics.frame_rate_limit":
                self.app.update_frame_rate_limit()
            elif key == "graphics.fullscreen":
                self.app.toggle_fullscreen()
            elif key == "graphics.vsync":
                # VSync requires a restart as it's set in QSurfaceFormat before widget creation
                pass
            elif key == "simulation.ups":
                self.app.update_simulation_rate()
        elif config_type == "keybindings":
            # Update the keybinding in the manager
            from conlyse.managers.keybinding_manager.key_action import KeyAction
            action_str = key.split('.')[-1]
            try:
                action = KeyAction(action_str)
                self.app.keybinding_manager.set_keybinding(action, value)
                self.app.config_manager.set(key, value, config_type="keybindings")
            except ValueError:
                pass

    def _refresh_account_section(self):
        """Update account section UI to reflect current authentication state."""
        auth = self.app.auth_manager
        if auth.is_authenticated and auth.current_user:
            user = auth.current_user
            role = user.role
            tier = auth.subscription_tier or "unknown tier"
            status_text = f"Signed in as {user.email} ({role}, {tier})"
        else:
            status_text = "Not signed in"

        self.account_status_label.setText(status_text)

        # 2FA controls are only useful when a login is pending 2FA.
        is_pending_2fa = auth.pending_two_fa
        self.two_fa_code_label.setVisible(is_pending_2fa)
        self.two_fa_code_input.setVisible(is_pending_2fa)
        self.two_fa_button.setEnabled(is_pending_2fa)

        # Logout only makes sense when authenticated.
        self.logout_button.setEnabled(auth.is_authenticated)

    def _on_login_clicked(self):
        from conlyse.managers.auth_manager import LoginResult

        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username or not password:
            self.account_status_label.setText("Username and password are required.")
            return

        # Device name can be a simple identifier for now.
        device_name = "Conlyse Desktop"
        result: LoginResult = self.app.auth_manager.login(username, password, device_name=device_name)

        if result.error_message:
            self.account_status_label.setText(result.error_message)
        elif result.two_fa_required:
            self.account_status_label.setText("2FA required. Please enter your code.")
        elif result.success:
            self.account_status_label.setText("Login successful.")

        # Clear password field after attempt.
        self.password_input.clear()
        self._refresh_account_section()

    def _on_two_fa_clicked(self):
        from conlyse.managers.auth_manager import TwoFAVerifyResult

        code = self.two_fa_code_input.text().strip()
        if not code:
            self.account_status_label.setText("Please enter a 2FA code.")
            return

        device_name = "Conlyse Desktop"
        result: TwoFAVerifyResult = self.app.auth_manager.complete_two_fa(code, device_name=device_name)

        if result.error_message:
            self.account_status_label.setText(result.error_message)
        elif result.success:
            self.account_status_label.setText("2FA verification successful.")

        self.two_fa_code_input.clear()
        self._refresh_account_section()

    def _on_logout_clicked(self):
        self.app.auth_manager.logout()
        self.account_status_label.setText("Logged out.")
        self._refresh_account_section()

    def _on_download_static_map_clicked(self):
        """Download static map data file from the API to app_data/static_maps."""
        import os

        map_id = self.static_map_id_input.text().strip()
        if not map_id:
            self.static_map_status_label.setText("Please enter a map ID.")
            return

        try:
            response = self.app.api_client.get(
                f"/downloads/static-map-data/{map_id}",
                requires_auth=False,
            )
        except Exception as exc:
            self.static_map_status_label.setText(f"Failed to fetch static map URL: {exc}")
            return

        url = response.get("url")
        if not url:
            self.static_map_status_label.setText("API response did not contain a download URL.")
            return

        dest_dir = os.path.join("app_data", "static_maps")
        dest_path = os.path.join(dest_dir, f"{map_id}.json")

        try:
            download_to_file(url, dest_path)
        except Exception as exc:
            self.static_map_status_label.setText(f"Download failed: {exc}")
            return

        self.static_map_status_label.setText(f"Static map downloaded to {dest_path}")

    def _add_update_section(self):
        """Settings section for checking and downloading desktop updates."""
        self.sidebar.addItem("Updates")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        container.setObjectName("settingsContentContainer")
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Updates")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        self.update_current_label = QLabel()
        self.update_latest_label = QLabel("Latest available: unknown")
        self.update_status_label = QLabel()

        layout.addWidget(self.update_current_label)
        layout.addWidget(self.update_latest_label)
        layout.addWidget(self.update_status_label)

        button_row = QHBoxLayout()
        self.check_updates_button = QPushButton("Check for Updates")
        self.download_update_button = QPushButton("Download Latest")

        self.check_updates_button.clicked.connect(self._on_check_updates_clicked)
        self.download_update_button.clicked.connect(self._on_download_update_clicked)

        button_row.addWidget(self.check_updates_button)
        button_row.addWidget(self.download_update_button)
        button_row.addStretch()
        layout.addLayout(button_row)

        layout.addStretch()
        scroll.setWidget(container)
        self.content_stack.addWidget(scroll)

        self._refresh_update_section()

    def _refresh_update_section(self):
        """Update the Updates section labels and button states."""
        um = self.app.update_manager
        self.update_current_label.setText(f"Current version: {um.current_version}")

        info = um.last_info
        if info:
            self.update_latest_label.setText(f"Latest available: {info.latest_version}")
        else:
            self.update_latest_label.setText("Latest available: unknown")

        api_online = self.app.api_client.last_ok is not False  # Treat None as \"unknown/assumed online\".
        self.check_updates_button.setEnabled(api_online)
        self.download_update_button.setEnabled(api_online and um.has_update)

        if um.last_error:
            self.update_status_label.setText(um.last_error)

    def _on_check_updates_clicked(self):
        um = self.app.update_manager
        info = um.check_for_updates()
        if info is None:
            # Error message is stored in um.last_error and shown by refresh.
            pass
        else:
            if um.has_update:
                self.update_status_label.setText(
                    f"Update available: {info.latest_version} (current {info.current_version})"
                )
            else:
                self.update_status_label.setText("You are running the latest version.")

        self._refresh_update_section()

    def _on_download_update_clicked(self):
        um = self.app.update_manager
        dest_path = um.download_latest()
        if dest_path is None:
            if um.last_error:
                self.update_status_label.setText(um.last_error)
            else:
                self.update_status_label.setText("Failed to download update.")
            self._refresh_update_section()
            return

        self.update_status_label.setText(f"Update downloaded to {dest_path}")
        self._refresh_update_section()

    def setup(self, context):
        pass

    def page_update(self, delta_time: float):
        pass

    def clean_up(self):
        pass
