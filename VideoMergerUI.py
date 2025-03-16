import sys
import os
import time
import json
import re
from PySide6.QtCore import (Qt, QThread, Signal, Slot, QDir, QSettings,
                            QMimeData, QUrl, QMetaObject, Q_ARG, QEvent, QTimer)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QDialog,
    QPushButton, QFileDialog, QWidget, QProgressBar, QDialogButtonBox,
    QLabel, QScrollArea, QMessageBox, QTreeView, QFileSystemModel,
    QSystemTrayIcon, QComboBox, QSpinBox, QFormLayout, QGroupBox, QCheckBox,
    QLineEdit, QRadioButton, QButtonGroup, QDoubleSpinBox, QColorDialog
)
from PySide6.QtGui import QIcon, QDragEnterEvent, QDropEvent, QPixmap, QColor, QDesktopServices

# فایل‌های مورد نیاز برای پردازش ویدیو
import glob
import platform
import datetime
from proglog import ProgressBarLogger
from moviepy import ImageClip, VideoFileClip, concatenate_videoclips, ColorClip, CompositeVideoClip


class Settings:
    def __init__(self):
        # استفاده از QSettings برای ذخیره تنظیمات در بین اجراهای برنامه
        self.qsettings = QSettings("VideoMerger", "FolderVideoMerger")

        # تنظیمات پیش‌فرض
        self.default_settings = {
            "image_duration": 10,  # مدت زمان نمایش هر تصویر (ثانیه)
            "output_resolution": "original",  # سایز خروجی (original, 720p, 1080p, etc.)
            "output_width": 1920,  # عرض خروجی سفارشی
            "output_height": 1080,  # ارتفاع خروجی سفارشی
            "use_custom_resolution": False,  # استفاده از رزولوشن سفارشی
            "sort_method": "date",  # روش مرتب‌سازی: date, name یا custom
            "custom_regex": r"_(\d+)_(\d+)_(\d+)_(\d+)_(\d+)_(\d+)\s(AM|PM)",  # رجکس سفارشی
            "output_path_type": "same_folder",  # same_folder, fixed_folder, ask_user
            "output_filename_format": "{folder_name}_video.mp4",  # فرمت نام فایل خروجی
            "fixed_output_folder": os.path.expanduser("~/Videos"),  # پوشه ثابت (پیش‌فرض: پوشه ویدیوها)

            # تنظیمات کیفیت خروجی
            "video_codec": "libx264",  # کدک ویدیو
            "video_bitrate": "700k",  # نرخ بیت ویدیو
            "audio_codec": "aac",  # کدک صدا
            "audio_bitrate": "128k",  # نرخ بیت صدا
            "fps": 30,  # فریم بر ثانیه
            "preset": "medium",  # پیش‌تنظیم کدک
            "threads": 2,  # تعداد ترد برای کدینگ

            # تنظیمات مقیاس‌دهی
            "scaling_mode": "fit",  # شیوه مقیاس‌دهی: fit, fill, stretch
            "background_color": "#000000",  # رنگ پس‌زمینه برای حالت fit
            "maintain_aspect_ratio": True,  # حفظ نسبت تصویر
            "normalize_all_clips": True,  # یکسان‌سازی ابعاد همه کلیپ‌ها
        }

        # بارگذاری تنظیمات از فایل یا استفاده از مقادیر پیش‌فرض
        self.load_settings()

    def load_settings(self):
        """بارگذاری تنظیمات از QSettings"""
        self.settings = {}
        for key, default_value in self.default_settings.items():
            self.settings[key] = self.qsettings.value(key, default_value)

            # تبدیل نوع داده به نوع صحیح
            if isinstance(default_value, int):
                self.settings[key] = int(self.settings[key])
            elif isinstance(default_value, float):
                self.settings[key] = float(self.settings[key])
            elif isinstance(default_value, bool):
                if isinstance(self.settings[key], str):
                    self.settings[key] = self.settings[key].lower() == 'true'

    def save_settings(self):
        """ذخیره تنظیمات در QSettings"""
        for key, value in self.settings.items():
            self.qsettings.setValue(key, value)

    def get(self, key):
        """دریافت مقدار یک تنظیم"""
        return self.settings.get(key, self.default_settings.get(key))

    def set(self, key, value):
        """تنظیم مقدار یک تنظیم و ذخیره آن"""
        self.settings[key] = value
        self.qsettings.setValue(key, value)


# مدیر صف برای کنترل تعداد پردازش‌های همزمان
class QueueManager:
    def __init__(self, max_concurrent=2, parent=None):
        self.queue = []  # لیست پردازش‌های در صف
        self.running = []  # لیست پردازش‌های در حال اجرا
        self.max_concurrent = max_concurrent  # حداکثر تعداد پردازش‌های همزمان
        self.widgets = {}  # ذخیره ویجت مرتبط با هر پردازش
        self.parent = parent  # نگهداری مرجع به پنجره اصلی برای به‌روزرسانی UI

    def add_task(self, widget, thread):
        """افزودن یک وظیفه جدید به مدیر صف"""
        self.widgets[thread] = widget
        if len(self.running) < self.max_concurrent:
            # اجرای مستقیم اگر ظرفیت وجود دارد
            self.running.append(thread)
            widget.status_changed("running")
            thread.start()
        else:
            # افزودن به صف اگر ظرفیت تکمیل است
            self.queue.append(thread)
            widget.status_changed("queued")

        # به‌روزرسانی نمایش وضعیت صف
        if self.parent:
            self.parent.update_queue_info()
            # پنهان کردن پیام راهنما چون حداقل یک پردازش وجود دارد
            self.parent.update_empty_state()

    def task_finished(self, thread):
        """وقتی یک وظیفه به پایان می‌رسد، این متد را فراخوانی می‌کند"""
        if thread in self.running:
            self.running.remove(thread)
            self._start_next()

        # به‌روزرسانی نمایش وضعیت صف
        if self.parent:
            self.parent.update_queue_info()

            # بررسی اگر همه کارها تمام شده‌اند
            if not self.running and not self.queue:
                self.parent.show_notification("همه پردازش‌ها به پایان رسید",
                                              "تمام پردازش‌های ویدیو با موفقیت به پایان رسیدند.")

    def _start_next(self):
        """شروع وظیفه بعدی در صف"""
        if self.queue and len(self.running) < self.max_concurrent:
            next_thread = self.queue.pop(0)
            self.running.append(next_thread)
            widget = self.widgets.get(next_thread)
            if widget:
                widget.status_changed("running")
            next_thread.start()

    def cancel_task(self, thread):
        """لغو یک وظیفه، چه در صف باشد چه در حال اجرا"""
        if thread in self.running:
            thread.cancel()
            self.running.remove(thread)
            self._start_next()
        elif thread in self.queue:
            self.queue.remove(thread)

        # در هر دو صورت، وضعیت ویجت را به‌روزرسانی می‌کنیم
        widget = self.widgets.get(thread)
        if widget:
            widget.status_changed("cancelled")

        # به‌روزرسانی نمایش وضعیت صف
        if self.parent:
            self.parent.update_queue_info()

    def remove_widget(self, thread):
        """حذف ویجت از دیکشنری"""
        if thread in self.widgets:
            del self.widgets[thread]

        # بررسی وضعیت خالی بودن لیست پردازش‌ها
        if self.parent:
            self.parent.update_empty_state()

    def pause_task(self, thread):
        """توقف موقت یک وظیفه"""
        if thread in self.running:
            thread.pause()
            # نیازی به تغییر وضعیت در صف نیست، فقط وضعیت ویجت را تغییر می‌دهیم
            widget = self.widgets.get(thread)
            if widget:
                widget.status_changed("paused")

    def resume_task(self, thread):
        """ادامه یک وظیفه متوقف شده"""
        if thread in self.running:
            thread.resume()
            widget = self.widgets.get(thread)
            if widget:
                widget.status_changed("running")

    def has_running_tasks(self):
        """بررسی وجود پردازش‌های در حال اجرا"""
        return len(self.running) > 0


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


