import os
from PySide6.QtCore import Qt, QDir, Signal, Slot
from PySide6.QtGui import QIcon, QPixmap, QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QDialogButtonBox, QFileDialog,
    QComboBox, QSpinBox, QButtonGroup, QRadioButton, QCheckBox,
    QTreeView, QFileSystemModel, QScrollArea, QColorDialog, QDoubleSpinBox, QWidget
)


class MultiFolderDialog(QDialog):
    """دیالوگ سفارشی برای انتخاب چندین پوشه"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("انتخاب چندین پوشه")
        self.setMinimumSize(800, 500)

        layout = QVBoxLayout(self)

        # یک برچسب راهنما
        info_label = QLabel("برای انتخاب چندین پوشه، از کلیدهای Ctrl یا Shift همراه با کلیک استفاده کنید.")
        layout.addWidget(info_label)

        # نمای درختی برای انتخاب پوشه‌ها
        self.tree_view = QTreeView()
        self.tree_view.setSelectionMode(QTreeView.ExtendedSelection)
        layout.addWidget(self.tree_view)

        # مدل سیستم فایل
        self.model = QFileSystemModel()
        self.model.setFilter(QDir.AllDirs | QDir.NoDotAndDotDot)  # فقط پوشه‌ها
        self.model.setRootPath(QDir.rootPath())

        self.tree_view.setModel(self.model)
        self.tree_view.setRootIndex(self.model.index(QDir.homePath()))  # شروع از پوشه خانه کاربر

        # فقط ستون‌های نام و مسیر را نمایش دهید
        self.tree_view.setColumnWidth(0, 300)
        for i in range(1, self.model.columnCount()):
            self.tree_view.hideColumn(i)

        # دکمه‌های تایید و لغو
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def selected_folders(self):
        """پوشه‌های انتخاب شده را به‌عنوان لیستی از مسیرها برگرداند"""
        indexes = self.tree_view.selectedIndexes()
        paths = []

        # فقط ستون نام را در نظر بگیرید تا از تکرار جلوگیری شود
        for index in indexes:
            if index.column() == 0:  # ستون نام
                path = self.model.filePath(index)
                if os.path.isdir(path) and path not in paths:
                    paths.append(path)

        return paths


class SettingsDialog(QDialog):
    def __init__(self, settings, queue_manager, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.queue_manager = queue_manager
        self.setWindowTitle("تنظیمات")
        self.setMinimumWidth(500)
        self.setMinimumHeight(600)  # تنظیم ارتفاع مناسب

        # ایجاد اسکرول اریا برای دیده شدن همه گزینه‌ها
        self.main_layout = QVBoxLayout(self)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        # ویجت داخل اسکرول اریا
        self.scroll_widget = QWidget()
        self.layout = QVBoxLayout(self.scroll_widget)
        self.layout.setSpacing(15)

        # ایجاد محتوای تنظیمات
        self.setup_ui()

        # دکمه‌های تایید و لغو در پایین صفحه (خارج از اسکرول)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        # تنظیم اسکرول و دکمه‌ها
        self.scroll_area.setWidget(self.scroll_widget)
        self.main_layout.addWidget(self.scroll_area)
        self.main_layout.addWidget(buttons)

    def setup_ui(self):
        # متد طولانی است و شامل ایجاد تمام کنترل‌های تنظیمات می‌شود
        # به دلیل طول زیاد، فقط چارچوب کلی آن نمایش داده می‌شود

        # گروه تنظیمات تصویر
        image_group = QGroupBox("تنظیمات تصاویر")
        image_layout = QFormLayout(image_group)

        # مدت زمان نمایش تصاویر
        self.image_duration = QSpinBox()
        self.image_duration.setMinimum(1)
        self.image_duration.setMaximum(60)
        self.image_duration.setValue(self.settings.get("image_duration"))
        self.image_duration.setSuffix(" ثانیه")
        image_layout.addRow("مدت زمان نمایش هر تصویر:", self.image_duration)

        self.layout.addWidget(image_group)

        # ... (گروه‌های تنظیمات دیگر)

        # وضعیت اولیه فیلدهای رزولوشن سفارشی، رجکس و پوشه ثابت
        self.toggle_custom_resolution(self.use_custom_resolution.isChecked())
        self.toggle_regex_field(self.sort_date.isChecked())
        self.toggle_fixed_folder_section(self.fixed_folder_radio.isChecked())
        self.toggle_scaling_options(self.normalize_all_clips.isChecked())

    def apply_filename_template(self, index):
        """اعمال الگوی انتخاب شده از منوی کشویی به فیلد فرمت"""
        if index > 0:  # اگر گزینه غیر از اولین گزینه (راهنما) انتخاب شده است
            # به جای currentData از itemData استفاده می‌کنیم
            template = self.format_templates.itemData(index)
            if template:
                self.output_filename_format.setText(template)

    # ... (سایر متدهای مورد نیاز دیالوگ تنظیمات)

    def accept(self):
        """ذخیره تنظیمات و بستن دیالوگ"""
        # هشدار در مورد پردازش‌های در حال اجرا
        if self.queue_manager.has_running_tasks():
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "اعمال تنظیمات",
                "تنظیمات جدید فقط برای پردازش‌های آینده اعمال می‌شود و بر روی پردازش‌های در حال اجرا تاثیری ندارد.",
                QMessageBox.Ok
            )

        # ذخیره تنظیمات در شیء settings
        # (ذخیره تمام تنظیمات...)

        # ذخیره تنظیمات
        self.settings.save_settings()

        super().accept()