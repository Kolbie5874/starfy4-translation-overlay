"""
Starfy4 Translation Overlay Utils
"""

from . import systemcheck
errors = systemcheck.run()

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QTextBrowser, QPushButton

def check_for_vlc() -> bool:
    """"
    Checks if VLC is installed.

    Returns:
        bool: True if VLC is installed, False otherwise.
    """

    return systemcheck.vlc_installed()


class ErrorBox(QWidget):
    def __init__(self, errors):
        super().__init__()
        self.initUI(errors)

    def initUI(self, errors):
        layout = QVBoxLayout()

        title_label = QLabel("Error Details", self)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title_label)

        error_text_browser = QTextBrowser(self)
        for error in errors:
            error_text_browser.append(error)
        layout.addWidget(error_text_browser)

        ok_button = QPushButton("OK", self)
        ok_button.clicked.connect(self.close)
        layout.addWidget(ok_button)

        self.setLayout(layout)
        self.setWindowTitle('Error')
        self.setGeometry(300, 300, 450, 300)


def call_systemcheck_gui():
    import sys

    app = QApplication(sys.argv)

    if errors:
        error_box = ErrorBox(errors)
        error_box.show()
        app.exec_()