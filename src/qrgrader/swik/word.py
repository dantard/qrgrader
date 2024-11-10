from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QBrush

from qrgrader.swik.rect import SwikRect


class MetaWord:
    def __init__(self, page_id, order, text, rect, parent=None, **kwargs):
        self.text = text
        self.width = rect.width()
        self.height = rect.height()
        self.x_pos = rect.x()
        self.y_pos = rect.y()
        self.order = order
        self.page_id = page_id

    def get_text(self):
        return self.text

    def join(self, parent):
        pass


class Word(SwikRect):
    def __init__(self, page_id, order, text, rect, parent=None, **kwargs):
        super(Word, self).__init__(parent, **kwargs)
        self.text = text
        self.width = rect.width()
        self.height = rect.height()
        self.x_pos = rect.x()
        self.y_pos = rect.y()
        self.setParentItem(parent)
        self.order = order
        self.setPen(Qt.transparent)
        self.page_id = page_id
        self.block_no = kwargs.get("block_no", None)
        self.line_no = kwargs.get("line_no", None)
        self.word_no = kwargs.get("word_no", None)

    def join(self, parent):
        self.setParentItem(parent)
        self.setRect(0, 0, self.width, self.height)
        self.setPos(self.x_pos, self.y_pos)

    def get_text(self):
        return self.text

    def set_selected(self, selected):
        if selected:
            self.setBrush(QBrush(QColor(0, 0, 255, 60)))
        else:
            self.setBrush(Qt.transparent)

    def set_highlighted(self, selected, color=QColor(255, 255, 60, 80)):
        if selected:
            self.setBrush(QBrush(color))
        else:
            self.setBrush(Qt.transparent)
