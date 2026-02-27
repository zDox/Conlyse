from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
    QMessageBox,
)

from conlyse.pages.page import Page
from conlyse.utils.enums import PageType

if TYPE_CHECKING:
    from conlyse.app import App


class AuthPage(Page):
    """Initial authentication page shown on startup when not logged in.

    Allows the user to:
    - Log in (with optional 2FA).
    - Register a new account.
    - Skip and continue in offline mode.
    """

    HEADER = True

    def __init__(self, app: App, parent=None):
        super().__init__(app, parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        title = QLabel("Welcome to Conlyse")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        subtitle = QLabel("Sign in to sync downloads and Pro features, or continue offline.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        form = QVBoxLayout()
        form.setSpacing(8)

        # Username
        username_label = QLabel("Username")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        form.addWidget(username_label)
        form.addWidget(self.username_input)

        # Password
        password_label = QLabel("Password")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Enter your password")
        form.addWidget(password_label)
        form.addWidget(self.password_input)

        # 2FA (only used when needed)
        self.two_fa_label = QLabel("2FA Code")
        self.two_fa_input = QLineEdit()
        self.two_fa_input.setPlaceholderText("Enter 2FA code")
        form.addWidget(self.two_fa_label)
        form.addWidget(self.two_fa_input)

        layout.addLayout(form)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # Buttons row
        buttons = QHBoxLayout()
        buttons.setSpacing(10)

        self.login_button = QPushButton("Log In")
        self.login_button.clicked.connect(self._on_login_clicked)
        buttons.addWidget(self.login_button)

        self.two_fa_button = QPushButton("Verify 2FA")
        self.two_fa_button.clicked.connect(self._on_two_fa_clicked)
        buttons.addWidget(self.two_fa_button)

        self.register_button = QPushButton("Register")
        self.register_button.clicked.connect(self._on_register_clicked)
        buttons.addWidget(self.register_button)

        self.skip_button = QPushButton("Skip (Offline Mode)")
        self.skip_button.clicked.connect(self._on_skip_clicked)
        buttons.addWidget(self.skip_button)

        layout.addLayout(buttons)
        layout.addStretch()

        # Initial state
        self._refresh_state()

    # ----------------------------------------------------------------- Page API

    def setup(self, context):
        # No special context; just refresh UI state.
        self._refresh_state()

    def page_update(self, delta_time: float):
        # Nothing to update each frame.
        pass

    def clean_up(self):
        # No persistent resources to clean.
        pass

    # ----------------------------------------------------------------- Helpers

    def _refresh_state(self):
        auth = self.app.auth_manager
        is_pending_2fa = auth.pending_two_fa

        self.two_fa_label.setVisible(is_pending_2fa)
        self.two_fa_input.setVisible(is_pending_2fa)
        self.two_fa_button.setEnabled(is_pending_2fa)

    def _on_login_clicked(self):
        from conlyse.managers.auth_manager import LoginResult

        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username or not password:
            self.status_label.setText("Username and password are required.")
            return

        device_name = "Conlyse Desktop"
        result: LoginResult = self.app.auth_manager.login(
            username,
            password,
            device_name=device_name,
        )

        if result.error_message:
            self.status_label.setText(result.error_message)
        elif result.two_fa_required:
            self.status_label.setText("2FA required. Please enter your code.")
        elif result.success:
            self.status_label.setText("Login successful.")
            # Go straight to the main replay list page.
            self.app.page_manager.switch_to(PageType.ReplayListPage)

        self.password_input.clear()
        self._refresh_state()

    def _on_two_fa_clicked(self):
        from conlyse.managers.auth_manager import TwoFAVerifyResult

        code = self.two_fa_input.text().strip()
        if not code:
            self.status_label.setText("Please enter a 2FA code.")
            return

        device_name = "Conlyse Desktop"
        result: TwoFAVerifyResult = self.app.auth_manager.complete_two_fa(
            code,
            device_name=device_name,
        )

        if result.error_message:
            self.status_label.setText(result.error_message)
        elif result.success:
            self.status_label.setText("2FA verification successful.")
            self.app.page_manager.switch_to(PageType.ReplayListPage)

        self.two_fa_input.clear()
        self._refresh_state()

    def _on_register_clicked(self):
        """Simple registration flow using the auth API."""
        import re
        from conlyse.api import ApiError, NetworkError

        username = self.username_input.text().strip()
        password = self.password_input.text()

        # Ask for email in a simple dialog to avoid cluttering the main form.
        email, ok = QMessageBox.getText(
            self,
            "Register",
            "Enter your email address:",
        )
        if not ok or not email:
            return

        email = email.strip()
        if not re.match(r".+@.+\\..+", email):
            self.status_label.setText("Please enter a valid email address.")
            return

        if not username or not password:
            self.status_label.setText("Username and password are required to register.")
            return

        payload = {
            "email": email,
            "username": username,
            "password": password,
        }
        try:
            self.app.api_client.post("/auth/register", json=payload)
        except (ApiError, NetworkError, Exception) as exc:
            self.status_label.setText(f"Registration failed: {exc}")
            return

        QMessageBox.information(
            self,
            "Registration successful",
            "Your account has been created. If email verification is enabled, "
            "please check your inbox for a verification email before logging in.",
        )
        self.status_label.setText("Registration successful. You can now log in.")

    def _on_skip_clicked(self):
        """Skip authentication and continue in offline mode."""
        self.status_label.setText("Continuing in offline mode.")
        self.app.page_manager.switch_to(PageType.ReplayListPage)

