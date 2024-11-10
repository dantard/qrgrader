import sys
import typing

from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import Qt, QPointF, QRectF, QTimer
from PyQt5.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QGraphicsRectItem, QWidget, QStyle, QGraphicsItem

from qrgrader.swik.action import Action
from qrgrader.swik.interfaces import Undoable
from qrgrader.swik.selector import PaintableSelectorRectItem
from qrgrader.swik.utils import check_parent_limits


class HandleItem(QGraphicsRectItem):
    def __init__(self, parent, cursor):
        super().__init__(-5, -5, 10, 10, parent=parent)
        self.setBrush(Qt.white)
        self.mycursor = cursor
        self.setPen(Qt.black)
        self.setFlags(QGraphicsRectItem.ItemIsMovable | QGraphicsRectItem.ItemIsSelectable | QGraphicsRectItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)

    def hoverEnterEvent(self, event):
        self.setBrush(Qt.black)
        super().hoverEnterEvent(event)
        self.parentItem().handle_hover_enter(self, event)
        self.setCursor(self.mycursor)

    def hoverLeaveEvent(self, event):
        self.setBrush(Qt.white)
        super().hoverLeaveEvent(event)
        self.parentItem().handle_hover_leave(self, event)

    def mousePressEvent(self, event):
        super(HandleItem, self).mousePressEvent(event)
        # self.parentItem().mousePressEvent(event)
        self.parentItem().handle_press(self, event)

    def mouseMoveEvent(self, event):
        super(HandleItem, self).mouseMoveEvent(event)
        self.parentItem().handle_move(self, event)

    def mouseReleaseEvent(self, event):
        super(HandleItem, self).mouseReleaseEvent(event)
        self.parentItem().handle_release(self, event)

    def paint(self, painter: QtGui.QPainter, option, widget: typing.Optional[QWidget] = ...) -> None:
        option.state = QStyle.State_None
        super().paint(painter, option, widget)


