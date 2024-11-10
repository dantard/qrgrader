from PyQt5.QtCore import QObject, pyqtSignal, Qt
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsTextItem

from qrgrader.swik.annotations.hyperlink import InternalLink
from qrgrader.swik.simplepage import SimplePage


# from utils import Signals


class Page(SimplePage):
    class PageSignals(QObject):
        item_added = pyqtSignal(QGraphicsItem)

    def __init__(self, index, view, manager, renderer, ratio):
        self.signals = Page.PageSignals()
        super().__init__(index, view, manager, renderer, ratio)
        self.words = None
        self.info = QGraphicsTextItem(self)
        self.info.setPlainText(str(index))
        font = self.info.font()
        font.setPixelSize(40)
        self.info.setFont(font)
        self.info.setVisible(False)
        self.info.setFlag(QGraphicsItem.ItemIgnoresTransformations)

        self.read_widgets()
        self.read_annotations()
        self.read_links()

    def set_visual_info(self, text, color=Qt.black):
        self.info.setPlainText(text)
        self.info.setDefaultTextColor(color)
        self.show_visual_info(True)

    def show_visual_info(self, value):
        self.info.setVisible(value)

    def read_annotations(self):
        annotations = self.renderer.get_annotations(self.index)
        for annotation in annotations:
            annotation.setParentItem(self)

    def read_links(self):
        links = self.renderer.get_links(self.index)
        for link in links:
            link.setParentItem(self)
            if type(link) == InternalLink:
                link.signals.clicked.connect(self.view.link_clicked)
                link.signals.link_hovered.connect(self.view.link_hovered)

    def read_widgets(self):
        widgets = self.renderer.get_widgets(self.index)
        for widget in widgets:
            widget.setParentItem(self)

    def toggle_info(self):
        self.info.setVisible(not self.info.isVisible())

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)

    def gather_words(self, force=False):
        if self.words is None or force:
            self.words = self.renderer.extract_words(self.index)
            for word in self.words:
                word.join(self)
        return self.words

    def has_words(self):
        return self.words is not None

    def get_words(self):
        return self.words

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemChildAddedChange:
            self.signals.item_added.emit(value)
        return super().itemChange(change, value)

    def invalidate(self):
        super().invalidate()
        if self.words is not None:
            for word in self.words:
                self.scene().removeItem(word)
            self.words = None
