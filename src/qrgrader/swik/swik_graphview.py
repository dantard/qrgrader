from PyQt5.QtCore import pyqtSignal, QRectF, Qt, QTimer, QPoint
from PyQt5.QtGui import QColor, QCursor, QHoverEvent, QPainter, QTransform
from PyQt5.QtWidgets import QGraphicsEllipseItem, QGraphicsView, QPushButton

import qrgrader.swik.utils as utils
from qrgrader.swik.graphview import GraphView
from qrgrader.swik.annotations.highlight_annotation import HighlightAnnotation
from qrgrader.swik.annotations.hyperlink import InternalLink
from qrgrader.swik.annotations.redact_annotation import RedactAnnotation, Patch
from qrgrader.swik.annotations.square_annotation import SquareAnnotation
from qrgrader.swik.bunch import NumerateBunch
from qrgrader.swik.link_shower import Shower
from qrgrader.swik.page import Page
from qrgrader.swik.simplepage import SimplePage
from qrgrader.swik.swik_text import SwikText, SwikTextReplace, SwikTextNumerate
from qrgrader.swik.widgets.pdf_widget import PdfWidget


class SwikGraphView(GraphView):
    drop_event = pyqtSignal(list)

    def __init__(self, manager, renderer, scene, page=SimplePage, mode=GraphView.MODE_VERTICAL_MULTIPAGE):
        super(SwikGraphView, self).__init__(manager, renderer, scene, page, mode)
        self.renderer.sync_requested.connect(self.sync_requested)
        self.renderer.sync_dynamic.connect(self.sync_dynamic)
        self.setAcceptDrops(True)
        self.link_shower = Shower(self.scene())

    def dropEvent(self, event) -> None:
        event.accept()
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            paths = []
            for url in urls:
                if url.isLocalFile():
                    paths.append(url.toLocalFile())
            if len(paths) > 0:
                self.drop_event.emit(paths)

    def dragEnterEvent(self, event) -> None:
        event.accept()

    def dragMoveEvent(self, event) -> None:
        event.accept()

        # Here you can process the file path as needed

    def sync_dynamic(self):
        items = self.scene().items()
        pages_to_refresh = set()

        square_annot = [item for item in items if type(item) == SquareAnnotation]
        for annot in square_annot:  # type: RedactAnnotation
            page: Page = annot.parentItem()
            self.renderer.add_annot(page.get_index(), annot)

        highlight_annot = [item for item in items if type(item) == HighlightAnnotation]
        for annot in highlight_annot:
            page: Page = annot.parentItem()
            self.renderer.add_highlight_annot(page.index, annot)
            pages_to_refresh.add(page.get_index())

        for index in pages_to_refresh:
            self.pages[index].invalidate()

    def sync_requested(self):
        items = self.scene().items()
        pages_to_refresh = set()

        redact_annot = [item for item in items if type(item) == RedactAnnotation or type(item) == Patch]
        for annot in redact_annot:  # type: RedactAnnotation
            page: Page = annot.parentItem()
            self.renderer.add_redact_annot(page.index, annot.get_rect_on_parent(), annot.brush().color())
            pages_to_refresh.add(page.index)
            self.scene().removeItem(annot)

        swik_text = [item for item in items if type(item) == SwikText]
        for text in swik_text:
            page: Page = text.parentItem()
            self.renderer.add_text(page.get_index(), text)
            pages_to_refresh.add(page.get_index())
            self.scene().removeItem(text)

        swik_text_replace = [item for item in items if type(item) == SwikTextReplace]
        for text in swik_text_replace:
            page: Page = text.parentItem()
            self.renderer.replace_word(page.get_index(), text)
            pages_to_refresh.add(page.get_index())
            self.scene().removeItem(text)

        swik_text_numerate = [item for item in items if type(item) == SwikTextNumerate]
        for text in swik_text_numerate:
            page: Page = text.parentItem()
            self.renderer.add_text(page.get_index(), text)
            pages_to_refresh.add(page.get_index())
            self.scene().removeItem(text)
        self.scene().remove_bunches(NumerateBunch)

        images = [item for item in items if isinstance(item, InsertImageRectItem)]
        for image in images:
            page: Page = image.parentItem()
            if image.get_image_filename() is not None:
                self.renderer.insert_image_from_file(page.get_index(), image.get_image_rect_on_parent(),
                                                     image.get_image_filename())
            else:
                self.renderer.insert_image(page.get_index(), image.get_image_rect_on_parent(), image.get_image())

            pages_to_refresh.add(page.get_index())
            self.scene().removeItem(image)

        widgets = [item for item in items if isinstance(item, PdfWidget)]
        for widget in widgets:
            self.renderer.add_widget(widget.parentItem().index, widget)

        for index in pages_to_refresh:
            self.pages[index].invalidate()

    def create_page(self, page, ratio=1):
        page = super().create_page(page, ratio)
        return page

    def link_hovered(self, kind, page, pos):

        dest_page = self.pages[page]

        if kind == InternalLink.ENTER:
            self.link_shower.enter(dest_page, pos)


        elif kind == InternalLink.LEAVE:
            self.link_shower.leave(dest_page, pos)

    def link_clicked(self, page, pos):
        # self.move_to_page(page)
        ellipse = QGraphicsEllipseItem(QRectF(0, 0, 10, 10), self.pages[page])
        ellipse.setBrush(QColor(255, 0, 0, 255))
        ellipse.setPen(Qt.transparent)
        ellipse.setPos(pos)
        self.centerOn(ellipse)
        utils.delayed(2000, self.scene().removeItem, ellipse)

    def toggle_page_info(self):
        for page in self.pages.values():
            page.toggle_info()
