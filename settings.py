import os
from PySide6.QtCore import QSettings


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