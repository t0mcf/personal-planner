from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton,
    QDateEdit, QCheckBox
)
from PySide6.QtCore import QDate, Signal

from db.core import connect_db
from db.todos import update_todo  

from helpers.db import db_session  

class EditTodoDialog(QDialog):
    saved = Signal()

    def __init__(self, todo: dict, parent=None):
        super().__init__(parent)

        self.todo = todo
        self.setWindowTitle('Edit todo')
        self.resize(420, 170)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(QLabel('Title'))
        self.title_input = QLineEdit(todo.get('title') or '')
        layout.addWidget(self.title_input)

        row = QHBoxLayout()
        layout.addLayout(row)

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat('yyyy-MM-dd')
        self.date_input.setDate(QDate.currentDate())
        row.addWidget(self.date_input, 0)

        self.backlog_box = QCheckBox('Backlog')
        self.backlog_box.toggled.connect(self.on_backlog_toggled)
        row.addWidget(self.backlog_box, 0)

        date_value = todo.get('date')
        if date_value:
            self.date_input.setDate(QDate.fromString(date_value, 'yyyy-MM-dd'))
            self.backlog_box.setChecked(False)
        else:
            self.backlog_box.setChecked(True)

        buttons = QHBoxLayout()
        layout.addLayout(buttons)
        buttons.addStretch(1)

        cancel = QPushButton('Cancel')
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)

        save = QPushButton('Save')
        save.clicked.connect(self.save)
        buttons.addWidget(save)

        self.on_backlog_toggled(self.backlog_box.isChecked())

    def on_backlog_toggled(self, checked: bool):
        self.date_input.setEnabled(not checked)

    def save(self):
        title = self.title_input.text().strip()
        if not title:
            return

        date_value = None
        if not self.backlog_box.isChecked():
            date_value = self.date_input.date().toString('yyyy-MM-dd')

        with db_session() as connection:
            update_todo(connection, int(self.todo['id']), title, date_value)

        self.saved.emit()
        self.accept()
