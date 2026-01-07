from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel, QVBoxLayout, QComboBox, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QDialog, QFileDialog, QMessageBox,
    QLineEdit, QFormLayout, QDoubleSpinBox, QSpinBox, QDateEdit, QCheckBox
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QShowEvent, QColor

from datetime import date, timedelta

from helpers.db import db_session
from db.finance import (
    list_transactions,
    insert_transaction,
    get_categories,
    get_transaction_by_id,
    update_transaction,
    import_transactions,
    create_recurring_rule,
    update_recurring_rule,
    stop_recurring_rule,
    list_recurring_rules,
    sync_recurring_transactions,
)

from ui.dialogs.add_transaction_dialog import AddTransactionDialog
from ui.dialogs.csv_import_config_dialog import CsvImportConfigDialog
from ui.constants import DEFAULT_CATEGORIES
from csv_parser import parse_transactions_from_csv
from helpers.currency import format_jpy


class RecurringRuleDialog(QDialog):
    def __init__(self, categories: list[str], parent=None, initial: dict | None = None):
        super().__init__(parent)
        self.setModal(True)
        self.initial = initial or {}
        self.setWindowTitle(self.initial.get("title") or "Recurring transaction")

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit(self.initial.get("name") or "-")
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(-10_000_000, 10_000_000)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setValue(float(self.initial.get("amount") or 0.0))

        self.category_box = QComboBox()
        self.category_box.addItems(categories)
        cat = self.initial.get("category") or "Uncategorized"
        idx = self.category_box.findText(cat)
        if idx >= 0:
            self.category_box.setCurrentIndex(idx)

        self.desc_edit = QLineEdit(self.initial.get("description") or "-")

        self.day_spin = QSpinBox()
        self.day_spin.setRange(1, 31)
        self.day_spin.setValue(int(self.initial.get("day_of_month") or 1))

        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        start = self.initial.get("start_date") or date.today().isoformat()
        y, m, d = [int(x) for x in start.split("-")]
        self.start_date.setDate(QDate(y, m, d))

        self.active_cb = QCheckBox("active")
        self.active_cb.setChecked(bool(self.initial.get("active", True)))

        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setEnabled(False)
        self.end_date_cb = QCheckBox("set end date")
        self.end_date_cb.setChecked(False)

        if self.initial.get("end_date"):
            ey, em, ed = [int(x) for x in self.initial["end_date"].split("-")]
            self.end_date.setDate(QDate(ey, em, ed))
            self.end_date_cb.setChecked(True)
            self.end_date.setEnabled(True)

        def end_toggle():
            self.end_date.setEnabled(self.end_date_cb.isChecked())

        self.end_date_cb.toggled.connect(end_toggle)

        form.addRow("name", self.name_edit)
        form.addRow("amount (+ income / - expense)", self.amount_spin)
        form.addRow("category", self.category_box)
        form.addRow("description", self.desc_edit)
        form.addRow("day of month", self.day_spin)
        form.addRow("start date", self.start_date)
        form.addRow("", self.active_cb)

        end_row = QHBoxLayout()
        end_row.addWidget(self.end_date_cb)
        end_row.addWidget(self.end_date)
        form.addRow("end date", end_row)

        layout.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.cancel_btn = QPushButton("Cancel")
        self.ok_btn = QPushButton("Save")
        buttons.addWidget(self.cancel_btn)
        buttons.addWidget(self.ok_btn)
        layout.addLayout(buttons)

        self.cancel_btn.clicked.connect(self.reject)
        self.ok_btn.clicked.connect(self.accept)

    def get_data(self) -> dict:
        end_date = None
        if self.end_date_cb.isChecked():
            qd = self.end_date.date()
            end_date = f"{qd.year():04d}-{qd.month():02d}-{qd.day():02d}"

        sd = self.start_date.date()
        start_date = f"{sd.year():04d}-{sd.month():02d}-{sd.day():02d}"

        return {
            "name": self.name_edit.text().strip() or "Recurring",
            "amount": float(self.amount_spin.value()),
            "category": self.category_box.currentText() or "Uncategorized",
            "description": self.desc_edit.text().strip(),
            "day_of_month": int(self.day_spin.value()),
            "start_date": start_date,
            "active": bool(self.active_cb.isChecked()),
            "end_date": end_date,
        }


