from PyQt5 import QtCore
from PyQt5.QtWidgets import QMenu

from qrgrader.swik.annotations.annotation import Annotation
from qrgrader.swik.interfaces import Copyable


class SquareAnnotation(Annotation, Copyable):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.page_pos_x = 0
        self.page_pos_y = 0

    def set_page_pos(self, x, y):
        self.page_pos_x = x
        self.page_pos_y = y

    def contextMenuEvent(self, event: 'QGraphicsSceneContextMenuEvent') -> None:
        super().contextMenuEvent(event)
        menu = QMenu("Square Annotation")
        menu.addAction("Edit", self.change_color)
        menu.addSeparator()
        delete = menu.addAction("Delete")
        res = menu.exec(event.screenPos())
        if res == delete:
            self.notify_deletion(self)
            self.scene().removeItem(self)

    def get_full_state(self):
        full = super().get_full_state()
        full["content"] = self.content
        full["pen"] = self.pen()
        return full

    def set_full_state(self, state):
        super().set_full_state(state)
        self.content = state["content"] if "content" in state else self.content
        self.setPen(state["pen"] if "pen" in state else self.pen())

    def duplicate(self):
        r = SquareAnnotation(brush=self.brush(), pen=self.pen())
        r.setRect(self.rect())
        r.setPos(self.pos() + QtCore.QPointF(10, 10))
        r.content = self.content
        return r, self.parentItem()