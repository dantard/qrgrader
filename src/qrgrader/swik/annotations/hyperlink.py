from PyQt5.QtCore import QObject, pyqtSignal, Qt, QRectF, QUrl, QPointF
from PyQt5.QtGui import QDesktopServices, QColor
from PyQt5.QtWidgets import QGraphicsRectItem


class Link(QGraphicsRectItem):
    class Signals(QObject):
        clicked = pyqtSignal(int, QPointF)
        link_hovered = pyqtSignal(int, int, QPointF)

    ENTER, MOVE, LEAVE = 0, 1, 2

    def __init__(self, rect: QRectF):
        super().__init__(QRectF(0, 0, rect.width(), rect.height()))
        self.signals = Link.Signals()
        self.setBrush(Qt.transparent)
        self.setPen(Qt.red)
        self.setPos(rect.x(), rect.y())

    def get_rect_on_parent(self):
        return QRectF(self.pos().x(), self.pos().y(), self.rect().width(), self.rect().height())


class ExternalLink(Link):
    def __init__(self, rect, uri):
        super().__init__(rect)
        self.uri = uri
        self.setAcceptHoverEvents(True)

    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super(Link, self).mousePressEvent(event)
        QDesktopServices.openUrl(QUrl(self.uri))

    def hoverEnterEvent(self, event):
        super().hoverEnterEvent(event)
        self.setCursor(Qt.PointingHandCursor)

    def hoverLeaveEvent(self, event):
        super().hoverLeaveEvent(event)
        self.setCursor(Qt.ArrowCursor)

    def set_color(self, color):
        self.setBrush(color)


class InternalLink(Link):
    def __init__(self, rect, dest):
        super().__init__(rect)
        self.dest_page = dest[0]
        self.x = dest[1]
        self.y = dest[2]
        self.setAcceptHoverEvents(True)

    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super(Link, self).mousePressEvent(event)
        self.signals.clicked.emit(self.dest_page, QPointF(self.x, self.y))

    def hoverMoveEvent(self, event):
        super().hoverMoveEvent(event)
        self.signals.link_hovered.emit(Link.MOVE, self.dest_page, QPointF(self.x, self.y))

    def hoverEnterEvent(self, event):
        self.signals.link_hovered.emit(Link.ENTER, self.dest_page, QPointF(self.x, self.y))
        self.setCursor(Qt.PointingHandCursor)

    def hoverLeaveEvent(self, event):
        self.signals.link_hovered.emit(Link.LEAVE, self.dest_page, QPointF(self.x, self.y))
        self.setCursor(Qt.ArrowCursor)