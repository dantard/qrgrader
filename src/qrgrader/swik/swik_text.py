import typing

from PyQt5 import QtGui
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QFont, QColor, QPen
from PyQt5.QtWidgets import QGraphicsTextItem, QMenu, QGraphicsRectItem, QGraphicsItem, QInputDialog

from qrgrader.swik.action import Action
from qrgrader.swik.color_widget import Color
from qrgrader.swik.dialogs import ComposableDialog, FontAndColorDialog
from qrgrader.swik.interfaces import Undoable


class SwikText(QGraphicsTextItem, Undoable):

    def __init__(self, text, parent, font_manager, font_info, size=11):
        super(SwikText, self).__init__()
        self.bg_color = Qt.transparent
        self.border_color = Qt.transparent
        # Necessary because of ReplaceSwikText
        self.check_parent_limits = True
        self.font_manager = font_manager
        self.setParentItem(parent)
        self.setFlag(QGraphicsTextItem.ItemIsMovable, True)
        self.font_info = font_info
        self.bg_color = Qt.transparent
        self.setDefaultTextColor(Qt.black)
        self.document().setPlainText(text)
        self.setFlag(QGraphicsTextItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsTextItem.ItemIsFocusable, True)
        self.setFlag(QGraphicsTextItem.ItemSendsGeometryChanges, True)
        self.apply_font(size)
        self.current_state = None
        self.hover_color = None
        self.notify_creation()

    def set_bg_color(self, color: QColor):
        self.bg_color = QColor(color)
        self.update()

    def set_border_color(self, color: QColor):
        self.border_color = QColor(color)
        self.update()

    def paint(self, painter, o, w):
        painter.setBrush(self.bg_color)
        painter.setPen(self.border_color)
        rect = self.boundingRect()
        # rect.setWidth(rect.width())
        painter.drawRect(rect)
        super().paint(painter, o, w)

    def get_font_info(self):
        return self.font_info

    def set_background_color(self, color: Color):
        self.bg_color = QColor(color)

    def get_background_color(self):
        return self.bg_color

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() == Qt.Key_Plus:
            font = self.font()
            font.setPointSizeF(font.pointSizeF() + 0.1)
            self.setFont(font)
        elif event.key() == Qt.Key_Minus:
            font = self.font()
            font.setPointSizeF(font.pointSizeF() - 0.1)
            self.setFont(font)
        super(SwikText, self).keyPressEvent(event)

    def contextMenuEvent(self, event: 'QGraphicsSceneContextMenuEvent') -> None:
        if not self.isSelected():
            self.setSelected(True)
        # WARNING: This must be the first line of the method
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        # This Line specifies that the event has been already handled
        event.accept()
        self.popup_context_menu(QMenu(), event)

    def popup_context_menu(self, menu, event):
        edit_text = menu.addAction("Edit")
        action = menu.addAction("Edit Font")
        res = menu.exec(event.screenPos())
        self.current_state = self.get_full_state()
        if res == action:
            font_dialog = FontAndColorDialog(self.font_manager, self.get_font_info().nickname, self.get_font_size(),
                                             self.defaultTextColor())
            if font_dialog.exec() == ComposableDialog.Accepted:
                font, color = font_dialog.get("Font"), font_dialog.get("Text Color")
                self.set_font_info(font.get_font(), font.get_font_size())
                self.setDefaultTextColor(color.get_color())
                self.notify_change(Action.FULL_STATE, self.current_state, self.get_full_state())
        elif res == edit_text:
            text, ok = QInputDialog().getText(self.scene().views()[0], "Input Text", "Enter text",
                                              text=self.toPlainText())
            if ok:
                self.current_state = self.get_full_state()
                self.set_text(text)
                self.notify_change(Action.FULL_STATE, self.current_state, self.get_full_state())
        return res

    def mouseDoubleClickEvent(self, event) -> None:
        super().mouseDoubleClickEvent(event)
        # self.setTextInteractionFlags(Qt.TextEditorInteraction)
        # self.setFocus()
        text, ok = QInputDialog().getText(self.scene().views()[0], "Input Text", "Enter text", text=self.toPlainText())
        if ok:
            self.current_state = self.get_full_state()
            self.set_text(text)
            self.notify_change(Action.FULL_STATE, self.current_state, self.get_full_state())

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        self.current_state = self.get_full_state()

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        self.notify_change(Action.FULL_STATE, self.current_state, self.get_full_state())

    def undo(self, kind, info):
        self.set_full_state(info)

    def itemChange(self, change, value: typing.Any) -> typing.Any:
        if self.parentItem() is not None and self.check_parent_limits and change == QGraphicsItem.ItemPositionChange:
            if value.x() < 0:
                value = QPointF(0, value.y())
            elif value.x() + self.boundingRect().width() > self.parentItem().boundingRect().width():
                value = QPointF(self.parentItem().boundingRect().width() - self.boundingRect().width(), value.y())

            if value.y() < 0:
                value = QPointF(value.x(), 0)
            elif value.y() + self.boundingRect().height() > self.parentItem().boundingRect().height():
                value = QPointF(value.x(), self.parentItem().boundingRect().height() - self.boundingRect().height())

        return super().itemChange(change, value)

    def focusOutEvent(self, event: QtGui.QFocusEvent) -> None:
        super().focusOutEvent(event)
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        if self.current_state != self.get_full_state():
            self.notify_change(Action.FULL_STATE, self.current_state, self.get_full_state())
        self.update()

    def focusInEvent(self, event: QtGui.QFocusEvent) -> None:
        super().focusInEvent(event)
        self.current_state = self.get_full_state()
        self.update()

    def get_rect_on_parent(self):
        return self.parentItem().mapRectFromItem(self, self.boundingRect())

    def get_text(self):
        return self.document().toPlainText()

    def set_text(self, text):
        self.document().setPlainText(text)

    def apply_font(self, size):
        document = self.document()
        document.setDocumentMargin(0)
        self.setDocument(document)
        q_font = self.font_info.get_qfont(size)
        self.setFont(q_font)

    def set_font_info(self, font_info, size=11):
        self.font_info = font_info
        self.apply_font(size)

    def set_font(self, font, size=None):
        super().setFont(font)
        if size is not None:
            self.set_size(size)
        self.update()

    def set_size(self, size):
        font = self.font()
        font.setPointSizeF(size)
        self.setFont(font)
        self.update()

    def get_font_size(self):
        return self.font().pointSizeF()

    # State management
    def get_full_state(self):
        return {"text": self.toPlainText(), "font": self.font_info, "font_size": self.get_font_size(),
                "text_color": self.defaultTextColor(), "pos": self.pos()}

    def set_full_state(self, state):
        self.document().setPlainText(state["text"] if "state" in state else self.document().toPlainText())
        if "font" in state:
            self.set_font_info(state["font"], state["font_size"] if "font_size" in state else None)
        self.setDefaultTextColor(state["text_color"] if "text_color" in state else self.defaultTextColor())
        self.setPos(state["pos"] if "pos" in state else self.pos())

    def set_hover_color(self, color):
        self.hover_color = color
        self.set_border_color(self.hover_color)
        QTimer.singleShot(2500, lambda: self.set_border_color(QColor(0, 0, 0, 0)))

    def hoverEnterEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        super().hoverEnterEvent(event)
        if self.hover_color is not None:
            self.set_border_color(self.hover_color)

    def hoverLeaveEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        super().hoverLeaveEvent(event)
        if self.hover_color is not None:
            self.set_border_color(QColor(0, 0, 0, 0))


