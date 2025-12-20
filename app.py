from PySide6.QtWidgets import QApplication, QMainWindow
import sys
import os 

from ui.main_window import MainWindow
from db import connect_db, init_db, insert_test_transaction, get_all_transactions


def main():
    os.environ['QT_LOGGING_RULES'] = 'qt.pointer.dispath=false' #to get rid of annoying log message
    db_connection = connect_db()
    init_db(db_connection)    
    db_connection.close()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
    
    
if __name__ == '__main__': 
    raise(SystemExit(main()))