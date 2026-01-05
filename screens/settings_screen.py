from qtpy import QtCore, QtWidgets

from models import ExportMode
from store import PreviewSettings, SaveSettings, SetExportMode, UpdateVideoSetting


class SettingsScreen(QtWidgets.QWidget):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.store.stateChanged.connect(self.render)

        title = QtWidgets.QLabel("Video Settings")
        title.setObjectName("Title")

        self.presets_card = self._build_presets()
        self.export_card = self._build_export_mode()
        self.advanced_card = self._build_advanced()
        self.preview_card = self._build_preview()

        self.save_bar = QtWidgets.QFrame()
        self.save_bar.setObjectName("StickyBar")
        save_layout = QtWidgets.QHBoxLayout(self.save_bar)
        save_layout.setContentsMargins(16, 12, 16, 12)
        save_layout.addStretch()
        self.save_button = QtWidgets.QPushButton("Save Settings")
        self.save_button.setObjectName("PrimaryButton")
        self.save_button.clicked.connect(lambda: self.store.dispatch(SaveSettings()))
        save_layout.addWidget(self.save_button)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(title)
        layout.addWidget(self.presets_card)
        layout.addWidget(self.export_card)
        layout.addWidget(self.advanced_card)
        layout.addWidget(self.preview_card)
        layout.addStretch()
        layout.addWidget(self.save_bar)

        self.render(self.store.get_state())

    def _build_presets(self) -> QtWidgets.QFrame:
        card = QtWidgets.QFrame()
        card.setObjectName("Card")
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        title = QtWidgets.QLabel("Presets")
        title.setObjectName("SectionTitle")

        chip_layout = QtWidgets.QHBoxLayout()
        self.preset_group = QtWidgets.QButtonGroup(self)
        for name in ["Classic", "Minimal", "Story Repost", "Cinematic"]:
            chip = QtWidgets.QPushButton(name)
            chip.setCheckable(True)
            chip.setObjectName("Chip")
            self.preset_group.addButton(chip)
            chip_layout.addWidget(chip)
        self.preset_group.buttonClicked.connect(self._preset_changed)

        save_label = QtWidgets.QLabel("Save as preset…")
        save_label.setObjectName("Muted")

        layout.addWidget(title)
        layout.addLayout(chip_layout)
        layout.addWidget(save_label)
        return card

    def _build_export_mode(self) -> QtWidgets.QFrame:
        card = QtWidgets.QFrame()
        card.setObjectName("Card")
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        title = QtWidgets.QLabel("Export Mode")
        title.setObjectName("SectionTitle")

        self.merged_radio = QtWidgets.QRadioButton("Merged video (single file)")
        self.separate_radio = QtWidgets.QRadioButton("Separate clips (one file per story)")
        self.merged_radio.toggled.connect(self._export_mode_changed)

        self.also_merged_checkbox = QtWidgets.QCheckBox("Also create merged video")
        self.also_merged_checkbox.toggled.connect(
            lambda value: self.store.dispatch(UpdateVideoSetting("also_create_merged", value))
        )

        self.naming_input = QtWidgets.QLineEdit()
        self.naming_input.setObjectName("Input")
        self.naming_input.setPlaceholderText("highlight_{index}_{date}")
        self.naming_input.textChanged.connect(
            lambda text: self.store.dispatch(UpdateVideoSetting("naming_template", text))
        )

        self.output_label = QtWidgets.QLabel("Exports/<ProjectName>/clips/")
        self.output_label.setObjectName("Muted")

        layout.addWidget(title)
        layout.addWidget(self.merged_radio)
        layout.addWidget(self.separate_radio)
        layout.addWidget(self.also_merged_checkbox)
        layout.addWidget(self.naming_input)
        layout.addWidget(self.output_label)
        return card

    def _build_advanced(self) -> QtWidgets.QFrame:
        card = QtWidgets.QFrame()
        card.setObjectName("Card")
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        title = QtWidgets.QLabel("Advanced")
        title.setObjectName("SectionTitle")

        grid = QtWidgets.QGridLayout()
        grid.addWidget(QtWidgets.QLabel("Aspect ratio"), 0, 0)
        self.aspect_combo = QtWidgets.QComboBox()
        self.aspect_combo.addItems(["9:16", "1:1", "16:9"])
        self.aspect_combo.currentTextChanged.connect(
            lambda value: self.store.dispatch(UpdateVideoSetting("aspect_ratio", value))
        )
        grid.addWidget(self.aspect_combo, 0, 1)

        grid.addWidget(QtWidgets.QLabel("Resolution"), 1, 0)
        self.resolution_combo = QtWidgets.QComboBox()
        self.resolution_combo.addItems(["720p", "1080p"])
        self.resolution_combo.currentTextChanged.connect(
            lambda value: self.store.dispatch(UpdateVideoSetting("resolution", value))
        )
        grid.addWidget(self.resolution_combo, 1, 1)

        grid.addWidget(QtWidgets.QLabel("FPS"), 2, 0)
        self.fps_combo = QtWidgets.QComboBox()
        self.fps_combo.addItems(["30", "60"])
        self.fps_combo.currentTextChanged.connect(
            lambda value: self.store.dispatch(UpdateVideoSetting("fps", int(value)))
        )
        grid.addWidget(self.fps_combo, 2, 1)

        grid.addWidget(QtWidgets.QLabel("Transition"), 3, 0)
        self.transition_combo = QtWidgets.QComboBox()
        self.transition_combo.addItems(["None", "Fade", "Slide"])
        self.transition_combo.currentTextChanged.connect(
            lambda value: self.store.dispatch(UpdateVideoSetting("transition", value))
        )
        grid.addWidget(self.transition_combo, 3, 1)

        self.duration_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.duration_slider.setRange(2, 6)
        self.duration_slider.setValue(3)
        self.duration_slider.valueChanged.connect(
            lambda value: self.store.dispatch(UpdateVideoSetting("still_duration", value))
        )
        self.duration_label = QtWidgets.QLabel("Still image duration: 3s")
        self.duration_label.setObjectName("Muted")
        self.duration_slider.valueChanged.connect(
            lambda value: self.duration_label.setText(f"Still image duration: {value}s")
        )

        self.watermark_checkbox = QtWidgets.QCheckBox("Watermark")
        self.watermark_checkbox.toggled.connect(
            lambda value: self.store.dispatch(UpdateVideoSetting("watermark", value))
        )

        layout.addWidget(title)
        layout.addLayout(grid)
        layout.addWidget(self.duration_label)
        layout.addWidget(self.duration_slider)
        layout.addWidget(self.watermark_checkbox)
        return card

    def _build_preview(self) -> QtWidgets.QFrame:
        card = QtWidgets.QFrame()
        card.setObjectName("Card")
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        title = QtWidgets.QLabel("Preview")
        title.setObjectName("SectionTitle")
        self.preview_button = QtWidgets.QPushButton("Preview 5 seconds")
        self.preview_button.setObjectName("SecondaryButton")
        self.preview_button.clicked.connect(lambda: self.store.dispatch(PreviewSettings()))
        self.preview_label = QtWidgets.QLabel("")
        self.preview_label.setObjectName("Muted")
        layout.addWidget(title)
        layout.addWidget(self.preview_button)
        layout.addWidget(self.preview_label)
        return card

    def _preset_changed(self, button):
        self.store.dispatch(UpdateVideoSetting("preset_name", button.text()))

    def _export_mode_changed(self):
        mode = ExportMode.MERGED if self.merged_radio.isChecked() else ExportMode.SEPARATE
        self.store.dispatch(SetExportMode(mode))

    def render(self, state) -> None:
        project = state.projects.get(state.current_project_id)
        if not project:
            return
        settings = project.settings

        for button in self.preset_group.buttons():
            button.setChecked(button.text() == settings.preset_name)

        self.merged_radio.blockSignals(True)
        self.separate_radio.blockSignals(True)
        self.merged_radio.setChecked(settings.export_mode == ExportMode.MERGED)
        self.separate_radio.setChecked(settings.export_mode == ExportMode.SEPARATE)
        self.merged_radio.blockSignals(False)
        self.separate_radio.blockSignals(False)

        separate = settings.export_mode == ExportMode.SEPARATE
        self.also_merged_checkbox.setVisible(separate)
        self.naming_input.setVisible(separate)
        self.output_label.setVisible(separate)
        self.also_merged_checkbox.blockSignals(True)
        self.also_merged_checkbox.setChecked(settings.also_create_merged)
        self.also_merged_checkbox.blockSignals(False)
        self.naming_input.blockSignals(True)
        self.naming_input.setText(settings.naming_template)
        self.naming_input.blockSignals(False)

        self.aspect_combo.blockSignals(True)
        self.aspect_combo.setCurrentText(settings.aspect_ratio)
        self.aspect_combo.blockSignals(False)
        self.resolution_combo.blockSignals(True)
        self.resolution_combo.setCurrentText(settings.resolution)
        self.resolution_combo.blockSignals(False)
        self.fps_combo.blockSignals(True)
        self.fps_combo.setCurrentText(str(settings.fps))
        self.fps_combo.blockSignals(False)
        self.transition_combo.blockSignals(True)
        self.transition_combo.setCurrentText(settings.transition)
        self.transition_combo.blockSignals(False)
        self.duration_slider.blockSignals(True)
        self.duration_slider.setValue(settings.still_duration)
        self.duration_slider.blockSignals(False)
        self.watermark_checkbox.blockSignals(True)
        self.watermark_checkbox.setChecked(settings.watermark)
        self.watermark_checkbox.blockSignals(False)

        if project.preview_state == "rendering":
            self.preview_label.setText("Rendering preview…")
        elif project.preview_state == "ready":
            self.preview_label.setText("Preview ready")
        else:
            self.preview_label.setText("")

        self.save_button.setEnabled(project.settings_dirty)
