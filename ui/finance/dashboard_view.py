from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolButton, QButtonGroup,
    QFrame, QListWidget, QSizePolicy, QToolTip
)
from PySide6.QtCharts import(
    QChart, QChartView, QBarSet, QBarCategoryAxis, QValueAxis, QStackedBarSeries
)

from PySide6.QtGui import QPainter, QColor, QCursor
from datetime import date, timedelta, datetime

from db import connect_db, get_timeseries_data


class FinanceDashboardView(QWidget):
    def __init__(self):
        super().__init__()
        
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # header row for timeframe selection
        header = QHBoxLayout()
        header.setSpacing(8)

        title = QLabel('Dashboard')
        title.setStyleSheet('font-size: 18px; font-weight: 600;')
        header.addWidget(title)

        header.addStretch(1)

        self.range_group = QButtonGroup(self)
        self.range_group.setExclusive(True)

        self.button_w = self.make_range_button('W', checked=True) #default checked
        self.button_m = self.make_range_button('M')
        self.button_6m = self.make_range_button('6M')
        self.button_y = self.make_range_button('Y')
        self.button_all = self.make_range_button('All')

        for i, b in enumerate([self.button_w, self.button_m, self.button_6m, self.button_y, self.button_all]):
            self.range_group.addButton(b, i)
            header.addWidget(b)

        root.addLayout(header)

        #summary for selected tf
        summary_row = QHBoxLayout()
        summary_row.setSpacing(12)

        self.summary_income, self.summary_income_value = self.make_summary_card('Income', '—')
        self.summary_expense, self.summary_expense_value = self.make_summary_card('Expenses', '—')
        self.summary_net, self.summary_net_value = self.make_summary_card('Net', '—')

        summary_row.addWidget(self.summary_income)
        summary_row.addWidget(self.summary_expense)
        summary_row.addWidget(self.summary_net)
        root.addLayout(summary_row)

        #big chart placeholder
        self.timeseries_frame = self.make_panel('Cashflow over time')
        self.timeseries_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self.timeseries_frame, stretch=3)

        #bottom row with space for category chart and latest tx lists
        bottom = QHBoxLayout()
        bottom.setSpacing(12)

        self.pie_frame = self.make_panel('Expenses by Category')
        self.pie_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        latest_frame = self.make_panel('Latest Transactions')
        latest_layout = latest_frame.layout()

        latest_layout.addWidget(QLabel('Latest Income'))
        self.latest_income = QListWidget()
        latest_layout.addWidget(self.latest_income)

        latest_layout.addWidget(QLabel('Latest Expenses'))
        self.latest_expense = QListWidget()
        latest_layout.addWidget(self.latest_expense)

        bottom.addWidget(self.pie_frame, stretch=2)
        bottom.addWidget(latest_frame, stretch=1)

        root.addLayout(bottom, stretch=2)

        #placeholder
        self.range_group.buttonClicked.connect(self.timeframe_clicked)

        # TEST placehodler
        self.latest_income.addItems(['+50.00  Salary', '+12.00  Refund'])
        self.latest_expense.addItems(['-5.00   Groceries', '-9.99  Subscription'])


        #styling, subject to change
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
            ''')
        
        #building chart
        self.cashflow_chart_view = QChartView()
        self.cashflow_chart_view.setRenderHint(QPainter.Antialiasing)
        
        self.timeseries_frame.layout().addWidget(self.cashflow_chart_view, stretch=1)
        
        self.refresh('W') #cause we use W as default, better to make more robust with default var. later


    #_________ UI creation functions _____________
    def make_range_button(self, text: str, checked: bool = False) -> QToolButton:
        b = QToolButton()
        b.setText(text)
        b.setCheckable(True)
        b.setChecked(checked)
        b.setProperty('rangeButton', True)
        return b

    def make_summary_card(self, title: str, value: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName('panel')
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)

        label_title = QLabel(title)
        label_title.setStyleSheet('color: #666;')
        label_value = QLabel(value)
        label_value.setStyleSheet('font-size: 20px; font-weight: 700;')

        layout.addWidget(label_title)
        layout.addWidget(label_value)
        layout.addStretch(1)
        return frame, label_value


    def make_panel(self, title: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName('panel')
        layout =  QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        label = QLabel(title)
        label.setObjectName('panelTitle')
        layout.addWidget(label)

        return frame


    #______ logic / charts ______
    def timeframe_clicked(self, button) -> None:
        timeframe = button.text()
        self.refresh(timeframe)
        pass

    def aggregation_for_timeframe(self, timeframe: str) -> str:
        if timeframe in ('W', 'M'):
            return 'day'
        if timeframe == '6M':
            return 'week'
        return 'month' #maybe add yearly for 'All time' timeframe with >= 2-3 yrs of data
    
    
    def update_cashflow_chart(
        self,
        labels: list[str],
        income: list[float],
        expense: list[float],
        net: list[float],
        tooltips: list[str],
        ) -> None:

        chart = self.build_cashflow_chart(
            labels,
            income,
            expense,
            net,
            tooltips,
        )

        self.cashflow_chart_view.setChart(chart)

        
    def refresh(self, timeframe: str):
        start_date, end_date = self.timeframe_to_dates(timeframe)
        aggregation = self.aggregation_for_timeframe(timeframe)
        
        connection = connect_db()
        
        timeseries_data = get_timeseries_data(connection, start_date, end_date, aggregation)
        keys = agg_keys(start_date, end_date, aggregation)

        labels = short_labels(timeframe, keys, aggregation)
        labels = make_labels_unique(labels)
        tooltips = tooltips_for_agg(timeframe, keys, aggregation)
        
        income, expenses, net = merge_timeseries(keys, timeseries_data)
        total_income = sum(income)
        total_expenses = sum(expenses)
        self.update_summary(total_income, total_expenses)

        connection.close()
        
        self.update_cashflow_chart(labels, income, expenses, net, tooltips)
        
    @staticmethod
    def timeframe_to_dates(timeframe: str): 
        today = date.today()
        end_date = today.isoformat()
        
        #maybe change this to a more sophisticated logic but for now should be fine 
        if timeframe == 'W':
            start = today - timedelta(days=6)
            return start.isoformat(), end_date

        if timeframe == 'M':
            start = today - timedelta(days=30)
            return start.isoformat(), end_date
        
        if timeframe == '6M':
            start = today - timedelta(days=182)
            return start.isoformat(), end_date
        
        if timeframe == 'Y':
            start = today - timedelta(days=364)
            return start.isoformat(), end_date
        
        if timeframe == 'All':
            return None, None
        
        return None, None 
    
    def build_cashflow_chart(self, labels: list[str], income: list[float], expenses: list[float], net: list[float], tooltips: list[str]) -> QChart:

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
        
        # coloring to make bg more transparent
        income_set.setColor(QColor(0, 120, 215, 140))
        expense_set.setColor(QColor(120, 200, 60, 140))

        chart = QChart()

        chart.setTheme(QChart.ChartThemeLight)
        chart.setAnimationOptions(QChart.NoAnimation)
        chart.setBackgroundVisible(False)
        
        chart.addSeries(stacked)

        axis_x = QBarCategoryAxis()
        axis_x.append(labels)        
        axis_y = QValueAxis()
        chart.addAxis(axis_x, Qt.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignLeft)
        stacked.attachAxis(axis_x)
        stacked.attachAxis(axis_y)

        def show_tip(index: int):
            if not (0 <= index < len(tooltips)):
                return
            
            inc = income[index]
            exp = expenses[index]
            net = inc + exp
            base = tooltips[index]
            
            text = (
                f'{base}\n'
                f'Income: {inc:,.2f}\n'
                f'Expenses: {exp:,.2f}\n'
                f'Net: {net:,.2f}'
            )
            
            #tried to add stuff to show longer but didnt work - fix this!
            QToolTip.showText(
                QCursor.pos(), 
                text,
                self.cashflow_chart_view,
                self.cashflow_chart_view.rect(),
                10000
                )
            
        def hovered(status: bool, index: int):
            if not status:
                return
            show_tip(index)

        income_set.hovered.connect(hovered)
        expense_set.hovered.connect(hovered)

        return chart
    
    
    #for summary cards at top
    def update_summary(self, total_income: float, total_expenses: float) -> None:
        net = total_expenses + total_income
        
        self.summary_income_value.setText(f'{total_income:,.2f}')
        self.summary_expense_value.setText(f'{total_expenses:,.2f}')
        self.summary_net_value.setText(f'{net:,.2f}')

    


#the following functions help create better labels (was super inconvenient at initial attempt)
    
def parse_date(s: str) -> date:
    return datetime.strptime(s, '%Y-%m-%d').date()

def agg_keys(start_date: str, end_date: str, aggregation: str) -> list[str]:
    start = parse_date(start_date)
    end = parse_date(end_date)

    keys: list[str] = []

    if aggregation == 'day':
        date = start
        while date <= end:
            keys.append(date.isoformat())
            date += timedelta(days=1)
        return keys

    if aggregation == 'week':
        # align start to monday
        date = start - timedelta(days=start.weekday())
        while date <= end:
            keys.append(date.isoformat())  # monday
            date += timedelta(days=7)
        return keys

    if aggregation == 'month':
        date = start.replace(day=1)
        while date <= end:
            keys.append(date.isoformat())  # first of month
            # next month (no extra libs)
            if date.month == 12:
                date = date.replace(year=date.year + 1, month=1, day=1)
            else:
                date = date.replace(month=date.month + 1, day=1)
        return keys

    raise ValueError(f'Invalid aggregation: {aggregation}')


def short_labels(timeframe: str, keys: list[str], aggregation: str) -> list[str]:
    labels: list[str] = []

    if aggregation == 'day':
        for k in keys:
            date = parse_date(k)
            if timeframe == 'W':
                labels.append(date.strftime('%a'))   # mon/tue/etc
            else:
                labels.append(date.day)         # 14./31./etc
        return labels

    if aggregation == 'week':
        # show month label only when month changes (rest empty)
        prev_month = None
        for k in keys:
            date = parse_date(k)
            if prev_month != date.month:
                labels.append(date.strftime('%b'))  # jun/jul...
                prev_month = date.month
            else:
                labels.append('')
        return labels

    if aggregation == 'month':
        for k in keys:
            date = parse_date(k)
            labels.append(date.strftime('%b'))  # jan/feb/...
        return labels

    raise ValueError(f'Invalid aggregation: {aggregation}')


#tooltips for hovering in plot

def tooltips_for_agg(timeframe: str, keys: list[str], aggregation: str) -> list[str]:
    tips: list[str] = []

    if aggregation == 'day':
        for k in keys:
            date = parse_date(k)
            tips.append(date.strftime('%a %Y-%m-%d'))
        return tips

    if aggregation == 'week':
        for k in keys:
            start = parse_date(k)
            end = start + timedelta(days=6)
            tips.append(f'Week: {start.isoformat()} – {end.isoformat()}')
        return tips

    if aggregation == 'month':
        for k in keys:
            date = parse_date(k)
            tips.append(date.strftime('%b %Y'))
        return tips

    raise ValueError(f'Invalid aggregation: {aggregation}')


#to fill in dates without transactions
#keys should be the full expected keys from agg_keys
#rows is supposed to be the output from get_timeseries_data
def merge_timeseries(keys: list[str], rows: list[dict]) -> tuple[list[float], list[float], list[float]]:
    existing_keys_lookup: dict[str, dict] = {row['label']: row for row in rows}

    income: list[float] = []
    expenses: list[float] = []
    net: list[float] = []

    for k in keys:
        row = existing_keys_lookup.get(k)
        inc = float(row['income']) if row else 0.0 #fill 0 if missing
        exp = float(row['expenses']) if row else 0.0 
        income.append(inc)
        expenses.append(exp)
        net.append(inc + exp)

    return income, expenses, net




    
    
def make_labels_unique(labels: list[str]) -> list[str]:
   
    seen: dict[str, int] = {}
    out: list[str] = []
    zwsp = "\u200b"  

    for lab in labels:
        lab_str = '' if lab is None else str(lab)
        count = seen.get(lab_str, 0)

        base = lab_str if lab_str != "" else zwsp

        if count == 0:
            out.append(base)
        else:
            out.append(base + (zwsp * count)) 

        seen[lab_str] = count + 1

    return out



