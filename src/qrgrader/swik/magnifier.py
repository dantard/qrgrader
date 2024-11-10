from PyQt5.QtCore import QPoint, Qt, pyqtSignal
from PyQt5.QtGui import QTransform, QPainter
from PyQt5.QtWidgets import QGraphicsView, QPushButton


class Magnifier(QGraphicsView):
    closed = pyqtSignal()

    def __init__(self, widget):
        super().__init__(widget.view.scene())
        self.pos1 = None
        self.main_view: QGraphicsView = widget.view
        self.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        # self.link_shower.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.scale = 1.5
        self.setTransform(QTransform().scale(self.scale, self.scale))
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)

        self.close_btn = QPushButton("✕")
        self.close_btn.setParent(self)
        self.close_btn.setGeometry(10, 10, 20, 20)
        self.close_btn.clicked.connect(self.finish)

        self.plus = QPushButton("+")
        self.plus.setParent(self)
        self.plus.setGeometry(40, 10, 20, 20)
        self.plus.clicked.connect(lambda: self.set_scale(0.1))

        self.minus = QPushButton("-")
        self.minus.setParent(self)
        self.minus.setGeometry(65, 10, 20, 20)
        self.minus.clicked.connect(lambda: self.set_scale(-0.1))
        self.square_width = int(300 / self.scale)
        self.update_scene_rect()

    def set_widget(self, widget):
        self.main_view: QGraphicsView = widget.view
        self.setScene(widget.view.scene())
        self.update_scene_rect()

    def set_scale(self, scale):
        self.scale += scale
        self.setTransform(QTransform().scale(self.scale, self.scale))
        self.square_width = int(300 / self.scale)
        self.update_scene_rect()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.pos1 = event.pos()

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if self.pos1 is not None:
            self.move(event.globalPos() - self.pos1)
        self.update_scene_rect()

    def finish(self):
        self.hide()
        self.closed.emit()

    def update_scene_rect(self):
        obj = self.main_view
        pose = QPoint(0, 0)
        while obj is not None:
            pose += obj.mapToParent(QPoint(0, 0))
            obj = obj.parent()

        pose = self.pos() - pose
        pose = self.main_view.mapToScene(pose)
        self.setSceneRect(pose.x(), pose.y(), self.square_width, self.square_width)

    def mouseReleaseEvent(self, event):
        self.pos1 = None
