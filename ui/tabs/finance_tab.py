from PySide6.QtWidgets import QWidget, QPushButton, QLabel, QVBoxLayout, QComboBox, QHBoxLayout, QTableWidget, QSplitter, QTableWidgetItem, QSizePolicy
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class FinanceTab(QWidget): 
    
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
        self.add_transaction_button = QPushButton('Add transaction')
        
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

        self.transaction_table = QTableWidget(0,4)
        self.transaction_table.setHorizontalHeaderLabels(['Date', 'Amount', 'Category', 'Info'])
        self.transaction_table.horizontalHeader().setStretchLastSection(True)
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
        return {
            'period': self.time_period.currentText(),
            'type': self.transaction_type.currentText(),
            'category': self.category.currentText(),
            #for custom dates, still to be implemented
            'start_date': None,
            'end_date': None,
        }
    
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
        rows = self.apply_filters(self._test_data, filters)
        self.fill_table(rows)
    
    #fill table display with certain rows
    def fill_table(self, rows):
        self.transaction_table.setRowCount(len(rows))
        
        for row_index, row in enumerate(rows):
            self.transaction_table.setItem(row_index, 0, QTableWidgetItem(row['date']))
            self.transaction_table.setItem(row_index, 1, QTableWidgetItem(f"{row['amount']:.2f}"))
            self.transaction_table.setItem(row_index, 2, QTableWidgetItem(row['category']))
            self.transaction_table.setItem(row_index, 3, QTableWidgetItem(row['info']))