class ResizableRectItem(PaintableSelectorRectItem, Undoable):

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        super(Undoable).__init__()
        self.resizeable = True
        self.movable = True
        self.setFlags(QGraphicsRectItem.ItemIsSelectable | QGraphicsRectItem.ItemSendsGeometryChanges | QGraphicsRectItem.ItemIsMovable)
        self.setAcceptHoverEvents(True)
        self.handles_enabled = True
        self.handles = []
        self.selected_handle_pos = None
        self.handle_pressed = False
        self.current_state = None

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(lambda: self.set_handle_visibility(False))
        self.timer.setInterval(2000)

        for cursor in [Qt.SizeFDiagCursor, Qt.SizeVerCursor, Qt.SizeBDiagCursor, Qt.SizeHorCursor, Qt.SizeFDiagCursor, Qt.SizeVerCursor, Qt.SizeBDiagCursor,
                       Qt.SizeHorCursor]:
            handle = HandleItem(self, cursor)
            handle.setBrush(Qt.white)
            handle.setPen(Qt.black)
            handle.setFlag(QGraphicsRectItem.ItemIsMovable, False)
            handle.setAcceptHoverEvents(True)
            handle.setVisible(False)
            self.handles.append(handle)

        self.update_handles_position()

    def setRect(self, rect: QtCore.QRectF) -> None:
        super(ResizableRectItem, self).setRect(rect)
        self.update_handles_position()

    def set_movable(self, movable):
        self.movable = movable

    def set_resizeable(self, resizeable):
        self.resizeable = resizeable

    def get_resizeable(self):
        return self.resizeable

    def get_movable(self):
        return self.movable

    def set_handles_enabled(self, enabled):
        self.handles_enabled = enabled

    def get_handles_enabled(self):
        return self.handles_enabled

    def update_handles_position(self):
        bounds = self.rect()
        handle_positions = [
            QPointF(bounds.left(), bounds.top()),
            QPointF(bounds.center().x(), bounds.top()),
            QPointF(bounds.right(), bounds.top()),
            QPointF(bounds.right(), bounds.center().y()),
            QPointF(bounds.right(), bounds.bottom()),
            QPointF(bounds.center().x(), bounds.bottom()),
            QPointF(bounds.left(), bounds.bottom()),
            QPointF(bounds.left(), bounds.center().y()),
        ]

        for handle, pos in zip(self.handles, handle_positions):
            handle.setPos(pos)

    def hoverMoveEvent(self, event):
        self.set_handle_visibility(True)
        self.timer.stop()
        if not self.handle_pressed:
            self.timer.start()

    # event.scenePos()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.current_state = self.get_full_state()
        self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        self.set_handle_visibility(True)
        self.timer.stop()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.setPos(self.pos().x() + self.rect().x(), self.pos().y() + self.rect().y())
        self.setRect(QRectF(0, 0, self.rect().width(), self.rect().height()))
        self.update_handles_position()
        if self.current_state != self.get_full_state():
            self.notify_change(Action.FULL_STATE, self.current_state, self.get_full_state())
        self.setCursor(Qt.OpenHandCursor)

    # Handles

    def handle_press(self, handle, event):
        self.handle_pressed = True
        self.selected_handle_pos = self.mapFromScene(handle.sceneBoundingRect().center())
        self.current_state = self.get_full_state()
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.timer.stop()

    def handle_move(self, handle_pressed, event):
        x, y = event.scenePos().x(), event.scenePos().y()
        if self.parentItem() is not None:
            x, y = check_parent_limits(self.parentItem(), x, y)

        new_pos = self.mapFromScene(x, y)

        delta = new_pos - self.selected_handle_pos
        rect = self.rect()

        if handle_pressed == self.handles[0]:
            rect.setTopLeft(rect.topLeft() + delta)
        elif handle_pressed == self.handles[1]:
            rect.setTop(rect.top() + delta.y())
        elif handle_pressed == self.handles[2]:
            rect.setTopRight(rect.topRight() + delta)
        elif handle_pressed == self.handles[3]:
            rect.setRight(rect.right() + delta.x())
        elif handle_pressed == self.handles[4]:
            rect.setBottomRight(rect.bottomRight() + delta)
        elif handle_pressed == self.handles[5]:
            rect.setBottom(rect.bottom() + delta.y())
        elif handle_pressed == self.handles[6]:
            rect.setBottomLeft(rect.bottomLeft() + delta)
        elif handle_pressed == self.handles[7]:
            rect.setLeft(rect.left() + delta.x())

        if self.parentItem() is not None:
            rect = self.mapRectToScene(rect)
            x1, y1, x2, y2 = rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height()

            x1, y1 = check_parent_limits(self.parentItem(), x1, y1)
            x2, y2 = check_parent_limits(self.parentItem(), x2, y2)

            rect = self.mapFromScene(QRectF(x1, y1, x2 - x1, y2 - y1).normalized()).boundingRect()

        self.setRect(rect.normalized())
        self.update_handles_position()
        self.selected_handle_pos = new_pos
        self.signals.resizing.emit(self)

    def handle_release(self, handle, event):
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.timer.start()
        self.handle_pressed = False
        if self.current_state != self.get_full_state():
            self.notify_change(Action.FULL_STATE, self.current_state, self.get_full_state())

    def view_mouse_release_event(self, view, event):
        res = super(ResizableRectItem, self).view_mouse_release_event(view, event)
        self.update_handles_position()
        return res

    def set_handle_visibility(self, visible: bool):
        for handle in self.handles:
            handle.setVisible(visible and self.handles_enabled)

    def handle_hover_enter(self, handle, event):
        self.set_handle_visibility(True)

    def handle_hover_leave(self, handle, event):
        pass  # self.set_handle_visibility(False)

    def hoverEnterEvent(self, event) -> None:
        self.set_handle_visibility(True)
        self.setCursor(Qt.OpenHandCursor)

    def itemChange(self, change: 'QGraphicsItem.GraphicsItemChange', value: typing.Any) -> typing.Any:

        if self.parentItem() is not None and change == QGraphicsItem.ItemPositionChange:
            if value.x() < 0:
                value = QPointF(0, value.y())
            elif value.x() + self.rect().width() > self.parentItem().rect().width():
                value = QPointF(self.parentItem().rect().width() - self.rect().width(), value.y())

            if value.y() < 0:
                value = QPointF(value.x(), 0)
            elif value.y() + self.rect().height() > self.parentItem().rect().height():
                value = QPointF(value.x(), self.parentItem().rect().height() - self.rect().height())

        return super().itemChange(change, value)

    def contextMenuEvent(self, event: 'QGraphicsSceneContextMenuEvent') -> None:
        if not self.isSelected():
            self.setSelected(True)
        # self.scene().context_menu(event)

    # State management
    def get_full_state(self):
        return {"rect": self.rect(), "brush": self.brush(), "pos": self.pos()}

    def set_full_state(self, state):
        self.setBrush(state["brush"] if "brush" in state else self.brush())
        self.setRect(state["rect"] if "rect" in state else self.rect())
        self.setPos(state["pos"] if "pos" in state else self.pos())

    def undo(self, action, previous_state):
        self.set_full_state(previous_state)


class MainWindow(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.rect_item = None
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.padre = self.scene.addRect(0, 0, 400, 400, pen=Qt.red)
        self.padre.setPos(50, 50)
        self.scene.addRect(0, 0, 800, 800, pen=Qt.red)
        self.done = 0

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:

        if self.done < 1:
            # self.rect_item = PaintableSelectorRectItem(text="hola")
            self.rect_item = ResizableRectItem(self.padre, text="hola")
            # self.rect_item = FancyResizableRectItem(pen=Qt.red, brush=Qt.green)
            # self.rect_item.set_border_width(5)
            # self.rect_item.set_fill_color(Qt.red, 111)

            # self.rect_item.set_movable(False)
            self.scene.addItem(self.rect_item)
            self.rect_item.view_mouse_press_event(self, event)
            self.rect_item.signals.done.connect(self.draw_done)
            # self.rect_item.signals.moving.connect(lambda x: print("moving"))
            # self.rect_item.signals.resizing.connect(lambda x: print("resizing"))
            # self.rect_item.signals.creating.connect(lambda x: print("creating"))

        super().mousePressEvent(event)

    def draw_done(self):
        return
        # for w, k in self.rect_item.get_kwargs().items():
        #     print(w, k)
        # tmp = self.rect_item
        # new = ResizableRectItem(**self.rect_item.get_kwargs(), copy=self.rect_item)
        #
        # new.setPos(tmp.pos())
        # new.setRect(tmp.rect())
        # self.scene.removeItem(self.rect_item)
        # self.scene.addItem(new)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        if self.rect_item is not None:
            self.rect_item.view_mouse_move_event(self, event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseReleaseEvent(event)
        if self.rect_item is not None:
            self.rect_item.view_mouse_release_event(self, event)
        self.done = self.done + 1


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
