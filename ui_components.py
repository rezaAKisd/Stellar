import os
import time
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QUrl
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QProgressBar, QMessageBox
)
from PySide6.QtGui import QDesktopServices


class FolderProcessWidget(QWidget):
    remove_requested = Signal(object)  # سیگنال برای درخواست حذف ویجت

    def __init__(self, folder_path, queue_manager, settings, main_window=None, parent=None):
        super().__init__(parent)
        self.folder_path = folder_path
        self.queue_manager = queue_manager
        self.settings = settings
        self.main_window = main_window  # ذخیره مرجع پنجره اصلی
        self.thread = None  # در اینجا فقط اعلام می‌کنیم و در زمان مناسب آن را تنظیم می‌کنیم
        from process_thread import VideoProcessThread
        self.thread = VideoProcessThread(folder_path, settings)
        self.status = "pending"  # وضعیت‌ها: pending, queued, running, paused, completed, cancelled, failed

        # اضافه کردن متغیرهای مربوط به زمان
        self.elapsed_time = 0
        self.estimated_remaining_time = 0

        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # مسیر پوشه و وضعیت
        folder_info_layout = QHBoxLayout()

        # دکمه باز کردن پوشه
        self.open_folder_button = QPushButton("🔍")
        self.open_folder_button.setToolTip("باز کردن پوشه در فایل منیجر")
        self.open_folder_button.clicked.connect(self.open_folder)
        self.open_folder_button.setMaximumWidth(30)
        self.open_folder_button.setStyleSheet("""
            QPushButton {
                background-color: #444;
                color: white;
                border-radius: 4px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)

        # نمایش نام کامل پوشه
        self.folder_label = QLabel(f"پوشه: {self.folder_path}")
        self.folder_label.setToolTip(self.folder_path)
        self.status_label = QLabel("وضعیت: در انتظار")

        folder_info_layout.addWidget(self.open_folder_button)
        folder_info_layout.addWidget(self.folder_label, 1)
        folder_info_layout.addWidget(self.status_label)
        layout.addLayout(folder_info_layout)

        # برچسب مرحله
        self.stage_label = QLabel("مرحله: در انتظار شروع")
        layout.addWidget(self.stage_label)

        # نوار پیشرفت
        progress_layout = QHBoxLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_percent_label = QLabel("0%")

        progress_layout.addWidget(self.progress_bar, 1)
        progress_layout.addWidget(self.progress_percent_label)
        layout.addLayout(progress_layout)

        # برچسب زمان باقیمانده
        self.time_label = QLabel("زمان: 00:00:00 | باقیمانده: 00:00:00")
        self.time_label.setStyleSheet("color: #555; padding: 5px;")
        layout.addWidget(self.time_label)

        # دکمه‌های کنترل
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)

        # دکمه ساخت مجدد (در ابتدا پنهان است)
        self.rebuild_button = QPushButton("ساخت مجدد")
        self.rebuild_button.setToolTip("ساخت مجدد ویدئو با تنظیمات فعلی")
        self.rebuild_button.clicked.connect(self.rebuild_process)
        self.rebuild_button.setVisible(False)  # در ابتدا پنهان است
        self.rebuild_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

        self.pause_button = QPushButton("توقف")
        self.pause_button.clicked.connect(self.toggle_pause)

        self.cancel_button = QPushButton("لغو")
        self.cancel_button.clicked.connect(self.cancel_process)

        button_layout.addWidget(self.rebuild_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

        # یک خط جداکننده
        separator_line = QWidget()
        separator_line.setFixedHeight(1)
        separator_line.setStyleSheet("background-color: #cccccc;")
        layout.addWidget(separator_line)

    def open_folder(self):
        """باز کردن پوشه در فایل منیجر سیستم"""
        url = QUrl.fromLocalFile(self.folder_path)
        QDesktopServices.openUrl(url)

    def cleanup(self):
        """پاکسازی منابع قبل از حذف ویجت"""
        if hasattr(self, 'thread') and self.thread:
            # اگر ترد هنوز در حال اجراست، آن را لغو کنید
            if self.thread.isRunning():
                self.thread.cancel()
                # صبر کنید تا ترد به پایان برسد (با تایم‌اوت)
                if not self.thread.wait(3000):  # 3 ثانیه صبر کنید
                    print(f"هشدار: ترد برای پوشه {self.folder_path} به پایان نرسید")

    def connect_signals(self):
        """اتصال سیگنال‌های ترد به ویجت"""
        self.thread.progress_updated.connect(self.update_progress)
        self.thread.stage_updated.connect(self.update_stage)
        self.thread.process_finished.connect(self.process_finished)
        self.thread.time_updated.connect(self.update_time)
        self.thread.output_file_error.connect(self.handle_output_file_error)

        # اتصال سیگنال‌های ترد به پنجره اصلی
        if self.main_window:
            self.thread.check_output_file.connect(self.main_window.handle_output_file_check)
            self.thread.ask_output_path.connect(self.main_window.handle_output_path_request)

    def start_process(self):
        """اضافه کردن این پردازش به مدیر صف"""
        self.status = "pending"
        self.queue_manager.add_task(self, self.thread)

    def rebuild_process(self):
        """شروع مجدد پردازش با تنظیمات فعلی"""
        # حذف ترد قبلی
        if hasattr(self, 'thread') and self.thread:
            self.queue_manager.remove_widget(self.thread)

        # ایجاد ترد جدید
        from process_thread import VideoProcessThread
        self.thread = VideoProcessThread(self.folder_path, self.settings)

        # اتصال مجدد سیگنال‌ها
        self.connect_signals()

        # ریست کردن UI
        self.status = "pending"
        self.progress_bar.setValue(0)
        self.progress_percent_label.setText("0%")
        self.stage_label.setText("مرحله: در انتظار شروع")
        self.status_label.setText("وضعیت: در انتظار")
        self.time_label.setText("زمان: 00:00:00 | باقیمانده: 00:00:00")

        # پنهان کردن دکمه ساخت مجدد و نمایش دکمه‌های دیگر
        self.rebuild_button.setVisible(False)
        self.pause_button.setEnabled(True)
        self.cancel_button.setEnabled(True)

        # شروع پردازش
        self.start_process()

    def status_changed(self, new_status):
        """به‌روزرسانی وضعیت ویجت"""
        self.status = new_status
        if new_status == "queued":
            self.status_label.setText("وضعیت: در صف")
            self.stage_label.setText("مرحله: در انتظار اجرا")
            self.pause_button.setEnabled(False)
        elif new_status == "running":
            self.status_label.setText("وضعیت: در حال پردازش")
            self.pause_button.setText("توقف")
            self.pause_button.setEnabled(True)
        elif new_status == "paused":
            self.status_label.setText("وضعیت: متوقف شده")
            self.pause_button.setText("ادامه")
            self.pause_button.setEnabled(True)
        elif new_status == "cancelled":
            self.status_label.setText("وضعیت: لغو شده")
            self.stage_label.setText("مرحله: عملیات لغو شد")
            self.pause_button.setEnabled(False)
            self.cancel_button.setEnabled(False)

            # بعد از 2 ثانیه ویجت را حذف کن
            QTimer.singleShot(2000, lambda: self.remove_requested.emit(self))

        elif new_status == "completed":
            self.status_label.setText("وضعیت: تکمیل شده")
            self.pause_button.setEnabled(False)
            self.cancel_button.setEnabled(False)
        elif new_status == "failed":
            self.status_label.setText("وضعیت: ناموفق")
            self.pause_button.setEnabled(False)
            self.cancel_button.setEnabled(False)

    def toggle_pause(self):
        """توقف یا ادامه پردازش"""
        if self.status == "running":
            self.queue_manager.pause_task(self.thread)
        elif self.status == "paused":
            self.queue_manager.resume_task(self.thread)

    def format_time(self, seconds):
        """تبدیل زمان به فرمت ساعت:دقیقه:ثانیه"""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def cancel_process(self):
        """لغو پردازش"""
        self.status_label.setText("وضعیت: در حال لغو...")
        self.stage_label.setText("مرحله: در حال لغو عملیات")
        self.pause_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.queue_manager.cancel_task(self.thread)

    @Slot(str, float, float)
    def update_time(self, folder_path, elapsed_time, estimated_remaining_time):
        """به‌روزرسانی نمایش زمان سپری شده و تخمین زمان باقیمانده"""
        if folder_path == self.folder_path:
            self.elapsed_time = elapsed_time
            self.estimated_remaining_time = estimated_remaining_time

            # تبدیل زمان‌ها به فرمت ساعت:دقیقه:ثانیه
            elapsed_formatted = self.format_time(elapsed_time)
            estimated_formatted = self.format_time(estimated_remaining_time)

            # به‌روزرسانی برچسب زمان
            self.time_label.setText(f"زمان: {elapsed_formatted} | باقیمانده: {estimated_formatted}")

    @Slot(str, str)
    def handle_output_file_error(self, folder_path, error_message):
        """مدیریت خطای فایل خروجی"""
        if folder_path == self.folder_path:
            self.status = "failed"
            self.status_label.setText("وضعیت: ناموفق")
            self.stage_label.setText(f"مرحله: خطا - {error_message}")
            self.status_label.setToolTip(error_message)

            # نمایش پیام خطا به کاربر
            QMessageBox.warning(
                None,
                "خطای فایل خروجی",
                f"پردازش '{os.path.basename(folder_path)}' به دلیل مشکل در فایل خروجی متوقف شد:\n\n{error_message}"
            )

            self.pause_button.setEnabled(False)
            self.cancel_button.setEnabled(False)

            # نمایش دکمه شروع مجدد
            self.rebuild_button.setVisible(True)

            # در صورت نیاز، ویجت را با تأخیر حذف کنیم
            QTimer.singleShot(5000, lambda: self.remove_requested.emit(self))

    @Slot(str, float)
    def update_progress(self, folder_path, percentage):
        if folder_path == self.folder_path:
            progress = int(percentage)
            self.progress_bar.setValue(progress)
            self.progress_percent_label.setText(f"{progress}%")

    @Slot(str, str)
    def update_stage(self, folder_path, stage):
        if folder_path == self.folder_path:
            self.stage_label.setText(f"مرحله: {stage}")

    @Slot(str, bool, str, float)
    def process_finished(self, folder_path, success, message, elapsed_time=0):
        """پردازش پایان یافته است"""
        if folder_path == self.folder_path:
            if success:
                self.status = "completed"
                self.status_label.setText("وضعیت: تکمیل شد")
                self.stage_label.setText("مرحله: عملیات با موفقیت به پایان رسید")
                self.progress_bar.setValue(100)
                self.progress_percent_label.setText("100%")

                # نمایش زمان کل پردازش
                elapsed_formatted = self.format_time(elapsed_time)
                self.time_label.setText(f"زمان کل ساخت: {elapsed_formatted}")

                # نمایش دکمه ساخت مجدد
                self.rebuild_button.setVisible(True)

                # نمایش نوتیفیکیشن
                folder_name = os.path.basename(folder_path)
                self.queue_manager.parent.show_notification(
                    f"پردازش {folder_name} تکمیل شد",
                    f"پردازش پوشه {folder_name} با موفقیت در {elapsed_formatted} به پایان رسید."
                )
            else:
                self.status = "failed"
                self.status_label.setText("وضعیت: ناموفق")
                self.stage_label.setText(f"مرحله: خطا - {message}")
                self.status_label.setToolTip(message)

                # نمایش زمان کل پردازش
                if elapsed_time > 0:
                    elapsed_formatted = self.format_time(elapsed_time)
                    self.time_label.setText(f"زمان صرف شده: {elapsed_formatted}")

                # نمایش دکمه ساخت مجدد حتی در صورت خطا
                self.rebuild_button.setVisible(True)

            self.pause_button.setEnabled(False)
            self.cancel_button.setEnabled(False)
            self.queue_manager.task_finished(self.thread)


class EmptyStateWidget(QWidget):
    """ویجت نمایش حالت خالی"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 100, 20, 100)
        layout.setSpacing(10)

        # آیکون یا تصویر حالت خالی
        empty_icon_label = QLabel()
        empty_icon_label.setAlignment(Qt.AlignCenter)
        # می‌توانید از یک آیکون استفاده کنید
        empty_icon_label.setText("📁")
        empty_icon_label.setStyleSheet("font-size: 64px; color: #cccccc;")
        layout.addWidget(empty_icon_label)

        # متن راهنمای اصلی
        main_text = QLabel("هیچ پردازشی در حال انجام نیست")
        main_text.setAlignment(Qt.AlignCenter)
        main_text.setStyleSheet("font-size: 18px; font-weight: bold; color: #666666;")
        layout.addWidget(main_text)

        # متن راهنمای فرعی
        sub_text = QLabel("برای شروع، فولدرهای خود را به اینجا بکشید یا روی دکمه «افزودن پوشه‌ها» کلیک کنید")
        sub_text.setAlignment(Qt.AlignCenter)
        sub_text.setWordWrap(True)
        sub_text.setStyleSheet("font-size: 14px; color: #888888;")
        layout.addWidget(sub_text)