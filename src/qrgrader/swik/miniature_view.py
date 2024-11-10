from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import QGraphicsView

from qrgrader.swik.graphview import GraphView
from qrgrader.swik.miniature_page import MiniaturePage
from qrgrader.swik.simplepage import SimplePage


class MiniatureView(GraphView):

    def __init__(self, manager, renderer, scene):
        super(MiniatureView, self).__init__(manager, renderer, scene,
                                            page=MiniaturePage, mode=GraphView.MODE_FIT_WIDTH,
                                            align=QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter, page_sep=60)

    def wheelEvent(self, event: 'QGraphicsSceneWheelEvent') -> None:
        super(QGraphicsView, self).wheelEvent(event)

    def set_page(self, index):
        self.clear_selection()
        if self.pages.get(index) is not None:
            self.pages[index].set_highlighted(True)
            self.centerOn(self.pages[index])

    def clear_selection(self):
        for p in self.pages.values():
            p.set_highlighted(False)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mousePressEvent(event)
        if event.button() == QtCore.Qt.LeftButton:

            self.clear_selection()

            page = self.get_items_at_pos(event.pos(), SimplePage, 0, False)

            if page is not None:
                self.page_clicked.emit(page.index)
                page.set_highlighted(True)
