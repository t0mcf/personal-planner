from datetime import date as dt_date

from PySide6.QtCore import Qt, Signal, QDate, QTimer
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QFrame,
    QLineEdit,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QDateEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
)

from helpers.db import db_session
from db.habits import (
    insert_habit,
    list_all_habits,
    set_habit_active,
    delete_habit,
    get_daily_streak,
    get_weekly_streak
)
from db.todos import (
    insert_todo,
    list_all_todos,
    delete_todo,
    set_todo_completed
)

from ui.dialogs.edit_habit_dialog import EditHabitDialog
from ui.dialogs.edit_todo_dialog import EditTodoDialog


# for habits
EMOJIS = [
    '',
    '📚', '🏃', '🧘', '💪', '🥗', '💧',
    '🎯', '🔥', '📝', '🎧', '🎨',
    '📖', '✍', '🛏', '🌿', '☀'
]


class ManagerView(QWidget):

    def __init__(self):
        super().__init__()

        self.build_ui()
        self.refresh()

    def build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 14, 18, 14)
        main_layout.setSpacing(12)

        top_bar = QHBoxLayout()
        main_layout.addLayout(top_bar)

        title = QLabel('Manager')
        title.setStyleSheet('font-size: 18px; font-weight: 700;')
        title.setAlignment(Qt.AlignCenter)
        top_bar.addWidget(title, 1)

        top_bar.addSpacing(80)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs, 1)

        self.habits_tab = HabitsManagerWidget()
        self.todos_tab = TodosManagerWidget()

        self.habits_tab.changed.connect(self.refresh)
        self.todos_tab.changed.connect(self.refresh)

        self.tabs.addTab(self.habits_tab, 'Habits')
        self.tabs.addTab(self.todos_tab, 'Todos')

        # performance: only refresh the visible tab when user switches
        self.tabs.currentChanged.connect(lambda _: self.refresh())

    def refresh(self):
        # performance: only refresh active tab (not both every time)
        idx = self.tabs.currentIndex()
        if idx == 0:
            self.habits_tab.refresh()
        else:
            self.todos_tab.refresh()


