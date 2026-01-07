from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolButton, QButtonGroup,
    QFrame, QSizePolicy, QToolTip, QTableWidget, QTableWidgetItem, QCheckBox
)
from PySide6.QtCharts import (
    QChart, QChartView, QBarSet, QBarCategoryAxis, QValueAxis, QStackedBarSeries,
    QHorizontalBarSeries
)
from PySide6.QtGui import QPainter, QColor, QCursor, QShowEvent

from datetime import date, timedelta, datetime

from helpers.db import db_session
from db.finance import get_timeseries_data, list_transactions, sync_recurring_transactions

from helpers.currency import format_jpy
from helpers.dates import last_day_of_month

class FinanceDashboardView(QWidget):
    def __init__(self):
        super().__init__()

        self.default_range = 'M'
        self.window_offset = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # header row
        header = QHBoxLayout()
        header.setSpacing(8)

        title = QLabel('Dashboard')
        title.setStyleSheet('font-size: 18px; font-weight: 600;')
        header.addWidget(title)

        header.addStretch(1)

        # checkbox first
        self.hide_recurring_cb = QCheckBox('hide recurring')
        self.hide_recurring_cb.setChecked(False)  # default for M
        header.addWidget(self.hide_recurring_cb)

        # timeframe buttons next
        self.range_group = QButtonGroup(self)
        self.range_group.setExclusive(True)

        self.button_d = self.make_range_button('D')
        self.button_w = self.make_range_button('W')
        self.button_m = self.make_range_button('M', checked=True)
        self.button_y = self.make_range_button('Y')

        for i, b in enumerate([self.button_d, self.button_w, self.button_m, self.button_y]):
            self.range_group.addButton(b, i)
            header.addWidget(b)

        # arrows after timeframe
        self.prev_btn = QToolButton()
        self.prev_btn.setText('◀')
        self.prev_btn.setToolTip('previous')
        header.addWidget(self.prev_btn)

        self.next_btn = QToolButton()
        self.next_btn.setText('▶')
        self.next_btn.setToolTip('next')
        header.addWidget(self.next_btn)

        # range label far right
        self.range_label = QLabel('—')
        self.range_label.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.range_label.setStyleSheet('color: #666; padding-left: 8px;')
        self.range_label.setFixedWidth(160)
        header.addWidget(self.range_label)


        root.addLayout(header)

        # summary cards
        summary_row = QHBoxLayout()
        summary_row.setSpacing(12)

        self.summary_income, self.summary_income_value = self.make_summary_card('Income', '—')
        self.summary_expense, self.summary_expense_value = self.make_summary_card('Expenses', '—')
        self.summary_net, self.summary_net_value = self.make_summary_card('Net', '—')

        summary_row.addWidget(self.summary_income)
        summary_row.addWidget(self.summary_expense)
        summary_row.addWidget(self.summary_net)
        root.addLayout(summary_row)

        # cashflow chart
        self.timeseries_frame = self.make_panel('Cashflow over time')
        self.timeseries_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self.timeseries_frame, stretch=3)

        # bottom row
        bottom = QHBoxLayout()
        bottom.setSpacing(12)

        self.category_frame = self.make_panel('Expenses by Category')
        self.category_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        latest_frame = self.make_panel('Latest Transactions')
        latest_layout = latest_frame.layout()

        self.latest_table = self.make_latest_table()
        latest_layout.addWidget(self.latest_table)

        bottom.addWidget(self.category_frame, stretch=2)
        bottom.addWidget(latest_frame, stretch=1)

        root.addLayout(bottom, stretch=2)

        # styling
        self.setStyleSheet(
            '''
            QFrame#panel {
                border: 1px solid #d0d0d0;
                border-radius: 10px;
                background: #ffffff;
            }
            QLabel#panelTitle {
                font-weight: 600;
            }
            QToolButton[rangeButton='true'] {
                padding: 4px 10px;
                border: 1px solid #c9c9c9;
                border-radius: 8px;
                background: transparent;
            }
            QToolButton[rangeButton='true']:checked {
                background: #e9e9e9;
                border: 1px solid #9f9f9f;
                font-weight: 600;
            }
            '''
        )

        # cashflow chart view
        self.cashflow_chart_view = QChartView()
        self.cashflow_chart_view.setRenderHint(QPainter.Antialiasing)
        self.timeseries_frame.layout().addWidget(self.cashflow_chart_view, stretch=1)

        # category chart view
        self.category_chart_view = QChartView()
        self.category_chart_view.setRenderHint(QPainter.Antialiasing)
        self.category_frame.layout().addWidget(self.category_chart_view, stretch=1)

        # signals
        self.range_group.buttonClicked.connect(self.timeframe_clicked)
        self.prev_btn.clicked.connect(self.shift_prev)
        self.next_btn.clicked.connect(self.shift_next)
        self.hide_recurring_cb.stateChanged.connect(self.hide_recurring_changed)

        # initial
        self.refresh(self.default_range)

    # ui helpers
    def make_range_button(self, text: str, checked: bool = False) -> QToolButton:
        b = QToolButton()
        b.setText(text)
        b.setCheckable(True)
        b.setChecked(checked)
        b.setProperty('rangeButton', True)
        return b

    def make_summary_card(self, title: str, value: str) -> tuple[QFrame, QLabel]:
        frame = QFrame()
        frame.setObjectName('panel')
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)

        label_title = QLabel(title)
        label_title.setStyleSheet('color: #666;')

        label_value = QLabel(value)
        if title == 'Net':
            label_value.setStyleSheet('font-size: 22px; font-weight: 800;')
        else:
            label_value.setStyleSheet('font-size: 20px; font-weight: 700;')

        layout.addWidget(label_title)
        layout.addWidget(label_value)
        layout.addStretch(1)
        return frame, label_value

    def make_panel(self, title: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName('panel')
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        label = QLabel(title)
        label.setObjectName('panelTitle')
        layout.addWidget(label)

        return frame

    def make_latest_table(self) -> QTableWidget:
        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(['Date', 'Amount', 'Name', 'Category', 'Info'])
        table.horizontalHeader().setStretchLastSection(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.verticalHeader().setVisible(False)
        return table

    # header interactions
    def current_timeframe(self) -> str:
        b = self.range_group.checkedButton()
        return b.text() if b else self.default_range

    def hide_recurring_changed(self) -> None:
        self.refresh(self.current_timeframe())

    def timeframe_clicked(self, button) -> None:
        self.window_offset = 0
        tf = button.text()

        # default checkbox behavior
        if tf in ('D', 'W'):
            self.hide_recurring_cb.setChecked(True)
        else:
            self.hide_recurring_cb.setChecked(False)

        self.refresh(tf)

    def shift_prev(self) -> None:
        self.window_offset += 1
        self.refresh(self.current_timeframe())

    def shift_next(self) -> None:
        if self.window_offset == 0:
            return
        self.window_offset -= 1
        self.refresh(self.current_timeframe())

    # logic
    def refresh(self, timeframe: str) -> None:
        start_date, end_date = self.timeframe_to_dates(timeframe, self.window_offset)
        aggregation = self.aggregation_for_timeframe(timeframe)
        exclude = self.hide_recurring_cb.isChecked()

        self.range_label.setText(self.format_range_label(timeframe, start_date, end_date))
        self.next_btn.setEnabled(self.window_offset > 0)

        with db_session() as connection:

            #recurring up to date
            sync_recurring_transactions(connection, rule_id=None, up_to_date=end_date)

            timeseries_data = get_timeseries_data(
                connection,
                start_date,
                end_date,
                aggregation,
                exclude_recurring=exclude,
            )

            keys = agg_keys(start_date, end_date, aggregation)
            labels = make_labels_unique(short_labels(timeframe, keys, aggregation))
            tooltips = tooltips_for_agg(keys, aggregation)

            income, expenses, net = merge_timeseries(keys, timeseries_data)

            self.update_summary(sum(income), sum(expenses))
            self.update_cashflow_chart(labels, income, expenses, net, tooltips)

            self.update_category_bars(connection, start_date, end_date, exclude_recurring=exclude)
            self.refresh_latest_transactions(connection=connection, exclude_recurring=exclude)


    @staticmethod
    def format_range_label(timeframe: str, start_date: str, end_date: str) -> str:
        s = parse_date(start_date)
        e = parse_date(end_date)

        if timeframe in ('D', 'W'):
            return f'{s.strftime("%d %b %Y")} – {e.strftime("%d %b %Y")}'
        if timeframe == 'M':
            return f'{s.strftime("%b %Y")} – {e.strftime("%b %Y")}'
        if timeframe == 'Y':
            return f'{s.strftime("%Y")} – {e.strftime("%Y")}'
        return f'{s.isoformat()} – {e.isoformat()}'

    @staticmethod
    def timeframe_to_dates(timeframe: str, offset: int) -> tuple[str, str]:
        today = date.today()

        # d: 14 days window
        if timeframe == 'D':
            end = today - timedelta(days=offset * 14)
            start = end - timedelta(days=13)
            return start.isoformat(), end.isoformat()

        # w: 12 weeks window
        if timeframe == 'W':
            end = today - timedelta(days=offset * 7 * 12)
            start = end - timedelta(days=7 * 12 - 1)
            return start.isoformat(), end.isoformat()

        # m: 12 months window
        if timeframe == 'M':
            end = today.replace(day=1)
            for _ in range(offset * 12):
                end = prev_month_start(end)
            start = end
            for _ in range(11):
                start = prev_month_start(start)
            end_last_day = last_day_of_month(end.year, end.month)
            return start.isoformat(), end_last_day.isoformat()

        # y: 5 years window
        if timeframe == 'Y':
            end_year = today.year - (offset * 5)
            start_year = end_year - 4
            start = date(start_year, 1, 1)
            end = date(end_year, 12, 31)
            return start.isoformat(), end.isoformat()

        end = today
        start = today - timedelta(days=7 * 11)
        return start.isoformat(), end.isoformat()

    @staticmethod
    def aggregation_for_timeframe(timeframe: str) -> str:
        if timeframe == 'D':
            return 'day'
        if timeframe == 'W':
            return 'week'
        if timeframe == 'M':
            return 'month'
        if timeframe == 'Y':
            return 'year'
        return 'week'

    # charts
    def update_cashflow_chart(
        self,
        labels: list[str],
        income: list[float],
        expense: list[float],
        net: list[float],
        tooltips: list[str],
    ) -> None:
        chart = self.build_cashflow_chart(labels, income, expense, net, tooltips)
        self.cashflow_chart_view.setChart(chart)

    def build_cashflow_chart(
        self,
        labels: list[str],
        income: list[float],
        expenses: list[float],
        net: list[float],
        tooltips: list[str],
    ) -> QChart:
        income_set = QBarSet('Income')
        expense_set = QBarSet('Expenses')

        for val in income:
            income_set.append(val)
        for val in expenses:
            expense_set.append(val)

        stacked = QStackedBarSeries()
        stacked.append(income_set)
        stacked.append(expense_set)
        stacked.setBarWidth(0.8)

        income_set.setBorderColor(Qt.transparent)
        expense_set.setBorderColor(Qt.transparent)

        income_set.setColor(QColor(0, 120, 215, 160))
        expense_set.setColor(QColor(200, 70, 70, 150))

        chart = QChart()
        chart.setTheme(QChart.ChartThemeLight)
        chart.setAnimationOptions(QChart.NoAnimation)
        chart.setBackgroundVisible(False)

        chart.addSeries(stacked)

        axis_x = QBarCategoryAxis()
        axis_x.append(labels)

        axis_y = QValueAxis()
        axis_y.setLabelFormat('%.0f')
        axis_y.setTickCount(6)

        min_y, max_y = nice_range(income, expenses)
        axis_y.setRange(min_y, max_y)

        chart.addAxis(axis_x, Qt.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignLeft)

        stacked.attachAxis(axis_x)
        stacked.attachAxis(axis_y)

        def show_tip(index: int):
            if not (0 <= index < len(tooltips)):
                return

            inc = income[index]
            exp = expenses[index]
            net_val = inc + exp
            base = tooltips[index]

            text = (
                f'{base}\n'
                f'Income: {format_money(inc)}\n'
                f'Expenses: {format_money(exp)}\n'
                f'Net: {format_money(net_val)}'
            )

            QToolTip.showText(
                QCursor.pos(),
                text,
                self.cashflow_chart_view,
                self.cashflow_chart_view.rect(),
                10000
            )

        def hovered(status: bool, index: int):
            if status:
                show_tip(index)

        income_set.hovered.connect(hovered)
        expense_set.hovered.connect(hovered)

        return chart

    def update_category_bars(self, connection, start_date: str, end_date: str, exclude_recurring: bool) -> None:
        rows = list_transactions(
            connection,
            start_date=start_date,
            end_date=end_date,
            tx_type="Expenses",
            limit=5000,
            exclude_recurring=exclude_recurring,
        )

        totals: dict[str, float] = {}
        total_exp = 0.0

        for r in rows:
            cat = r.get("category") or "Uncategorized"
            amt = float(r.get("amount") or 0.0)
            if amt >= 0:
                continue
            v = abs(amt)
            totals[cat] = totals.get(cat, 0.0) + v
            total_exp += v

        items = sorted(totals.items(), key=lambda x: x[1], reverse=True)
        top = items[:5]
        other_sum = sum(v for _, v in items[5:])

        labels = [c for c, _ in top]
        values = [v for _, v in top]

        labels.append("Other")
        values.append(other_sum)

        if total_exp <= 0:
            labels = ["—", "", "", "", "", ""]
            perc = [0, 0, 0, 0, 0, 0]
        else:
            perc = [(v / total_exp) * 100.0 for v in values]

        # reverse so biggest is on top and other stays bottom
        labels.reverse()
        perc.reverse()

        bar_set = QBarSet("%")
        bar_set.setColor(QColor(0, 120, 215, 170))
        for p in perc:
            bar_set.append(float(p))

        series = QHorizontalBarSeries()
        series.append(bar_set)

        chart = QChart()
        chart.setBackgroundVisible(False)
        chart.addSeries(series)
        chart.legend().setVisible(False)
        #chart.setMargins(QMargins(140, 20, 20, 20))
    
        axis_y = QBarCategoryAxis()
        axis_y.append(labels)
        
        #to show full labels even when not fullscreen
        f = axis_y.labelsFont()
        f.setPointSize(max(8, f.pointSize() - 2))
        axis_y.setLabelsFont(f)


        axis_x = QValueAxis()
        axis_x.setRange(0, 100)
        axis_x.setLabelFormat('%.0f%%')
        axis_x.setTickCount(5)

        chart.addAxis(axis_y, Qt.AlignLeft)
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_y)
        series.attachAxis(axis_x)

        self.category_chart_view.setChart(chart)

    # summary + latest
    def update_summary(self, total_income: float, total_expenses: float) -> None:
        net = total_expenses + total_income

        self.summary_income_value.setText(format_jpy(total_income))
        self.summary_expense_value.setText(format_jpy(total_expenses))
        self.summary_net_value.setText(format_jpy(net))

        self.summary_expense_value.setStyleSheet('font-size: 20px; font-weight: 700; color: #c84646;')

        if net < 0:
            self.summary_net_value.setStyleSheet('font-size: 22px; font-weight: 800; color: #c84646;')
        else:
            self.summary_net_value.setStyleSheet('font-size: 22px; font-weight: 800;')

    def refresh_latest_transactions(self, limit: int = 10, connection=None, exclude_recurring: bool = False) -> None:
       

        rows = list_transactions(connection, tx_type='All', limit=limit, exclude_recurring=exclude_recurring)

        self.latest_table.setRowCount(len(rows))

        income_color = QColor(0, 120, 215)
        expense_color = QColor(200, 70, 70)

        for i, row in enumerate(rows):
            amt = float(row.get('amount') or 0.0)

            date_item = QTableWidgetItem(row.get('date') or '')
            amount_item = QTableWidgetItem(format_jpy(amt))
            name_item = QTableWidgetItem(row.get('name') or '-')
            category_item = QTableWidgetItem(row.get('category') or '-')
            info_item = QTableWidgetItem(row.get('info') or '-')

            color = income_color if amt >= 0 else expense_color
            amount_item.setForeground(color)

            self.latest_table.setItem(i, 0, date_item)
            self.latest_table.setItem(i, 1, amount_item)
            self.latest_table.setItem(i, 2, name_item)
            self.latest_table.setItem(i, 3, category_item)
            self.latest_table.setItem(i, 4, info_item)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.refresh(self.current_timeframe())


# label helpers
def parse_date(s: str) -> date:
    return datetime.strptime(s, '%Y-%m-%d').date()


def prev_month_start(d: date) -> date:
    if d.month == 1:
        return date(d.year - 1, 12, 1)
    return date(d.year, d.month - 1, 1)

def agg_keys(start_date: str, end_date: str, aggregation: str) -> list[str]:
    start = parse_date(start_date)
    end = parse_date(end_date)

    keys: list[str] = []

    if aggregation == 'day':
        d = start
        while d <= end:
            keys.append(d.isoformat())
            d += timedelta(days=1)
        return keys

    if aggregation == 'week':
        d = start - timedelta(days=start.weekday())
        while d <= end:
            keys.append(d.isoformat())
            d += timedelta(days=7)
        return keys

    if aggregation == 'month':
        d = start.replace(day=1)
        while d <= end:
            keys.append(d.isoformat())
            if d.month == 12:
                d = d.replace(year=d.year + 1, month=1, day=1)
            else:
                d = d.replace(month=d.month + 1, day=1)
        return keys

    if aggregation == 'year':
        d = date(start.year, 1, 1)
        while d <= end:
            keys.append(d.isoformat())
            d = date(d.year + 1, 1, 1)
        return keys

    raise ValueError(f'Invalid aggregation: {aggregation}')


def short_labels(timeframe: str, keys: list[str], aggregation: str) -> list[str]:
    labels: list[str] = []

    if aggregation == 'day':
        for k in keys:
            d = parse_date(k)
            labels.append(d.strftime('%a') if timeframe == 'D' else str(d.day))
        return labels

    if aggregation == 'week':
        prev_month = None
        for k in keys:
            d = parse_date(k)
            if prev_month != d.month:
                labels.append(d.strftime('%b'))
                prev_month = d.month
            else:
                labels.append('')
        return labels

    if aggregation == 'month':
        for k in keys:
            d = parse_date(k)
            labels.append(d.strftime('%b'))
        return labels

    if aggregation == 'year':
        for k in keys:
            d = parse_date(k)
            labels.append(d.strftime('%Y'))
        return labels

    raise ValueError(f'Invalid aggregation: {aggregation}')


def tooltips_for_agg(keys: list[str], aggregation: str) -> list[str]:
    tips: list[str] = []

    if aggregation == 'day':
        for k in keys:
            d = parse_date(k)
            tips.append(d.strftime('%a %Y-%m-%d'))
        return tips

    if aggregation == 'week':
        for k in keys:
            start = parse_date(k)
            end = start + timedelta(days=6)
            tips.append(f'Week: {start.isoformat()} – {end.isoformat()}')
        return tips

    if aggregation == 'month':
        for k in keys:
            d = parse_date(k)
            tips.append(d.strftime('%b %Y'))
        return tips

    if aggregation == 'year':
        for k in keys:
            d = parse_date(k)
            tips.append(d.strftime('%Y'))
        return tips

    raise ValueError(f'Invalid aggregation: {aggregation}')


def merge_timeseries(keys: list[str], rows: list[dict]) -> tuple[list[float], list[float], list[float]]:
    existing: dict[str, dict] = {row['label']: row for row in rows}

    income: list[float] = []
    expenses: list[float] = []
    net: list[float] = []

    for k in keys:
        row = existing.get(k)
        inc = float(row['income']) if row else 0.0
        exp = float(row['expenses']) if row else 0.0
        income.append(inc)
        expenses.append(exp)
        net.append(inc + exp)

    return income, expenses, net


def make_labels_unique(labels: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    out: list[str] = []
    zwsp = '\u200b'

    for lab in labels:
        lab_str = '' if lab is None else str(lab)
        count = seen.get(lab_str, 0)

        base = lab_str if lab_str != '' else zwsp

        if count == 0:
            out.append(base)
        else:
            out.append(base + (zwsp * count))

        seen[lab_str] = count + 1

    return out


def format_money(x: float) -> str:
    return f'{x:,.0f}'


def nice_range(income: list[float], expenses: list[float]) -> tuple[float, float]:
    if not income and not expenses:
        return -1.0, 1.0

    max_pos = max([0.0] + income)
    min_neg = min([0.0] + expenses)

    span = max_pos - min_neg
    if span <= 0:
        span = 1.0

    step = nice_step(span / 5.0)

    top = step * int((max_pos + step - 1) // step) if max_pos > 0 else step
    bot = -step * int((abs(min_neg) + step - 1) // step) if min_neg < 0 else -step

    if top == 0:
        top = step
    if bot == 0:
        bot = -step

    return bot, top


def nice_step(x: float) -> float:
    if x <= 0:
        return 1.0
    exp = 0
    while x >= 10:
        x /= 10
        exp += 1
    while x < 1:
        x *= 10
        exp -= 1

    if x <= 1:
        base = 1
    elif x <= 2:
        base = 2
    elif x <= 5:
        base = 5
    else:
        base = 10

    return float(base * (10 ** exp))
