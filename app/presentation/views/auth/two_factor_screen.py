"""Two-Factor Authentication Screen"""
from qtpy.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QCheckBox
)
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QIntValidator


class CodeInput(QWidget):
    """6-digit code input with individual boxes"""

    code_complete = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        self.inputs = []
        for i in range(6):
            digit_input = QLineEdit()
            digit_input.setObjectName("code-digit")
            digit_input.setMaxLength(1)
            digit_input.setAlignment(Qt.AlignCenter)
            digit_input.setFixedSize(50, 60)
            digit_input.setStyleSheet(
                "font-size: 24px; font-weight: 600; "
                "border: 2px solid #d1d1d6; border-radius: 8px; "
                "background-color: white; color: #1d1d1f;"
            )

            # Only allow digits
            digit_input.setValidator(QIntValidator(0, 9))

            # Connect signals
            digit_input.textChanged.connect(
                lambda text, idx=i: self._on_digit_changed(text, idx)
            )
            digit_input.installEventFilter(self)

            layout.addWidget(digit_input)
            self.inputs.append(digit_input)

        # Focus first input
        self.inputs[0].setFocus()

    def eventFilter(self, obj, event):
        """Handle backspace to move to previous input"""
        from qtpy.QtCore import QEvent
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Backspace:
                # Find which input this is
                for i, input_widget in enumerate(self.inputs):
                    if obj == input_widget:
                        if not input_widget.text() and i > 0:
                            # If empty and not first, move to previous
                            self.inputs[i - 1].setFocus()
                            self.inputs[i - 1].clear()
                        return False
        return super().eventFilter(obj, event)

    def _on_digit_changed(self, text: str, index: int):
        """Handle digit input change"""
        if text and index < 5:
            # Move to next input
            self.inputs[index + 1].setFocus()

        # Check if complete
        code = self.get_code()
        if len(code) == 6:
            self.code_complete.emit(code)

    def get_code(self) -> str:
        """Get the complete 6-digit code"""
        return ''.join(inp.text() for inp in self.inputs)

    def clear(self):
        """Clear all inputs"""
        for inp in self.inputs:
            inp.clear()
        self.inputs[0].setFocus()

    def setEnabled(self, enabled: bool):
        """Enable/disable all inputs"""
        for inp in self.inputs:
            inp.setEnabled(enabled)
        super().setEnabled(enabled)


class TwoFactorScreen(QWidget):
    """Two-Factor Authentication screen"""

    # Signals
    verify_clicked = Signal(str, bool)  # code, trust_device
    back_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        # Main layout - center everything
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setContentsMargins(40, 40, 40, 40)

        # Card container
        card = QWidget()
        card.setObjectName("auth-card")
        card.setFixedWidth(500)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(20)
        card_layout.setContentsMargins(40, 40, 40, 40)

        # Back button
        self.back_btn = QPushButton("\u2190 Back")
        self.back_btn.setObjectName("text-button")
        self.back_btn.clicked.connect(self.back_clicked.emit)
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.setStyleSheet(
            "text-align: left; padding: 8px 0; font-size: 14px; "
            "background-color: transparent; border: none; color: #007aff;"
        )
        card_layout.addWidget(self.back_btn, 0, Qt.AlignLeft)

        # Logo
        logo = QLabel("\U0001F4E5")  # Download box emoji
        logo.setObjectName("auth-logo")
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("font-size: 64px;")
        card_layout.addWidget(logo)

        # Title
        title = QLabel("Two-Factor Authentication")
        title.setObjectName("auth-title")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: 600; color: #1d1d1f;")
        card_layout.addWidget(title)

        # Instruction text
        instruction = QLabel(
            "Enter the 6-digit code from your authenticator app"
        )
        instruction.setObjectName("auth-instruction")
        instruction.setAlignment(Qt.AlignCenter)
        instruction.setWordWrap(True)
        instruction.setStyleSheet("font-size: 14px; color: #86868b;")
        card_layout.addWidget(instruction)

        card_layout.addSpacing(10)

        # Code input boxes
        self.code_input = CodeInput()
        self.code_input.code_complete.connect(self._on_code_complete)
        code_container = QWidget()
        code_layout = QHBoxLayout(code_container)
        code_layout.addStretch()
        code_layout.addWidget(self.code_input)
        code_layout.addStretch()
        card_layout.addWidget(code_container)

        card_layout.addSpacing(10)

        # Trust device checkbox
        self.trust_checkbox = QCheckBox("Trust this device")
        self.trust_checkbox.setObjectName("auth-checkbox")
        card_layout.addWidget(self.trust_checkbox)

        card_layout.addSpacing(10)

        # Verify button
        self.verify_btn = QPushButton("Verify")
        self.verify_btn.setObjectName("primary-button")
        self.verify_btn.setMinimumHeight(44)
        self.verify_btn.setEnabled(False)
        self.verify_btn.clicked.connect(self._on_verify)
        self.verify_btn.setCursor(Qt.PointingHandCursor)
        card_layout.addWidget(self.verify_btn)

        # Error message
        self.error_label = QLabel()
        self.error_label.setObjectName("error-message")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        card_layout.addWidget(self.error_label)

        main_layout.addWidget(card)

    def _on_code_complete(self, code: str):
        """Enable verify button when code is complete"""
        self.verify_btn.setEnabled(True)

    def _on_verify(self):
        """Handle verify button click"""
        code = self.code_input.get_code()
        trust = self.trust_checkbox.isChecked()

        if len(code) != 6:
            self.show_error("Please enter the complete 6-digit code")
            return

        self.clear_error()
        self.verify_clicked.emit(code, trust)

    def show_error(self, message: str):
        """Show error message"""
        self.error_label.setText(message)
        self.error_label.show()
        self.code_input.clear()
        self.verify_btn.setEnabled(False)

    def clear_error(self):
        """Clear error message"""
        self.error_label.hide()
        self.error_label.clear()

    def set_loading(self, loading: bool):
        """Set loading state"""
        self.verify_btn.setEnabled(not loading)
        self.code_input.setEnabled(not loading)
        self.back_btn.setEnabled(not loading)

        if loading:
            self.verify_btn.setText("Verifying...")
        else:
            self.verify_btn.setText("Verify")

    def reset(self):
        """Reset the form"""
        self.code_input.clear()
        self.trust_checkbox.setChecked(False)
        self.clear_error()
        self.verify_btn.setEnabled(False)
