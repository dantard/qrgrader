from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPainter, QHoverEvent, QCursor
from PyQt5.QtWidgets import QPushButton, QGraphicsView


class Shower(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self.close = QPushButton("✕")
        self.close.setParent(self)
        self.close.clicked.connect(self.hide)
        self.pin = QPushButton("•")
        self.pin.setParent(self)
        self.pin.setCheckable(True)
        self.setAttribute(Qt.WA_Hover, True)
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.bury)

        self.timer2 = QTimer()
        self.timer2.setSingleShot(True)
        self.timer2.timeout.connect(self.show_link)

        self.pos1 = None
        self.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        # self.link_shower.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        # self.setTransform(QTransform().scale(0.5, 0.5))
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)

    def setPoseSize(self, x, y, w, h):
        if self.pin.isChecked():
            self.setGeometry(self.geometry().x(), self.geometry().y(), w, h)
        else:
            self.setGeometry(x, y, w, h)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.pos1 = event.pos()

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if self.pos1 is not None:
            self.move(event.globalPos() - self.pos1)

    def mouseReleaseEvent(self, event):
        self.pos1 = None

    def show(self):
        super().show()
        self.timer.start(1500)

    def event(self, event):
        if event.type() == QHoverEvent.HoverEnter:
            self.timer.stop()
        if event.type() == QHoverEvent.HoverLeave:
            self.bury()
        return super().event(event)

    def resizeEvent(self, event):
        self.close.setGeometry(self.width() - 40, 10, 20, 20)
        self.pin.setGeometry(self.width() - 65, 10, 20, 20)
        super().resizeEvent(event)

    def bury(self):
        if not self.pin.isChecked():
            self.hide()

    def hoverLeaveEvent(self, event):
        QTimer.singleShot(100, self.bury)

    def enter(self, page, pos):
        self.page = page
        self.pos = self.page.mapToScene(pos)
        self.timer2.start(1000)

    def leave(self, page, pos):
        self.timer2.stop()

    def show_link(self):
        self.setSceneRect(0, self.pos.y() - 600, self.page.sceneBoundingRect().width(), 1200)
        self.setPoseSize(QCursor.pos().x() + 5, QCursor.pos().y() + 20, int(self.page.sceneBoundingRect().width()), 400)
        self.verticalScrollBar().setValue(int(self.pos.y()))
        self.show()


