from PySide6.QtWidgets import QMainWindow, QTabWidget
from ui.finance.finance_tab import FinanceTab
from ui.todos.todos_container import TodosContainer
from ui.home.home_view import HomeView

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('personal planner')
        self.resize(1200, 800)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.home_view = HomeView()
        self.finance_tab = FinanceTab()
        self.todos_container = TodosContainer()

        self.tabs.addTab(self.home_view, 'home')
        self.tabs.addTab(self.finance_tab, 'finance')
        self.tabs.addTab(self.todos_container, 'todos')

        self.wire_home()
        self.home_view.refresh()

    def wire_home(self):
        self.home_view.open_todos.connect(
            lambda: self.tabs.setCurrentWidget(self.todos_container)
        )
        self.home_view.open_finance.connect(
            lambda: self.tabs.setCurrentWidget(self.finance_tab)
        )
