"""PDF EBOOK Reader application entry point."""

import sys

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main() -> None:
    """Create the Qt application and show the main window."""
    app = QApplication(sys.argv)
    app.setApplicationName("PDF EBOOK Reader")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