class HabitsManagerWidget(QWidget):
    changed = Signal()

    def __init__(self):
        super().__init__()

        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        create_card, create_layout = self.make_card('Create habit')
        layout.addWidget(create_card)

        form_row = QHBoxLayout()
        create_layout.addLayout(form_row)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText('Title')
        form_row.addWidget(self.title_input, 2)

        self.emoji_input = QComboBox()
        self.emoji_input.addItems(EMOJIS)
        self.emoji_input.setMaximumWidth(80)
        form_row.addWidget(self.emoji_input)

        self.frequency_input = QComboBox()
        self.frequency_input.addItems(['daily', 'weekly'])
        self.frequency_input.currentTextChanged.connect(self.on_frequency_changed)
        self.frequency_input.setMaximumWidth(120)
        form_row.addWidget(self.frequency_input, 0)

        self.weekly_target_input = QSpinBox()
        self.weekly_target_input.setRange(1, 99)
        self.weekly_target_input.setValue(3)
        self.weekly_target_input.setMaximumWidth(90)
        form_row.addWidget(self.weekly_target_input, 0)

        self.start_date_input = QDateEdit()
        self.start_date_input.setCalendarPopup(True)
        self.start_date_input.setDisplayFormat('yyyy-MM-dd')
        self.start_date_input.setDate(QDate.currentDate())
        self.start_date_input.setMaximumWidth(140)
        form_row.addWidget(self.start_date_input, 0)

        self.active_input = QCheckBox('Active')
        self.active_input.setChecked(True)
        form_row.addWidget(self.active_input, 0)

        add_button = QPushButton('Add')
        add_button.clicked.connect(self.add_habit)
        form_row.addWidget(add_button, 0)

        self.on_frequency_changed(self.frequency_input.currentText())

        list_card, list_layout = self.make_card('All habits')
        layout.addWidget(list_card, 1)

        self.habits_list = QListWidget()
        # performance: smoother scrolling for uniform-height rows
        self.habits_list.setUniformItemSizes(True)
        list_layout.addWidget(self.habits_list, 1)

    def make_card(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame()
        frame.setStyleSheet(
            'QFrame { background: #ffffff; border: 1px solid #d9d9d9; border-radius: 10px; }'
        )

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        header = QLabel(title)
        header.setStyleSheet('font-weight: 600;')
        layout.addWidget(header)

        return frame, layout

    def on_frequency_changed(self, frequency: str):
        is_weekly = (frequency == 'weekly')
        self.weekly_target_input.setEnabled(is_weekly)
        if not is_weekly:
            self.weekly_target_input.setValue(1)

    def add_habit(self):
        title = self.title_input.text().strip()
        if not title:
            return

        emoji = self.emoji_input.currentText() or None

        frequency = self.frequency_input.currentText()
        weekly_target = int(self.weekly_target_input.value()) if frequency == 'weekly' else None
        start_date = self.start_date_input.date().toString('yyyy-MM-dd')
        active = bool(self.active_input.isChecked())

        with db_session() as connection:
            insert_habit(
                connection,
                title=title,
                emoji=emoji,
                frequency=frequency,
                weekly_target=weekly_target,
                active=active,
                start_date=start_date,
            )

        self.title_input.setText('')
        self.emoji_input.setCurrentText('')

        self.refresh()
        self.changed.emit()

    def refresh(self):
        self.habits_list.setUpdatesEnabled(False)
        self.habits_list.clear()

        today = dt_date.today().isoformat()

        # performance: one connection for habits + streaks
        with db_session() as connection:
            habits = list_all_habits(connection)

            streaks: dict[int, int] = {}
            for h in habits:
                hid = int(h['id'])
                if h['frequency'] == 'daily':
                    streaks[hid] = get_daily_streak(connection, hid, today)
                else:
                    streaks[hid] = get_weekly_streak(connection, hid, today)

        for habit in habits:
            item = QListWidgetItem()
            widget = self.make_habit_row(habit, streaks.get(int(habit['id']), 0))
            item.setSizeHint(widget.sizeHint())
            self.habits_list.addItem(item)
            self.habits_list.setItemWidget(item, widget)

        self.habits_list.setUpdatesEnabled(True)

    def make_habit_row(self, habit: dict, streak: int) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        name = habit['title']
        if habit.get('emoji'):
            name = f"{habit['emoji']} {name}"

        name_label = QLabel(name)
        name_label.setMinimumWidth(220)
        layout.addWidget(name_label, 1)

        meta = []
        meta.append(habit['frequency'])
        if habit['frequency'] == 'weekly':
            meta.append(f"target {int(habit['weekly_target'] or 0)}")
        if habit.get('start_date'):
            meta.append(f"start {habit['start_date']}")
        meta_label = QLabel(' • '.join(meta))
        meta_label.setStyleSheet('color: #666; font-size: 12px;')
        layout.addWidget(meta_label, 1)

        active_box = QCheckBox('Active')
        active_box.setChecked(bool(habit['active']))
        active_box.setProperty('habit_id', habit['id'])
        active_box.toggled.connect(self.toggle_active)
        layout.addWidget(active_box, 0)

        delete_button = QPushButton('Delete')
        delete_button.setProperty('habit_id', habit['id'])
        delete_button.clicked.connect(self.remove_habit)
        layout.addWidget(delete_button, 0)

        edit = QPushButton('Edit')
        edit.setProperty('habit', habit)
        edit.clicked.connect(self.edit_habit)
        layout.addWidget(edit)

        streak_label = QLabel(f'🔥 {streak}' if streak > 0 else '')
        streak_label.setStyleSheet('color: #666; font-size: 12px;')
        streak_label.setMinimumWidth(46)
        layout.addWidget(streak_label)

        return row

    def edit_habit(self):
        habit = self.sender().property('habit')
        dialog = EditHabitDialog(habit, self)
        dialog.saved.connect(self.refresh)
        dialog.exec()

    def toggle_active(self, checked: bool):
        box = self.sender()
        if not box:
            return

        habit_id = box.property('habit_id')
        if habit_id is None:
            return

        with db_session() as connection:
            set_habit_active(connection, int(habit_id), checked)

        self.changed.emit()

    def remove_habit(self):
        button = self.sender()
        if not button:
            return

        habit_id = button.property('habit_id')
        if habit_id is None:
            return

        answer = QMessageBox.question(
            self,
            'Delete habit',
            'Really delete this habit? This will also remove its logs.',
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        with db_session() as connection:
            delete_habit(connection, int(habit_id))

        self.refresh()
        self.changed.emit()


class TodosManagerWidget(QWidget):
    changed = Signal()

    def __init__(self):
        super().__init__()

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self.refresh)

        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        create_card, create_layout = self.make_card('Create todo')
        layout.addWidget(create_card)

        row = QHBoxLayout()
        create_layout.addLayout(row)

        self.todo_title_input = QLineEdit()
        self.todo_title_input.setPlaceholderText('Todo title')
        row.addWidget(self.todo_title_input, 2)

        self.todo_date_input = QDateEdit()
        self.todo_date_input.setCalendarPopup(True)
        self.todo_date_input.setDisplayFormat('yyyy-MM-dd')
        self.todo_date_input.setDate(QDate.currentDate())
        self.todo_date_input.setMaximumWidth(140)
        row.addWidget(self.todo_date_input, 0)

        self.backlog_box = QCheckBox('Backlog')
        self.backlog_box.toggled.connect(self.on_backlog_toggled)
        row.addWidget(self.backlog_box, 0)

        add_button = QPushButton('Add')
        add_button.clicked.connect(self.add_todo)
        row.addWidget(add_button, 0)

        list_card, list_layout = self.make_card('All todos')
        layout.addWidget(list_card, 1)

        filter_row = QHBoxLayout()
        list_layout.addLayout(filter_row)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('Search title...')
        # performance: debounce refresh instead of refresh on every keystroke
        self.search_input.textChanged.connect(lambda _: self.request_refresh())
        filter_row.addWidget(self.search_input, 2)

        self.mode_input = QComboBox()
        self.mode_input.addItems(['All', 'Backlog', 'By date'])
        self.mode_input.currentTextChanged.connect(self.on_mode_changed)
        filter_row.addWidget(self.mode_input, 0)

        self.filter_date_input = QDateEdit()
        self.filter_date_input.setCalendarPopup(True)
        self.filter_date_input.setDisplayFormat('yyyy-MM-dd')
        self.filter_date_input.setDate(QDate.currentDate())
        # performance: debounce date-based refresh too
        self.filter_date_input.dateChanged.connect(lambda _: self.request_refresh())
        filter_row.addWidget(self.filter_date_input, 0)

        self.todos_list = QListWidget()
        # performance: smoother scrolling for uniform-height rows
        self.todos_list.setUniformItemSizes(True)
        list_layout.addWidget(self.todos_list, 1)

        self.on_backlog_toggled(self.backlog_box.isChecked())
        self.on_mode_changed(self.mode_input.currentText())

    def request_refresh(self):
        # small delay collapses rapid events into one refresh
        self._refresh_timer.start(180)

    def make_card(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame()
        frame.setStyleSheet(
            'QFrame { background: #ffffff; border: 1px solid #d9d9d9; border-radius: 10px; }'
        )

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        header = QLabel(title)
        header.setStyleSheet('font-weight: 600;')
        layout.addWidget(header)

        return frame, layout

    def on_backlog_toggled(self, checked: bool):
        self.todo_date_input.setEnabled(not checked)

    def add_todo(self):
        title = self.todo_title_input.text().strip()
        if not title:
            return

        date_value = None
        if not self.backlog_box.isChecked():
            date_value = self.todo_date_input.date().toString('yyyy-MM-dd')

        with db_session() as connection:
            insert_todo(connection, title, date_value)

        self.todo_title_input.setText('')
        self.refresh()
        self.changed.emit()

    def refresh(self):
        self.todos_list.setUpdatesEnabled(False)
        self.todos_list.clear()

        with db_session() as connection:
            todos = list_all_todos(connection)

        query = (self.search_input.text() or '').strip().lower()
        mode = self.mode_input.currentText()
        day_iso = self.filter_date_input.date().toString('yyyy-MM-dd')

        filtered = []
        for t in todos:
            title = (t.get('title') or '')
            date_value = t.get('date')

            if query and query not in title.lower():
                continue

            if mode == 'Backlog' and date_value is not None:
                continue

            if mode == 'By date' and date_value != day_iso:
                continue

            filtered.append(t)

        # sort so that completed are at bottom
        filtered.sort(key=lambda t: t['completed'])

        for todo in filtered:
            item = QListWidgetItem()
            widget = self.make_todo_row(todo)
            item.setSizeHint(widget.sizeHint())
            self.todos_list.addItem(item)
            self.todos_list.setItemWidget(item, widget)

        self.todos_list.setUpdatesEnabled(True)

    def make_todo_row(self, todo: dict) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        checkbox = QCheckBox()
        checkbox.setChecked(bool(todo['completed']))
        checkbox.setProperty('todo_id', todo['id'])
        checkbox.toggled.connect(self.toggle_todo)
        layout.addWidget(checkbox)

        title = todo['title']
        if todo.get('completed'):
            title = f'✓ {title}'

        title_label = QLabel(title)
        if todo.get('completed'):
            title_label.setStyleSheet('color: #888; text-decoration: line-through;')

        layout.addWidget(title_label, 1)

        date_text = todo['date'] if todo.get('date') else 'Backlog'
        date_label = QLabel(date_text)
        date_label.setStyleSheet('color: #666; font-size: 12px;')
        date_label.setMinimumWidth(90)
        date_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(date_label, 0)

        delete_button = QPushButton('Delete')
        delete_button.setProperty('todo_id', todo['id'])
        delete_button.clicked.connect(self.remove_todo)
        layout.addWidget(delete_button, 0)

        edit_button = QPushButton('Edit')
        edit_button.setProperty('todo', todo)
        edit_button.clicked.connect(self.edit_todo)
        layout.addWidget(edit_button, 0)

        return row

    def toggle_todo(self, checked: bool):
        checkbox = self.sender()
        if not checkbox:
            return

        todo_id = checkbox.property('todo_id')
        if todo_id is None:
            return

        with db_session() as connection:
            set_todo_completed(connection, int(todo_id), checked)

        self.refresh()
        self.changed.emit()

    def edit_todo(self):
        todo = self.sender().property('todo')
        dialog = EditTodoDialog(todo, self)
        dialog.saved.connect(self.refresh)
        dialog.exec()

    def remove_todo(self):
        button = self.sender()
        if not button:
            return

        todo_id = button.property('todo_id')
        if todo_id is None:
            return

        with db_session() as connection:
            delete_todo(connection, int(todo_id))

        self.refresh()
        self.changed.emit()

    def on_mode_changed(self, text: str):
        self.filter_date_input.setEnabled(text == 'By date')
        self.refresh()
