import os 
from PySide6.QtNetwork import QNetworkProxy

from PySide6.QtWidgets import QApplication, QMainWindow
import sys


from ui.main_window import MainWindow
from db.core import connect_db, init_db


def main():
    QNetworkProxy.setApplicationProxy(QNetworkProxy(QNetworkProxy.NoProxy)) #to make weather work
    os.environ['QT_LOGGING_RULES'] = 'qt.pointer.dispatch=false' #to get rid of annoying log message
    db_connection = connect_db()
    init_db(db_connection)    
    db_connection.close()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
    
    
if __name__ == '__main__': 
    raise(SystemExit(main()))