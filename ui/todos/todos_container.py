from PySide6.QtWidgets import QWidget, QVBoxLayout, QStackedWidget

from ui.todos.day_view import DayView
from ui.todos.manager_view import ManagerView


class TodosContainer(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        self.day_view = DayView()
        self.manager_view = ManagerView()

        self.stack.addWidget(self.day_view)
        self.stack.addWidget(self.manager_view)

        self.day_view.open_manager.connect(self.show_manager)
        self.manager_view.back_to_day.connect(self.show_day)

        self.stack.setCurrentWidget(self.day_view)

    def show_manager(self):
        self.manager_view.refresh()
        self.stack.setCurrentWidget(self.manager_view)

    def show_day(self):
        self.day_view.refresh()
        self.stack.setCurrentWidget(self.day_view)
