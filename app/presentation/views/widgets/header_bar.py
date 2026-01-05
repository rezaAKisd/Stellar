"""Header Bar Widget"""
from qtpy.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton,
    QDialog, QVBoxLayout, QTextEdit, QMessageBox
)
from qtpy.QtCore import Signal


class SessionDialog(QDialog):
    """Dialog for entering session token"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connect Instagram Session")
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)

        layout = QVBoxLayout(self)

        # Instructions
        instructions = QLabel(
            "IMPORTANT: Do NOT enter your Instagram password here.\n\n"
            "To connect your session:\n"
            "1. Click 'Open Browser' and log in to Instagram (official website)\n"
            "2. Copy your session token or session string\n"
            "3. Paste it below and click 'Save Session'\n\n"
            "Disclaimer: Only download content you have rights to access."
        )
        instructions.setWordWrap(True)
        instructions.setObjectName("instructions")
        layout.addWidget(instructions)

        # Session token input
        self.session_input = QTextEdit()
        self.session_input.setPlaceholderText("Paste session token here...")
        self.session_input.setMaximumHeight(100)
        layout.addWidget(self.session_input)

        # Buttons
        btn_layout = QHBoxLayout()

        self.open_browser_btn = QPushButton("Open Browser")
        self.open_browser_btn.setObjectName("secondary")
        self.open_browser_btn.clicked.connect(self._open_browser)
        btn_layout.addWidget(self.open_browser_btn)

        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("secondary")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Save Session")
        self.save_btn.setObjectName("primary")
        self.save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)

    def _open_browser(self):
        """Open Instagram in browser"""
        import webbrowser
        webbrowser.open("https://www.instagram.com")

    def get_session_token(self) -> str:
        """Get entered session token"""
        return self.session_input.toPlainText().strip()


class HeaderBar(QWidget):
    """Top header bar with connection status and actions"""

    connect_clicked = Signal()
    use_existing_clicked = Signal()
    disconnect_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Setup UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)

        # App name
        self.app_name = QLabel("Highlight Studio")
        self.app_name.setObjectName("app-title")
        layout.addWidget(self.app_name)

        layout.addSpacing(20)

        # Status pill
        from .status_pill import StatusPill
        self.status_pill = StatusPill("Not connected", "gray")
        layout.addWidget(self.status_pill)

        layout.addStretch()

        # Disclaimer
        disclaimer = QLabel("Only download content you have rights to access.")
        disclaimer.setObjectName("disclaimer")
        layout.addWidget(disclaimer)

        layout.addSpacing(20)

        # Connect button
        self.connect_btn = QPushButton("Connect Instagram")
        self.connect_btn.setObjectName("primary")
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        layout.addWidget(self.connect_btn)

        # Use existing session button
        self.existing_btn = QPushButton("Use existing session")
        self.existing_btn.setObjectName("secondary")
        self.existing_btn.clicked.connect(self._on_use_existing_clicked)
        layout.addWidget(self.existing_btn)

        # Disconnect button (initially hidden)
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setObjectName("secondary")
        self.disconnect_btn.clicked.connect(self.disconnect_clicked.emit)
        self.disconnect_btn.hide()
        layout.addWidget(self.disconnect_btn)

    def _on_connect_clicked(self):
        """Handle connect button click"""
        dialog = SessionDialog(self)
        if dialog.exec_():
            session_token = dialog.get_session_token()
            if session_token:
                self.connect_clicked.emit()
                # In real implementation, we'd pass the token
                # For now, emit with placeholder
                from qtpy.QtCore import QTimer
                QTimer.singleShot(0, lambda: self._emit_session_token(session_token))

    def _on_use_existing_clicked(self):
        """Handle use existing session"""
        dialog = SessionDialog(self)
        dialog.setWindowTitle("Use Existing Session")
        if dialog.exec_():
            session_token = dialog.get_session_token()
            if session_token:
                self.use_existing_clicked.emit()
                QTimer.singleShot(0, lambda: self._emit_session_token(session_token))

    def _emit_session_token(self, token: str):
        """Store token for ViewModel to pick up"""
        self._last_session_token = token

    def get_last_session_token(self) -> str:
        """Get the last entered session token"""
        return getattr(self, '_last_session_token', '')

    def update_connection_status(self, is_connected: bool, session_present: bool, status_text: str):
        """Update connection status display"""
        if is_connected:
            self.status_pill.set_status("Connected", "green")
            self.disconnect_btn.show()
        else:
            self.status_pill.set_status(status_text, "gray")
            self.disconnect_btn.hide()
