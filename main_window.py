import os
from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QScrollArea,
    QPushButton, QLabel, QFileDialog, QMessageBox, QSystemTrayIcon
)
from PySide6.QtGui import QIcon, QDragEnterEvent, QDropEvent, QPixmap, QColor

from settings import Settings
from queue_manager import QueueManager
from ui_components import FolderProcessWidget, EmptyStateWidget
from dialogs import MultiFolderDialog, SettingsDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("مرج کننده ویدئوهای فولدر (حداکثر 2 پردازش همزمان)")
        self.setMinimumSize(800, 600)
        self.folder_widgets = {}

        # بارگذاری تنظیمات
        self.settings = Settings()

        # ایجاد آیکون ترای سیستم برای نوتیفیکیشن
        self.setup_system_tray()

        # ایجاد مدیر صف با محدودیت 2 پردازش همزمان
        self.queue_manager = QueueManager(max_concurrent=2, parent=self)

        self.setup_ui()

        # فعال کردن پشتیبانی از درگ و دراپ
        self.setAcceptDrops(True)

    def setup_system_tray(self):
        """راه‌اندازی آیکون ترای سیستم برای نوتیفیکیشن"""
        try:
            self.tray_icon = QSystemTrayIcon(self)

            # ایجاد یک آیکون ساده با یک پیکسل‌مپ
            pixmap = QPixmap(16, 16)
            pixmap.fill(QColor(0, 120, 215))

            # تنظیم آیکون
            self.tray_icon.setIcon(QIcon(pixmap))
            self.tray_icon.setToolTip("مرج کننده ویدئو")
            self.tray_icon.setVisible(True)
        except Exception as e:
            print(f"خطا در راه‌اندازی سیستم تری: {e}")
            self.tray_icon = None

    def show_notification(self, title, message):
        """نمایش نوتیفیکیشن"""
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.showMessage(title, message, QSystemTrayIcon.Information, 5000)
        else:
            # اگر سیستم تری در دسترس نیست، از یک پیغام ساده استفاده کنید
            print(f"نوتیفیکیشن: {title} - {message}")

    def setup_ui(self):
        """راه‌اندازی رابط کاربری اصلی"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        # بخش بالایی - دکمه‌ها و اطلاعات
        top_section = QWidget()
        top_layout = QHBoxLayout(top_section)
        top_layout.setContentsMargins(10, 10, 10, 10)

        # دکمه افزودن پوشه
        self.add_button = QPushButton("افزودن پوشه‌ها")
        self.add_button.clicked.connect(self.add_folders)
        self.add_button.setMinimumHeight(40)
        self.add_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
                font-size: 14px;
                padding: 0 15px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        top_layout.addWidget(self.add_button)

        # دکمه تنظیمات
        self.settings_button = QPushButton("تنظیمات")
        self.settings_button.clicked.connect(self.show_settings)
        self.settings_button.setMinimumHeight(40)
        self.settings_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 5px;
                font-size: 14px;
                padding: 0 15px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
            QPushButton:pressed {
                background-color: #0a6fc7;
            }
        """)
        top_layout.addWidget(self.settings_button)

        # اطلاعات صف
        self.queue_info = QLabel("وضعیت صف: 0 در حال اجرا | 0 در صف")
        self.queue_info.setStyleSheet("font-weight: bold; color: #333; margin-left: 20px;")
        top_layout.addWidget(self.queue_info)
        top_layout.addStretch()

        main_layout.addWidget(top_section)

        # خط جداکننده
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #cccccc;")
        main_layout.addWidget(separator)

        # ناحیه اصلی - با استفاده از استکد ویجت
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        # ویجت نمایش حالت خالی
        self.empty_state_widget = EmptyStateWidget()
        self.content_layout.addWidget(self.empty_state_widget)

        # ناحیه اسکرول برای نمایش پوشه‌ها
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; }")

        # ویجت محتوا برای ناحیه اسکرول
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.addStretch()

        self.scroll_area.setWidget(self.scroll_widget)
        self.content_layout.addWidget(self.scroll_area)

        # در ابتدا، فقط حالت خالی نمایش داده شود
        self.scroll_area.setVisible(False)

        main_layout.addWidget(self.content_area, 1)  # بیشترین فضا به این بخش اختصاص داده شود

        # نمایش تنظیمات فعلی
        self.update_settings_display()

    # ... (سایر متدهای پنجره اصلی)

    def closeEvent(self, event):
        """مدیریت رویداد بستن پنجره"""
        # بررسی وجود پردازش‌های فعال
        if self.queue_manager.has_running_tasks():
            reply = QMessageBox.question(
                self,
                "پردازش‌های فعال",
                "پردازش‌هایی در حال اجرا هستند. آیا مطمئن هستید که می‌خواهید خارج شوید؟",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.No:
                event.ignore()
                return

        # پاکسازی تمام ترد‌ها قبل از خروج
        for folder, widget in list(self.folder_widgets.items()):
            if hasattr(widget, 'cleanup'):
                widget.cleanup()

        event.accept()

    def add_folders(self):
        """باز کردن دیالوگ انتخاب پوشه و افزودن پوشه‌های انتخاب شده به لیست پردازش"""
        dialog = MultiFolderDialog(self)
        if dialog.exec():
            selected_folders = dialog.selected_folders()
            if selected_folders:
                for folder_path in selected_folders:
                    self.add_folder_to_process(folder_path)

    def add_folder_to_process(self, folder_path):
        """افزودن یک پوشه به لیست پردازش"""
        # بررسی تکراری نبودن پوشه
        if folder_path in self.folder_widgets:
            QMessageBox.information(
                self,
                "پوشه تکراری",
                f"پوشه {folder_path} قبلاً اضافه شده است.",
                QMessageBox.Ok
            )
            return

        # بررسی وجود محتوا در پوشه
        media_files = self.check_folder_content(folder_path)
        if not media_files:
            reply = QMessageBox.question(
                self,
                "پوشه خالی",
                f"هیچ فایل تصویر یا ویدئویی در پوشه {folder_path} یافت نشد.\nآیا مایل به اضافه کردن این پوشه هستید؟",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        # ایجاد ویجت برای پوشه
        widget = FolderProcessWidget(folder_path, self.queue_manager, self.settings, self)
        self.folder_widgets[folder_path] = widget

        # اتصال سیگنال درخواست حذف به تابع مربوطه
        widget.remove_requested.connect(self.remove_folder_widget)

        # اضافه کردن ویجت به اسکرول اریا
        self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, widget)

        # شروع پردازش
        widget.start_process()

        # به‌روزرسانی وضعیت خالی بودن
        self.update_empty_state()

    def check_folder_content(self, folder_path):
        """بررسی وجود فایل‌های تصویر و ویدئو در پوشه"""
        # پسوندهای قابل قبول
        image_exts = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff']
        video_exts = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm']
        valid_exts = image_exts + video_exts

        media_files = []

        # بررسی همه فایل‌های موجود در پوشه
        for f in os.listdir(folder_path):
            file_path = os.path.join(folder_path, f)
            if os.path.isfile(file_path):
                ext = os.path.splitext(f)[1].lower()
                if ext in valid_exts:
                    media_files.append(file_path)

        return media_files

    def remove_folder_widget(self, widget):
        """حذف یک ویجت پوشه از لیست"""
        folder_path = widget.folder_path

        # حذف از دیکشنری
        if folder_path in self.folder_widgets:
            del self.folder_widgets[folder_path]

        # حذف از رابط کاربری
        widget.setParent(None)
        widget.deleteLater()

        # به‌روزرسانی وضعیت خالی بودن
        self.update_empty_state()

    def update_empty_state(self):
        """به‌روزرسانی نمایش حالت خالی"""
        if len(self.folder_widgets) == 0:
            self.empty_state_widget.setVisible(True)
            self.scroll_area.setVisible(False)
        else:
            self.empty_state_widget.setVisible(False)
            self.scroll_area.setVisible(True)

    def update_queue_info(self):
        """به‌روزرسانی اطلاعات نمایشی صف"""
        running_tasks = len(self.queue_manager.running)
        queued_tasks = len(self.queue_manager.queue)
        self.queue_info.setText(f"وضعیت صف: {running_tasks} در حال اجرا | {queued_tasks} در صف")

    def handle_output_file_check(self, folder_path, output_file_path):
        """بررسی وجود فایل خروجی و پرسش برای بازنویسی"""
        if os.path.exists(output_file_path):
            reply = QMessageBox.question(
                self,
                "فایل خروجی موجود است",
                f"فایل '{os.path.basename(output_file_path)}' از قبل وجود دارد. آیا می‌خواهید آن را بازنویسی کنید؟",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            # پیدا کردن ترد مربوط به این پوشه
            for thread in self.queue_manager.widgets:
                if getattr(thread, 'folder_path', None) == folder_path:
                    # تنظیم وضعیت تایید برای بازنویسی
                    thread.set_overwrite_confirmed(reply == QMessageBox.Yes)
                    # در صورت تأیید، ادامه پردازش
                    if reply == QMessageBox.Yes:
                        thread.set_output_filename(output_file_path)
                        return True
                    else:
                        # در صورت عدم تأیید، لغو پردازش
                        self.queue_manager.cancel_task(thread)
                        return False
        return True

    def handle_output_path_request(self, folder_path, default_filename):
        """مدیریت درخواست مسیر خروجی از کاربر"""
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره فایل خروجی",
            default_filename,
            "فایل‌های ویدئویی (*.mp4 *.mkv *.avi)"
        )

        # پیدا کردن ترد مربوط به این پوشه
        for thread in self.queue_manager.widgets:
            if getattr(thread, 'folder_path', None) == folder_path:
                if output_path:
                    thread.set_output_filename(output_path)
                    return True
                else:
                    # در صورت انصراف کاربر، لغو پردازش
                    self.queue_manager.cancel_task(thread)
                    return False
        return False

    def show_settings(self):
        """نمایش دیالوگ تنظیمات"""
        dialog = SettingsDialog(self.settings, self.queue_manager, self)
        if dialog.exec():
            # به‌روزرسانی نمایش تنظیمات
            self.update_settings_display()

    def update_settings_display(self):
        """به‌روزرسانی نمایش تنظیمات فعلی"""
        # این متد می‌تواند برای نمایش خلاصه تنظیمات فعلی استفاده شود
        pass

    def dragEnterEvent(self, event: QDragEnterEvent):
        """بررسی مجاز بودن عملیات درگ و دراپ"""
        # بررسی وجود URLs در داده‌های درگ شده
        if event.mimeData().hasUrls():
            # چک کردن اینکه همه URLs مربوط به پوشه‌ها باشند
            urls = event.mimeData().urls()
            for url in urls:
                # تبدیل URL به مسیر محلی
                path = url.toLocalFile()
                if not os.path.isdir(path):
                    # اگر هر یک از URLs پوشه نباشد، درگ را نپذیر
                    event.ignore()
                    return
            # همه URLs پوشه هستند، پس قبول کن
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """مدیریت حرکت در هنگام درگ"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        """مدیریت رها کردن پوشه‌ها"""
        if event.mimeData().hasUrls():
            # پذیرش عملیات پیشنهادی
            event.acceptProposedAction()

            # استخراج مسیرهای پوشه‌ها
            folder_paths = []
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if os.path.isdir(path) and path not in folder_paths:
                    folder_paths.append(path)

            # افزودن پوشه‌ها به لیست پردازش
            for folder_path in folder_paths:
                self.add_folder_to_process(folder_path)
        else:
            event.ignore()