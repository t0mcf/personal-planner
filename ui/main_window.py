from PySide6.QtWidgets import QMainWindow, QTabWidget
from ui.finance.finance_tab import FinanceTab
from ui.todos.todos_container import TodosContainer
from ui.home.home_view import HomeView
from ui.xp.xp_view import XPView

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Dailify')
        self.resize(1200, 800)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.home_view = HomeView()
        self.finance_tab = FinanceTab()
        self.todos_container = TodosContainer()
        self.xp_view = XPView()

        self.tabs.addTab(self.home_view, 'Home')
        self.tabs.addTab(self.finance_tab, 'Finance')
        self.tabs.addTab(self.todos_container, 'Activity')
        self.tabs.addTab(self.xp_view, 'Progression')

        self.wire_home()
        self.home_view.refresh()

    def wire_home(self):
        self.home_view.open_todos.connect(
            lambda: self.tabs.setCurrentWidget(self.todos_container)
        )
        self.home_view.open_finance.connect(
            lambda: self.tabs.setCurrentWidget(self.finance_tab)
        )
        self.home_view.open_xp.connect(
            lambda: self.tabs.setCurrentWidget(self.xp_view)
        )
        
        def open_day(day: str):
            self.tabs.setCurrentWidget(self.todos_container)
            self.todos_container.open_day(day)

        self.home_view.open_day.connect(open_day)

