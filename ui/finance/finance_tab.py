from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QToolButton, QButtonGroup

from ui.finance.dashboard_view import FinanceDashboardView
from ui.finance.transactions_view import FinanceTransactionsView


class FinanceTab(QWidget):
    def __init__(self):
        super().__init__()

        self._stack = QStackedWidget()
        self._dashboard_view = FinanceDashboardView()
        self._transactions_view = FinanceTransactionsView()

        self._stack.addWidget(self._dashboard_view)      
        self._stack.addWidget(self._transactions_view)   

        # top navigation for switching between dashboard and detailed transaction view
        nav = QHBoxLayout()

        self._btn_dashboard = QToolButton()
        self._btn_dashboard.setText("Dashboard")
        self._btn_dashboard.setCheckable(True)

        self._btn_transactions = QToolButton()
        self._btn_transactions.setText("Transactions")
        self._btn_transactions.setCheckable(True)

        group = QButtonGroup(self)
        group.setExclusive(True) #to have only one active at a time 
        group.addButton(self._btn_dashboard, 0)
        group.addButton(self._btn_transactions, 1)

        group.idClicked.connect(self._stack.setCurrentIndex)

        nav.addWidget(self._btn_dashboard)
        nav.addWidget(self._btn_transactions)
        nav.addStretch(1)


        root = QVBoxLayout()
        root.addLayout(nav)
        root.addWidget(self._stack)

        self.setLayout(root)

        # Default: Dashboard
        self._stack.setCurrentIndex(0)
        
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
            }""")

