import os 
os.environ['QT_LOGGING_RULES'] = 'qt.pointer.dispatch=false' #to get rid of annoying log message


from PySide6.QtWidgets import QApplication, QMainWindow
import sys


from ui.main_window import MainWindow
from db.core import connect_db, init_db


def main():
    db_connection = connect_db()
    init_db(db_connection)    
    db_connection.close()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
    
    
if __name__ == '__main__': 
    raise(SystemExit(main()))