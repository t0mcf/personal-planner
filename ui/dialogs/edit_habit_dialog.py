from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton,
    QComboBox, QSpinBox, QDateEdit
)
from PySide6.QtCore import QDate, Signal
from datetime import date as dt_date

from db.core import connect_db
from db.habits import update_habit
from helpers.db import db_session

#for habits
EMOJIS = [
    '',
    '📚', '🏃', '🧘', '💪', '🥗', '💧',
    '🎯', '🔥', '📝', '🎧', '🎨',
    '📖', '✍', '🛏', '🌿', '☀'
]

class EditHabitDialog(QDialog):
    saved = Signal()

    def __init__(self, habit: dict, parent=None):
        super().__init__(parent)

        self.habit = habit
        self.setWindowTitle('Edit habit')
        self.resize(420, 200)

        layout = QVBoxLayout(self)

        self.title_input = QLineEdit(habit['title'])
        layout.addWidget(QLabel('Title'))
        layout.addWidget(self.title_input)

        self.emoji_input = QComboBox()
        self.emoji_input.addItems(EMOJIS)
        self.emoji_input.setCurrentText(habit.get('emoji') or '')
        layout.addWidget(QLabel('Emoji'))
        layout.addWidget(self.emoji_input)

        self.frequency_input = QComboBox()
        self.frequency_input.addItems(['daily', 'weekly'])
        self.frequency_input.setCurrentText(habit['frequency'])
        self.frequency_input.currentTextChanged.connect(self.update_state)
        layout.addWidget(QLabel('Frequency'))
        layout.addWidget(self.frequency_input)

        self.weekly_target_input = QSpinBox()
        self.weekly_target_input.setRange(1, 99)
        self.weekly_target_input.setValue(int(habit.get('weekly_target') or 1))
        layout.addWidget(QLabel('Weekly target'))
        layout.addWidget(self.weekly_target_input)

        self.start_date_input = QDateEdit()
        self.start_date_input.setCalendarPopup(True)
        self.start_date_input.setDisplayFormat('yyyy-MM-dd')
        start = habit.get('start_date') or dt_date.today().isoformat()
        self.start_date_input.setDate(QDate.fromString(start, 'yyyy-MM-dd'))
        layout.addWidget(QLabel('Start date'))
        layout.addWidget(self.start_date_input)

        buttons = QHBoxLayout()
        layout.addLayout(buttons)
        buttons.addStretch()

        cancel = QPushButton('Cancel')
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)

        save = QPushButton('Save')
        save.clicked.connect(self.save)
        buttons.addWidget(save)

        self.update_state(self.frequency_input.currentText())

    def update_state(self, frequency: str):
        self.weekly_target_input.setEnabled(frequency == 'weekly')

    def save(self):
        title = self.title_input.text().strip()
        if not title:
            return

        emoji = self.emoji_input.currentText() or None
        frequency = self.frequency_input.currentText()
        weekly_target = (
            self.weekly_target_input.value()
            if frequency == 'weekly'
            else None
        )
        start_date = self.start_date_input.date().toString('yyyy-MM-dd')

        with db_session() as connection:
            update_habit(
                connection,
                habit_id=int(self.habit['id']),
                title=title,
                emoji=emoji,
                frequency=frequency,
                weekly_target=weekly_target,
                start_date=start_date,
            )

        self.saved.emit()
        self.accept()
