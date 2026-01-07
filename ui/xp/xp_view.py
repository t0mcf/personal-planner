from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QListWidget,
    QListWidgetItem,
    QFrame,
    QGridLayout,
    QScrollArea,
)

from helpers.db import db_session
from db.xp import get_total_xp, list_recent_xp_events, level_for_total_xp, next_badge_milestone
from db.achievements import list_achievements, list_unlocked_ids, unlock

from ui.xp.level_badge import LevelBadge
from ui.xp.achievement_grid import AchievementTile
from ui.xp.achievement_checks import CHECKS

from datetime import date as dt_date

class XPView(QWidget):
    def __init__(self):
        super().__init__()
        self.build_ui()

    def build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(14)

        title = QLabel('Progression')
        title.setStyleSheet('font-size: 26px; font-weight: 900;')
        layout.addWidget(title)

        # top card
        top = QFrame()
        top.setStyleSheet(
            '''
            QFrame {
                background: #ffffff;
                border: 1px solid #d9d9d9;
                border-radius: 12px;
            }
            '''
        )
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(14, 12, 14, 12)
        top_layout.setSpacing(12)
        layout.addWidget(top, 0)

        self.badge = LevelBadge(1)
        top_layout.addWidget(self.badge, 0, Qt.AlignTop)

        right = QVBoxLayout()
        right.setSpacing(6)
        top_layout.addLayout(right, 1)

        self.level_label = QLabel('level 1')
        self.level_label.setStyleSheet('font-size: 22px; font-weight: 900;')
        right.addWidget(self.level_label)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(16)
        right.addWidget(self.progress)

        self.progress_label = QLabel('0 / 100 xp')
        self.progress_label.setStyleSheet('font-size: 14px; font-weight: 700; color: #666;')
        right.addWidget(self.progress_label)

        self.milestone_label = QLabel('')
        self.milestone_label.setStyleSheet('font-size: 13px; font-weight: 650; color: #666;')
        right.addWidget(self.milestone_label)

        mid = QHBoxLayout()
        mid.setSpacing(14)
        layout.addLayout(mid, 1)

        left = QVBoxLayout()
        left.setSpacing(10)
        mid.addLayout(left, 0)

        log_title = QLabel('log')
        log_title.setStyleSheet('font-size: 14px; font-weight: 900; color: #111;')
        left.addWidget(log_title)

        self.log = QListWidget()
        self.log.setStyleSheet(
            '''
            QListWidget {
                border: 1px solid #d9d9d9;
                border-radius: 12px;
                background: #ffffff;
            }
            QListWidget::item {
                padding: 8px 10px;
                border-bottom: 1px solid #eeeeee;
            }
            '''
        )
        self.log.setFixedWidth(360)
        left.addWidget(self.log, 1)

        right_col = QVBoxLayout()
        right_col.setSpacing(10)
        mid.addLayout(right_col, 1)

        ach_title = QLabel('Achievements')
        ach_title.setStyleSheet('font-size: 14px; font-weight: 900; color: #111;')
        right_col.addWidget(ach_title)

        self.ach_scroll = QScrollArea()
        self.ach_scroll.setWidgetResizable(True)
        self.ach_scroll.setStyleSheet('QScrollArea { border: none; }')
        right_col.addWidget(self.ach_scroll, 1)

        self.ach_container = QWidget()
        self.ach_scroll.setWidget(self.ach_container)

        self.achievement_grid = QGridLayout(self.ach_container)
        self.achievement_grid.setSpacing(10)
        self.achievement_grid.setContentsMargins(0, 0, 0, 0)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh()

    def refresh(self) -> None:
        with db_session() as connection:

            total = get_total_xp(connection)
            level, into, step = level_for_total_xp(total)
            events = list_recent_xp_events(connection, limit=60)

            self.badge.set_level(level)
            self.level_label.setText(f'level {level}')

            self.progress.setMaximum(step)
            self.progress.setValue(into)
            self.progress_label.setText(f'{into} / {step} xp   (total {total})')

            next_m = next_badge_milestone(level)
            self.milestone_label.setText('badge tier maxed' if next_m is None else f'next badge at level {next_m}')

            self.log.clear()
            for e in events:
                xp = int(e.get('xp_amount') or 0)
                msg = (e.get('message') or '').strip()
                when = (e.get('created_at') or '')[:16]
                sign = '+' if xp > 0 else ''
                line = f'{when}   {sign}{xp} xp   {msg}'
                self.log.addItem(QListWidgetItem(line))

            day = dt_date.today().isoformat()

            achs = list_achievements(connection)
            unlocked = list_unlocked_ids(connection)

            for a in achs:
                aid = a["id"]
                if aid in unlocked:
                    continue
                fn = CHECKS.get(aid)
                if fn and fn(connection, day):
                    unlock(connection, aid)
                    unlocked.add(aid)


            while self.achievement_grid.count():
                item = self.achievement_grid.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            row = col = 0
            for ach in achs:
                is_unlocked = (ach["id"] in unlocked)
                hidden = bool(ach.get("hidden_description"))
                tile = AchievementTile(
                    ach["name"],
                    ach["description"],
                    is_unlocked,
                    hidden,
                )
                self.achievement_grid.addWidget(tile, row, col)
                col += 1
                if col >= 3:
                    col = 0
                    row += 1

