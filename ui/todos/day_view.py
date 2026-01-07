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
    QProgressBar,
    QButtonGroup,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QShowEvent

from helpers.db import db_session
from db.todos import (
    list_todos_for_day,
    insert_todo,
)
from db.journal import (
    get_journal_data,
    save_journal_entry,
)
from db.habits import (
    list_active_habits,
    is_daily_done,
    get_weekly_progress,
    get_daily_streak,
    get_weekly_streak
)

from ui.todos.calendar_widget import CalendarWidget

from actions.actions import *


class DayView(QWidget):
    def __init__(self, day: str | None = None):
        super().__init__()

        self.day = day or dt_date.today().isoformat()

        self._mood_value: int | None = None
        self._sleep_value: int | None = None

        self._journal_save_timer = QTimer(self)
        self._journal_save_timer.setSingleShot(True)
        self._journal_save_timer.timeout.connect(self._save_journal_all_fields)

        self.build_ui()
        self.refresh()

    #___ui functions___

    def build_ui(self):
        main_layout = QVBoxLayout(self)

        center_row = QHBoxLayout()
        main_layout.addLayout(center_row, 1)

        content_widget = QWidget()
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

        splitter = QSplitter(Qt.Horizontal)
        content_layout.addWidget(splitter, 1)

        # left panel (unchanged)
        left_panel = QWidget()
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

        # right panel (JOURNAL: updated)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        journal_label = QLabel('Journal')
        journal_label.setStyleSheet('font-weight: 600; margin-top: 4px;')
        right_layout.addWidget(journal_label)

        # Mood row
        mood_row = QHBoxLayout()
        mood_row.setSpacing(8)
        right_layout.addLayout(mood_row)

        mood_title = QLabel('Mood')
        mood_title.setStyleSheet('color: #666; font-size: 12px;')
        mood_row.addWidget(mood_title)

        self.mood_group = QButtonGroup(self)
        self.mood_group.setExclusive(True)

        mood_emojis = ['😞', '😐', '🙂', '😄', '🤩']
        for i, e in enumerate(mood_emojis, start=1):
            b = QToolButton()
            b.setText(e)
            b.setCheckable(True)
            b.setFixedWidth(34)
            b.setProperty('mood_value', i)
            self.mood_group.addButton(b, i)
            b.clicked.connect(self.on_mood_clicked)
            mood_row.addWidget(b)

        mood_row.addStretch(1)

        # Sleep row
        sleep_row = QHBoxLayout()
        sleep_row.setSpacing(8)
        right_layout.addLayout(sleep_row)

        sleep_title = QLabel('Sleep')
        sleep_title.setStyleSheet('color: #666; font-size: 12px;')
        sleep_row.addWidget(sleep_title)

        self.sleep_group = QButtonGroup(self)
        self.sleep_group.setExclusive(True)

        for i in range(1, 6):
            b = QToolButton()
            b.setText(f'😴 {i}')
            b.setCheckable(True)
            b.setFixedWidth(48)
            b.setProperty('sleep_value', i)
            self.sleep_group.addButton(b, i)
            b.clicked.connect(self.on_sleep_clicked)
            sleep_row.addWidget(b)

        sleep_row.addStretch(1)

        # Reflection (HEADINGS, not placeholders)
        right_layout.addWidget(self._make_journal_section_label('What went well'))
        self.ref_went_well = self._make_small_text_box()
        right_layout.addWidget(self.ref_went_well)

        right_layout.addWidget(self._make_journal_section_label('What was difficult'))
        self.ref_difficult = self._make_small_text_box()
        right_layout.addWidget(self.ref_difficult)

        right_layout.addWidget(self._make_journal_section_label('One thing to remember'))
        self.ref_remember = self._make_small_text_box()
        right_layout.addWidget(self.ref_remember)

        # Free journal
        right_layout.addWidget(self._make_journal_section_label('Notes'))

        self.journal_edit = QTextEdit()
        self.journal_edit.setPlaceholderText('Write anything…')
        self.journal_edit.textChanged.connect(self.request_autosave_journal)
        right_layout.addWidget(self.journal_edit, 1)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([700, 450])

        #styling for mood/sleep buttons 
        
        right_panel.setStyleSheet(
            """
            QToolButton {
                border: 1px solid #c9c9c9;
                background: transparent;
                padding: 4px 6px;
                border-radius: 8px;
            }

            QToolButton:checked {
                background: #e3e3e3;
                border: 2px solid #6f6f6f;
                font-weight: 600;
            }

            QToolButton:hover:!checked {
                background: #f4f4f4;
            }
            """
        )


    def _make_journal_section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet('color: #666; font-size: 12px; margin-top: 2px;')
        return lbl

    def _make_small_text_box(self) -> QTextEdit:
        box = QTextEdit()
        box.setFixedHeight(56)
        box.textChanged.connect(self.request_autosave_journal)
        return box

    # ___data part___

    def refresh(self):
        self.load_todos()
        self.load_habits()
        self.load_journal()
        self.update_summary()

    def load_todos(self):
        self.todo_list.clear()

        with db_session() as connection:
            todos = list_todos_for_day(connection, self.day)


        for row in todos:
            item = QListWidgetItem()
            widget = self.make_todo_row(row)
            item.setSizeHint(widget.sizeHint())
            self.todo_list.addItem(item)
            self.todo_list.setItemWidget(item, widget)

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

    def toggle_todo(self, checked: bool):
        checkbox = self.sender()
        if not checkbox:
            return

        todo_id = checkbox.property('todo_id')
        if todo_id is None:
            return

        with db_session() as connection:
            toggle_todo(connection, self.day, int(todo_id), checked)

        self.refresh()

    def add_todo(self):
        text, confirmed = QInputDialog.getText(
            self,
            'Add Todo',
            'Todo:'
        )

        if not confirmed or not text.strip():
            return

        with db_session() as connection:
            insert_todo(connection, text.strip(), self.day)
        self.refresh()

    # ___journaling part____

    def request_autosave_journal(self):
        self._journal_save_timer.start(250)

    def on_mood_clicked(self):
        b = self.sender()
        if not b:
            return
        self._mood_value = b.property('mood_value')
        self.request_autosave_journal()

    def on_sleep_clicked(self):
        b = self.sender()
        if not b:
            return
        self._sleep_value = b.property('sleep_value')
        self.request_autosave_journal()

    def _save_journal_all_fields(self):
        notes = self.journal_edit.toPlainText()
        went_well = self.ref_went_well.toPlainText()
        difficult = self.ref_difficult.toPlainText()
        remember = self.ref_remember.toPlainText()

        with db_session() as connection:

            save_journal_entry(
                connection,
                self.day,
                notes,
                mood=self._mood_value,
                sleep=self._sleep_value,
                went_well=went_well,
                difficult=difficult,
                remember=remember,
            )

            # XP behavior stays exactly like before: XP tied to "notes" text
            save_journal(connection, self.day, notes)

        # Option A: Journal ✓ only if there is any TEXT (mood/sleep do NOT count)
        has_text = bool(notes.strip()) or bool(went_well.strip()) or bool(difficult.strip()) or bool(remember.strip())
        self.summary_journal_value.setText('📓 ✓' if has_text else '📓 -')

    def load_journal(self):
        with db_session() as connection:
            data = get_journal_data(connection, self.day)

        notes = ''
        went_well = ''
        difficult = ''
        remember = ''
        mood = None
        sleep = None

        if data:
            notes = data.get('text') or ''
            went_well = data.get('went_well') or ''
            difficult = data.get('difficult') or ''
            remember = data.get('remember') or ''
            mood = data.get('mood')
            sleep = data.get('sleep')

        self._mood_value = int(mood) if mood is not None else None
        self._sleep_value = int(sleep) if sleep is not None else None

        # block signals while setting
        self.ref_went_well.blockSignals(True)
        self.ref_difficult.blockSignals(True)
        self.ref_remember.blockSignals(True)
        self.journal_edit.blockSignals(True)

        self.ref_went_well.setPlainText(went_well)
        self.ref_difficult.setPlainText(difficult)
        self.ref_remember.setPlainText(remember)
        self.journal_edit.setPlainText(notes)

        self.ref_went_well.blockSignals(False)
        self.ref_difficult.blockSignals(False)
        self.ref_remember.blockSignals(False)
        self.journal_edit.blockSignals(False)

        self._set_group_checked(self.mood_group, self._mood_value)
        self._set_group_checked(self.sleep_group, self._sleep_value)

    def _set_group_checked(self, group: QButtonGroup, value: int | None):
        group.setExclusive(False)

        for b in group.buttons():
            b.blockSignals(True)
            b.setChecked(False)
            b.blockSignals(False)

        group.setExclusive(True)

        if value is None:
            return

        btn = group.button(int(value))
        if btn:
            btn.blockSignals(True)
            btn.setChecked(True)
            btn.blockSignals(False)


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

    # habits stuff unchanged below...

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

        with db_session() as connection:
            toggle_daily_habit(connection, self.day, int(habit_id), checked)

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

        with db_session() as connection:
            increment_weekly_habit(connection, self.day, int(habit_id))

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

        with db_session() as connection:
            habits = list_active_habits(connection)
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


        if not daily:
            empty = QLabel('No daily habits active')
            empty.setStyleSheet('color: #777;')
            self.daily_habits_layout.addWidget(empty)

        if not weekly:
            empty = QLabel('No weekly habits active')
            empty.setStyleSheet('color: #777;')
            self.weekly_habits_layout.addWidget(empty)

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
        with db_session() as connection:

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

            # Option A: Journal ✓ only if there is any TEXT (mood/sleep do NOT count)
            jd = get_journal_data(connection, self.day) or {}
            notes = (jd.get("text") or "")
            ww = (jd.get("went_well") or "")
            df = (jd.get("difficult") or "")
            rm = (jd.get("remember") or "")

            has_text = bool(notes.strip()) or bool(ww.strip()) or bool(df.strip()) or bool(rm.strip())
            self.summary_journal_value.setText('📓 ✓' if has_text else '📓 -')

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.refresh()
