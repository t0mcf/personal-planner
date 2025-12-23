from datetime import date as dt_date

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QPainter, QColor, QShowEvent
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QSizePolicy,
    QListWidget,
    QListWidgetItem,
)

from PySide6.QtCharts import (
    QChart,
    QChartView,
    QBarSeries,
    QBarSet,
    QBarCategoryAxis,
    QValueAxis,
)

from db.core import connect_db
from db.todos import list_todos_for_day, list_all_todos
from db.journal import get_journal_entry
from db.habits import (
    list_active_habits,
    is_daily_done,
    get_weekly_progress,
    get_daily_streak,
    get_weekly_streak,
)
from db.finance import get_timeseries_data, list_recent_transactions

from ui.home.weather_widget import WeatherWidget


#styles for text
TITLE_STYLE = 'font-size: 26px; font-weight: 800;'
BIG_STYLE = 'font-size: 30px; font-weight: 900;'
MID_STYLE = 'font-size: 18px; font-weight: 700;'
STAT_STYLE = 'font-size: 22px; font-weight: 800;'


class HomeView(QWidget):
    open_todos = Signal()
    open_manager = Signal()
    open_calendar = Signal()
    open_finance = Signal()
    add_todo_today = Signal()
    add_transaction = Signal()

    def __init__(self):
        super().__init__()

        self.day = dt_date.today().isoformat()

        self.build_finance_chart()
        self.build_ui()

    def build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        center_row = QHBoxLayout()
        outer.addLayout(center_row, 1)
        
        content = QWidget()
        #had the following line to prevent hor. scaling, maybe wasnt a good idea though
        #content.setMaximumWidth(1400) 
        center_row.addWidget(content, 0)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(14)

        header = QHBoxLayout()
        layout.addLayout(header, 0)

        title = QLabel('Home')
        title.setStyleSheet(TITLE_STYLE)
        header.addWidget(title)

        header.addStretch(1)

        self.date_label = QLabel(self.day)
        self.date_label.setStyleSheet('color: #666; font-size: 13px;')
        header.addWidget(self.date_label)

        #top row has tiles for finances, overview of todos and stuff, & weather
        top_row = QHBoxLayout()
        top_row.setSpacing(14)

        self.finance_tile, self.finance_layout = self.make_tile('Finance (Current Month)')
        self.finance_tile.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        right_col = QVBoxLayout()
        right_col.setSpacing(14)

        self.today_tile, self.today_layout = self.make_tile('Today')
        self.today_tile.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        self.weather_tile, self.weather_layout = self.make_tile('Weather')
        self.weather_tile.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        right_col.addWidget(self.today_tile, 0)
        right_col.addWidget(self.weather_tile, 1)

        top_row.addWidget(self.finance_tile, 1)
        top_row.addLayout(right_col, 1)

        layout.addLayout(top_row, 2)

        #bottom row for xp and activity log (this one still to fill with more than finance info)
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(14)

        self.xp_tile, self.xp_layout = self.make_tile('XP')
        self.xp_tile.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.activity_tile, self.activity_layout = self.make_tile('Recent activity')
        self.activity_tile.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        bottom_row.addWidget(self.xp_tile, 1)
        bottom_row.addWidget(self.activity_tile, 1)

        layout.addLayout(bottom_row, 1)

        #quick action bar at the very bottom
        self.actions_bar, self.actions_layout = self.make_tile('Quick actions')
        self.actions_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        layout.addWidget(self.actions_bar, 0)

        #finance overview (for now doing current month, maybe change but ig its sufficient)
        self.finance_net = QLabel('Net: 0.00')
        self.finance_net.setStyleSheet(BIG_STYLE)
        self.finance_layout.addWidget(self.finance_net)

        self.finance_lines = QLabel('Income: 0.00\nExpenses: 0.00')
        self.finance_lines.setStyleSheet(MID_STYLE)
        self.finance_layout.addWidget(self.finance_lines)

        self.chart_view.setMinimumHeight(170)
        self.chart_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.finance_layout.addWidget(self.chart_view, 1)

        finance_btn_row = QHBoxLayout()
        self.finance_layout.addLayout(finance_btn_row)
        finance_btn_row.addStretch(1)

        open_finance = QPushButton('Open Finance')
        open_finance.clicked.connect(self.open_finance.emit)
        finance_btn_row.addWidget(open_finance)

        #overview about all the day view stuff
        self.today_todos = QLabel('📝 -')
        self.today_habits = QLabel('🔁 -')
        self.today_journal = QLabel('📓 -')
        self.today_streak = QLabel('🔥 -')

        for lab in [self.today_todos, self.today_habits, self.today_journal, self.today_streak]:
            lab.setStyleSheet(STAT_STYLE)
            self.today_layout.addWidget(lab)

        next_header = QLabel('Next')
        next_header.setStyleSheet('font-size: 13px; font-weight: 800; color: #666; margin-top: 6px;')
        self.today_layout.addWidget(next_header)

        self.next_list = QListWidget()
        self.next_list.setStyleSheet(
            '''
            QListWidget {
                border: none;
                background: transparent;
            }
            QListWidget::item {
                padding: 6px 2px;
            }
            '''
        )
        self.next_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.next_list.setMaximumHeight(140)
        self.today_layout.addWidget(self.next_list)

        today_btn_row = QHBoxLayout()
        self.today_layout.addLayout(today_btn_row)
        today_btn_row.addStretch(1)

        open_day = QPushButton('Open Day')
        open_day.clicked.connect(self.open_todos.emit)
        today_btn_row.addWidget(open_day)

        #weather
        self.weather_widget = WeatherWidget()
        self.weather_layout.addWidget(self.weather_widget, 1)

        #xp (only placeholder rn)
        self.xp_big = QLabel('☆ XP: —')
        self.xp_big.setStyleSheet(BIG_STYLE)
        self.xp_layout.addWidget(self.xp_big)

        self.xp_level = QLabel('Level: —')
        self.xp_next = QLabel('Next: —')
        self.xp_badges = QLabel('Badges: —')

        for lab in [self.xp_level, self.xp_next, self.xp_badges]:
            lab.setStyleSheet(MID_STYLE)
            self.xp_layout.addWidget(lab)

        xp_btn_row = QHBoxLayout()
        self.xp_layout.addLayout(xp_btn_row)
        xp_btn_row.addStretch(1)

        xp_button = QPushButton('Open XP')
        xp_button.setEnabled(False)
        xp_btn_row.addWidget(xp_button)

        #recent activity tile 
        self.activity_list = QListWidget()
        self.activity_list.setStyleSheet(
            '''
            QListWidget {
                border: none;
                background: transparent;
            }
            QListWidget::item {
                padding: 8px 4px;
                border-bottom: 1px solid #eeeeee;
            }
            '''
        )
        self.activity_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.activity_layout.addWidget(self.activity_list, 1)

        #quick action bar
        actions_row = QHBoxLayout()
        actions_row.setSpacing(10)
        self.actions_layout.addLayout(actions_row)

        add_todo = QPushButton('+ Todo (Today)')
        add_todo.clicked.connect(self.add_todo_today.emit)
        actions_row.addWidget(add_todo)

        open_calendar = QPushButton('Open Calendar')
        open_calendar.clicked.connect(self.open_calendar.emit)
        actions_row.addWidget(open_calendar)

        open_manager = QPushButton('Open Manager')
        open_manager.clicked.connect(self.open_manager.emit)
        actions_row.addWidget(open_manager)

        add_tx = QPushButton('+ Transaction')
        add_tx.clicked.connect(self.add_transaction.emit)
        actions_row.addWidget(add_tx)

        actions_row.addStretch(1)

    def make_tile(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame()
        frame.setStyleSheet(
            '''
            QFrame {
                background: #ffffff;
                border: 1px solid #d9d9d9;
                border-radius: 12px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
            '''
        )

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        header = QLabel(title)
        header.setStyleSheet('font-weight: 900; font-size: 14px; color: #111;')
        layout.addWidget(header)

        return frame, layout

    def build_finance_chart(self):
        self.income_set = QBarSet('Income')
        self.expense_set = QBarSet('Expenses')

        #blue and orange rn, maybe change to red and green but then it would be best to have a colorblind mode (maybe it also doesnt matter cause up/down should be clear anyway)
        self.income_set.setColor(QColor('#3b82f6'))   
        self.expense_set.setColor(QColor('#f59e0b'))  

        series = QBarSeries()
        series.append(self.income_set)
        series.append(self.expense_set)

        chart = QChart()
        chart.addSeries(series)
        chart.legend().hide()
        chart.setBackgroundVisible(False)
        chart.setPlotAreaBackgroundVisible(False)

        axis_x = QBarCategoryAxis()
        axis_x.append(['Current Month'])

        axis_y = QValueAxis()
        axis_y.setLabelsVisible(False)
        axis_y.setGridLineVisible(True)
        axis_y.setTickCount(5)
        axis_y.setRange(-100, 100)

        chart.addAxis(axis_x, Qt.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)

        self.chart = chart
        self.axis_y = axis_y

        self.chart_view = QChartView(chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)

    def refresh(self):
        self.day = dt_date.today().isoformat()
        self.date_label.setText(self.day)

        connection = connect_db()

        todos_today = list_todos_for_day(connection, self.day)
        total_todos = len(todos_today)
        done_todos = sum(1 for t in todos_today if t['completed'])

        journal_text = get_journal_entry(connection, self.day) or ''
        journal_mark = '✓' if journal_text.strip() else '-'

        habits = list_active_habits(connection)
        daily = [h for h in habits if h['frequency'] == 'daily']
        weekly = [h for h in habits if h['frequency'] == 'weekly']

        daily_done = sum(1 for h in daily if is_daily_done(connection, h['id'], self.day))

        weekly_done = 0
        for h in weekly:
            done, target = get_weekly_progress(connection, h['id'], self.day)
            if target and done >= target:
                weekly_done += 1

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

        #list for next todos, fetching from backlog if not enough available (<4)
        next_items = []
        for t in todos_today:
            if not t['completed']:
                next_items.append(('today', t['title']))
        if len(next_items) < 4:
            all_todos = list_all_todos(connection)
            for t in all_todos:
                if t.get('date') is None and not t.get('completed'):
                    next_items.append(('backlog', t['title']))
                if len(next_items) >= 4:
                    break

        #finance info, maybe only refresh this on app start?
        today = dt_date.fromisoformat(self.day)
        start_month = dt_date(today.year, today.month, 1).isoformat()

        series_data = get_timeseries_data(
            connection=connection,
            start_date=start_month,
            end_date=self.day,
            aggregation='day',
        )

        income_total = 0.0
        expenses_total = 0.0
        for row in series_data:
            income_total += float(row.get('income', 0) or 0)
            expenses_total += float(row.get('expenses', 0) or 0)  

        net = income_total + expenses_total

        recent = list_recent_transactions(connection, limit=6)

        connection.close()

        #day view info update
        self.today_todos.setText(f'📝 {done_todos}/{total_todos}' if total_todos else '📝 -')

        habits_parts = []
        if daily:
            habits_parts.append(f'D {daily_done}/{len(daily)}')
        if weekly:
            habits_parts.append(f'W {weekly_done}/{len(weekly)}')
        self.today_habits.setText(('🔁 ' + '  |  '.join(habits_parts)) if habits_parts else '🔁 -')

        self.today_journal.setText(f'📓 {journal_mark}')
        self.today_streak.setText(f'🔥 D{best_daily}  W{best_weekly}' if (best_daily or best_weekly) else '🔥 -')

        #todo list update
        self.next_list.clear()
        if not next_items:
            item = QListWidgetItem('No open todos ')
            self.next_list.addItem(item)
        else:
            for kind, title in next_items[:4]:
                prefix = '• '
                if kind == 'backlog':
                    prefix = '• (backlog) '
                self.next_list.addItem(QListWidgetItem(prefix + title))

        #finance text update
        self.finance_net.setText(f'Net: {net:,.2f}')
        self.finance_lines.setText(f'Income: {income_total:,.2f}\nExpenses: {expenses_total:,.2f}')

        #chart update
        self.income_set.remove(0, self.income_set.count())
        self.expense_set.remove(0, self.expense_set.count())

        self.income_set.append(float(income_total))
        self.expense_set.append(float(expenses_total))  # negative => down

        max_abs = max(abs(income_total), abs(expenses_total), 10.0)
        self.axis_y.setRange(-max_abs * 1.15, max_abs * 1.15)

        #recent activity update
        self.activity_list.clear()
        if not recent:
            self.activity_list.addItem(QListWidgetItem('No recent finance activity.'))
        else:
            for tx in recent:
                day = tx.get('tx_date') or ''
                amount = float(tx.get('amount') or 0)
                name = (tx.get('name') or '').strip()
                desc = (tx.get('description') or '').strip()

                label = name if name else desc
                if not label:
                    label = '(no description)'

                sign = '+' if amount > 0 else ''
                text = f'{day}   {sign}{amount:,.2f}   {label}'
                self.activity_list.addItem(QListWidgetItem(text))
        
        #weather update
        self.weather_widget.refresh()
    
    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.refresh()
    
