from PySide6.QtWidgets import QApplication, QMainWindow
import sys

from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
    
    
if __name__ == '__main__': 
    raise(SystemExit(main()))