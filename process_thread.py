import os
import time
import re
import datetime
import glob
from PySide6.QtCore import QThread, Signal, QTimer
from PySide6.QtWidgets import QApplication
from proglog import ProgressBarLogger
from moviepy import ImageClip, VideoFileClip, concatenate_videoclips, ColorClip, CompositeVideoClip

class VideoProcessThread(QThread):
    progress_updated = Signal(str, float)
    stage_updated = Signal(str, str)  # folder_path, stage_description
    process_finished = Signal(str, bool, str, float)  # folder_path, success, message, elapsed_time
    check_output_file = Signal(str, str)  # folder_path, output_file_path
    ask_output_path = Signal(str, str)  # folder_path, default_filename
    time_updated = Signal(str, float, float)  # folder_path, elapsed_time, estimated_remaining_time
    output_file_error = Signal(str, str)  # folder_path, error_message

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

        # افزودن تایمر برای بررسی وضعیت فایل خروجی
        self.file_check_timer = None
        self.output_file_valid = True

    def __del__(self):
        """مدیریت تخریب شیء ترد"""
        self.wait()  # صبر کنید تا ترد به پایان برسد

    # اضافه کردن کلاس داخلی ThreadBarLogger برای نمایش پیشرفت
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

    def run(self):
        self.start_time = time.time()
        self.last_progress_update = self.start_time
        self.total_pause_time = 0

        try:
            # قبل از هر کار، پرچم‌های وضعیت را بازنشانی می‌کنیم
            self.overwrite_confirmed = False
            self.output_file_valid = True
            self.process_video()

            # محاسبه کل زمان صرف شده (با کسر زمان توقف)
            elapsed_time = time.time() - self.start_time - self.total_pause_time

            if not self.cancelled and self.output_file_valid:
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
        finally:
            # متوقف کردن تایمر بررسی فایل در صورت وجود
            if self.file_check_timer and self.file_check_timer.isActive():
                self.file_check_timer.stop()
                self.file_check_timer = None

            # اطمینان از آزادسازی منابع حتی در صورت خطا
            try:
                # آزادسازی هر منبعی که ممکن است باز مانده باشد
                pass
            except:
                pass

    def cancel(self):
        """لغو پردازش"""
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
            QApplication.processEvents()  # اجازه پردازش رویدادها در رابط کاربری

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

    def start_file_monitoring(self):
        """شروع مانیتورینگ فایل خروجی"""
        # ایجاد تایمر برای بررسی دوره‌ای فایل خروجی
        if not self.file_check_timer:
            self.file_check_timer = QTimer()
            self.file_check_timer.timeout.connect(self.check_output_file_status)
            self.file_check_timer.start(2000)  # بررسی هر 2 ثانیه

    def check_output_file_status(self):
        """بررسی وضعیت فایل خروجی"""
        if self.cancelled or not self.output_filename:
            return

        # بررسی وجود و قابلیت نوشتن در فایل
        try:
            # اگر فایل وجود ندارد
            if not os.path.exists(self.output_filename):
                self.output_file_valid = False
                self.cancelled = True
                self.output_file_error.emit(self.folder_path, "فایل خروجی حذف یا جابجا شده است")
                return

            # بررسی قابلیت نوشتن
            try:
                with open(self.output_filename, 'a+'):
                    pass
            except (PermissionError, IOError):
                self.output_file_valid = False
                self.cancelled = True
                self.output_file_error.emit(self.folder_path,
                                            "فایل خروجی قابل دسترسی نیست (ممکن است توسط برنامه دیگری باز شده باشد)")
                return

        except Exception as e:
            self.output_file_valid = False
            self.cancelled = True
            self.output_file_error.emit(self.folder_path, f"خطا در بررسی فایل خروجی: {str(e)}")

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
        """پردازش اصلی ویدیو"""
        folder_path = self.folder_path
        self.update_stage("در حال آماده‌سازی")

        # مقداردهی اولیه متغیرهای زمان‌سنجی
        self.last_progress_percent = 0

        if not os.path.exists(folder_path):
            raise Exception(f"پوشه وجود ندارد: {folder_path}")

        # تعیین مسیر و نام فایل خروجی براساس تنظیمات
        folder_name = os.path.basename(folder_path)
        output_path_type = self.settings.get("output_path_type")
        output_filename_format = self.settings.get("output_filename_format")

        # جایگزینی متغیرها در فرمت نام فایل خروجی
        output_filename = output_filename_format.format(folder_name=folder_name)

        # تعیین مسیر کامل فایل خروجی
        if output_path_type == "same_folder":
            output_path = os.path.join(folder_path, output_filename)
        elif output_path_type == "fixed_folder":
            fixed_folder = self.settings.get("fixed_output_folder")
            if not os.path.exists(fixed_folder):
                os.makedirs(fixed_folder, exist_ok=True)
            output_path = os.path.join(fixed_folder, output_filename)
        elif output_path_type == "ask_user":
            # ارسال سیگنال برای درخواست مسیر از کاربر
            default_path = os.path.join(folder_path, output_filename)
            self.ask_output_path.emit(folder_path, default_path)
            # صبر می‌کنیم تا مسیر فایل تنظیم شود
            while not hasattr(self, 'output_filename') or not self.output_filename:
                time.sleep(0.1)
                # بررسی لغو شدن
                if self.cancelled:
                    return
            output_path = self.output_filename
        else:
            # حالت پیش‌فرض: ذخیره در همان پوشه
            output_path = os.path.join(folder_path, output_filename)

        # تنظیم مسیر خروجی
        self.output_filename = output_path

        # بررسی وجود فایل خروجی
        if os.path.exists(output_path) and not self.overwrite_confirmed:
            self.check_output_file.emit(folder_path, output_path)
            # صبر برای تصمیم کاربر
            while not self.overwrite_confirmed and not self.cancelled:
                time.sleep(0.1)

            # اگر عملیات لغو شده، خارج شویم
            if self.cancelled:
                return

        # شروع مانیتورینگ فایل خروجی
        self.start_file_monitoring()

        # جستجوی فایل‌های تصویر و ویدیو در پوشه
        self.update_stage("در حال جستجوی فایل‌های رسانه‌ای...")
        image_exts = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff']
        video_exts = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm']

        media_files = []

        # بررسی تمام فایل‌های موجود در پوشه
        for f in os.listdir(folder_path):
            if self.cancelled:
                return

            file_path = os.path.join(folder_path, f)
            if os.path.isfile(file_path):
                ext = os.path.splitext(f)[1].lower()
                if ext in image_exts or ext in video_exts:
                    media_files.append(file_path)

        if not media_files:
            raise Exception("هیچ فایل تصویری یا ویدیویی در پوشه یافت نشد.")

        # مرتب‌سازی فایل‌ها
        self.update_stage("در حال مرتب‌سازی فایل‌ها...")
        media_files.sort(key=self.extract_sort_key)

        # بارگذاری کلیپ‌ها
        self.update_stage("در حال بارگذاری و پردازش فایل‌ها...")
        clips = []
        total_files = len(media_files)

        # تعیین رزولوشن خروجی
        output_resolution = self.settings.get("output_resolution")
        use_custom_resolution = self.settings.get("use_custom_resolution")
        if use_custom_resolution:
            target_width = self.settings.get("output_width")
            target_height = self.settings.get("output_height")
        elif output_resolution == "720p":
            target_width, target_height = 1280, 720
        elif output_resolution == "1080p":
            target_width, target_height = 1920, 1080
        elif output_resolution == "4k":
            target_width, target_height = 3840, 2160
        else:  # original یا هر مقدار دیگر
            # در مراحل بعدی تعیین می‌شود
            target_width, target_height = None, None

        # تنظیمات مقیاس‌دهی
        scaling_mode = self.settings.get("scaling_mode")
        maintain_aspect_ratio = self.settings.get("maintain_aspect_ratio")
        normalize_all_clips = self.settings.get("normalize_all_clips")
        bg_color_hex = self.settings.get("background_color")

        # تبدیل رنگ hex به RGB
        bg_color = tuple(int(bg_color_hex.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4))

        # پیدا کردن بزرگترین رزولوشن در میان فایل‌ها اگر output_resolution == "original"
        if output_resolution == "original" and not use_custom_resolution:
            max_width, max_height = 0, 0
            for file_path in media_files:
                if self.cancelled:
                    return

                ext = os.path.splitext(file_path)[1].lower()
                try:
                    if ext in image_exts:
                        from PIL import Image
                        with Image.open(file_path) as img:
                            width, height = img.size
                    elif ext in video_exts:
                        clip = VideoFileClip(file_path)
                        width, height = clip.size
                        clip.close()

                    if width > max_width:
                        max_width = width
                    if height > max_height:
                        max_height = height
                except Exception as e:
                    print(f"خطا در بررسی ابعاد فایل {file_path}: {str(e)}")

            target_width, target_height = max_width, max_height

            # اگر هیچ فایلی قابل خواندن نبود، از یک مقدار پیش‌فرض استفاده کنیم
            if target_width == 0 or target_height == 0:
                target_width, target_height = 1280, 720

        # ایجاد کلیپ‌ها با نمایش پیشرفت
        for i, file_path in enumerate(media_files):
            if self.cancelled:
                return

            self.check_pause()  # بررسی وضعیت توقف

            # به‌روزرسانی پیشرفت
            progress_percent = (i / total_files) * 40  # 40% اول برای بارگذاری
            self.progress_updated.emit(folder_path, progress_percent)
            self.update_time_estimate(progress_percent)

            ext = os.path.splitext(file_path)[1].lower()

            try:
                if ext in image_exts:
                    # مدت زمان نمایش هر تصویر
                    duration = self.settings.get("image_duration")
                    clip = ImageClip(file_path, duration=duration)
                elif ext in video_exts:
                    clip = VideoFileClip(file_path)
                else:
                    continue  # فایل غیرقابل پشتیبانی

                # اعمال مقیاس‌دهی اگر لازم است
                if normalize_all_clips:
                    clip = self.apply_scaling(clip, (target_width, target_height), scaling_mode, maintain_aspect_ratio,
                                              bg_color)

                clips.append(clip)
            except Exception as e:
                print(f"خطا در بارگذاری فایل {file_path}: {str(e)}")

        if not clips:
            raise Exception("هیچ کلیپ معتبری ایجاد نشد.")

        # ادغام کلیپ‌ها
        self.update_stage("در حال ادغام کلیپ‌ها...")
        final_clip = concatenate_videoclips(clips, method="chain")

        # تنظیم پارامترهای خروجی
        fps = self.settings.get("fps")
        preset = self.settings.get("preset")
        video_codec = self.settings.get("video_codec")
        video_bitrate = self.settings.get("video_bitrate")
        audio_codec = self.settings.get("audio_codec")
        audio_bitrate = self.settings.get("audio_bitrate")
        threads = self.settings.get("threads")

        # تنظیم فلگ لغو برای جلوگیری از دستکاری در مراحل حساس
        self.set_pause_lock(True)

        try:
            self.update_stage("در حال نوشتن ویدیوی خروجی...")

            # ایجاد لاگر برای نمایش پیشرفت
            logger = self.ThreadBarLogger(
                lambda path, percent: self.progress_updated.emit(path, 40 + percent * 0.6),  # 40% تا 100%
                lambda stage: self.update_stage(stage),
                folder_path,
                self.check_pause,
                lambda percent: self.update_time_estimate(40 + percent * 0.6)
            )

            # نوشتن فایل خروجی
            final_clip.write_videofile(
                output_path,
                fps=fps,
                preset=preset,
                codec=video_codec,
                bitrate=video_bitrate,
                audio_codec=audio_codec,
                audio_bitrate=audio_bitrate,
                threads=threads,
                logger=logger
            )

            # بستن کلیپ‌ها برای آزادسازی منابع
            for clip in clips:
                clip.close()

            # تأیید اتمام موفقیت‌آمیز
            self.update_stage("پردازش با موفقیت به پایان رسید")
            self.progress_updated.emit(folder_path, 100)

        except Exception as e:
            raise Exception(f"خطا در ایجاد فایل خروجی: {str(e)}")
        finally:
            # حتماً قفل را آزاد کنید تا عملیات توقف دوباره امکان‌پذیر شود
            self.set_pause_lock(False)