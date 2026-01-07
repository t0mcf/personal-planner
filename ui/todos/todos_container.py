from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QToolButton, QButtonGroup

from ui.todos.day_view import DayView
from ui.todos.manager_view import ManagerView


class TodosContainer(QWidget):
    def __init__(self):
        super().__init__()

        self._stack = QStackedWidget()
        self._day_view = DayView()
        self._manager_view = ManagerView()

        self._stack.addWidget(self._day_view)
        self._stack.addWidget(self._manager_view)

        # top navigation for switching between day and manager view (same as FinanceTab)
        nav = QHBoxLayout()

        self._btn_day = QToolButton()
        self._btn_day.setText("Day")
        self._btn_day.setCheckable(True)

        self._btn_manager = QToolButton()
        self._btn_manager.setText("Manager")
        self._btn_manager.setCheckable(True)

        group = QButtonGroup(self)
        group.setExclusive(True)  # have only one active at a time
        group.addButton(self._btn_day, 0)
        group.addButton(self._btn_manager, 1)

        group.idClicked.connect(self._stack.setCurrentIndex)

        nav.addWidget(self._btn_day)
        nav.addWidget(self._btn_manager)
        nav.addStretch(1)

        root = QVBoxLayout()
        root.addLayout(nav)
        root.addWidget(self._stack)

        self.setLayout(root)

        # Default: Day
        self._stack.setCurrentIndex(0)
        self._btn_day.setChecked(True)

        self.setStyleSheet(
            """
            QToolButton {
                padding: 6px 12px;
                border: 1px solid #c9c9c9;
                background: transparent;
                color: #222;
            }

            QToolButton:checked {
                background: #e9e9e9;
                border: 1px solid #9f9f9f;
                font-weight: 600;
            }

            QToolButton:hover:!checked {
                background: #f4f4f4;
            }

            QToolButton:first {
                border-top-left-radius: 8px;
                border-bottom-left-radius: 8px;
            }

            QToolButton:last {
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
            }"""
        )


    def open_day(self, day: str) -> None:
        self._stack.setCurrentIndex(0)
        self._btn_day.setChecked(True)
        self._day_view.set_day(day)
