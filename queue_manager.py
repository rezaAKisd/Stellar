from PySide6.QtCore import QObject


class QueueManager(QObject):
    def __init__(self, max_concurrent=2, parent=None):
        super().__init__(parent)
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
            # صبر کنید تا ترد به پایان برسد (با تایم‌اوت)
            if thread.isRunning() and not thread.wait(500):  # نیم ثانیه صبر کنید
                # اگر ترد به سرعت خاتمه نیافت، منتظر نمانید اما بعداً آن را بررسی کنید
                print(f"هشدار: ترد به سرعت متوقف نشد")
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