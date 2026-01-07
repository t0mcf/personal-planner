from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QComboBox,
    QPushButton,
    QMessageBox,
    QDateEdit,
    QDoubleSpinBox,
)
from PySide6.QtCore import QDate, QLocale

from db.finance import list_currencies
from helpers.db import db_session

class AddTransactionDialog(QDialog):

    def __init__(
        self,
        categories: list[str] | None = None,
        parent=None,
        initial_data: dict | None = None,
        title: str = 'Add transaction',
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle(title)
        self.setModal(True)

        categories = categories or []
        if 'Uncategorized' not in categories:
            categories = ['Uncategorized'] + categories

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        main_layout.addLayout(form_layout)

        # date
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        form_layout.addRow("Date:", self.date_edit)

        # amount + currency
        self.amount_sel = QDoubleSpinBox()
        self.amount_sel.setLocale(QLocale.c())
        self.amount_sel.setDecimals(2)
        self.amount_sel.setRange(-1_000_000_000, 1_000_000_000)
        self.amount_sel.setSingleStep(1.0)

        self.currency_cb = QComboBox()
        with db_session() as connection: 
            currencies = list_currencies(connection)
            
        if "JPY" not in currencies:
            currencies.insert(0, "JPY")

        self.currency_cb.addItems(currencies)
        self.currency_cb.setCurrentText("JPY")

        amount_row = QHBoxLayout()
        amount_row.addWidget(self.amount_sel)
        amount_row.addWidget(self.currency_cb)
        form_layout.addRow("Amount:", amount_row)

        # category
        self.category_input = QComboBox()
        self.category_input.setEditable(True)
        self.category_input.addItems(categories)
        self.category_input.setCurrentText("Uncategorized")
        form_layout.addRow("Category:", self.category_input)

        # name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText('e.g. "Family Mart", "Lukas"')
        form_layout.addRow("Name:", self.name_input)

        # description
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("optional note")
        form_layout.addRow("Description:", self.desc_input)

        # buttons
        buttons = QHBoxLayout()
        buttons.addStretch()
        self.cancel_button = QPushButton("Cancel")
        self.save_button = QPushButton("Save")
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.save_button)
        main_layout.addLayout(buttons)

        self.cancel_button.clicked.connect(self.reject)
        self.save_button.clicked.connect(self._save_input)

        # edit mode
        if initial_data:
            if initial_data.get("tx_date"):
                d = QDate.fromString(initial_data["tx_date"], "yyyy-MM-dd")
                if d.isValid():
                    self.date_edit.setDate(d)

            currency = initial_data.get("currency") or "JPY"
            self.currency_cb.setCurrentText(currency)

            if currency == "JPY" or initial_data.get("amount_original") is None:
                self.amount_sel.setValue(float(initial_data.get("amount") or 0.0))
            else:
                self.amount_sel.setValue(float(initial_data.get("amount_original")))

            if initial_data.get("category"):
                self.category_input.setCurrentText(initial_data["category"])
            if initial_data.get("name"):
                self.name_input.setText(initial_data["name"])
            if initial_data.get("description"):
                self.desc_input.setText(initial_data["description"])

    def _save_input(self) -> None:
        if self.amount_sel.value() == 0.0:
            QMessageBox.warning(self, "Invalid amount", "Amount may not be 0.")
            return
        self.accept()

    def get_data(self) -> dict:
        currency = self.currency_cb.currentText()
        raw_amount = float(self.amount_sel.value())

        return {
            "tx_date": self.date_edit.date().toString("yyyy-MM-dd"),
            "currency": currency,
            "amount": raw_amount if currency == "JPY" else 0.0,
            "amount_original": None if currency == "JPY" else raw_amount,
            "category": self.category_input.currentText().strip() or "Uncategorized",
            "name": self.name_input.text().strip() or None,
            "description": self.desc_input.text().strip() or None,
        }