class SwikTextReplace(SwikText):
    def __init__(self, word, font_manager, font, size, color=Qt.black):
        super(SwikTextReplace, self).__init__(word.get_text(), word.parentItem(), font_manager, font, size)
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.setZValue(1)
        self.setPos(word.pos())
        self.setDefaultTextColor(QColor(color))
        # self.set_bg_color(QColor(255, 255, 255))
        self.set_border_color(QColor(255, 0, 0))


class SwikTextNumerate(SwikText):
    ANCHOR_TOP_LEFT = 0
    ANCHOR_TOP_RIGHT = 1
    ANCHOR_BOTTOM_LEFT = 2
    ANCHOR_BOTTOM_RIGHT = 3
    ANCHOR_TOP_CENTER = 4
    ANCHOR_BOTTOM_CENTER = 5

    class Signals(QObject):
        moved = pyqtSignal(object, QPointF)
        state_changed = pyqtSignal(QGraphicsTextItem, object, object)
        action = pyqtSignal(object, str)
        move_started = pyqtSignal(object)
        move_finished = pyqtSignal(object)

    def __init__(self, text, parent, font_manager, path, size):
        super(SwikTextNumerate, self).__init__(text, parent, font_manager, path, size)
        self.signals = self.Signals()
        self.current_pose = None
        self.anchor = SwikTextNumerate.ANCHOR_TOP_LEFT
        self.box = QGraphicsRectItem(self)
        self.setTextInteractionFlags(Qt.NoTextInteraction)

    def mouseDoubleClickEvent(self, event) -> None:
        pass

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        self.signals.move_started.emit(self)

    def mouseMoveEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mouseMoveEvent(event)
        self.signals.moved.emit(self, self.pos())

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        if self.current_pose != self.pos():
            self.signals.move_finished.emit(self)

    def popup_context_menu(self, menu, event):
        start_here = menu.addAction("Start Here")
        remove = menu.addAction("Remove")
        remove_all = menu.addAction("Remove all")
        center = menu.addAction("Center")
        menu_anchor = menu.addMenu("Anchor")
        top_left = menu_anchor.addAction("Top Left")
        top_right = menu_anchor.addAction("Top Right")
        bottom_left = menu_anchor.addAction("Bottom Left")
        bottom_right = menu_anchor.addAction("Bottom Right")
        top_center = menu_anchor.addAction("Top Center")
        bottom_center = menu_anchor.addAction("Bottom Center")

        anchor = [top_left, top_right, bottom_left, bottom_right, top_center, bottom_center]
        for a in anchor:
            a.setCheckable(True)
            if anchor.index(a) == self.anchor:
                a.setChecked(True)

        menu.addSeparator()

        res = super().popup_context_menu(menu, event)

        if res == start_here:
            self.signals.action.emit(self, "start_here")
        elif res == remove_all:
            self.signals.action.emit(self, 'remove_all')
        elif res == remove:
            self.signals.action.emit(self, 'remove')
        elif res in anchor:
            self.anchor = anchor.index(res)
            self.signals.action.emit(self, 'anchor_changed')
        elif res == center:
            self.signals.action.emit(self, 'center')

        if self.current_state != self.get_full_state():
            self.signals.state_changed.emit(self, self.current_state, self.get_full_state())

    def notify_deletion(self):
        pass

    def notify_change(self, kind, old, new):
        pass

    def notify_creation(self):
        pass


class SwikTextMimic(SwikTextReplace):

    def notify_deletion(self):
        pass

    def notify_change(self, kind, old, new):
        pass

    def notify_creation(self):
        pass
