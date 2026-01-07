from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, QLineEdit, QPushButton,
    QCheckBox, QLabel
)

class CsvImportConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CSV import")
        self.setModal(True)

        root = QVBoxLayout(self)
        form = QFormLayout()
        root.addLayout(form)

        self.use_paypal_cb = QCheckBox("use paypal preset")
        self.use_paypal_cb.setChecked(True)
        form.addRow("", self.use_paypal_cb)

        self.only_completed_cb = QCheckBox("only completed (paypal)")
        self.only_completed_cb.setChecked(True)
        form.addRow("", self.only_completed_cb)

        self.source_edit = QLineEdit("paypal")
        form.addRow("source", self.source_edit)

        self.default_category_edit = QLineEdit("Uncategorized")
        form.addRow("default category", self.default_category_edit)

        self.default_currency_edit = QLineEdit("JPY")
        self.default_currency_edit.setMaxLength(3)
        form.addRow("default currency", self.default_currency_edit)

        self.date_col = QLineEdit("Date")
        self.amount_col = QLineEdit("Net")
        self.external_id_col = QLineEdit("Transaction ID")

        self.status_col = QLineEdit("Status")
        self.name_col = QLineEdit("Name")
        self.currency_col = QLineEdit("Currency")
        self.category_col = QLineEdit("")  # paypal doesn't provide by default

        self.item_title_col = QLineEdit("Item Title")
        self.subject_col = QLineEdit("Subject")
        self.note_col = QLineEdit("Note")
        self.description_col = QLineEdit("")  # optional custom col

        form.addRow("date column *", self.date_col)
        form.addRow("amount column *", self.amount_col)
        form.addRow("external id column *", self.external_id_col)

        form.addRow("status column", self.status_col)
        form.addRow("name column", self.name_col)
        form.addRow("currency column", self.currency_col)
        form.addRow("category column", self.category_col)

        form.addRow("item title column", self.item_title_col)
        form.addRow("subject column", self.subject_col)
        form.addRow("note column", self.note_col)
        form.addRow("description column", self.description_col)

        hint = QLabel('(*) required. leave optional fields empty if not present.')
        hint.setStyleSheet("color: #666;")
        root.addWidget(hint)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.cancel_btn = QPushButton("Cancel")
        self.pick_file_btn = QPushButton("Choose file and import")
        buttons.addWidget(self.cancel_btn)
        buttons.addWidget(self.pick_file_btn)
        root.addLayout(buttons)

        self.cancel_btn.clicked.connect(self.reject)
        self.pick_file_btn.clicked.connect(self.accept)

        self.use_paypal_cb.toggled.connect(self.update_enabled_state)
        self.update_enabled_state()

    def update_enabled_state(self):
        paypal = self.use_paypal_cb.isChecked()

        enabled = not paypal

        for w in [
            self.date_col, self.amount_col, self.external_id_col,
            self.status_col, self.name_col, self.currency_col, self.category_col,
            self.item_title_col, self.subject_col, self.note_col, self.description_col,
        ]:
            w.setEnabled(enabled)

        self.only_completed_cb.setEnabled(paypal)
        if paypal:
            if not self.source_edit.text().strip():
                self.source_edit.setText("paypal")

    def get_config(self) -> dict:
        use_paypal = self.use_paypal_cb.isChecked()

        cfg = {
            "use_paypal": use_paypal,
            "only_completed": self.only_completed_cb.isChecked(),
            "source": self.source_edit.text().strip() or ("paypal" if use_paypal else "csv"),
            "default_category": self.default_category_edit.text().strip() or "Uncategorized",
            "default_currency": (self.default_currency_edit.text().strip() or "JPY").upper(),
        }

        mapping = {
            "date": self.date_col.text().strip(),
            "amount": self.amount_col.text().strip(),
            "external_id": self.external_id_col.text().strip(),
            "status": self.status_col.text().strip(),
            "name": self.name_col.text().strip(),
            "currency": self.currency_col.text().strip(),
            "category": self.category_col.text().strip(),
            "item_title": self.item_title_col.text().strip(),
            "subject": self.subject_col.text().strip(),
            "note": self.note_col.text().strip(),
            "description": self.description_col.text().strip(),
        }

        # normalize empties to None
        mapping = {k: (v if v else None) for k, v in mapping.items()}
        cfg["mapping"] = mapping

        return cfg
