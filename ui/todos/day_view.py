from datetime import date as dt_date, timedelta

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QHBoxLayout,
    QCheckBox,
    QInputDialog,
    QToolButton
)
from PySide6.QtCore import Qt

from db.core import connect_db
from db.todos import (
    list_todos_for_day,
    insert_todo,
    set_todo_completed,
)
from db.journal import (
    get_journal_entry,
    save_journal_entry,
)


class DayView(QWidget):
    def __init__(self, day: str | None = None):
        super().__init__()

        self.day = day or dt_date.today().isoformat()

        self.build_ui()
        self.refresh()

    #___ui functions___

    def build_ui(self):
        main_layout = QVBoxLayout(self)
        
        top_bar = QHBoxLayout()
        main_layout.addLayout(top_bar)
        
        prev_button = QToolButton()
        prev_button.setText('◀')
        prev_button.clicked.connect(self.prev_day)
        top_bar.addWidget(prev_button)
        
        self.date_label = QLabel(self.day)
        self.date_label.setAlignment(Qt.AlignCenter)
        self.date_label.setStyleSheet('font-size: 18px; font-weight: 600;')
        top_bar.addWidget(self.date_label)

        next_button = QToolButton()
        next_button.setText('▶')
        next_button.clicked.connect(self.next_day)
        top_bar.addWidget(next_button)

        self.todo_list = QListWidget()
        main_layout.addWidget(self.todo_list)

        add_button = QPushButton('+ Add Todo')
        add_button.clicked.connect(self.add_todo)
        main_layout.addWidget(add_button)

        journal_label = QLabel('Journal')
        journal_label.setStyleSheet('font-weight: 600; margin-top: 8px;')
        main_layout.addWidget(journal_label)

        self.journal_edit = QTextEdit()
        self.journal_edit.textChanged.connect(self.autosave_journal)
        main_layout.addWidget(self.journal_edit)

    # ___data part___

    def refresh(self):
        self.load_todos()
        self.load_journal()
        
    #load todos just for this day
    #idea: if todos without date, maybe also display them every day or add an option to do so
    #in that case change needed here
    def load_todos(self):
        self.todo_list.clear()

        connection = connect_db()
        todos = list_todos_for_day(connection, self.day)
        connection.close()

        for row in todos:
            item = QListWidgetItem()
            widget = self.make_todo_row(row)
            item.setSizeHint(widget.sizeHint())
            self.todo_list.addItem(item)
            self.todo_list.setItemWidget(item, widget)
            

    #layout for a single row in the todo list 
    def make_todo_row(self, row: dict) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        checkbox = QCheckBox()
        checkbox.setProperty('todo_id', row['id'])
        checkbox.setChecked(bool(row['completed']))
        checkbox.toggled.connect(self.toggle_todo)

        label = QLabel(row['title'])
        if row['completed']:
            label.setStyleSheet('color: #888; text-decoration: line-through;')

        layout.addWidget(checkbox)
        layout.addWidget(label)
        layout.addStretch()

        return widget


    #function to be connected with the checkbox (finishing todo)
    #expand this if xp logic added at some point!
    def toggle_todo(self, checked: bool):
        checkbox = self.sender() #to get the checkbox which was clicked
        if not checkbox:
            return
        
        todo_id = checkbox.property('todo_id')
        if todo_id is None:
            return
        
        connection = connect_db()
        set_todo_completed(connection, int(todo_id), checked)
        connection.close()
        
        self.refresh()

    #no date logic yet
    #subject to change
    def add_todo(self):
        text, confirmed = QInputDialog.getText(
            self,
            'Add Todo',
            'Todo:'
        )

        if not confirmed or not text.strip(): #user didn't confirm or no text
            return

        connection = connect_db()
        insert_todo(connection, text.strip(), self.day)
        connection.close()
        self.refresh()

    # ___journaling part____

    def load_journal(self):
        connection = connect_db()
        text = get_journal_entry(connection, self.day)
        connection.close()

        self.journal_edit.blockSignals(True)
        self.journal_edit.setPlainText(text or '')
        self.journal_edit.blockSignals(False)

    def autosave_journal(self):
        text = self.journal_edit.toPlainText()

        connection = connect_db()
        save_journal_entry(connection, self.day, text)
        connection.close()


    #___day switching logic___
    def set_day(self, day: str):
        self.day = day
        self.date_label.setText(day)
        self.refresh()

    def prev_day(self):
        date = dt_date.fromisoformat(self.day) - timedelta(days=1)
        self.set_day(date.isoformat())

    def next_day(self):
        date = dt_date.fromisoformat(self.day) + timedelta(days=1)
        self.set_day(date.isoformat())