class VideoProcessThread(QThread):
    progress_updated = Signal(str, float)
    stage_updated = Signal(str, str)  # folder_path, stage_description
    process_finished = Signal(str, bool, str, float)  # folder_path, success, message, elapsed_time
    check_output_file = Signal(str, str)  # folder_path, output_file_path
    ask_output_path = Signal(str, str)  # folder_path, default_filename
    time_updated = Signal(str, float, float)  # folder_path, elapsed_time, estimated_remaining_time

    def __init__(self, folder_path, settings):
        super().__init__()
        self.folder_path = folder_path
        self.cancelled = False
        self.paused = False
        self.pause_lock = False  # قفل برای جلوگیری از ورود به حالت توقف در زمان‌های حساس
        self.output_filename = ""  # مسیر فایل خروجی برای پاک کردن در صورت لغو
        self.current_stage = ""
        self.settings = settings
        self.overwrite_confirmed = False  # آیا کاربر تایید کرده است که فایل موجود بازنویسی شود

        # متغیرهای مربوط به زمان‌سنجی
        self.start_time = 0
        self.last_progress_update = 0
        self.last_progress_percent = 0
        self.total_pause_time = 0
        self.pause_start_time = 0

    def run(self):
        self.start_time = time.time()
        self.last_progress_update = self.start_time
        self.total_pause_time = 0

        try:
            # قبل از هر کار، پرچم‌های وضعیت را بازنشانی می‌کنیم
            self.overwrite_confirmed = False
            self.process_video()

            # محاسبه کل زمان صرف شده (با کسر زمان توقف)
            elapsed_time = time.time() - self.start_time - self.total_pause_time

            if not self.cancelled:
                self.process_finished.emit(self.folder_path, True, "عملیات با موفقیت انجام شد", elapsed_time)
            else:
                # پاک کردن فایل ناقص در صورت لغو
                self.cleanup_output_file()
                self.process_finished.emit(self.folder_path, False, "عملیات لغو شد", elapsed_time)
        except Exception as e:
            # محاسبه زمان صرف شده حتی در صورت خطا
            elapsed_time = time.time() - self.start_time - self.total_pause_time
            # پاک کردن فایل ناقص در صورت خطا
            self.cleanup_output_file()
            self.process_finished.emit(self.folder_path, False, str(e), elapsed_time)

    def cancel(self):
        self.cancelled = True

    def pause(self):
        """توقف موقت پردازش"""
        if not self.paused:
            self.paused = True
            self.pause_start_time = time.time()

    def resume(self):
        """ادامه پردازش"""
        if self.paused:
            self.paused = False
            # محاسبه زمان توقف و اضافه کردن به کل زمان توقف
            if self.pause_start_time > 0:
                self.total_pause_time += time.time() - self.pause_start_time
                self.pause_start_time = 0

    def check_pause(self):
        """بررسی وضعیت توقف و انتظار تا ادامه پردازش"""
        # اگر قفل توقف فعال است، نمی‌توان توقف کرد
        if self.pause_lock:
            return

        if self.paused and not self.cancelled:
            # ثبت زمان شروع توقف اگر هنوز ثبت نشده باشد
            if self.pause_start_time == 0:
                self.pause_start_time = time.time()

        while self.paused and not self.cancelled:
            # در حالت توقف، هر 0.5 ثانیه بررسی می‌کنیم که آیا باید ادامه دهیم
            time.sleep(0.5)
            QApplication.processEvents()

    def set_pause_lock(self, locked):
        """تنظیم قفل توقف برای جلوگیری از توقف در مراحل حساس"""
        self.pause_lock = locked

    def cleanup_output_file(self):
        """پاک کردن فایل خروجی ناقص در صورت لغو یا خطا"""
        if self.output_filename and os.path.exists(self.output_filename) and not self.overwrite_confirmed:
            try:
                os.remove(self.output_filename)
                print(f"فایل ناقص پاک شد: {self.output_filename}")
            except Exception as e:
                print(f"خطا در پاک کردن فایل ناقص: {e}")

    def update_stage(self, stage):
        """به‌روزرسانی مرحله فعلی پردازش"""
        if stage != self.current_stage:
            self.current_stage = stage
            self.stage_updated.emit(self.folder_path, stage)
            # بعد از تغییر مرحله، حتماً وضعیت توقف را بررسی کنیم
            self.check_pause()

    def set_overwrite_confirmed(self, confirmed):
        """تنظیم وضعیت تایید بازنویسی فایل"""
        self.overwrite_confirmed = confirmed

    def set_output_filename(self, path):
        """تنظیم مسیر فایل خروجی"""
        self.output_filename = path

    def update_time_estimate(self, progress_percent):
        """به‌روزرسانی تخمین زمان باقیمانده"""
        current_time = time.time()
        elapsed_time = current_time - self.start_time - self.total_pause_time

        # حداقل 2 ثانیه از آپدیت قبلی گذشته باشد یا پیشرفت بیش از 2 درصد باشد
        if (current_time - self.last_progress_update > 2 or
            progress_percent - self.last_progress_percent > 2) and progress_percent > 0:

            # تخمین زمان باقیمانده
            if progress_percent < 100 and progress_percent > 0:
                estimated_remaining = (elapsed_time * (100 - progress_percent)) / progress_percent
            else:
                estimated_remaining = 0

            # ارسال سیگنال به‌روزرسانی زمان
            self.time_updated.emit(self.folder_path, elapsed_time, estimated_remaining)

            # به‌روزرسانی زمان و درصد آخرین آپدیت
            self.last_progress_update = current_time
            self.last_progress_percent = progress_percent

    class ThreadBarLogger(ProgressBarLogger):
        def __init__(self, signal_fn, stage_fn, folder_path, check_pause_fn, time_update_fn):
            super().__init__()
            self.signal_fn = signal_fn  # تابع سیگنال برای به‌روزرسانی درصد پیشرفت
            self.stage_fn = stage_fn  # تابع سیگنال برای به‌روزرسانی مرحله
            self.folder_path = folder_path
            self.check_pause_fn = check_pause_fn  # تابع بررسی وضعیت توقف
            self.time_update_fn = time_update_fn  # تابع به‌روزرسانی تخمین زمان
            self.stages = {
                "t": "در حال آماده‌سازی زمان‌بندی",
                "chunk": "در حال چانک کردن فایل‌ها",
                "writing": "در حال نوشتن فایل خروجی",
                "rendering": "در حال رندر کردن",
                "finalize": "در حال نهایی کردن"
            }

        def bars_callback(self, bar, attr, value, old_value=None):
            # بررسی وضعیت توقف
            self.check_pause_fn()

            # به‌روزرسانی درصد پیشرفت
            if bar not in self.bars:
                return

            if attr == 'index':
                percentage = (value / self.bars[bar]['total']) * 100
                self.signal_fn(self.folder_path, percentage)
                # به‌روزرسانی تخمین زمان
                self.time_update_fn(percentage)

            # به‌روزرسانی مرحله پردازش
            if bar == 'chunk' and old_value is None:
                self.stage_fn("در حال چانک کردن فایل‌ها")
            elif bar == 'moviepy.audio.AudioClip.reader.AudioFileClip':
                self.stage_fn("در حال پردازش صدا")
            elif bar == 'moviepy.video.VideoClip.reader.FFMPEG_VideoReader':
                self.stage_fn("در حال پردازش ویدیو")
            elif bar == 'moviepy.video.VideoClip.VideoClip.write_videofile.<locals>.ffmpeg_write_video':
                self.stage_fn("در حال نوشتن فایل ویدیویی")
            elif bar == 'moviepy.video.io.ffmpeg_tools.ffmpeg_merge_video_audio':
                self.stage_fn("در حال ادغام ویدیو و صدا")

    def extract_sort_key(self, file_path):
        """استخراج کلید مرتب‌سازی از نام فایل براساس تنظیمات"""
        file_name = os.path.basename(file_path)

        # انتخاب روش مرتب‌سازی
        sort_method = self.settings.get("sort_method")

        # مرتب‌سازی براساس تاریخ (رجکس پیش‌فرض یا سفارشی)
        if sort_method == "date":
            regex_pattern = self.settings.get("custom_regex")
            match = re.search(regex_pattern, file_name)
            if match:
                # بسته به تعداد گروه‌های رجکس، متفاوت عمل می‌کنیم
                groups = match.groups()
                if len(groups) == 7:  # فرمت پیش‌فرض: ماه، روز، سال، ساعت، دقیقه، ثانیه، AM/PM
                    month, day, year, hour, minute, second, period = groups
                    hour = int(hour)
                    # تبدیل ساعت به فرمت 24 ساعته
                    if period == "PM" and hour != 12:
                        hour += 12
                    elif period == "AM" and hour == 12:
                        hour = 0
                    return (1, int(year), int(month), int(day), hour, int(minute), int(second))
                else:
                    # اگر رجکس گروه‌های متفاوتی داشت، از مقادیر استخراج شده استفاده کنیم
                    return (1,) + tuple(int(g) if g.isdigit() else g for g in groups)

        # مرتب‌سازی بر اساس نام فایل
        elif sort_method == "name":
            return (2, file_name)

        # مرتب‌سازی پیش‌فرض در صورت عدم تطابق
        return (3, file_name)

    def apply_scaling(self, clip, target_resolution, scaling_mode, maintain_aspect_ratio, bg_color):
        """اعمال مقیاس‌دهی به یک کلیپ با توجه به تنظیمات"""
        width, height = target_resolution

        if not maintain_aspect_ratio or scaling_mode == "stretch":
            # کشیدن کامل بدون حفظ نسبت
            return clip.resize(width=width, height=height)

        elif scaling_mode == "fit":
            # قرار دادن کامل در قاب (ممکن است حاشیه‌های خالی اضافه شود)
            resized_clip = clip.resize(width=width, height=height, keep_aspect_ratio=True)

            # ساخت یک کلیپ با اندازه و رنگ پس‌زمینه دلخواه
            color_clip = ColorClip(size=(width, height), color=bg_color, duration=clip.duration)

            # قرار دادن کلیپ اصلی در مرکز
            result = CompositeVideoClip([color_clip, resized_clip.set_position("center")])
            return result

        elif scaling_mode == "fill":
            # پر کردن کامل قاب (ممکن است بخشی از تصویر برش بخورد)
            clip_aspect_ratio = clip.w / clip.h
            target_aspect_ratio = width / height

            if clip_aspect_ratio > target_aspect_ratio:
                # تصویر عریض‌تر است - مقیاس بر اساس ارتفاع
                resized_clip = clip.resize(height=height)
                # برش از طرفین برای رسیدن به عرض هدف
                resized_clip = resized_clip.crop(x_center=resized_clip.w / 2, y_center=resized_clip.h / 2,
                                                 width=width, height=height)
            else:
                # تصویر کشیده‌تر است - مقیاس بر اساس عرض
                resized_clip = clip.resize(width=width)
                # برش از بالا و پایین برای رسیدن به ارتفاع هدف
                resized_clip = resized_clip.crop(x_center=resized_clip.w / 2, y_center=resized_clip.h / 2,
                                                 width=width, height=height)

            return resized_clip

        # حالت پیش‌فرض - بدون تغییر مقیاس
        return clip

    def process_video(self):
        self.update_stage("در حال آماده‌سازی")

        # مقداردهی اولیه متغیرهای زمان‌سنجی
        self.last_progress_percent = 0

        # تعیین مسیر و نام فایل خروجی براساس تنظیمات
        folder_path = self.folder_path
        folder_name = os.path.basename(folder_path)
        output_path_type = self.settings.get("output_path_type")
        output_filename_format = self.settings.get("output_filename_format")

        # جایگزینی متغیرهای در فرمت نام فایل با استفاده از روش ایمن
        try:
            # تاریخ امروز را با فرمت YYYY-MM-DD به دست می‌آوریم
            today_date = datetime.datetime.now().strftime("%Y-%m-%d")

            # استفاده از format برای جایگزینی متغیرها
            output_filename = output_filename_format.format(folder_name=folder_name, date=today_date)
        except KeyError as e:
            # اگر متغیر نامعتبری در الگو استفاده شده باشد
            self.update_stage(f"خطا در الگوی نام فایل: متغیر {str(e)} موجود نیست")
            # استفاده از یک نام پیش‌فرض
            output_filename = f"{folder_name}_video.mp4"
        except Exception as e:
            # سایر خطاها
            self.update_stage(f"خطا در الگوی نام فایل: {str(e)}")
            # استفاده از یک نام پیش‌فرض
            output_filename = f"{folder_name}_video.mp4"

        # بررسی و مطمئن شدن که پسوند .mp4 وجود دارد
        if not output_filename.lower().endswith('.mp4'):
            output_filename += '.mp4'

        # بررسی و اصلاح کاراکترهای غیرمجاز در نام فایل
        # کاراکترهایی مانند /\:*?"<>| در نام فایل مشکل ایجاد می‌کنند
        invalid_chars = r'[\\/*?:"<>|]'
        output_filename = re.sub(invalid_chars, '_', output_filename)

        # حالا تعیین مسیر کامل
        if output_path_type == "same_folder":
            # ذخیره در همان پوشه
            self.output_filename = os.path.join(folder_path, output_filename)
        elif output_path_type == "fixed_folder":
            # ذخیره در پوشه ثابت
            fixed_folder = self.settings.get("fixed_output_folder")
            if not os.path.exists(fixed_folder):
                os.makedirs(fixed_folder, exist_ok=True)
            self.output_filename = os.path.join(fixed_folder, output_filename)
        elif output_path_type == "ask_user":
            # درخواست مسیر از کاربر
            self.ask_output_path.emit(folder_path, output_filename)
            # منتظر پاسخ کاربر می‌مانیم
            self.overwrite_confirmed = False  # بازنشانی پرچم
            max_wait_time = 60  # حداکثر زمان انتظار به ثانیه
            wait_start = time.time()

            while not self.cancelled and not self.output_filename and (time.time() - wait_start < max_wait_time):
                time.sleep(0.1)
                QApplication.processEvents()  # اجازه پردازش رویدادها در رابط کاربری

            # اگر عملیات لغو شده یا کاربر مسیری انتخاب نکرده است
            if self.cancelled or not self.output_filename:
                return
        else:
            # حالت پیش‌فرض: ذخیره در همان پوشه
            self.output_filename = os.path.join(folder_path, output_filename)

        # چاپ مسیر فایل خروجی برای اشکال‌زدایی
        print(f"مسیر فایل خروجی: {self.output_filename}")

        if not os.path.exists(folder_path):
            raise Exception(f"پوشه وجود ندارد: {folder_path}")

        progress_callback = self.ThreadBarLogger(
            self.progress_updated.emit,
            self.update_stage,
            folder_path,
            self.check_pause,
            self.update_time_estimate
        )

        file_types = ['*.mp4', '*.avi', '*.mov', '*.mkv', '*.wmv',  # فرمت‌های ویدیو
                      '*.jpg', '*.jpeg', '*.png', '*.bmp', '*.gif']  # فرمت‌های تصویر

        self.update_stage("در حال جستجوی فایل‌ها")
        self.check_pause()  # بررسی وضعیت توقف

        # استفاده از set برای حذف تکراری‌ها
        unique_files = set()
        for file_type in file_types:
            # اضافه کردن با حروف کوچک
            files_found = glob.glob(os.path.join(folder_path, file_type))
            unique_files.update(files_found)

        # تبدیل به لیست برای مرتب‌سازی
        all_files = list(unique_files)

        if not all_files:
            raise Exception(f"فایل قابل پشتیبانی در {folder_path} پیدا نشد")

        # مرتب‌سازی براساس روش انتخاب شده
        self.update_stage("در حال مرتب‌سازی فایل‌ها")
        self.check_pause()  # بررسی وضعیت توقف
        sorted_files = sorted(all_files, key=self.extract_sort_key)

        clips = []
        self.update_stage("در حال بارگذاری فایل‌ها")

        # مقادیر تنظیمات
        image_duration = self.settings.get("image_duration")
        output_resolution = self.settings.get("output_resolution")
        use_custom_resolution = self.settings.get("use_custom_resolution")
        output_width = self.settings.get("output_width")
        output_height = self.settings.get("output_height")

        # تنظیمات مقیاس‌دهی
        normalize_all_clips = self.settings.get("normalize_all_clips")
        maintain_aspect_ratio = self.settings.get("maintain_aspect_ratio")
        scaling_mode = self.settings.get("scaling_mode")
        background_color = self.settings.get("background_color")

        # تبدیل رنگ پس‌زمینه از فرمت هگز به RGB
        bg_color = tuple(int(background_color.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4))

        # تعیین رزولوشن خروجی
        target_resolution = None
        if output_resolution != "original":
            if output_resolution == "480p":
                target_resolution = (640, 480)  # عرض، ارتفاع
            elif output_resolution == "720p":
                target_resolution = (1280, 720)
            elif output_resolution == "1080p":
                target_resolution = (1920, 1080)
            elif use_custom_resolution:
                target_resolution = (output_width, output_height)

        # نمایش تعداد فایل‌ها برای اطلاعات بیشتر
        self.update_stage(f"بارگذاری {len(sorted_files)} فایل")

        total_files = len(sorted_files)
        processed_extensions = set()  # برای نمایش اطلاعات انواع فایل‌های پردازش شده

        for index, file_path in enumerate(sorted_files):
            # بررسی وضعیت توقف
            self.check_pause()

            if self.cancelled:
                # آزاد کردن منابع
                for c in clips:
                    try:
                        c.close()
                    except:
                        pass
                return

            file_ext = os.path.splitext(file_path)[1].lower()
            processed_extensions.add(file_ext)
            file_name = os.path.basename(file_path)

            # به‌روزرسانی پیشرفت بارگذاری فایل‌ها
            progress_percent = (index / total_files) * 100
            self.progress_updated.emit(self.folder_path, progress_percent)
            self.update_stage(f"در حال بارگذاری {file_name} [{index + 1}/{total_files}]")
            self.update_time_estimate(progress_percent)

            try:
                if file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
                    # تصویر - با مدت زمان تنظیم شده
                    clip = ImageClip(file_path, duration=image_duration)

                    # اعمال مقیاس‌دهی
                    if normalize_all_clips and target_resolution:
                        clip = self.apply_scaling(clip, target_resolution, scaling_mode, maintain_aspect_ratio,
                                                  bg_color)
                    elif target_resolution:
                        clip = clip.resize(height=target_resolution[1])

                elif file_ext in ['.mp4', '.avi', '.mov', '.mkv', '.wmv']:
                    # ویدیو
                    video_clip = VideoFileClip(file_path)

                    # اعمال مقیاس‌دهی
                    if normalize_all_clips and target_resolution:
                        video_clip = self.apply_scaling(video_clip, target_resolution, scaling_mode,
                                                        maintain_aspect_ratio, bg_color)
                    elif target_resolution:  # مقیاس‌دهی ساده اگر یکسان‌سازی فعال نیست
                        video_clip = video_clip.resize(height=target_resolution[1])

                    clip = video_clip
                else:
                    continue

                clips.append(clip)

            except Exception as e:
                # رد کردن فایل‌های مشکل‌دار
                self.update_stage(f"رد کردن فایل مشکل‌دار: {file_name} - خطا: {str(e)}")
                time.sleep(1)  # کمی مکث برای خواندن پیام
                continue

        if not clips:
            raise Exception(f"هیچ کلیپ معتبری برای ادغام در {folder_path} وجود ندارد")

        # نمایش اطلاعات تعداد کلیپ‌ها و انواع فایل‌ها
        self.update_stage(f"آماده ادغام {len(clips)} کلیپ (انواع فایل: {', '.join(processed_extensions)})")

        if self.cancelled:
            # آزاد کردن منابع
            for c in clips:
                try:
                    c.close()
                except:
                    pass
            return

        try:
            self.update_stage("در حال ادغام کلیپ‌ها")
            self.check_pause()  # بررسی وضعیت توقف

            # فعال کردن قفل توقف برای عملیات حساس
            self.set_pause_lock(True)
            final_clip = concatenate_videoclips(clips, method="compose")
            self.set_pause_lock(False)

            # نمایش طول ویدیوی نهایی
            duration_seconds = int(final_clip.duration)
            minutes = duration_seconds // 60
            seconds = duration_seconds % 60
            self.update_stage(f"طول ویدیوی نهایی: {minutes} دقیقه و {seconds} ثانیه")

            # بررسی مجدد وضعیت لغو قبل از نوشتن فایل
            if self.cancelled:
                final_clip.close()
                for c in clips:
                    try:
                        c.close()
                    except:
                        pass
                return

            # نوشتن در آدرس نهایی
            self.update_stage("در حال نوشتن فایل ویدیویی نهایی")
            self.check_pause()  # بررسی وضعیت توقف

            # استفاده از تنظیمات کیفیت خروجی
            final_clip.write_videofile(
                self.output_filename,
                codec=self.settings.get("video_codec"),
                bitrate=self.settings.get("video_bitrate"),
                audio_codec=self.settings.get("audio_codec"),
                audio_bitrate=self.settings.get("audio_bitrate"),
                fps=self.settings.get("fps"),
                preset=self.settings.get("preset"),
                threads=self.settings.get("threads"),
                logger=progress_callback
            )

            # آزاد کردن منابع
            self.update_stage("در حال آزادسازی منابع")
            for clip in clips:
                try:
                    clip.close()
                except:
                    pass
            try:
                final_clip.close()
            except:
                pass

            self.update_stage("عملیات با موفقیت به پایان رسید")

        except Exception as e:
            # آزاد کردن منابع
            for clip in clips:
                try:
                    clip.close()
                except:
                    pass
            raise e


