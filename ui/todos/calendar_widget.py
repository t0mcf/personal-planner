import calendar
from datetime import date as dt_date

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QToolButton,
    QSizePolicy
)

from db.core import connect_db
from db.todos import get_todo_stats_for_month
from db.habits import get_daily_habit_stats_for_month
from db.journal import get_journal_status_for_month


class CalendarWidget(QWidget):
    day_selected = Signal(str)  # 'YYYY-MM-DD'

    def __init__(self, day: str | None = None, parent: QWidget | None = None):
        super().__init__(parent)

        today_date = dt_date.today()
        selected_date = dt_date.fromisoformat(day) if day else today_date

        #calendar state
        self.year = selected_date.year
        self.month = selected_date.month
        self.selected_day = selected_date.isoformat()

        self.build_ui()
        self.render_month()

    def build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)

        header = QHBoxLayout()
        main_layout.addLayout(header)

        prev_btn = QToolButton()
        prev_btn.setText('◀')
        prev_btn.clicked.connect(self.prev_month)
        header.addWidget(prev_btn)

        self.month_label = QLabel('')
        self.month_label.setAlignment(Qt.AlignCenter)
        self.month_label.setStyleSheet('font-size: 16px; font-weight: 600;')
        header.addWidget(self.month_label, 1)

        next_btn = QToolButton()
        next_btn.setText('▶')
        next_btn.clicked.connect(self.next_month)
        header.addWidget(next_btn)

        weekdays = QGridLayout()
        weekdays.setContentsMargins(0, 0, 0, 0)
        weekdays.setHorizontalSpacing(0)
        weekdays.setVerticalSpacing(0)
        main_layout.addLayout(weekdays)

        names = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
        for col, name in enumerate(names):
            label = QLabel(name)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet('font-weight: 600; color: #777; padding: 6px 0;')
            weekdays.addWidget(label, 0, col)

        self.grid = QGridLayout()
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(0)
        self.grid.setVerticalSpacing(0)
        main_layout.addLayout(self.grid, 1)

        self.tiles: list[DayTile] = []

        for i in range(6 * 7):
            tile = DayTile()
            tile.clicked.connect(self.select_day)

            self.tiles.append(tile)

            row = i // 7
            col = i % 7
            self.grid.addWidget(tile, row, col)

        for col in range(7):
            self.grid.setColumnStretch(col, 1)
        for row in range(6):
            self.grid.setRowStretch(row, 1)

    def render_month(self):
        self.month_label.setText(f'{self.year:04d}-{self.month:02d}')
    
        #get data for info per day tile 
        connection = connect_db()
        todo_stats = get_todo_stats_for_month(connection, self.year, self.month)
        journal_status = get_journal_status_for_month(connection, self.year, self.month)
        total_daily, daily_done_by_day = get_daily_habit_stats_for_month(connection, self.year, self.month)
        connection.close()
        
        cal = calendar.Calendar(firstweekday=calendar.MONDAY)
        month_days = list(cal.itermonthdates(self.year, self.month))
        

        if len(month_days) < 42:
            last = month_days[-1]
            while len(month_days) < 42:
                last = dt_date.fromordinal(last.toordinal() + 1)
                month_days.append(last)
        else:
            month_days = month_days[:42]

        for index in range(42):
            day_date = month_days[index]
            tile = self.tiles[index]

            day_iso = day_date.isoformat()
            in_current_month = (day_date.month == self.month)
            selected = (day_iso == self.selected_day)

            tile.set_day(day_iso, day_date.day, in_current_month, selected)
            
            #displaying stats per day
            todo_done, todo_total = todo_stats.get(day_iso, (0, 0))
            daily_done = daily_done_by_day.get(day_iso, 0)

            journal_has = journal_status.get(day_iso, False)
            journal_text = '✓' if journal_has else '-'

            info_lines = [
                f'📝 {todo_done}/{todo_total}' if todo_total else '📝 -',
                f'🔁  {daily_done}/{total_daily}' if total_daily else '🔁  -',
                f'📓 {journal_text}',
            ]

            tile.set_info_lines(info_lines)


    def select_day(self, day_iso: str):
        self.selected_day = day_iso
        self.render_month()
        self.day_selected.emit(day_iso)


    #deprecated
    def click_day(self):
        button = self.sender()
        if not button:
            return

        day_iso = button.property('day')
        if not day_iso:
            return

        self.selected_day = day_iso
        self.render_month()
        self.day_selected.emit(day_iso)

    def prev_month(self):
        if self.month == 1:
            self.year -= 1
            self.month = 12
        else:
            self.month -= 1

        self.render_month()

    def next_month(self):
        if self.month == 12:
            self.year += 1
            self.month = 1
        else:
            self.month += 1

        self.render_month()



from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, Signal


class DayTile(QWidget):
    clicked = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self.day_iso: str | None = None
        self.in_current_month = True
        self.is_selected = False

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(0)

        self.content = QLabel('')
        self.content.setTextFormat(Qt.RichText)
        self.content.setWordWrap(True)
        self.content.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.setStyleSheet('background: #ffffff; border: 2px solid #4b8cff; border-radius: 10px;')

        layout.addWidget(self.content, 1)

        self.day_number = 0
        self.info_lines: list[str] = []

        self.apply_style()

    def set_day(self, day_iso: str, day_number: int, in_current_month: bool, selected: bool):
        self.day_iso = day_iso
        self.day_number = day_number
        self.in_current_month = in_current_month
        self.is_selected = selected

        self.setEnabled(True)
        self.render()

    def set_info_lines(self, lines: list[str]):
        self.info_lines = lines
        self.render()

    def clear(self):
        self.day_iso = None
        self.day_number = 0
        self.info_lines = []
        self.setEnabled(False)
        self.is_selected = False
        self.content.setText('')
        self.apply_style()

    def apply_style(self):
        if self.is_selected:
            self.setStyleSheet('background: #ffffff; border: 2px solid #4b8cff; border-radius: 10px;')
        else:
            self.setStyleSheet('background: #ffffff; border: 1px solid #cfcfcf; border-radius: 10px;')

    def render(self):
        if not self.day_iso:
            self.content.setText('')
            self.apply_style()
            return

        day_color = '#222' if self.in_current_month else '#aaa'

        info_html = ''
        if self.info_lines:
            items = ''.join([f'<div style="margin-top: 4px; color: #666; font-size: 12px;">{line}</div>' for line in self.info_lines])
            info_html = f'<div style="margin-top: 10px;">{items}</div>'

        html = f"""
        <div style="width: 100%; height: 100%;">
          <div style="text-align: right; font-weight: 600; color: {day_color};">
            {self.day_number}
          </div>
          {info_html}
        </div>
        """

        self.content.setText(html)
        self.apply_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.day_iso:
            self.clicked.emit(self.day_iso)
