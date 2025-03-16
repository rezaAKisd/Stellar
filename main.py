import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt  # اطمینان از import صحیح
from main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # استایل یکسان در تمام پلتفرم‌ها

    # تنظیم جهت راست به چپ برای زبان فارسی
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)  # استفاده از enum صحیح

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()