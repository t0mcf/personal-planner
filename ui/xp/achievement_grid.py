from PySide6.QtWidgets import QGridLayout, QLabel, QFrame
from PySide6.QtCore import Qt

class AchievementTile(QFrame):
    def __init__(self, name: str, description: str, unlocked: bool, hidden: bool):
        super().__init__()
        self.setFixedSize(160, 90)
        self.setStyleSheet("""
            QFrame {
                border: 1px solid #d9d9d9;
                border-radius: 10px;
                background: #ffffff;
            }
        """)

        layout = QGridLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel(name)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-weight: 900;")

        desc = QLabel(
            description if unlocked or not hidden else "???"
        )
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 11px; color: #666;")

        if not unlocked:
            self.setGraphicsEffect(None)
            self.setStyleSheet(self.styleSheet() + "QFrame { color: #999; }")
            self.setWindowOpacity(0.55)

        layout.addWidget(title, 0, 0)
        layout.addWidget(desc, 1, 0)
