from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont
from PySide6.QtWidgets import QWidget


def badge_tier_for_level(level: int) -> int:
    if level >= 100:
        return 4
    if level >= 50:
        return 3
    if level >= 25:
        return 2
    if level >= 10:
        return 1
    return 0


class LevelBadge(QWidget):
    def __init__(self, level: int = 1):
        super().__init__()
        self.level = max(1, int(level))
        self.setFixedSize(72, 72)

    def set_level(self, level: int) -> None:
        self.level = max(1, int(level))
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(3, 3, self.width() - 6, self.height() - 6)
        tier = badge_tier_for_level(self.level)

        bg, border, border_w = self.colors_for_tier(tier)

        painter.setBrush(QBrush(bg))
        painter.setPen(QPen(border, border_w))
        painter.drawEllipse(rect)

        if tier >= 2:
            inner = QRectF(11, 11, self.width() - 22, self.height() - 22)
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor(255, 255, 255, 90), 2))
            painter.drawEllipse(inner)

        font = QFont()
        font.setBold(True)
        font.setPointSize(17)
        painter.setFont(font)
        painter.setPen(QColor('#111111'))
        painter.drawText(self.rect(), Qt.AlignCenter, str(self.level))

    def colors_for_tier(self, tier: int) -> tuple[QColor, QColor, int]:
        if tier == 0:
            return (QColor('#f3f4f6'), QColor('#9ca3af'), 3)
        if tier == 1:
            return (QColor('#eef2ff'), QColor('#94a3b8'), 4)
        if tier == 2:
            return (QColor('#fff7ed'), QColor('#f59e0b'), 4)
        if tier == 3:
            return (QColor('#ecfeff'), QColor('#06b6d4'), 5)
        return (QColor('#fdf2f8'), QColor('#db2777'), 6)