class FolderProcessWidget(QWidget):
    remove_requested = Signal(object)  # سیگنال برای درخواست حذف ویجت

    def __init__(self, folder_path, queue_manager, settings, main_window=None, parent=None):
        super().__init__(parent)
        self.folder_path = folder_path
        self.queue_manager = queue_manager
        self.settings = settings
        self.main_window = main_window  # ذخیره مرجع پنجره اصلی
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

    def connect_signals(self):
        """اتصال سیگنال‌های ترد به ویجت"""
        self.thread.progress_updated.connect(self.update_progress)
        self.thread.stage_updated.connect(self.update_stage)
        self.thread.process_finished.connect(self.process_finished)
        self.thread.time_updated.connect(self.update_time)  # اتصال سیگنال جدید

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

        # گروه تنظیمات رزولوشن
        resolution_group = QGroupBox("تنظیمات رزولوشن خروجی")
        resolution_layout = QFormLayout(resolution_group)

        # انتخاب رزولوشن خروجی
        self.output_resolution = QComboBox()
        self.output_resolution.addItem("سایز اصلی", "original")
        self.output_resolution.addItem("480p (640x480)", "480p")
        self.output_resolution.addItem("720p (1280x720)", "720p")
        self.output_resolution.addItem("1080p (1920x1080)", "1080p")

        # تنظیم مقدار پیش‌فرض
        current_resolution = self.settings.get("output_resolution")
        index = self.output_resolution.findData(current_resolution)
        if index >= 0:
            self.output_resolution.setCurrentIndex(index)

        resolution_layout.addRow("رزولوشن خروجی:", self.output_resolution)

        # چک‌باکس برای فعال کردن رزولوشن سفارشی
        self.use_custom_resolution = QCheckBox("استفاده از رزولوشن سفارشی")
        self.use_custom_resolution.setChecked(self.settings.get("use_custom_resolution"))
        self.use_custom_resolution.toggled.connect(self.toggle_custom_resolution)
        resolution_layout.addRow("", self.use_custom_resolution)

        # ویجت‌های رزولوشن سفارشی
        resolution_custom_layout = QHBoxLayout()

        self.output_width = QSpinBox()
        self.output_width.setMinimum(320)
        self.output_width.setMaximum(7680)  # 8K
        self.output_width.setValue(self.settings.get("output_width"))
        self.output_width.setSuffix(" px")

        self.output_height = QSpinBox()
        self.output_height.setMinimum(240)
        self.output_height.setMaximum(4320)  # 8K
        self.output_height.setValue(self.settings.get("output_height"))
        self.output_height.setSuffix(" px")

        resolution_custom_layout.addWidget(QLabel("عرض:"))
        resolution_custom_layout.addWidget(self.output_width)
        resolution_custom_layout.addWidget(QLabel("ارتفاع:"))
        resolution_custom_layout.addWidget(self.output_height)

        resolution_layout.addRow("ابعاد سفارشی:", resolution_custom_layout)

        self.layout.addWidget(resolution_group)

        # گروه جدید تنظیمات مقیاس‌دهی
        scaling_group = QGroupBox("تنظیمات یکسان‌سازی ابعاد")
        scaling_layout = QVBoxLayout(scaling_group)

        # فعال/غیرفعال کردن یکسان‌سازی ابعاد کلیپ‌ها
        self.normalize_all_clips = QCheckBox("یکسان‌سازی ابعاد تمام کلیپ‌ها (عکس‌ها و فیلم‌ها)")
        self.normalize_all_clips.setChecked(self.settings.get("normalize_all_clips"))
        scaling_layout.addWidget(self.normalize_all_clips)

        # حفظ نسبت تصویر
        self.maintain_aspect_ratio = QCheckBox("حفظ نسبت تصویر اصلی")
        self.maintain_aspect_ratio.setChecked(self.settings.get("maintain_aspect_ratio"))
        scaling_layout.addWidget(self.maintain_aspect_ratio)

        # انتخاب شیوه مقیاس‌دهی
        scaling_method_layout = QFormLayout()

        self.scaling_mode = QComboBox()
        self.scaling_mode.addItem("قرار دادن کامل در قاب (Fit) - ممکن است حاشیه‌های خالی اضافه شود", "fit")
        self.scaling_mode.addItem("پر کردن کامل قاب (Fill) - ممکن است بخشی از تصویر برش بخورد", "fill")
        self.scaling_mode.addItem("کشیدن کامل (Stretch) - بدون حفظ نسبت تصویر", "stretch")

        # تنظیم مقدار پیش‌فرض
        current_mode = self.settings.get("scaling_mode")
        index = self.scaling_mode.findData(current_mode)
        if index >= 0:
            self.scaling_mode.setCurrentIndex(index)

        self.scaling_mode.currentIndexChanged.connect(self.update_scaling_options)
        scaling_method_layout.addRow("شیوه مقیاس‌دهی:", self.scaling_mode)
        scaling_layout.addLayout(scaling_method_layout)

        # انتخاب رنگ پس‌زمینه برای حالت Fit
        background_layout = QHBoxLayout()
        background_layout.addWidget(QLabel("رنگ پس‌زمینه:"))

        # کمبوباکس برای انتخاب رنگ‌های متداول
        self.color_combo = QComboBox()
        self.color_combo.setMinimumWidth(120)

        # اضافه کردن رنگ‌های پیش‌فرض به منو
        predefined_colors = [
            ("سیاه", "#000000"),
            ("سفید", "#FFFFFF"),
            ("خاکستری", "#808080"),
            ("قرمز", "#FF0000"),
            ("سبز", "#00FF00"),
            ("آبی", "#0000FF"),
            ("آبی تیره", "#0000AA"),
            ("زرد", "#FFFF00"),
            ("فیروزه‌ای", "#00FFFF"),
            ("بنفش", "#FF00FF"),
            ("نارنجی", "#FFA500"),
            ("قهوه‌ای", "#A52A2A"),
            ("سفارشی...", "custom")
        ]

        for color_name, color_value in predefined_colors:
            # رنگ پس‌زمینه برای آیتم کمبوباکس
            icon_pixmap = QPixmap(16, 16)
            if color_value != "custom":
                icon_pixmap.fill(QColor(color_value))
                self.color_combo.addItem(QIcon(icon_pixmap), color_name, color_value)
            else:
                self.color_combo.addItem(color_name, color_value)

        # تنظیم رنگ فعلی
        current_color = self.settings.get("background_color")
        found = False
        for i in range(self.color_combo.count() - 1):  # به جز آیتم آخر که "سفارشی" است
            if self.color_combo.itemData(i) == current_color:
                self.color_combo.setCurrentIndex(i)
                found = True
                break

        if not found:
            # اگر رنگ در لیست نبود، گزینه سفارشی را انتخاب می‌کنیم
            self.color_combo.setCurrentIndex(self.color_combo.count() - 1)

        self.color_combo.currentIndexChanged.connect(self.on_color_selection_changed)
        background_layout.addWidget(self.color_combo)

        # دکمه نمایش رنگ فعلی
        self.background_color_button = QPushButton()
        self.background_color_button.setMinimumWidth(80)
        self.background_color = current_color
        self.update_color_button()
        self.background_color_button.clicked.connect(self.choose_background_color)

        background_layout.addWidget(self.background_color_button)
        background_layout.addStretch()

        scaling_layout.addLayout(background_layout)

        # اضافه کردن توضیحات
        scaling_info = QLabel("با فعال کردن یکسان‌سازی، تمام ویدیوها و تصاویر در خروجی نهایی ابعاد یکسانی خواهند داشت.")
        scaling_info.setWordWrap(True)
        scaling_info.setStyleSheet("color: #666666; font-size: 11px;")
        scaling_layout.addWidget(scaling_info)

        # اضافه کردن توضیحات برای حالت‌های مختلف
        self.scaling_mode_info = QLabel()
        self.scaling_mode_info.setWordWrap(True)
        self.scaling_mode_info.setStyleSheet("color: #666666; font-size: 11px;")
        scaling_layout.addWidget(self.scaling_mode_info)
        self.update_scaling_info(self.scaling_mode.currentData())

        self.layout.addWidget(scaling_group)

        # اتصال سیگنال‌های کنترل‌ها
        self.normalize_all_clips.toggled.connect(self.toggle_scaling_options)

        # گروه تنظیمات مرتب‌سازی فایل‌ها
        sort_group = QGroupBox("تنظیمات مرتب‌سازی فایل‌ها")
        sort_layout = QVBoxLayout(sort_group)

        # رادیو باتن‌ها برای انتخاب روش مرتب‌سازی
        self.sort_method_group = QButtonGroup(self)

        self.sort_date = QRadioButton("مرتب‌سازی براساس تاریخ")
        self.sort_name = QRadioButton("مرتب‌سازی براساس نام فایل")

        self.sort_method_group.addButton(self.sort_date, 1)
        self.sort_method_group.addButton(self.sort_name, 2)

        # تنظیم وضعیت پیش‌فرض
        if self.settings.get("sort_method") == "date":
            self.sort_date.setChecked(True)
        elif self.settings.get("sort_method") == "name":
            self.sort_name.setChecked(True)

        sort_layout.addWidget(self.sort_date)
        sort_layout.addWidget(self.sort_name)

        # فیلد برای وارد کردن الگوی رجکس سفارشی
        regex_layout = QFormLayout()
        self.custom_regex = QLineEdit(self.settings.get("custom_regex"))
        self.custom_regex.setMinimumWidth(350)
        regex_layout.addRow("الگوی رجکس سفارشی برای استخراج تاریخ:", self.custom_regex)

        # توضیح رجکس
        regex_info = QLabel(
            "مثال: r\"_(\d+)_(\d+)_(\d+)_(\d+)_(\d+)_(\d+)\s(AM|PM)\" برای استخراج تاریخ به فرمت ماه_روز_سال_ساعت_دقیقه_ثانیه")
        regex_info.setWordWrap(True)
        regex_info.setStyleSheet("color: #666666; font-size: 11px;")

        sort_layout.addLayout(regex_layout)
        sort_layout.addWidget(regex_info)

        # اتصال وضعیت فعال/غیرفعال بودن فیلد رجکس به رادیو باتن تاریخ
        self.sort_date.toggled.connect(self.toggle_regex_field)

        self.layout.addWidget(sort_group)

        # گروه تنظیمات مسیر ذخیره فایل خروجی
        output_path_group = QGroupBox("تنظیمات مسیر ذخیره فایل خروجی")
        output_path_layout = QVBoxLayout(output_path_group)

        # رادیو باتن‌ها برای انتخاب نوع مسیر خروجی
        self.output_path_group = QButtonGroup(self)

        self.same_folder_radio = QRadioButton("ذخیره در همان پوشه")
        self.fixed_folder_radio = QRadioButton("ذخیره در یک پوشه ثابت")
        self.ask_user_radio = QRadioButton("پرسیدن مسیر برای هر ویدئو")

        self.output_path_group.addButton(self.same_folder_radio, 1)
        self.output_path_group.addButton(self.fixed_folder_radio, 2)
        self.output_path_group.addButton(self.ask_user_radio, 3)

        # تنظیم وضعیت پیش‌فرض
        output_path_type = self.settings.get("output_path_type")
        if output_path_type == "same_folder":
            self.same_folder_radio.setChecked(True)
        elif output_path_type == "fixed_folder":
            self.fixed_folder_radio.setChecked(True)
        elif output_path_type == "ask_user":
            self.ask_user_radio.setChecked(True)

        output_path_layout.addWidget(self.same_folder_radio)
        output_path_layout.addWidget(self.fixed_folder_radio)
        output_path_layout.addWidget(self.ask_user_radio)

        # فیلد برای فرمت نام فایل خروجی
        filename_layout = QVBoxLayout()

        # بخش بالایی: کمبوباکس فرمت‌های پرکاربرد
        format_header_layout = QHBoxLayout()
        format_header_layout.addWidget(QLabel("الگوی نام فایل خروجی:"))

        self.format_templates = QComboBox()
        self.format_templates.addItem("انتخاب الگوی پیش‌فرض...", "")
        self.format_templates.addItem("نام‌پوشه_video.mp4", "{folder_name}_video.mp4")
        self.format_templates.addItem("video_نام‌پوشه.mp4", "video_{folder_name}.mp4")
        self.format_templates.addItem("نام‌پوشه.mp4", "{folder_name}.mp4")
        self.format_templates.addItem("نام‌پوشه_تاریخ.mp4", "{folder_name}_{date}.mp4")
        self.format_templates.addItem("output.mp4", "output.mp4")
        self.format_templates.currentIndexChanged.connect(self.apply_filename_template)

        format_header_layout.addWidget(self.format_templates)
        filename_layout.addLayout(format_header_layout)

        # بخش پایینی: فیلد متن برای ویرایش دستی فرمت
        format_input_layout = QHBoxLayout()
        format_input_layout.addWidget(QLabel("فرمت:"))
        self.output_filename_format = QLineEdit(self.settings.get("output_filename_format"))
        format_input_layout.addWidget(self.output_filename_format)
        filename_layout.addLayout(format_input_layout)

        output_path_layout.addLayout(filename_layout)

        # راهنمای فرمت نام فایل - بهبود یافته
        filename_help = QLabel("متغیرهای قابل استفاده:\n"
                               "{folder_name} = نام پوشه\n"
                               "{date} = تاریخ فعلی (YYYY-MM-DD)")
        filename_help.setWordWrap(True)
        filename_help.setStyleSheet("color: #666666; font-size: 11px;")
        output_path_layout.addWidget(filename_help)

        # انتخاب پوشه ثابت
        fixed_folder_layout = QHBoxLayout()
        self.fixed_output_folder = QLineEdit(self.settings.get("fixed_output_folder"))
        self.browse_button = QPushButton("انتخاب...")
        self.browse_button.clicked.connect(self.browse_fixed_folder)

        fixed_folder_layout.addWidget(QLabel("پوشه ثابت:"))
        fixed_folder_layout.addWidget(self.fixed_output_folder)
        fixed_folder_layout.addWidget(self.browse_button)
        output_path_layout.addLayout(fixed_folder_layout)

        # اتصال فعال/غیرفعال کردن بخش پوشه ثابت
        self.fixed_folder_radio.toggled.connect(self.toggle_fixed_folder_section)

        self.layout.addWidget(output_path_group)

        # گروه تنظیمات کیفیت خروجی
        quality_group = QGroupBox("تنظیمات کیفیت خروجی")
        quality_layout = QFormLayout(quality_group)

        # کدک ویدیو
        self.video_codec = QComboBox()
        self.video_codec.addItems(["libx264", "libx265", "mpeg4", "libvpx", "libvpx-vp9"])
        self.video_codec.setCurrentText(self.settings.get("video_codec"))
        quality_layout.addRow("کدک ویدیو:", self.video_codec)

        # بیت‌ریت ویدیو
        self.video_bitrate = QLineEdit(self.settings.get("video_bitrate"))
        quality_layout.addRow("بیت‌ریت ویدیو (مثال: 700k, 2M):", self.video_bitrate)

        # کدک صدا
        self.audio_codec = QComboBox()
        self.audio_codec.addItems(["aac", "mp3", "libvorbis", "libopus"])
        self.audio_codec.setCurrentText(self.settings.get("audio_codec"))
        quality_layout.addRow("کدک صدا:", self.audio_codec)

        # بیت‌ریت صدا
        self.audio_bitrate = QLineEdit(self.settings.get("audio_bitrate"))
        quality_layout.addRow("بیت‌ریت صدا (مثال: 128k):", self.audio_bitrate)

        # FPS
        self.fps = QSpinBox()
        self.fps.setRange(15, 60)
        self.fps.setValue(self.settings.get("fps"))
        quality_layout.addRow("فریم بر ثانیه:", self.fps)

        # پیش‌تنظیم کدک
        self.preset = QComboBox()
        self.preset.addItems(
            ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"])
        self.preset.setCurrentText(self.settings.get("preset"))
        quality_layout.addRow("پیش‌تنظیم (سرعت/کیفیت):", self.preset)
        preset_info = QLabel("ultrafast = سریع‌ترین، کیفیت پایین | veryslow = کندترین، بهترین کیفیت")
        preset_info.setStyleSheet("color: #666666; font-size: 10px;")
        quality_layout.addRow("", preset_info)

        # تعداد ترد
        self.threads = QSpinBox()
        self.threads.setRange(1, 16)
        self.threads.setValue(self.settings.get("threads"))
        quality_layout.addRow("تعداد ترد (پردازنده):", self.threads)

        self.layout.addWidget(quality_group)

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

    def toggle_custom_resolution(self, enabled):
        """فعال/غیرفعال کردن فیلدهای رزولوشن سفارشی"""
        self.output_width.setEnabled(enabled)
        self.output_height.setEnabled(enabled)
        # اگر سفارشی فعال شد، رزولوشن پیش‌فرض را غیرفعال کن
        self.output_resolution.setEnabled(not enabled)

    def toggle_regex_field(self, enabled):
        """فعال/غیرفعال کردن فیلد رجکس"""
        self.custom_regex.setEnabled(enabled)

    def toggle_fixed_folder_section(self, enabled):
        """فعال/غیرفعال کردن بخش تنظیم پوشه ثابت"""
        self.fixed_output_folder.setEnabled(enabled)
        self.browse_button.setEnabled(enabled)

    def on_color_selection_changed(self, index):
        """مدیریت تغییر انتخاب رنگ از کمبوباکس"""
        color_value = self.color_combo.currentData()

        if color_value == "custom":
            # اگر "سفارشی" انتخاب شد، دیالوگ انتخاب رنگ را باز می‌کنیم
            self.choose_background_color()
        else:
            # در غیر این صورت، رنگ انتخاب شده را تنظیم می‌کنیم
            self.background_color = color_value
            self.update_color_button()

    def update_color_button(self):
        """به‌روزرسانی دکمه رنگ با رنگ انتخاب شده"""
        color = QColor(self.background_color)
        style = f"background-color: {self.background_color};"

        # تیره یا روشن بودن رنگ را تشخیص دهید و رنگ متن را متناسب با آن تنظیم کنید
        luminance = (0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()) / 255
        if luminance > 0.5:
            style += "color: black;"
        else:
            style += "color: white;"

        self.background_color_button.setStyleSheet(style)
        self.background_color_button.setText(self.background_color)

    def choose_background_color(self):
        """انتخاب رنگ پس‌زمینه"""
        color = QColorDialog.getColor(QColor(self.background_color), self, "انتخاب رنگ پس‌زمینه")

        if color.isValid():
            self.background_color = color.name()
            self.update_color_button()

            # اگر رنگ انتخابی با یکی از رنگ‌های پیش‌فرض مطابقت داشت، آن را انتخاب کنیم
            found = False
            for i in range(self.color_combo.count() - 1):  # به جز آیتم آخر که "سفارشی" است
                if self.color_combo.itemData(i) == self.background_color:
                    self.color_combo.setCurrentIndex(i)
                    found = True
                    break

            if not found:
                # اگر در لیست نبود، گزینه سفارشی را انتخاب کنیم
                self.color_combo.setCurrentIndex(self.color_combo.count() - 1)

    def toggle_scaling_options(self, enabled):
        """فعال/غیرفعال کردن گزینه‌های مقیاس‌دهی"""
        self.maintain_aspect_ratio.setEnabled(enabled)
        self.scaling_mode.setEnabled(enabled)
        self.update_scaling_options()

    def update_scaling_options(self):
        """به‌روزرسانی وضعیت گزینه‌های مقیاس‌دهی بر اساس حالت انتخاب شده"""
        enabled = self.normalize_all_clips.isChecked()
        mode = self.scaling_mode.currentData() if enabled else None

        # فعال/غیرفعال کردن کمبوی رنگ و دکمه رنگ پس‌زمینه بر اساس حالت مقیاس‌دهی
        color_enabled = enabled and mode == "fit"
        self.color_combo.setEnabled(color_enabled)
        self.background_color_button.setEnabled(color_enabled)

        # به‌روزرسانی متن توضیحات
        self.update_scaling_info(mode)

    def update_scaling_info(self, mode):
        """به‌روزرسانی متن توضیحات بر اساس حالت مقیاس‌دهی"""
        if mode == "fit":
            self.scaling_mode_info.setText(
                "حالت Fit: تصویر کامل نمایش داده می‌شود و حاشیه‌های خالی با رنگ پس‌زمینه پر می‌شوند.")
        elif mode == "fill":
            self.scaling_mode_info.setText(
                "حالت Fill: تصویر کل قاب را پر می‌کند و ممکن است بخش‌هایی از تصویر برش بخورد.")
        elif mode == "stretch":
            self.scaling_mode_info.setText("حالت Stretch: تصویر کشیده می‌شود تا کل قاب را بدون حفظ نسبت اصلی پر کند.")
        else:
            self.scaling_mode_info.setText("")

    def browse_fixed_folder(self):
        """انتخاب پوشه ثابت برای ذخیره فایل‌های خروجی"""
        folder = QFileDialog.getExistingDirectory(
            self, "انتخاب پوشه ذخیره", self.fixed_output_folder.text())
        if folder:
            self.fixed_output_folder.setText(folder)

    def accept(self):
        """ذخیره تنظیمات و بستن دیالوگ"""
        # هشدار در مورد پردازش‌های در حال اجرا
        if self.queue_manager.has_running_tasks():
            reply = QMessageBox.information(
                self,
                "اعمال تنظیمات",
                "تنظیمات جدید فقط برای پردازش‌های آینده اعمال می‌شود و بر روی پردازش‌های در حال اجرا تاثیری ندارد.",
                QMessageBox.Ok
            )

        # ذخیره تنظیمات در شیء settings
        self.settings.set("image_duration", self.image_duration.value())

        self.settings.set("use_custom_resolution", self.use_custom_resolution.isChecked())
        self.settings.set("output_width", self.output_width.value())
        self.settings.set("output_height", self.output_height.value())

        if not self.use_custom_resolution.isChecked():
            current_data = self.output_resolution.currentData()
            self.settings.set("output_resolution", current_data)

        # ذخیره تنظیمات مرتب‌سازی
        if self.sort_date.isChecked():
            self.settings.set("sort_method", "date")
        elif self.sort_name.isChecked():
            self.settings.set("sort_method", "name")

        # ذخیره رجکس سفارشی
        self.settings.set("custom_regex", self.custom_regex.text())

        # ذخیره تنظیمات مسیر خروجی
        if self.same_folder_radio.isChecked():
            self.settings.set("output_path_type", "same_folder")
        elif self.fixed_folder_radio.isChecked():
            self.settings.set("output_path_type", "fixed_folder")
        elif self.ask_user_radio.isChecked():
            self.settings.set("output_path_type", "ask_user")

        # ذخیره فرمت نام فایل و پوشه ثابت
        self.settings.set("output_filename_format", self.output_filename_format.text())
        self.settings.set("fixed_output_folder", self.fixed_output_folder.text())

        # ذخیره تنظیمات کیفیت خروجی
        self.settings.set("video_codec", self.video_codec.currentText())
        self.settings.set("video_bitrate", self.video_bitrate.text())
        self.settings.set("audio_codec", self.audio_codec.currentText())
        self.settings.set("audio_bitrate", self.audio_bitrate.text())
        self.settings.set("fps", self.fps.value())
        self.settings.set("preset", self.preset.currentText())
        self.settings.set("threads", self.threads.value())

        # ذخیره تنظیمات مقیاس‌دهی
        self.settings.set("normalize_all_clips", self.normalize_all_clips.isChecked())
        self.settings.set("maintain_aspect_ratio", self.maintain_aspect_ratio.isChecked())
        self.settings.set("scaling_mode", self.scaling_mode.currentData())
        self.settings.set("background_color", self.background_color)

        # ذخیره تنظیمات
        self.settings.save_settings()

        super().accept()


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
            from PySide6.QtGui import QPixmap, QColor

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

    def update_settings_display(self):
        """به‌روزرسانی نمایش تنظیمات فعلی در پایین صفحه"""
        # ابتدا متن رزولوشن را آماده می‌کنیم
        res_text = "سایز اصلی"
        if self.settings.get("use_custom_resolution"):
            width = self.settings.get("output_width")
            height = self.settings.get("output_height")
            res_text = f"سفارشی ({width}x{height})"
        elif self.settings.get("output_resolution") != "original":
            res_text = self.settings.get("output_resolution")

        # متن روش مرتب‌سازی
        sort_text = "نام فایل"
        if self.settings.get("sort_method") == "date":
            sort_text = "تاریخ"

        # متن محل ذخیره
        output_path_type = self.settings.get("output_path_type")
        if output_path_type == "same_folder":
            output_path_text = "همان پوشه"
        elif output_path_type == "fixed_folder":
            output_path_text = "پوشه ثابت"
        else:  # ask_user
            output_path_text = "پرسش از کاربر"

        # متن کیفیت ویدیو
        quality_text = f"{self.settings.get('video_codec')}/{self.settings.get('video_bitrate')}"

        # متن کامل تنظیمات
        settings_text = f"تنظیمات: تصویر {self.settings.get('image_duration')} ثانیه | رزولوشن: {res_text} | مرتب‌سازی: {sort_text} | کیفیت: {quality_text} | ذخیره در: {output_path_text}"

        # جستجو و به‌روزرسانی برچسب تنظیمات
        for child in self.centralWidget().children():
            if isinstance(child, QLabel) and "تنظیمات" in child.text():
                child.setText(settings_text)
                return

        # اگر برچسبی پیدا نشد، یکی جدید ایجاد می‌کنیم
        current_settings = QLabel(settings_text)
        current_settings.setStyleSheet("color: #666; margin: 5px;")
        self.centralWidget().layout().addWidget(current_settings)

    def update_queue_info(self):
        """به‌روزرسانی اطلاعات صف"""
        running = len(self.queue_manager.running)
        queued = len(self.queue_manager.queue)
        self.queue_info.setText(f"وضعیت صف: {running} در حال اجرا | {queued} در صف")

    def update_empty_state(self):
        """بررسی و به‌روزرسانی نمایش حالت خالی"""
        has_widgets = len(self.folder_widgets) > 0

        # نمایش یا پنهان کردن حالت خالی و ناحیه اسکرول
        self.empty_state_widget.setVisible(not has_widgets)
        self.scroll_area.setVisible(has_widgets)

    def add_folders(self):
        # استفاده از دیالوگ سفارشی برای انتخاب چندین پوشه
        dialog = MultiFolderDialog(self)
        if dialog.exec():
            folders = dialog.selected_folders()
            self.process_folders(folders)

    def process_folders(self, folders):
        """پردازش لیستی از پوشه‌ها"""
        if not folders:
            return

        for folder in folders:
            if folder in self.folder_widgets:
                QMessageBox.warning(self, "هشدار", f"پوشه {folder} قبلاً اضافه شده است.")
                continue

            # ایجاد ویجت برای این پوشه - انتقال مرجع به پنجره اصلی
            folder_widget = FolderProcessWidget(folder, self.queue_manager, self.settings, self)
            self.folder_widgets[folder] = folder_widget

            # اتصال سیگنال حذف ویجت
            folder_widget.remove_requested.connect(self.remove_folder_widget)

            # قرار دادن قبل از فضای خالی انتهایی
            self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, folder_widget)

            # شروع پردازش
            folder_widget.start_process()

        # به‌روزرسانی اطلاعات صف و وضعیت خالی
        self.update_queue_info()
        self.update_empty_state()

    def remove_folder_widget(self, widget):
        """حذف یک ویجت پردازش فولدر از UI"""
        # یافتن کلید فولدر با استفاده از ویجت
        folder_to_remove = None
        for folder, w in self.folder_widgets.items():
            if w == widget:
                folder_to_remove = folder
                break

        # حذف از UI
        if widget in self.scroll_layout.parentWidget().children():
            self.scroll_layout.removeWidget(widget)
            widget.deleteLater()  # آزادسازی حافظه

        # حذف از دیکشنری
        if folder_to_remove:
            del self.folder_widgets[folder_to_remove]
            # اعلام به مدیر صف
            self.queue_manager.remove_widget(widget.thread)

        # به‌روزرسانی وضعیت خالی
        self.update_empty_state()

    def show_settings(self):
        """نمایش دیالوگ تنظیمات"""
        dialog = SettingsDialog(self.settings, self.queue_manager, self)
        if dialog.exec():
            # به‌روزرسانی نمایش تنظیمات
            self.update_settings_display()

    @Slot(str, str)
    def handle_output_file_check(self, folder_path, output_file):
        """بررسی وجود فایل خروجی و درخواست تایید از کاربر"""
        # یافتن thread مربوطه
        thread = None
        for folder, widget in self.folder_widgets.items():
            if folder == folder_path:
                thread = widget.thread
                break

        if not thread:
            return

        # نمایش دیالوگ تایید
        reply = QMessageBox.question(
            self,
            "فایل خروجی موجود است",
            f"فایل خروجی {os.path.basename(output_file)} از قبل وجود دارد.\nآیا می‌خواهید آن را بازنویسی کنید؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # تایید بازنویسی
            thread.set_overwrite_confirmed(True)
        else:
            # لغو عملیات
            thread.cancel()

    @Slot(str, str)
    def handle_output_path_request(self, folder_path, default_filename):
        """دریافت مسیر فایل خروجی از کاربر"""
        # یافتن thread مربوطه
        thread = None
        for folder, widget in self.folder_widgets.items():
            if folder == folder_path:
                thread = widget.thread
                break

        if not thread:
            return

        # نمایش دیالوگ انتخاب مسیر فایل
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "انتخاب مسیر ذخیره",
            os.path.join(os.path.expanduser("~/Videos"), default_filename),
            "Video Files (*.mp4)"
        )

        if file_path:
            thread.set_output_filename(file_path)
        else:
            # اگر کاربر لغو کرد، پردازش را لغو کن
            thread.cancel()

    # پیاده‌سازی رویدادهای درگ و دراپ
    def dragEnterEvent(self, event: QDragEnterEvent):
        """بررسی اینکه آیا محتوای درگ شده پوشه است یا خیر"""
        mime_data = event.mimeData()

        if mime_data.hasUrls():
            # بررسی اینکه آیا URL‌های درگ شده پوشه هستند یا خیر
            for url in mime_data.urls():
                if url.isLocalFile() and os.path.isdir(url.toLocalFile()):
                    event.acceptProposedAction()
                    return

        event.ignore()

    def dropEvent(self, event: QDropEvent):
        """پردازش پوشه‌های رها شده"""
        mime_data = event.mimeData()

        if mime_data.hasUrls():
            folders = []

            for url in mime_data.urls():
                if url.isLocalFile():
                    path = url.toLocalFile()
                    if os.path.isdir(path):
                        folders.append(path)

            # پردازش پوشه‌های دریافت شده
            self.process_folders(folders)

            event.acceptProposedAction()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    # تنظیم استایل کلی برنامه
    app.setStyle("Fusion")

    sys.exit(app.exec())