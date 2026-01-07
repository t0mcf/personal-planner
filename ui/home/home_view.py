from datetime import date as dt_date
from datetime import datetime

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
    QProgressBar,
    QDialog,
    QInputDialog,
)

from PySide6.QtCharts import (
    QChart,
    QChartView,
    QBarSeries,
    QBarSet,
    QBarCategoryAxis,
    QValueAxis,
)

from db.todos import list_todos_for_day, list_all_todos, insert_todo
from db.journal import get_journal_entry
from db.habits import (
    list_active_habits,
    is_daily_done,
    get_weekly_progress,
    get_daily_streak,
    get_weekly_streak,
)
from db.finance import get_timeseries_data, list_recent_transactions, get_categories, insert_transaction

from ui.home.weather_widget import WeatherWidget

from db.xp import get_total_xp, level_for_total_xp, list_recent_xp_events
from ui.xp.level_badge import LevelBadge

from db.achievements import list_achievements, list_unlocked_ids
from ui.xp.achievement_grid import AchievementTile

from ui.todos.calendar_widget import CalendarWidget

from ui.dialogs.add_transaction_dialog import AddTransactionDialog
from ui.constants import DEFAULT_CATEGORIES

from helpers.db import db_session


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

    open_xp = Signal()
    open_day = Signal(str)

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

        top_row = QHBoxLayout()
        top_row.setSpacing(14)

        self.finance_tile, self.finance_layout = self.make_tile('Finance (Current Month)')
        self.finance_tile.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        right_col = QVBoxLayout()
        right_col.setSpacing(14)

        self.today_tile, self.today_layout = self.make_tile('Today')
        self.today_tile.setMinimumHeight(240)
        self.today_tile.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.weather_tile, self.weather_layout = self.make_tile('Weather')
        self.weather_tile.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        right_col.addWidget(self.today_tile, 0)
        right_col.addWidget(self.weather_tile, 1)

        top_row.addWidget(self.finance_tile, 1)
        top_row.addLayout(right_col, 1)

        layout.addLayout(top_row, 2)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(14)

        self.xp_tile, self.xp_layout = self.make_tile('Progression')
        self.xp_tile.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.xp_layout.setAlignment(Qt.AlignTop)

        self.activity_tile, self.activity_layout = self.make_tile('Recent activity')
        self.activity_tile.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        bottom_row.addWidget(self.xp_tile, 1)
        bottom_row.addWidget(self.activity_tile, 1)

        layout.addLayout(bottom_row, 1)

        self.actions_bar, self.actions_layout = self.make_tile('Quick actions')
        self.actions_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        layout.addWidget(self.actions_bar, 0)

        #finance 
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

        # today stats
        self.today_todos = QLabel('📝 -')
        self.today_habits = QLabel('🔁 -')
        self.today_journal = QLabel('📓 -')
        self.today_streak = QLabel('🔥 -')

        for lab in [self.today_todos, self.today_habits, self.today_journal, self.today_streak]:
            lab.setStyleSheet(STAT_STYLE)

        top_stats_row = QHBoxLayout()
        top_stats_row.setSpacing(14)
        top_stats_row.addWidget(self.today_todos)
        top_stats_row.addWidget(self.today_habits)
        top_stats_row.addStretch(1)
        self.today_layout.addLayout(top_stats_row)

        bottom_stats_row = QHBoxLayout()
        bottom_stats_row.setSpacing(14)
        bottom_stats_row.addWidget(self.today_journal)
        bottom_stats_row.addWidget(self.today_streak)
        bottom_stats_row.addStretch(1)
        self.today_layout.addLayout(bottom_stats_row)

        next_header = QLabel('Next')
        next_header.setStyleSheet('font-size: 13px; font-weight: 800; color: #666; margin-top: 6px;')
        self.today_layout.addWidget(next_header)

        next_row = QHBoxLayout()
        next_row.setSpacing(10)
        self.today_layout.addLayout(next_row)

        self.next_todos_list = QListWidget()
        self.next_todos_list.setStyleSheet(
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
        self.next_todos_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.next_todos_list.setMaximumHeight(140)

        self.next_habits_list = QListWidget()
        self.next_habits_list.setStyleSheet(
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
        self.next_habits_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.next_habits_list.setMaximumHeight(140)

        next_row.addWidget(self.next_todos_list, 1)
        next_row.addWidget(self.next_habits_list, 1)

        today_btn_row = QHBoxLayout()
        self.today_layout.addLayout(today_btn_row)
        today_btn_row.addStretch(1)

        open_day = QPushButton('Open Day')
        open_day.clicked.connect(self.open_todos.emit)
        today_btn_row.addWidget(open_day)

        # weather 
        self.weather_widget = WeatherWidget()
        self.weather_layout.addWidget(self.weather_widget, 1)

        # xp 
        xp_row = QHBoxLayout()
        xp_row.setSpacing(12)
        self.xp_layout.addLayout(xp_row)

        self.xp_badge = LevelBadge(1)
        self.xp_badge.setFixedSize(56, 56)
        xp_row.addWidget(self.xp_badge, 0, Qt.AlignTop)

        xp_right = QVBoxLayout()
        xp_right.setSpacing(6)
        xp_row.addLayout(xp_right, 1)

        self.xp_level_label = QLabel('level 1')
        self.xp_level_label.setStyleSheet('font-size: 20px; font-weight: 900;')
        xp_right.addWidget(self.xp_level_label)

        self.xp_progress = QProgressBar()
        self.xp_progress.setTextVisible(False)
        self.xp_progress.setFixedHeight(14)
        xp_right.addWidget(self.xp_progress)

        self.xp_progress_label = QLabel('0 / 100 xp   (total 0)')
        self.xp_progress_label.setStyleSheet('font-size: 13px; font-weight: 700; color: #666;')
        xp_right.addWidget(self.xp_progress_label)

        self.xp_hint_label = QLabel('')
        self.xp_hint_label.setStyleSheet('font-size: 12px; font-weight: 650; color: #666;')
        xp_right.addWidget(self.xp_hint_label)

        latest_header = QLabel('Latest achievements')
        latest_header.setStyleSheet('font-size: 13px; font-weight: 800; color: #666; margin-top: 6px;')
        xp_right.addWidget(latest_header)

        self.latest_achievement_container = QWidget()
        self.latest_achievement_layout = QHBoxLayout(self.latest_achievement_container)
        self.latest_achievement_layout.setContentsMargins(0, 0, 0, 0)
        self.latest_achievement_layout.setSpacing(10)
        xp_right.addWidget(self.latest_achievement_container, 0)

        self.latest_achievement_placeholder = QLabel('No achievements unlocked yet.')
        self.latest_achievement_placeholder.setStyleSheet('font-size: 12px; font-weight: 650; color: #666;')
        self.latest_achievement_layout.addWidget(self.latest_achievement_placeholder)

        self.achievement_count_label = QLabel('')
        self.achievement_count_label.setStyleSheet('font-size: 12px; font-weight: 650; color: #666;')
        xp_right.addWidget(self.achievement_count_label)

        xp_btn_row = QHBoxLayout()
        self.xp_layout.addLayout(xp_btn_row)
        xp_btn_row.addStretch(1)
        self.xp_layout.addStretch(1)

        xp_button = QPushButton('Open Progression Screen')
        xp_button.setEnabled(True)
        xp_button.clicked.connect(self.open_xp.emit)
        xp_btn_row.addWidget(xp_button)

        # recent activity 
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

        # quick actions
        actions_row = QHBoxLayout()
        actions_row.setSpacing(10)
        self.actions_layout.addLayout(actions_row)

        add_todo = QPushButton('+ Todo (Today)')
        add_todo.clicked.connect(self.open_add_todo_today)
        actions_row.addWidget(add_todo)

        open_calendar = QPushButton('Open Calendar')
        open_calendar.clicked.connect(self.open_calendar_dialog)
        actions_row.addWidget(open_calendar)

        add_tx = QPushButton('+ Transaction')
        add_tx.clicked.connect(self.open_add_transaction_dialog)
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

    def open_add_todo_today(self) -> None:
        text, confirmed = QInputDialog.getText(
            self,
            'Add Todo',
            'Todo:',
        )
        if not confirmed or not text.strip():
            return

        with db_session() as connection:
            insert_todo(connection, text.strip(), dt_date.today().isoformat())

        self.refresh()

    def open_calendar_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle('Calendar')
        dialog.resize(900, 650)

        layout = QVBoxLayout(dialog)

        calendar_widget = CalendarWidget(dt_date.today().isoformat())
        layout.addWidget(calendar_widget)

        chosen = {'day': None}

        def on_day(day: str):
            chosen['day'] = day
            dialog.accept()

        calendar_widget.day_selected.connect(on_day)

        if dialog.exec() and chosen['day']:
            self.open_day.emit(chosen['day'])

    def open_add_transaction_dialog(self) -> None:
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

        self.refresh()

    def _set_latest_achievements(self, rows: list[dict]) -> None:
        while self.latest_achievement_layout.count():
            item = self.latest_achievement_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not rows:
            self.latest_achievement_placeholder = QLabel('No achievements unlocked yet.')
            self.latest_achievement_placeholder.setStyleSheet('font-size: 12px; font-weight: 650; color: #666;')
            self.latest_achievement_layout.addWidget(self.latest_achievement_placeholder)
            return

        for r in rows[:2]:
            tile = AchievementTile(
                str(r.get("name") or ""),
                str(r.get("description") or ""),
                True,
                False,
            )
            self.latest_achievement_layout.addWidget(tile)

        self.latest_achievement_layout.addStretch(1)

    #maybe change to several helper methods but i guess it's still straightforward enough this way
    def refresh(self):
        self.day = dt_date.today().isoformat()
        self.date_label.setText(self.day)

        def _habit_label(h: dict) -> str:
            title = h.get("title") or ""
            emoji = (h.get("emoji") or "").strip()
            return f"{emoji} {title}" if emoji else title

        with db_session() as connection:
            todos_today = list_todos_for_day(connection, self.day)
            total_todos = len(todos_today)
            done_todos = sum(1 for t in todos_today if t.get("completed"))

            journal_text = get_journal_entry(connection, self.day) or ""
            journal_mark = "✓" if journal_text.strip() else "-"

            habits = list_active_habits(connection)
            daily = [h for h in habits if h.get("frequency") == "daily"]
            weekly = [h for h in habits if h.get("frequency") == "weekly"]

            #to avoid having to double get the data from db
            daily_done_map = {h["id"]: is_daily_done(connection, h["id"], self.day) for h in daily}
            weekly_prog_map = {h["id"]: get_weekly_progress(connection, h["id"], self.day) for h in weekly}

            daily_done = sum(1 for done in daily_done_map.values() if done)

            weekly_done = 0
            for h in weekly:
                done, target = weekly_prog_map[h["id"]]
                if target and done >= target:
                    weekly_done += 1

            best_daily = 0
            for h in daily:
                s = get_daily_streak(connection, h["id"], self.day)
                if s > best_daily:
                    best_daily = s

            best_weekly = 0
            for h in weekly:
                s = get_weekly_streak(connection, h["id"], self.day)
                if s > best_weekly:
                    best_weekly = s

            #build next todos list 
            next_todos: list[tuple[str, str]] = []
            for t in todos_today:
                if not t.get("completed"):
                    next_todos.append(("today", t.get("title") or ""))

            if len(next_todos) < 4:
                all_todos = list_all_todos(connection)
                for t in all_todos:
                    if t.get("date") is None and not t.get("completed"):
                        next_todos.append(("backlog", t.get("title") or ""))
                    if len(next_todos) >= 4:
                        break

            #next habits list 
            next_habits: list[str] = []

            for h in daily:
                if not daily_done_map[h["id"]]:
                    next_habits.append(_habit_label(h))

            for h in weekly:
                done, target = weekly_prog_map[h["id"]]
                if target and done < target:
                    next_habits.append(f"{_habit_label(h)} ({done}/{target})")

            today = dt_date.fromisoformat(self.day)
            start_month = dt_date(today.year, today.month, 1).isoformat()

            series_data = get_timeseries_data(
                connection=connection,
                start_date=start_month,
                end_date=self.day,
                aggregation="day",
            )

            income_total = 0.0
            expenses_total = 0.0
            for row in series_data:
                income_total += float(row.get("income", 0) or 0)
                expenses_total += float(row.get("expenses", 0) or 0)

            net = income_total + expenses_total

            total_xp = get_total_xp(connection)
            level, into, step = level_for_total_xp(total_xp)

            recent_xp = list_recent_xp_events(connection, limit=10)
            recent_tx = list_recent_transactions(connection, limit=10)

            achs = list_achievements(connection)
            unlocked = list_unlocked_ids(connection)

            latest_rows = connection.execute(
                """
                SELECT a.name, a.description, u.unlocked_at
                FROM achievements_unlocked u
                JOIN achievements a ON a.id = u.achievement_id
                ORDER BY datetime(u.unlocked_at) DESC
                LIMIT 2
                """
            ).fetchall()

        self.today_todos.setText(f"📝 {done_todos}/{total_todos}" if total_todos else "📝 -")

        habits_parts = []
        if daily:
            habits_parts.append(f"D {daily_done}/{len(daily)}")
        if weekly:
            habits_parts.append(f"W {weekly_done}/{len(weekly)}")
        self.today_habits.setText(("🔁 " + "  |  ".join(habits_parts)) if habits_parts else "🔁 -")

        self.today_journal.setText(f"📓 {journal_mark}")
        self.today_streak.setText(f"🔥 D{best_daily}  W{best_weekly}" if (best_daily or best_weekly) else "🔥 -")

        self.next_todos_list.clear()
        if not next_todos:
            self.next_todos_list.addItem(QListWidgetItem("No open todos"))
        else:
            for kind, title in next_todos[:4]:
                prefix = "• " if kind != "backlog" else "• (backlog) "
                self.next_todos_list.addItem(QListWidgetItem(prefix + title))

        self.next_habits_list.clear()
        if not next_habits:
            self.next_habits_list.addItem(QListWidgetItem("No open habits"))
        else:
            for title in next_habits[:4]:
                self.next_habits_list.addItem(QListWidgetItem("• " + title))

        self.finance_net.setText(f"Net: {net:,.2f}")
        self.finance_lines.setText(f"Income: {income_total:,.2f}\nExpenses: {expenses_total:,.2f}")

        self.income_set.remove(0, self.income_set.count())
        self.expense_set.remove(0, self.expense_set.count())

        self.income_set.append(float(income_total))
        self.expense_set.append(float(expenses_total))

        max_abs = max(abs(income_total), abs(expenses_total), 10.0)
        self.axis_y.setRange(-max_abs * 1.15, max_abs * 1.15)

        items: list[tuple[object, str]] = []

        for tx in recent_tx:
            created = tx.get("created_at")
            amount = float(tx.get("amount") or 0)
            name = (tx.get("name") or "").strip()
            desc = (tx.get("description") or "").strip()

            label = name or desc or "transaction"
            sign = "+" if amount > 0 else ""
            text = f"💰 {sign}{amount:,.2f} • {label}"
            items.append((parse_dt(None, created), text))

        for e in recent_xp:
            xp = int(e.get("xp_amount") or 0)
            msg = (e.get("message") or "").strip()
            sign = "+" if xp > 0 else ""
            text = f"⭐ {sign}{xp} xp • {msg}"
            items.append((parse_dt(None, e.get("created_at")), text))

        items.sort(key=lambda x: x[0], reverse=True)
        self.activity_list.clear()

        if not items:
            self.activity_list.addItem(QListWidgetItem("No recent activity."))
        else:
            for _, text in items[:10]:
                self.activity_list.addItem(QListWidgetItem(text))

        self.weather_widget.refresh()

        self.xp_badge.set_level(level)
        self.xp_level_label.setText(f"level {level}")

        self.xp_progress.setMaximum(step)
        self.xp_progress.setValue(into)
        self.xp_progress_label.setText(f"{into} / {step} xp   (total {total_xp})")

        self._set_latest_achievements([dict(r) for r in latest_rows])

        total_ach = len(achs)
        unlocked_count = len(unlocked)
        self.achievement_count_label.setText(
            f"{unlocked_count}/{total_ach} achievements unlocked" if total_ach else ""
        )

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.refresh()


def parse_dt(date_str: str | None, time_str: str | None = None) -> datetime:
    if time_str:
        s = time_str.strip()
    else:
        s = (date_str or "").strip()

    if not s:
        return datetime(1970, 1, 1)

    try:
        return datetime.fromisoformat(s)
    except ValueError:
        try:
            return datetime.fromisoformat(s + " 00:00:00")
        except ValueError:
            return datetime(1970, 1, 1)
