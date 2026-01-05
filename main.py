#!/usr/bin/env python3
"""
MyHighlights - Instagram Highlight Downloader
Desktop application for downloading and managing Instagram highlights
"""

import os
import sys
import asyncio
import logging

# Set Qt API preference
if "QT_API" not in os.environ:
    os.environ["QT_API"] = "pyside6"

from qtpy.QtWidgets import QApplication
from qtpy.QtCore import Qt
import qasync

from myhighlights.ui.main_window import MainWindow


def setup_logging():
    """Configure logging for the application"""
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    # File handler
    file_handler = logging.FileHandler('myhighlights.log', mode='w')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Reduce noise from Qt and other libraries
    logging.getLogger('qtpy').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info("MyHighlights Application Starting")
    logger.info("=" * 80)
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Platform: {sys.platform}")

def main():
    """Application entry point"""
    # Setup logging first
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Configuring Qt application...")

    # Enable high DPI support
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("MyHighlights")
    app.setOrganizationName("MyHighlights")

    logger.info("Setting up async event loop...")
    # Setup async event loop with qasync
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    logger.info("Creating main window...")
    # Create and show main window
    window = MainWindow()
    window.show()
    logger.info("Main window shown")

    logger.info("Starting event loop...")
    # Run event loop
    with loop:
        sys.exit(loop.run_forever())


if __name__ == "__main__":
    main()
