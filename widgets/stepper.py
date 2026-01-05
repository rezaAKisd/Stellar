from typing import Dict, List

from qtpy import QtCore, QtWidgets


class Stepper(QtWidgets.QFrame):
    stepClicked = QtCore.Signal(object)

    def __init__(self, steps: List[object], parent=None):
        super().__init__(parent)
        self.setObjectName("Stepper")
        self._buttons: Dict[object, QtWidgets.QToolButton] = {}

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        for step in steps:
            button = QtWidgets.QToolButton()
            button.setText(step.name.title())
            button.setCheckable(False)
            button.clicked.connect(lambda _, s=step: self.stepClicked.emit(s))
            button.setObjectName("StepperButton")
            layout.addWidget(button)
            self._buttons[step] = button

        layout.addStretch()

    def set_state(self, current, enabled_steps: List[object]) -> None:
        for step, button in self._buttons.items():
            button.setEnabled(step in enabled_steps)
            state = "done" if step in enabled_steps else "disabled"
            if step == current:
                state = "current"
            button.setProperty("state", state)
            button.style().unpolish(button)
            button.style().polish(button)
