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
    QToolButton,
    QDialog, 
    QSplitter,
    QFrame,
    QProgressBar
)

from PySide6.QtCore import Qt, Signal

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
from db.habits import list_active_habits, is_daily_done, set_daily_done, get_weekly_progress, increment_habit_today, get_daily_streak, get_weekly_streak

from ui.todos.calendar_widget import CalendarWidget


class DayView(QWidget):
    open_manager = Signal()
    def __init__(self, day: str | None = None):
        super().__init__()

        self.day = day or dt_date.today().isoformat()

        self.build_ui()
        self.refresh()

    #___ui functions___

    def build_ui(self):
        
        main_layout = QVBoxLayout(self)

        center_row = QHBoxLayout()
        main_layout.addLayout(center_row, 1)

        #workaround to prevent scaling in fullscreen (looks weird)
        #maybe take out again idk, for now it feels better
        content_widget = QWidget()
        content_widget.setMaximumWidth(1400)
        content_widget.setMaximumHeight(1000)

        center_row.addWidget(content_widget, 0)

        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)
                
        top_bar = QHBoxLayout()
        content_layout.addLayout(top_bar)
        
        #summary cards on top
        
        summary_row = QHBoxLayout()
        summary_row.setSpacing(12)
        content_layout.addLayout(summary_row)

        self.summary_todos_card, self.summary_todos_value = self.make_summary_card('Todos', '-')
        self.summary_habits_card, self.summary_habits_value = self.make_summary_card('Habits', '-')
        self.summary_streaks_card, self.summary_streaks_value = self.make_summary_card('Top Streaks', '-')
        self.summary_journal_card, self.summary_journal_value = self.make_summary_card('Journal', '-')

        summary_row.addWidget(self.summary_todos_card)
        summary_row.addWidget(self.summary_habits_card)
        summary_row.addWidget(self.summary_streaks_card)
        summary_row.addWidget(self.summary_journal_card)
        
        self.summary_todos_card.setMinimumWidth(140)
        self.summary_habits_card.setMinimumWidth(140)
        self.summary_streaks_card.setMinimumWidth(140)
        self.summary_journal_card.setMinimumWidth(140)

        prev_button = QToolButton()
        prev_button.setText('◀')
        prev_button.clicked.connect(self.prev_day)
        top_bar.addWidget(prev_button)
        
        self.date_label = QLabel(self.day)
        self.date_label.setAlignment(Qt.AlignCenter)
        self.date_label.setStyleSheet('font-size: 18px; font-weight: 600;')
        top_bar.addWidget(self.date_label, 1)

        next_button = QToolButton()
        next_button.setText('▶')
        next_button.clicked.connect(self.next_day)
        top_bar.addWidget(next_button)
        
        calendar_button = QPushButton('📅')
        calendar_button.clicked.connect(self.open_calendar)
        top_bar.addWidget(calendar_button)
        
        #to switch to manager view
        manager_button = QPushButton('⚙️')
        manager_button.clicked.connect(self.open_manager.emit)
        top_bar.addWidget(manager_button)
        
        splitter = QSplitter(Qt.Horizontal)
        content_layout.addWidget(splitter, 1)
        
        #for habits and todos
        left_panel = (QWidget())
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
                
        todos_label = QLabel('Todos')
        todos_label.setStyleSheet('font-weight: 600; margin-top: 4px')
        left_layout.addWidget(todos_label)
        
        self.todo_list = QListWidget()
        left_layout.addWidget(self.todo_list, 1)

        add_button = QPushButton('+ Add Todo')
        add_button.clicked.connect(self.add_todo)
        left_layout.addWidget(add_button)

        self.habits_container = QWidget()
        habits_container_layout = QVBoxLayout(self.habits_container)
        habits_container_layout.setContentsMargins(0, 0, 0, 0)
        habits_container_layout.setSpacing(10)

        daily_card, daily_layout = self.make_card('Daily habits')
        self.daily_habits_layout = daily_layout
        habits_container_layout.addWidget(daily_card)

        weekly_card, weekly_layout = self.make_card('Weekly habits')
        self.weekly_habits_layout = weekly_layout
        habits_container_layout.addWidget(weekly_card)

        left_layout.addWidget(self.habits_container)


        #for journaling part 
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        journal_label = QLabel('Journal')
        journal_label.setStyleSheet('font-weight: 600; margin-top: 4px;')
        right_layout.addWidget(journal_label)

        self.journal_edit = QTextEdit()
        self.journal_edit.textChanged.connect(self.autosave_journal)
        right_layout.addWidget(self.journal_edit, 1)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([700, 450])
        
    # ___data part___

    def refresh(self):
        self.load_todos()
        self.load_habits()
        self.load_journal()
        self.update_summary()
        
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


    #for habit cards
    def make_card(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame()
        frame.setStyleSheet(
            'QFrame { background: #ffffff; border: 1px solid #d9d9d9; border-radius: 10px; }'
        )

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        header = QLabel(title)
        header.setStyleSheet('font-weight: 600;')
        layout.addWidget(header)

        return frame, layout


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
        
        self.summary_journal_value.setText('📓 ✓' if text.strip() else '📓 -')


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


    def open_calendar(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Calendar')
        dialog.resize(900, 650)

        layout = QVBoxLayout(dialog)

        calendar_widget = CalendarWidget(self.day)
        layout.addWidget(calendar_widget)

        chosen = {'day': None}

        def on_day(day: str):
            chosen['day'] = day
            dialog.accept()

        calendar_widget.day_selected.connect(on_day)

        if dialog.exec() and chosen['day']:
            self.set_day(chosen['day'])
            
   
    def make_daily_habit_row(self, habit_id: int, title: str, emoji: str | None, done: bool, streak: int) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        checkbox = QCheckBox()
        checkbox.setChecked(done)
        checkbox.setProperty('habit_id', habit_id)
        checkbox.toggled.connect(self.toggle_daily_habit)

        label = QLabel(f'{emoji} {title}' if emoji else title) 
        label.setProperty('habit_id', habit_id)
        if done:
            label.setStyleSheet('color: #888; text-decoration: line-through;')

        streak_label = QLabel(f'🔥 {streak}' if streak > 0 else '')
        streak_label.setStyleSheet('color: #666; font-size: 12px;')
        streak_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        streak_label.setMinimumWidth(46)


        layout.addWidget(checkbox)
        layout.addWidget(label)
        layout.addWidget(streak_label)
        layout.addStretch()

        return row
    
    
    def toggle_daily_habit(self, checked: bool):
        checkbox = self.sender()
        if not checkbox:
            return
        
        habit_id = checkbox.property('habit_id')
        if habit_id is None:
            return
        
        connection = connect_db()
        set_daily_done(connection, int(habit_id), self.day, checked) #edit db
        connection.close()
        
        self.refresh()
        

    
    def make_weekly_habit_row(self, habit_id: int, title: str, emoji: str | None, done: int, target: int, streak: int) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        name = f'{emoji} {title}' if emoji else title
        label = QLabel(name)
        label.setMinimumWidth(140)

        progress = QProgressBar()
        progress.setRange(0, target if target > 0 else 1)
        progress.setValue(done)
        progress.setTextVisible(False)
        progress.setFixedHeight(14)

        count_label = QLabel(f'{done} / {target}')
        count_label.setStyleSheet('color: #666; font-size: 12px;')
        count_label.setMinimumWidth(55)
        count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        streak_label = QLabel(f'🔥 {streak}' if streak > 0 else '')
        streak_label.setStyleSheet('color: #666; font-size: 12px;')
        streak_label.setMinimumWidth(46)
        streak_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        plus_button = QPushButton('+')
        plus_button.setFixedWidth(32)
        plus_button.setProperty('habit_id', habit_id)
        plus_button.clicked.connect(self.increment_weekly_habit)

        if target > 0 and done >= target:
            plus_button.setEnabled(False)

        layout.addWidget(label)
        layout.addWidget(progress, 1)
        layout.addWidget(count_label)
        layout.addWidget(streak_label)
        layout.addWidget(plus_button)

        return row
    

    def increment_weekly_habit(self):
        button = self.sender()
        if not button:
            return

        habit_id = button.property('habit_id')
        if habit_id is None:
            return

        connection = connect_db()
        increment_habit_today(connection, int(habit_id), self.day)
        connection.close()

        self.refresh()


                
    def clear_card_body(self, layout: QVBoxLayout):
        while layout.count() > 1:
            item = layout.takeAt(1)
            widget = item.widget()
            if widget:
                widget.deleteLater()


    def load_habits(self):
        self.clear_card_body(self.daily_habits_layout)
        self.clear_card_body(self.weekly_habits_layout)

        connection = connect_db()
        habits = list_active_habits(connection)
        
        #only active habits: maybe change list_active_habits to alr do that if needed elsewhere, but for now this works 
        habits = [h for h in habits if h['start_date'] <= self.day]

        daily = [h for h in habits if h['frequency'] == 'daily']
        weekly = [h for h in habits if h['frequency'] == 'weekly']

        for habit in daily:
            done = is_daily_done(connection, habit['id'], self.day)
            streak = get_daily_streak(connection, habit['id'], self.day)
            self.daily_habits_layout.addWidget(
                self.make_daily_habit_row(habit['id'], habit['title'], habit['emoji'], done, streak)
            )

        for habit in weekly:
            done, target = get_weekly_progress(connection, habit['id'], self.day)
            streak = get_weekly_streak(connection, habit['id'], self.day)
            self.weekly_habits_layout.addWidget(
                self.make_weekly_habit_row(habit['id'], habit['title'], habit['emoji'], done, target, streak)
            )

        connection.close()

        if not daily:
            empty = QLabel('No daily habits active')
            empty.setStyleSheet('color: #777;')
            self.daily_habits_layout.addWidget(empty)

        if not weekly:
            empty = QLabel('No weekly habits active')
            empty.setStyleSheet('color: #777;')
            self.weekly_habits_layout.addWidget(empty)
            
    #for top row, similar design as in the finance dashboard view
    def make_summary_card(self, title: str, value: str) -> tuple[QFrame, QLabel]:
        frame = QFrame()
        frame.setStyleSheet(
            '''
            QFrame {
                background: #ffffff;
                border: 1px solid #d9d9d9;
                border-radius: 10px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
            '''
        )

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)

        label_title = QLabel(title)
        label_title.setStyleSheet('color: #666; border: none; background: transparent;')

        label_value = QLabel(value)
        label_value.setStyleSheet('font-size: 20px; font-weight: 700; border: none; background: transparent;')

        layout.addWidget(label_title)
        layout.addWidget(label_value)
        layout.addStretch(1)

        return frame, label_value

    
    def update_summary(self):
        connection = connect_db()

        todos = list_todos_for_day(connection, self.day)
        total_todos = len(todos)
        done_todos = sum(1 for t in todos if t['completed'])

        self.summary_todos_value.setText(f'📝 {done_todos}/{total_todos}' if total_todos else '📝 -')

        habits = list_active_habits(connection)
        daily = [h for h in habits if h['frequency'] == 'daily']
        weekly = [h for h in habits if h['frequency'] == 'weekly']

        daily_done = 0
        for h in daily:
            if is_daily_done(connection, h['id'], self.day):
                daily_done += 1

        weekly_done = 0
        for h in weekly:
            done, target = get_weekly_progress(connection, h['id'], self.day)
            if target > 0 and done >= target:
                weekly_done += 1

        daily_total = len(daily)
        weekly_total = len(weekly)

        if daily_total or weekly_total:
            parts = []
            if daily_total:
                parts.append(f'D {daily_done}/{daily_total}')
            if weekly_total:
                parts.append(f'W {weekly_done}/{weekly_total}')
            self.summary_habits_value.setText('🔁 ' + '   '.join(parts))
        else:
            self.summary_habits_value.setText('-')


        best_daily = 0
        for h in daily:
            s = get_daily_streak(connection, h['id'], self.day)
            if s > best_daily:
                best_daily = s

        best_weekly = 0
        for h in weekly:
            s = get_weekly_streak(connection, h['id'], self.day)
            if s > best_weekly:
                best_weekly = s

        if best_daily or best_weekly:
            self.summary_streaks_value.setText(f'🔥 D{best_daily}  W{best_weekly}')
        else:
            self.summary_streaks_value.setText('-')

        #for journaling just do a tick if there is an entry, maybe useless, might remove
        text = get_journal_entry(connection, self.day) or ''
        has_journal = bool(text.strip())
        self.summary_journal_value.setText('📓 ✓' if has_journal else '📓 -')

        connection.close()

