from PySide6.QtWidgets import QApplication, QMainWindow
import sys

from ui.main_window import MainWindow
from db import connect_db, init_db, insert_test_transaction, get_all_transactions


def main():
    db_connection = connect_db()
    init_db(db_connection)
    if len(get_all_transactions(db_connection)) <= 1:
        insert_test_transaction(db_connection)
    
    db_connection.close()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
    
    
if __name__ == '__main__': 
    raise(SystemExit(main()))