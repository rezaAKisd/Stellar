from qtpy import QtCore, QtWidgets


class StatusPill(QtWidgets.QLabel):
    def __init__(self, text: str = "", tone: str = "neutral", parent=None):
        super().__init__(text, parent)
        self.setObjectName("StatusPill")
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.set_tone(tone)

    def set_tone(self, tone: str) -> None:
        self.setProperty("tone", tone)
        self.style().unpolish(self)
        self.style().polish(self)

    def set_text(self, text: str, tone: str) -> None:
        self.setText(text)
        self.set_tone(tone)
