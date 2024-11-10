from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import QGraphicsRectItem, QGraphicsItem, QGraphicsTextItem

from qrgrader.swik.simplepage import SimplePage


class MiniaturePage(SimplePage):
    def __init__(self, index, view, manager, renderer, ratio):
        super().__init__(index, view, manager, renderer, ratio)
        self.background = QGraphicsRectItem(self)
        self.background.setBrush(QBrush(QColor(180, 180, 180, 30)))
        self.box.setBrush(QBrush(QColor(255, 255, 0, 30)))

        self.background.setRect(QRectF(0, 0, self.boundingRect().width(), 55))
        self.background.setPos(0, self.boundingRect().height() + 10)
        self.background.setFlag(QGraphicsItem.ItemIgnoresTransformations)

        self.number = QGraphicsTextItem(self.background)
        self.number.setPlainText(str(self.index + 1))
        font = self.number.font()
        font.setPixelSize(22)
        self.number.setFont(font)
        center = (self.rect().width() - self.number.boundingRect().width() * 2) / 2
        self.number.setPos(center, self.boundingRect().height() + 10)
        self.number.setFlag(QGraphicsItem.ItemIgnoresTransformations)

    def update_ratio(self, ratio):
        super().update_ratio(ratio)
        if self.background is not None:
            self.background.setPos(0, self.rect().height() + 10 / self.ratio)
            self.background.setRect(QRectF(0, 0, self.get_scaled_width(), 35))
            center = (self.background.rect().width() - self.number.boundingRect().width()) / 2
            self.number.setPos(center, 0)

    def connect_signals(self):
        super().connect_signals()

    def set_highlighted(self, value):
        if value:
            # self.box.setBrush(QBrush(QColor(255, 255, 0, 30)))
            self.background.setBrush(QBrush(QColor(255, 180, 180, 255)))
        else:
            self.background.setBrush(QBrush(QColor(180, 180, 180, 255)))

        # self.box.setVisible(value)

    # def paint_accessories(self):
    #    pass
    # Selection Box
    # self.box.setRect(QRectF(-5, -5, self.get_scaled_width() + 10, self.get_scaled_height() + 10))
    # self.box.setBrush(QBrush(QColor(255, 255, 0, 30)))
