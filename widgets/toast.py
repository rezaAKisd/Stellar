from typing import List

from qtpy import QtCore, QtWidgets


class ToastWidget(QtWidgets.QFrame):
    def __init__(self, message: str, level: str = "info", parent=None):
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setProperty("level", level)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        label = QtWidgets.QLabel(message)
        layout.addWidget(label)
        self.style().unpolish(self)
        self.style().polish(self)


class ToastHost(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ToastHost")
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)
        self._layout.addStretch()

    def set_toasts(self, messages: List[object]) -> None:
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        for toast in messages:
            widget = ToastWidget(toast.message, toast.level)
            self._layout.insertWidget(0, widget)
