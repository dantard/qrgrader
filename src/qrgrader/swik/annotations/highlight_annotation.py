from PyQt5.QtCore import QRectF, Qt, QPointF
from PyQt5.QtWidgets import QGraphicsRectItem, QDialog, QMenu

from qrgrader.swik.action import Action
from qrgrader.swik.color_widget import ColorAndAlpha, TextLineEdit
from qrgrader.swik.dialogs import ComposableDialog
from qrgrader.swik.interfaces import Undoable


class HighlightAnnotation(QGraphicsRectItem, Undoable):
    class Quad(QGraphicsRectItem):

        def __init__(self, parent):
            super().__init__()
            self.setParentItem(parent)

        def mouseDoubleClickEvent(self, event) -> None:
            super().mouseDoubleClickEvent(event)
            self.parentItem().quad_double_click(event)

        def contextMenuEvent(self, event: 'QGraphicsSceneContextMenuEvent') -> None:
            self.parentItem().quad_context_menu(event)

    def __init__(self, color, parent):
        super().__init__()
        self.quads = []
        self.setParentItem(parent)
        self.color = color
        self.setBrush(Qt.transparent)
        self.setPen(Qt.transparent)
        self.content = str()
        self.notify_creation()

    def get_full_state(self):
        return {"color": self.color, "content": self.content}

    def set_full_state(self, state):
        self.set_color(state["color"])
        self.set_content(state["content"])

    def get_color(self):
        return self.color

    def set_content(self, text):
        self.content = text
        self.setToolTip(text)
        for quad in self.quads:
            quad.setToolTip(text)

    def get_content(self):
        return self.content

    def set_color(self, color):
        self.color = color
        for quad in self.quads:
            quad.setBrush(color)

    def quad_double_click(self, event):
        before = self.get_full_state()
        color = ComposableDialog()
        color.add_row("Content", TextLineEdit(self.content))
        color.add_row("Color", ColorAndAlpha(self.get_color()))

        if color.exec() == QDialog.Accepted:
            self.set_color(color.get("Color").get_color())
            self.set_content(color.get("Content").get_text())
            if before != self.get_full_state():
                self.notify_change(Action.FULL_STATE, before, self.get_full_state())

    def add_quad(self, rect):
        quad = self.Quad(self)
        quad.setBrush(self.color)
        quad.setPen(Qt.transparent)
        x, y = rect.x(), rect.y()
        w, h = rect.width(), rect.height()
        quad.setRect(QRectF(0, 0, w, h))
        pos = self.mapFromParent(QPointF(x, y))
        quad.setPos(pos)
        quad.setZValue(1)
        self.quads.append(quad)

    def get_quads(self):
        quads_on_page = []
        for quad in self.quads:
            quad_on_annotation = QRectF(quad.pos().x(), quad.pos().y(), quad.rect().width(), quad.rect().height())
            quad_on_page = self.mapRectToParent(quad_on_annotation)
            quads_on_page.append(quad_on_page)
        return quads_on_page

    def quad_context_menu(self, event):
        menu = QMenu("Highlight Annotation")
        edit = menu.addAction("Edit")
        menu.addSeparator()
        delete = menu.addAction("Delete")
        res = menu.exec(event.screenPos())
        if res == delete:
            self.notify_deletion(self)
            self.scene().removeItem(self)
        if res == edit:
            self.quad_double_click(event)

    def undo(self, kind, info):
        self.set_full_state(info)
