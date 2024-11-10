from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPen, QBrush, QColor

from qrgrader.swik.rect import SwikRect


class ColoreableRectItem(SwikRect):
    def __init__(self, parent=None, **kwargs):
        super(ColoreableRectItem, self).__init__(parent, **kwargs)
        # super(Undoable, self).__init__()

    def apply_kwargs(self, **kwargs):
        super().apply_kwargs(**kwargs)
        self.setPen(kwargs.get("pen", QPen(Qt.black)))
        self.setBrush(kwargs.get("brush", QBrush(Qt.transparent)))

    def copy(self, item, **kwargs):
        super().copy(item, **kwargs)
        self.setPen(item.pen())
        self.setBrush(item.brush())

    def set_border_color(self, color: QColor):
        color = QColor(color)
        pen = self.pen()
        pen.setColor(color)
        self.setPen(pen)

    def set_fill_color(self, color: QColor):
        color = QColor(color)
        brush = QBrush(color)
        self.setBrush(brush)

    def set_border_width(self, width: int):
        pen = self.pen()
        pen.setWidth(int(width))
        self.setPen(pen)
