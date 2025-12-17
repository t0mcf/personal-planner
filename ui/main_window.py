from typing import Optional
import PySide6.QtCore
from PySide6.QtWidgets import QMainWindow, QTabWidget
from ui.tabs.finance_tab import FinanceTab

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('personal planner')
        self.resize(1100, 700)
        self._init_ui()
        
    def _init_ui(self):
        tabs = QTabWidget()
        
        tabs.addTab(FinanceTab(), 'finance')
        
        self.setCentralWidget(tabs)