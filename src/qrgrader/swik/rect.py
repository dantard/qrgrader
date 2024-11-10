from PyQt5.QtCore import QPointF, QRectF
from PyQt5.QtWidgets import QGraphicsRectItem

from qrgrader.swik.utils import Signals


class SwikRect(QGraphicsRectItem):

    def __init__(self, parent=None, **kwargs):

        super(SwikRect, self).__init__()
        self.signals = Signals()
        self.setParentItem(parent)
        self.kwargs = None

        if (item := kwargs.get("copy", None)) is not None:
            self.copy(item, **kwargs)
        else:
            self.apply_kwargs(**kwargs)

    def apply_kwargs(self, **kwargs):
        self.kwargs = kwargs

    def copy(self, item, **kwargs):
        self.setParentItem(item.parentItem())
        self.setRect(item.rect())
        self.setPos(item.pos() + kwargs.get("offset", QPointF(0, 0)))
        self.kwargs = item.get_kwargs()

    def get_rect_on_scene(self):
        return self.sceneBoundingRect()

    def get_rect_on_parent(self):
        if self.parentItem() is None:
            return self.sceneBoundingRect()
        else:
            return self.parentItem().mapRectFromItem(self, self.rect())

    def get_kwargs(self):
        self.kwargs.pop("parent", None)
        return self.kwargs

    def get_kwarg(self, key, default=None):
        return self.kwargs.get(key, default)

    def die(self):
        self.scene().removeItem(self)

    def get_parent(self):
        return self.parentItem()

