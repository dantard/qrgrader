from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtWidgets import QDialog, QMenu, QGraphicsRectItem

from qrgrader.swik.action import Action
from qrgrader.swik.color_widget import Color
from qrgrader.swik.dialogs import ComposableDialog
from qrgrader.swik.interfaces import Copyable
from qrgrader.swik.resizeable import ResizableRectItem


class RedactAnnotation(ResizableRectItem, Copyable):
    initial_color = Qt.black

    def change_color(self):
        before = self.get_full_state()

        color = ComposableDialog()
        color.add_row("Fill", Color(self.brush().color()))

        if color.exec() == QDialog.Accepted:
            new_color = color.get("Fill").get_color()
            self.set_fill_color(new_color)
            RedactAnnotation.initial_color = new_color

            if before != self.get_full_state():
                self.notify_change(Action.FULL_STATE, before, self.get_full_state())

    def mouseDoubleClickEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mouseDoubleClickEvent(event)
        self.change_color()

    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mousePressEvent(event)

    def duplicate(self):
        r = RedactAnnotation(brush=self.brush(), pen=self.pen())
        r.setRect(self.rect())
        r.setPos(self.pos() + QPointF(10, 10))
        return r, self.parentItem()

    def contextMenuEvent(self, event: 'QGraphicsSceneContextMenuEvent') -> None:
        super().contextMenuEvent(event)
        menu = QMenu("Redact Annotation")
        menu.addAction("Edit", self.change_color)
        menu.addSeparator()
        delete = menu.addAction("Delete")
        res = menu.exec(event.screenPos())
        if res == delete:
            self.notify_deletion()
            self.scene().removeItem(self)


class Patch(QGraphicsRectItem):
    def __init__(self, parent):
        super().__init__(parent)
        self.setBrush(Qt.white)
        self.setPen(Qt.white)

    def get_rect_on_parent(self):
        if self.parentItem() is None:
            return self.sceneBoundingRect()
        else:
            rect = QRectF(self.rect().x() - 1, self.rect().y() - 1, self.rect().width() + 2, self.rect().height() + 2)
            return self.parentItem().mapRectFromItem(self, rect)