class ManageRecurringDialog(QDialog):
    def __init__(self, categories: list[str], parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle("Manage recurring")
        self.categories = categories

        root = QVBoxLayout(self)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Amount", "Category", "Day", "Start", "End", "Active"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)

        actions = QHBoxLayout()
        self.sync_btn = QPushButton("Sync all")
        self.edit_btn = QPushButton("Edit selected")
        self.stop_btn = QPushButton("Stop selected")
        self.close_btn = QPushButton("Close")
        actions.addWidget(self.sync_btn)
        actions.addWidget(self.edit_btn)
        actions.addWidget(self.stop_btn)
        actions.addStretch()
        actions.addWidget(self.close_btn)
        root.addLayout(actions)

        self.sync_btn.clicked.connect(self.sync_all)
        self.edit_btn.clicked.connect(self.edit_selected)
        self.stop_btn.clicked.connect(self.stop_selected)
        self.close_btn.clicked.connect(self.accept)

        self.table.itemSelectionChanged.connect(self.update_buttons)

        self.refresh()
        self.update_buttons()

    def selected_rule_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if not item:
            return None
        try:
            return int(item.text())
        except Exception:
            return None

    def update_buttons(self):
        has = self.selected_rule_id() is not None
        self.edit_btn.setEnabled(has)
        self.stop_btn.setEnabled(has)

    def refresh(self):
        with db_session() as connection:
            rules = list_recurring_rules(connection, active_only=False)

        self.table.setRowCount(len(rules))
        for i, r in enumerate(rules):
            self.table.setItem(i, 0, QTableWidgetItem(str(r.get("id"))))
            self.table.setItem(i, 1, QTableWidgetItem(r.get("name") or ""))
            self.table.setItem(i, 2, QTableWidgetItem(format_jpy(r.get('amount') or 0.0)))
            self.table.setItem(i, 3, QTableWidgetItem(r.get("category") or "Uncategorized"))
            self.table.setItem(i, 4, QTableWidgetItem(str(r.get("day_of_month") or "")))
            self.table.setItem(i, 5, QTableWidgetItem(r.get("start_date") or ""))
            self.table.setItem(i, 6, QTableWidgetItem(r.get("end_date") or ""))
            self.table.setItem(i, 7, QTableWidgetItem("yes" if int(r.get("active") or 0) == 1 else "no"))

    def sync_all(self):
        with db_session() as connection:
            stats = sync_recurring_transactions(connection, rule_id=None, up_to_date=None)
        QMessageBox.information(self, "Sync", f"Inserted: {stats['inserted']}\nDuplicates: {stats['duplicates']}")
        self.refresh()

    def edit_selected(self):
        rid = self.selected_rule_id()
        if rid is None:
            return

        with db_session() as connection:
            rules = [r for r in list_recurring_rules(connection, active_only=False) if int(r["id"]) == rid]
            if not rules:
                return
            rule = rules[0]

        dialog = RecurringRuleDialog(self.categories, parent=self, initial=rule | {"title": "Edit recurring"})
        if dialog.exec() != QDialog.Accepted:
            return
        data = dialog.get_data()

        with db_session() as connection:
            update_recurring_rule(
                connection,
                rule_id=rid,
                name=data["name"],
                amount=data["amount"],
                category=data["category"],
                description=data["description"],
                day_of_month=data["day_of_month"],
                start_date=data["start_date"],
                active=data["active"],
                end_date=data["end_date"],
            )
            stats = sync_recurring_transactions(connection, rule_id=rid, up_to_date=None)

        QMessageBox.information(self, "Updated", f"Synced\nInserted: {stats['inserted']}\nDuplicates: {stats['duplicates']}")
        self.refresh()

    def stop_selected(self):
        rid = self.selected_rule_id()
        if rid is None:
            return

        resp = QMessageBox.question(
            self,
            "Stop recurring",
            "Stop this recurring rule?\n(old transactions stay)",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return

        with db_session() as connection:
            stop_recurring_rule(connection, rule_id=rid, end_date=date.today().isoformat())

        self.refresh()


class FinanceTransactionsView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.init_ui()

    # ui
    def init_ui(self):
        main_layout = QVBoxLayout(self)

        title = QLabel('finance')
        title.setObjectName('tabTitle')
        main_layout.addWidget(title)

        # filters + actions
        bar = QVBoxLayout()
        filters_row = QHBoxLayout()
        actions_row = QHBoxLayout()

        self.time_period = QComboBox()
        self.time_period.addItems(['This month', 'Last 30 days', 'This year', 'All time'])

        self.transaction_type = QComboBox()
        self.transaction_type.addItems(['All', 'Expenses', 'Income'])

        self.category = QComboBox()
        self.category.addItems(['All'])

        self.csv_import_button = QPushButton('Import csv file')
        self.csv_import_button.clicked.connect(self.open_csv_import)

        self.add_transaction_button = QPushButton('Add transaction')
        self.add_transaction_button.clicked.connect(self.open_add_dialog)

        self.edit_transaction_button = QPushButton('Edit selected')
        self.edit_transaction_button.clicked.connect(self.open_edit_dialog_from_button)

        self.delete_transaction_button = QPushButton('Delete selected')
        self.delete_transaction_button.clicked.connect(self.delete_selected_transaction)

        self.add_recurring_button = QPushButton('Add recurring')
        self.add_recurring_button.clicked.connect(self.open_add_recurring_dialog)

        self.manage_recurring_button = QPushButton('Manage recurring')
        self.manage_recurring_button.clicked.connect(self.open_manage_recurring_dialog)

        filters_row.addWidget(QLabel('Period:'))
        filters_row.addWidget(self.time_period)
        filters_row.addWidget(QLabel('Type:'))
        filters_row.addWidget(self.transaction_type)
        filters_row.addWidget(QLabel('Category:'))
        filters_row.addWidget(self.category)
        filters_row.addStretch()

        actions_row.addWidget(self.csv_import_button)
        actions_row.addWidget(self.add_transaction_button)
        actions_row.addWidget(self.edit_transaction_button)
        actions_row.addWidget(self.delete_transaction_button)
        actions_row.addWidget(self.add_recurring_button)
        actions_row.addWidget(self.manage_recurring_button)
        actions_row.addStretch()

        bar.addLayout(filters_row)
        bar.addLayout(actions_row)
        main_layout.addLayout(bar)

        # table (expanded)
        self.transaction_table = QTableWidget(0, 7)
        self.transaction_table.setHorizontalHeaderLabels([
            'Date',
            'Amount (JPY)',
            'Category',
            'Name',
            'Original',
            'FX rate',
            'Description',
        ])
        self.transaction_table.horizontalHeader().setStretchLastSection(True)
        self.transaction_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.transaction_table.setSelectionMode(QTableWidget.SingleSelection)
        self.transaction_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.transaction_table.verticalHeader().setVisible(False)
        self.transaction_table.cellDoubleClicked.connect(self.open_edit_dialog)
        main_layout.addWidget(self.transaction_table, 1)

        # signals
        self.time_period.currentIndexChanged.connect(self.refresh)
        self.transaction_type.currentIndexChanged.connect(self.refresh)
        self.category.currentIndexChanged.connect(self.refresh)
        self.transaction_table.itemSelectionChanged.connect(self.update_action_buttons)

        # initial
        self.reload_categories()
        self.refresh()
        self.update_action_buttons()

    # helpers
    def selected_tx_id(self):
        row = self.transaction_table.currentRow()
        if row < 0:
            return None
        item = self.transaction_table.item(row, 0)
        if not item:
            return None
        tx_id = item.data(Qt.UserRole)
        return int(tx_id) if tx_id is not None else None

    def update_action_buttons(self):
        has = self.selected_tx_id() is not None
        self.edit_transaction_button.setEnabled(has)
        self.delete_transaction_button.setEnabled(has)

    def reload_categories(self):
        with db_session() as connection:
            categories_db = get_categories(connection)

        merged = []
        for c in (DEFAULT_CATEGORIES + categories_db + ['Uncategorized']):
            if c and c not in merged:
                merged.append(c)

        current = self.category.currentText() if self.category.count() > 0 else 'All'

        self.category.blockSignals(True)
        self.category.clear()
        self.category.addItem('All')
        for c in merged:
            self.category.addItem(c)

        idx = self.category.findText(current)
        self.category.setCurrentIndex(idx if idx >= 0 else 0)
        self.category.blockSignals(False)

    # filters
    def get_filters(self):
        start_date, end_date = period_to_range(self.time_period.currentText())
        return {
            'type': self.transaction_type.currentText(),
            'category': self.category.currentText(),
            'start_date': start_date,
            'end_date': end_date,
        }

    # refresh
    def refresh(self):
        filters = self.get_filters()
        with db_session() as connection:
            sync_recurring_transactions(connection, rule_id=None, up_to_date=None)

            rows = list_transactions(
                connection,
                start_date=filters['start_date'],
                end_date=filters['end_date'],
                tx_type=filters['type'],
                category=filters['category'],
                limit=500,
            )

        self.fill_table(rows)
        self.update_action_buttons()

    def fill_table(self, rows):
        self.transaction_table.setRowCount(len(rows))

        income_color = QColor(0, 120, 215)
        expense_color = QColor(200, 70, 70)

        for row_index, row in enumerate(rows):
            # date
            date_item = QTableWidgetItem(row.get('date', ''))
            date_item.setData(Qt.UserRole, row.get('id'))
            self.transaction_table.setItem(row_index, 0, date_item)

            #amount (JPY)
            amt = float(row.get('amount') or 0.0)
            amount_item = QTableWidgetItem(format_jpy(amt))
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            amount_item.setForeground(income_color if amt >= 0 else expense_color)
            self.transaction_table.setItem(row_index, 1, amount_item)

            # category
            self.transaction_table.setItem(row_index, 2, QTableWidgetItem(row.get('category') or 'Uncategorized'))

            #name
            self.transaction_table.setItem(row_index, 3, QTableWidgetItem(row.get('name') or '-'))
            
            #original amount
            orig = row.get('amount_original')
            cur = row.get('currency') or '-'
            
            if orig is None or orig == '':
                orig_txt = ''
            else:
                try:
                    orig_txt = f"{cur} {float(orig):,.2f}".strip()
                except Exception:
                    orig_txt = f"{cur} {orig}".strip()
            orig_item = QTableWidgetItem(orig_txt)
            orig_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.transaction_table.setItem(row_index, 4, orig_item)

            #fx rate
            fx = row.get('fx_rate_to_jpy')
            if fx is None or fx == '':
                fx_txt = ''
            else:
                try:
                    fx_txt = f"{float(fx):,.6f}"
                except Exception:
                    fx_txt = str(fx)
            fx_item = QTableWidgetItem(fx_txt)
            fx_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.transaction_table.setItem(row_index, 5, fx_item)

            #description
            self.transaction_table.setItem(row_index, 6, QTableWidgetItem(row.get('description') or '-'))

    # add/edit/delete
    def open_add_dialog(self) -> None:
        with db_session() as connection:
            categories_db = get_categories(connection)
            categories = []
            for category in (DEFAULT_CATEGORIES + categories_db + ['Uncategorized']):
                if category not in categories:
                    categories.append(category)

            dialog = AddTransactionDialog(categories=categories, parent=self)
            if dialog.exec() != QDialog.Accepted:
                return

            tx = dialog.get_data()

            insert_transaction(
                connection,
                tx_date=tx["tx_date"],
                amount=tx["amount"],
                amount_original=tx["amount_original"],
                currency=tx["currency"],
                category=tx["category"],
                name=tx["name"],
                description=tx["description"],
                source="manual",
            )

        self.reload_categories()
        self.refresh()

    def open_edit_dialog_from_button(self) -> None:
        tx_id = self.selected_tx_id()
        if tx_id is None:
            return
        self.open_edit_dialog(self.transaction_table.currentRow(), 0)

    def open_edit_dialog(self, row: int, col: int) -> None:
        item = self.transaction_table.item(row, 0)
        if not item:
            return

        tx_id = item.data(Qt.UserRole)
        if tx_id is None:
            return

        with db_session() as connection:
            tx = get_transaction_by_id(connection, int(tx_id))
            if not tx:
                return

            categories_db = get_categories(connection)
            categories = []
            for category in (DEFAULT_CATEGORIES + categories_db + ['Uncategorized']):
                if category not in categories:
                    categories.append(category)

            dialog = AddTransactionDialog(
                categories=categories,
                parent=self,
                initial_data=tx,
                title="Edit transaction",
            )

            if dialog.exec() != QDialog.Accepted:
                return

            edited = dialog.get_data()

            update_transaction(
                connection,
                tx_id=int(tx_id),
                tx_date=edited["tx_date"],
                amount=edited["amount"],
                amount_original=edited["amount_original"],
                currency=edited["currency"],
                category=edited["category"],
                name=edited["name"],
                description=edited["description"],
            )

        self.reload_categories()
        self.refresh()

    def delete_selected_transaction(self) -> None:
        tx_id = self.selected_tx_id()
        if tx_id is None:
            return

        row = self.transaction_table.currentRow()
        date_txt = self.transaction_table.item(row, 0).text() if row >= 0 else ''
        amt_txt = self.transaction_table.item(row, 1).text() if row >= 0 else ''
        name_txt = self.transaction_table.item(row, 3).text() if row >= 0 else ''

        resp = QMessageBox.question(
            self,
            'Delete transaction',
            f'Delete this transaction?\n\n{date_txt}  {amt_txt}  {name_txt}',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return

        with db_session() as connection:
            connection.execute("DELETE FROM transactions WHERE id = ?", (int(tx_id),))
            connection.commit()

        self.reload_categories()
        self.refresh()

    #recurring transaction 
    def open_add_recurring_dialog(self):
        categories = self.get_merged_categories()
        dialog = RecurringRuleDialog(categories, parent=self, initial={"title": "Add recurring", "active": True})
        if dialog.exec() != QDialog.Accepted:
            return
        data = dialog.get_data()

        with db_session() as connection:
            rid = create_recurring_rule(
                connection,
                name=data["name"],
                amount=data["amount"],
                category=data["category"],
                description=data["description"],
                day_of_month=data["day_of_month"],
                start_date=data["start_date"],
            )
            if not data["active"] or data["end_date"]:
                update_recurring_rule(
                    connection,
                    rule_id=rid,
                    name=data["name"],
                    amount=data["amount"],
                    category=data["category"],
                    description=data["description"],
                    day_of_month=data["day_of_month"],
                    start_date=data["start_date"],
                    active=data["active"],
                    end_date=data["end_date"],
                )

            stats = sync_recurring_transactions(connection, rule_id=rid, up_to_date=None)

        QMessageBox.information(self, "Recurring", f"Created & synced\nInserted: {stats['inserted']}\nDuplicates: {stats['duplicates']}")
        self.reload_categories()
        self.refresh()

    def open_manage_recurring_dialog(self):
        categories = self.get_merged_categories()
        dialog = ManageRecurringDialog(categories, parent=self)
        dialog.exec()
        self.reload_categories()
        self.refresh()

    def get_merged_categories(self) -> list[str]:
        with db_session() as connection:
            categories_db = get_categories(connection)

        merged = []
        for c in (DEFAULT_CATEGORIES + categories_db + ["Uncategorized"]):
            if c and c not in merged:
                merged.append(c)
        return merged

    # csv import
    def open_csv_import(self) -> None:
        dialog = CsvImportConfigDialog(parent=self)
        if dialog.exec() != QDialog.Accepted:
            return

        cfg = dialog.get_config()

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select CSV",
            "",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not file_path:
            return

        try:
            if cfg["use_paypal"]:
                transactions = parse_transactions_from_csv(
                    file_path,
                    preset="paypal",
                    source=cfg["source"],
                    default_category=cfg["default_category"],
                    default_currency=cfg["default_currency"],
                    only_completed=cfg["only_completed"],
                )
            else:
                transactions = parse_transactions_from_csv(
                    file_path,
                    preset=None,
                    source=cfg["source"],
                    default_category=cfg["default_category"],
                    default_currency=cfg["default_currency"],
                    only_completed=False,
                    mapping=cfg["mapping"],
                )
        except Exception as e:
            QMessageBox.critical(self, "CSV Import Failed", f"Could not parse file:\n{e}")
            return

        if not transactions:
            QMessageBox.information(self, "CSV Import", "No importable transactions found.")
            return

        with db_session() as connection: 
            stats = import_transactions(connection, transactions)

        QMessageBox.information(
            self,
            "CSV Import Complete",
            f"Imported: {stats.get('imported', 0)}\nDuplicates skipped: {stats.get('duplicates', 0)}\nFailed: {stats.get('failed', 0)}",
        )

        self.reload_categories()
        self.refresh()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.reload_categories()
        self.refresh()


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

    return None, None

