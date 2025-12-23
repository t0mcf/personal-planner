from PySide6.QtWidgets import QWidget, QPushButton, QLabel, QVBoxLayout, QComboBox, QHBoxLayout, QTableWidget, QSplitter, QTableWidgetItem, QDialog, QFileDialog, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QShowEvent

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from datetime import date, timedelta

from db.core import connect_db
from db.finance import list_transactions, insert_transaction, get_categories, get_transaction_by_id, update_transaction, import_transactions

from ui.dialogs.add_transaction_dialog import AddTransactionDialog
from ui.constants import DEFAULT_CATEGORIES

from csv_parser import parse_transactions_from_csv

class FinanceTransactionsView(QWidget): 
    
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        
        title = QLabel('finance')
        title.setObjectName('tabTitle')
        main_layout.addWidget(title)
        
        #horizontal split (table | visualizations)
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter, 1)
        
        #table part
        table = QWidget()
        table_layout = QVBoxLayout(table)
        
        bar = QVBoxLayout()
        
        filters_row = QHBoxLayout()
        actions_row = QHBoxLayout()

        self.time_period = QComboBox()
        self.time_period.addItems(['This month', 'Last 30 days', 'This year', 'All time'])
        
        self.transaction_type = QComboBox()
        self.transaction_type.addItems(['All', 'Expenses', 'Income'])
        
        self.category = QComboBox()
        self.category.addItems(['All', 'Uncategorized'])
        
        self.csv_import_button = QPushButton('Import csv file')
        self.csv_import_button.clicked.connect(self.open_csv_import)
        
        self.add_transaction_button = QPushButton('Add transaction')
        self.add_transaction_button.clicked.connect(self.open_add_dialog)
        
        filters_row.addWidget(QLabel('Period:'))
        filters_row.addWidget(self.time_period)
        filters_row.addWidget(QLabel('Type:'))
        filters_row.addWidget(self.transaction_type)
        filters_row.addWidget(QLabel('Category:'))
        filters_row.addWidget(self.category)
        filters_row.addStretch()
        
        actions_row.addWidget(self.csv_import_button)
        actions_row.addWidget(self.add_transaction_button)
        actions_row.addStretch()
        
        bar.addLayout(filters_row)
        bar.addLayout(actions_row)
        
        table_layout.addLayout(bar)

        self.transaction_table = QTableWidget(0,5)
        self.transaction_table.setHorizontalHeaderLabels(['Date', 'Amount', 'Category', 'Name', 'Info'])
        self.transaction_table.horizontalHeader().setStretchLastSection(True)
        self.transaction_table.cellDoubleClicked.connect(self.open_edit_dialog)
        table_layout.addWidget(self.transaction_table)
        
        #visualization part
        visu = QWidget()
        visu_layout = QVBoxLayout(visu)
        
        self.chart_title = QLabel('Expenses by Category')
        visu_layout.addWidget(self.chart_title)

        self.figure = Figure(figsize=(4, 3))
        self.canvas = FigureCanvas(self.figure)
        visu_layout.addWidget(self.canvas)
        
        visu_layout.addStretch()
        
        #___
        splitter.addWidget(table)
        splitter.addWidget(visu)
        splitter.setSizes([600, 400])
        
        #refresh after every change
        self.time_period.currentIndexChanged.connect(self.refresh)
        self.transaction_type.currentIndexChanged.connect(self.refresh)
        self.category.currentIndexChanged.connect(self.refresh)
        
        #test data
        self._test_data = [
            {'date': '2025-12-12', 'amount': -51.90, 'category': 'Groceries', 'info': 'Fresco'},
            {'date': '2025-12-12', 'amount': -10.99, 'category': 'Subscriptions', 'info': 'Spotify'},
            {'date': '2025-12-13', 'amount': 50, 'category': 'Income', 'info': 'Unknown'},
            {'date': '2025-12-13', 'amount': -3.49, 'category': 'Groceries', 'info': '7-Eleven'},
            {'date': '2025-12-13', 'amount': -6.50, 'category': 'Restaurant', 'info': 'Icchan Ramen'},
            {'date': '2025-12-14', 'amount': 1200, 'category': 'Income', 'info': 'Salary'},
            {'date': '2025-12-14', 'amount': -250, 'category': 'Clothing', 'info': 'Flamingo Vintage Store'}
        ]
        
        self.category.addItems(set([entry['category'] for entry in self._test_data]))
        
        self.refresh()
        
    def get_filters(self):
        period = self.time_period.currentText()
        if period != 'Custom':
            start_date, end_date = period_to_range(period)
        
        return {
            'period': period, #useless now, right?
            'type': self.transaction_type.currentText(),
            'category': self.category.currentText(),
            #for custom dates, still to be implemented
            'start_date': start_date,
            'end_date': end_date,
        }
    
    #deprecated
    def apply_filters(self, rows, filters):
        if filters['type'] == 'Expenses':
            rows = [row for row in rows if row['amount'] < 0]
        elif filters['type'] == 'Income':
            rows = [row for row in rows if row['amount'] > 0]
        if filters['category'] != 'All':
            rows = [row for row in rows if row['category'] == filters['category']]
        return rows 
    
    #changing table display depending on filters
    def refresh(self):
        filters = self.get_filters()       
        db_connection = connect_db()
            
        rows = list_transactions(
            db_connection,
            start_date=filters['start_date'],
            end_date=filters['end_date'],
            tx_type=filters['type'],
            limit=200
        )
        db_connection.close()
        
        self.fill_table(rows)
    
    #fill table display with certain rows
    def fill_table(self, rows):
        self.transaction_table.setRowCount(len(rows))
        
        for row_index, row in enumerate(rows):
            date_item = QTableWidgetItem(row['date']) #to add id to date item (date bc it always exists) for identification
            date_item.setData(Qt.UserRole, row['id'])
            self.transaction_table.setItem(row_index, 0, date_item)
            self.transaction_table.setItem(row_index, 1, QTableWidgetItem(f"{row['amount']:.2f}"))
            self.transaction_table.setItem(row_index, 2, QTableWidgetItem(row['category'])),
            self.transaction_table.setItem(row_index, 3, QTableWidgetItem(row['name']))
            self.transaction_table.setItem(row_index, 4, QTableWidgetItem(row['info']))
        
            
    def open_add_dialog(self) -> None:
        connection = connect_db()
        
        categories_db = get_categories(connection)
        categories = []
        for category in DEFAULT_CATEGORIES + categories_db: #no duplicates
            if category not in categories:
                categories.append(category)
    
        dialog = AddTransactionDialog(categories = categories, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        
        tx_data = dialog.get_data()
        
        insert_transaction(
            connection,
            tx_date=tx_data['tx_date'],
            amount=tx_data['amount'],
            category=tx_data['category'],
            name=tx_data['name'],
            description=tx_data['description'],
            source='manual',
            external_id=None,
        )
        
        connection.close()
        
        self.refresh()
        
        
    def open_edit_dialog(self, row: int, col: int) -> None:
        item = self.transaction_table.item(row, 0)
        if not item:
            return
        
        tx_id = item.data(Qt.UserRole)
        if not tx_id: 
            return
        
        connection = connect_db()
        tx = get_transaction_by_id(connection, int(tx_id))
        connection.close()
        
        if not tx:
            print(f'Could not load id {tx_id}') #for debugging, remove later
            return
        
        initial_data = {
            'tx_date': tx['tx_date'],
            'amount': tx['amount'],
            'category': tx['category'],
            'name': tx['name'],
            'description': tx['description'],
        }

        dialog = AddTransactionDialog(
            categories=[],         
            parent=self,
            initial_data=initial_data,
            title='Edit transaction',
        )

        if dialog.exec() != QDialog.Accepted:
            return

        edited = dialog.get_data()
        
        connection = connect_db()
        
        update_transaction(
            connection,
            tx_id=int(tx_id),
            tx_date=edited['tx_date'],
            amount=edited['amount'],
            category=edited['category'],
            name=edited['name'],
            description=edited['description'],
        )
        connection.close()

        self.refresh()
        
    
    def open_csv_import(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            'Select PayPal CSV',
            '',
            'CSV Files (*.csv);;All Files (*)',
        )
        if not file_path: #if user cancels
            return

        try:
            transactions = parse_transactions_from_csv(file_path)
        except Exception as e:
            QMessageBox.critical(self, 'CSV Import Failed', f'Could not parse file:\n{e}')
            return

        if not transactions:
            QMessageBox.information(self, 'CSV Import', 'No importable transactions found.')
            return

        connection = connect_db()
        try:
            stats = import_transactions(connection, transactions)
        finally:
            connection.close()

        QMessageBox.information(
            self,
            'CSV Import Complete',
            f"Imported: {stats['imported']}\nDuplicates skipped: {stats['duplicates']}",
        )

        self.refresh()
    
    
    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.refresh()


                 
#returns start and end date depending on period (end will always be today)
def period_to_range(period: str):
    today = date.today()
    end_date = today.isoformat()
    
    if period == 'This month':
        start = today.replace(day=1)
        return start.isoformat(), end_date

    if period == 'Last 30 days':
        start = today - timedelta(days=30)
        return start.isoformat(), end_date
    
    if period == 'This year':
        start = date(today.year, 1, 1)
        return start.isoformat(), end_date
    
    if period == 'All time':
        return None, None
    
    return None, None #if not yet implemented, shouldn't happen