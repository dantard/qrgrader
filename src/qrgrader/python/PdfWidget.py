import cv2
import fitz
import numpy as np
from PyQt5 import QtCore, QtGui
from PyQt5 import QtWidgets
from PyQt5.QtCore import QRectF, QCoreApplication, QTimer, pyqtSignal, QMutex
from PyQt5.QtCore import Qt
from PyQt5.QtGui import (QPixmap, QImage, QPainter, QIcon, QColor, QPen, QPaintEvent)
from PyQt5.QtWidgets import (QWidget, QLabel, QScrollArea, QApplication,
                             QVBoxLayout, QFileDialog, QSplitter, QToolBar, QHBoxLayout, QListWidget, QListWidgetItem, QProgressDialog)


class PdfWidget(QWidget):
    class Image(QLabel):

        def __init__(self, id, callback):
            super(QLabel, self).__init__()
            self.setMouseTracking(True)
            self.id = id
            self.callback = callback
            self.signals_enabled = False
            self.hidden = True

        painted = pyqtSignal(int)

        def enableSignals(self, value=True):
            self.signals_enabled = value

        def forceRepaint(self):
            self.painted.emit(self.id)
            pass

        def setPixmap(self, a0: QtGui.QPixmap, skip=False) -> None:
            super().setPixmap(a0)

        def paintEvent(self, a0: QPaintEvent):
            super().paintEvent(a0)

        def mouseMoveEvent(self, ev: QtGui.QMouseEvent) -> None:
            if self.callback is not None:
                self.callback(self.id, self, ev)
            else:
                super().mouseMoveEvent(ev)

        def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:
            if self.callback is not None:
                self.callback(self.id, self, ev)
            else:
                super().mouseReleaseEvent(ev)

        def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
            if self.callback is not None:
                self.callback(self.id, self, ev)
            else:
                super().mousePressEvent(ev)

    class ResizeableQListWidget(QListWidget):
        resizing = pyqtSignal()

        def resizeEvent(self, e: QtGui.QResizeEvent) -> None:
            super().resizeEvent(e)
            self.resizing.emit()

    class WheelScrollArea(QScrollArea):
        def __init__(self, callback, mode=Qt.Vertical):
            super(QScrollArea, self).__init__()
            self.setMouseTracking(True)
            self.callback = callback
            self.mode = mode

        resizing = pyqtSignal()

        def resizeEvent(self, e: QtGui.QResizeEvent) -> None:
            super().resizeEvent(e)
            self.resizing.emit()

        def wheelEvent(self, a0: QtGui.QWheelEvent) -> None:
            modifiers = QtWidgets.QApplication.keyboardModifiers()
            if modifiers != QtCore.Qt.ControlModifier:
                super().wheelEvent(a0)

                if self.mode == Qt.Vertical:
                    super().wheelEvent(a0)
                else:
                    modifiers = QtWidgets.QApplication.keyboardModifiers()
                    if modifiers != QtCore.Qt.ShiftModifier:
                        super().wheelEvent(a0)
                    else:
                        QCoreApplication.sendEvent(self.horizontalScrollBar(), a0)

            else:
                self.callback(a0)

    class Annotation:
        def __init__(self, page):
            self.page = page

        def fromAnnot(self, annot):
            self.rect = QRectF(annot.rect[0], annot.rect[1], annot.rect[2] - annot.rect[0], annot.rect[3] - annot.rect[1])
            self.stroke = annot.colors['stroke']
            self.fill = annot.colors['fill']
            self.opacity = annot.opacity
            self.flags = annot.flags
            self.name = annot.info["name"]
            self.ratio = 1
            self.saved_color = self.stroke

        def fromRect(self, rect, ratio):
            self.rect = rect
            self.stroke = (1, 0, 0)
            self.fill = None
            self.opacity = 1
            self.flags = 0
            self.flags |= fitz.PDF_ANNOT_IS_LOCKED
            self.flags |= fitz.PDF_ANNOT_IS_READ_ONLY
            self.name = str()
            self.ratio = ratio
            self.saved_color = self.stroke

        def set_transparent(self, val):
            self.opacity = 0 if val else 1

        def save_color(self):
            self.saved_color = self.stroke

        def restore_color(self):
            self.stroke = self.saved_color

        def set_color(self, stroke):
            self.stroke = stroke

        def is_transparent(self):
            return self.opacity == 0

        def isPointWithin(self, pos, ratio=1):
            return self.rect.x() * ratio / self.ratio <= pos.x() <= self.rect.x() * ratio / self.ratio + self.rect.width() * ratio / self.ratio and self.rect.y() * ratio / self.ratio <= pos.y() <= self.rect.y() * ratio / self.ratio + self.rect.height() * ratio / self.ratio

        def get_qcolor(self):
            return QColor(self.stroke[0] * 255, self.stroke[1] * 255, self.stroke[2] * 255)

        def get_name(self):
            return self.name

        def get_rect(self, ratio):
            return QRectF(self.rect.x() * ratio / self.ratio, self.rect.y() * ratio / self.ratio, self.rect.width() * ratio / self.ratio,
                          self.rect.height() * ratio / self.ratio)

        def create_annot(self, page):
            r = fitz.Rect(self.rect.x(), self.rect.y(), self.rect.x() + self.rect.width(), self.rect.y() + self.rect.height())
            annot = page.add_rect_annot(r)  # 'Square'
            annot.set_border(width=2)
            annot.set_colors(stroke=self.stroke)
            annot.set_flags(self.flags)
            annot.set_name(self.name)
            annot.update(opacity=self.opacity)
            return annot

    def __init__(self, mode=Qt.Vertical, ratio=1):
        super().__init__()

        self.mode = mode

        # Setup scroll area
        self.scroll_area = self.WheelScrollArea(self.scrolled, mode)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.horizontalScrollBar().valueChanged.connect(self.check_visibility)
        self.scroll_area.verticalScrollBar().valueChanged.connect(self.check_visibility)
        self.scroll_area.resizing.connect(self.check_visibility)

        scroll_area_helper_widget = QWidget()
        self.scroll_area.setWidget(scroll_area_helper_widget)

        if mode == Qt.Vertical:
            self.scroll_area_layout = QVBoxLayout()
        else:
            self.scroll_area_layout = QHBoxLayout()

        self.scroll_area_layout.setAlignment(Qt.AlignTop)
        scroll_area_helper_widget.setLayout(self.scroll_area_layout)

        main_layout = QVBoxLayout()

        tb = QToolBar()
        main_layout.addWidget(tb)

        tb.addAction("Page Down", lambda: self.move_to_page(self.page - 1)).setIcon(QApplication.style().standardIcon(QApplication.style().SP_ArrowBack))
        self.lb_page = QLabel()
        tb.addWidget(self.lb_page)
        tb.addAction("Page Up", lambda: self.move_to_page(self.page + 1)).setIcon(QApplication.style().standardIcon(QApplication.style().SP_ArrowForward))
        tb.addSeparator()
        tb.addAction("Zoom out", lambda: self.zoom(self.ratio - 0.1)).setIcon(QIcon.fromTheme("zoom-out"))

        self.lb_zoom = QLabel("{:3d} %".format(int(ratio * 100)))
        self.lb_zoom.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.lb_zoom.setMinimumWidth(50)
        tb.addWidget(self.lb_zoom)
        tb.addAction("Zoom in", lambda: self.zoom(self.ratio + 0.1)).setIcon(QIcon.fromTheme("zoom-in"))

        tb.addSeparator()

        tb.addAction("Save", lambda: self.save_annotations()).setIcon(QApplication.style().standardIcon(QApplication.style().SP_DialogSaveButton))

        # tb.addAction("Refresh", lambda: self.reload()).setIcon(QApplication.style().standardIcon(QApplication.style().SP_BrowserReload))
        # tb.addAction("Remove Annotations", lambda: self.save_annotations(False)).setIcon(QApplication.style().standardIcon(QApplication.style().SP_BrowserStop))

        self.miniature = self.ResizeableQListWidget()
        self.miniature.setMaximumWidth(200)
        self.miniature.itemSelectionChanged.connect(self.pdf_miniature_selected)
        self.miniature.verticalScrollBar().valueChanged.connect(self.check_visibility)
        self.miniature.resizing.connect(self.check_visibility)

        self.splitter = QSplitter()
        self.splitter.addWidget(self.miniature)
        self.splitter.addWidget(self.scroll_area)
        self.splitter.splitterMoved.connect(self.redraw_miniatures)
        main_layout.addWidget(self.splitter)
        self.splitter.setSizes([1, 19])

        # Set the central widget of the Window.
        self.setLayout(main_layout)

        # Variables
        self.annot_click_feedback = None
        self.dpi = 150
        self.ratio = ratio
        self.top_left = None
        self.rects = []
        self.temp = []
        self.rect = None
        self.pdf_name = None
        self.page = 1
        self.pages = []
        self.mutex = QMutex()

    def set_annot_click_feedback(self, callback):
        self.annot_click_feedback = callback

    def resizeEvent(self, ev):
        self.check_visibility()


    def redraw_miniatures(self):
        sizes = self.splitter.sizes()
        for p in self.pages:
            p.resize_miniature(sizes[0] - 25)

    def move_to_page_shot(self, page):
        QTimer.singleShot(50, lambda: self.move_to_page(page))

    def get_annotations(self):
        return self.rects

    def addTemp(self, page, rect):
        a = self.Annotation(page)
        a.fromRect(rect, self.ratio)

    def save_annotations(self, annotations=True):
        doc = fitz.open(self.pdf_name)
        answ = []
        for page_num in range(len(self.rects)):
            page = doc[page_num]
            doc.xref_set_key(page.xref, "Annots", "[]")
            for q in self.rects[page_num]:
                r = q.create_annot(page)
                answ.append(q.get_name())

            doc[page_num].apply_redactions()
        #           Remove Annots
        #           doc.xref_set_key(page.xref, "Annots", "[]")
        answ.sort()

        doc.save(self.pdf_name, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)

    def pdf_miniature_selected(self):
        curr = self.miniature.currentItem()
        if curr is not None:
            idx = self.miniature.currentRow()
            self.move_to_page(idx)

    def set_page(self, index):
        self.lb_page.setText("{} de {}".format(index + 1, len(self.pages)))
        self.page = index
        self.miniature.blockSignals(True)
        self.miniature.setCurrentRow(index)
        self.miniature.blockSignals(False)

    def scrolled(self, event):
        delta = event.angleDelta().y() / 1200
        if 0.1 <= self.ratio + delta <= 3.01:
            self.ratio = self.ratio + delta
            self.zoom_changed()

    def zoom(self, ratio):
        if 0.1 <= ratio <= 3.01:
            self.ratio = ratio
            self.zoom_changed()

    def zoom_changed(self):
        current_page = self.page
        self.lb_zoom.setText("{:d}%".format(int(self.ratio * 100)))
        self.check_visibility()

        def do_zoom():
            self.move_to_page(current_page)

        QTimer.singleShot(10, do_zoom)

    def move_to_page(self, page):

        if 0 <= page < len(self.pages):
            p = self.pages[page]
            p.forceRepaint()

            if self.mode == Qt.Vertical:
                #k = p.resized_image.height()
                #self.scroll_area.verticalScrollBar().setValue(int(page * (k + 6))+5)
                self.scroll_area.verticalScrollBar().setValue(p.image_frame.pos().y()-5)
            else:
                #k = p.resized_image.width()
                #self.scroll_area.horizontalScrollBar().setValue(page * (k + 6))
                self.scroll_area.horizontalScrollBar().setValue(p.image_frame.pos().x()-5)

            self.set_page(page)
            self.force_paint(page)

    def image_requested(self, pdf_page):
        #print("Image requested?", pdf_page)
        self.load_single_page(pdf_page)
        self.pages[pdf_page].show_image()

    def miniature_requested(self, pdf_page):
        #        print("Mini requested? YES", pdf_page)
        self.load_single_page(pdf_page)
        self.pages[pdf_page].show_miniature()

    def adjust_contrast_brightness(self, img, contrast: float = 1.0, brightness: int = 0):
        """
        Adjusts contrast and brightness of an uint8 image.
        contrast:   (0.0,  inf) with 1.0 leaving the contrast as is
        brightness: [-255, 255] with 0 leaving the brightness as is
        """
        brightness += int(round(255 * (1 - contrast) / 2))
        return cv2.addWeighted(img, contrast, img, 0, brightness)

    def load_single_page(self, pdf_page):
        p = self.pages[pdf_page]
        if not p.image_loaded:
            #print("Loading ", pdf_page)
            mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)
            pix = self.doc[pdf_page].get_pixmap(matrix=mat, alpha=False, annots=False)  # render page to an image
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
            img = self.adjust_contrast_brightness(img)
            height, width, channel = img.shape
            image = QImage(img.data, width, height, 3 * width, QImage.Format_RGB888)
            q_image = QPixmap.fromImage(image)

            p.image = q_image
            p.resized_image = q_image.scaledToWidth(int(595 * self.ratio), QtCore.Qt.SmoothTransformation)
            sizes = self.splitter.sizes()
            p.miniature_image = q_image.scaledToWidth((sizes[0] - 25), QtCore.Qt.SmoothTransformation)
            p.image_loaded = True
            return q_image
        return None

    class Pages:
        def __init__(self, index):
            self.index = index
            self.miniature_image = None
            self.image = None
            self.resized_image = None
            self.image_frame = None
            self.miniature_frame = None
            self.image_loaded = False
            self.image_shown = False
            self.miniature_shown = False
            self.miniature_item = None

        def enableImagesSignals(self, value=True):
            self.image_frame.enableSignals(value)
            self.miniature_frame.enableSignals(value)

        def fill(self, dpi, ratio, miniature_size):
            pix = QPixmap(int(595 * dpi / 72), int(842 * dpi / 72))
            pix.fill(Qt.white)
            self.image = pix
            self.resized_image = pix.scaledToWidth(int(595 * ratio))
            self.miniature_image = pix.scaledToWidth(miniature_size, Qt.SmoothTransformation)
            self.miniature_frame.setPixmap(self.miniature_image)
            self.image_frame.setPixmap(self.resized_image)
            self.miniature_item.setSizeHint(self.miniature_frame.sizeHint())

        def clear(self, dpi, ratio, miniature_size):
            self.fill(dpi, ratio, miniature_size)
            self.image_loaded = False
            self.image_shown = False
            self.miniature_shown = False

        def show_image(self):
            # print("Show image?", self.index)
            if not self.image_shown:
                # print("Show image? YES", self.index)
                self.image_frame.setPixmap(self.resized_image, True)
                self.image_shown = self.image_loaded

        def show_miniature(self):
            if not self.miniature_shown:
                self.miniature_frame.setPixmap(self.miniature_image)
                self.miniature_shown = True
            self.miniature_item.setSizeHint(self.miniature_frame.sizeHint())

        def resize_miniature(self, size):
            if self.miniature_image is not None:
                if self.miniature_image.width() != size:
                    self.miniature_image = self.image.scaledToWidth(size, QtCore.Qt.SmoothTransformation)
                    self.miniature_frame.setPixmap(self.miniature_image)

        def invalidate_image(self):
            self.image_shown = False

        def resize(self, ratio):
            self.resized_image = self.image.scaledToWidth(int(self.image.width() * ratio), QtCore.Qt.SmoothTransformation)

        def forceRepaint(self):
            self.image_frame.forceRepaint()
            self.miniature_frame.forceRepaint()

    def open_pdf(self, file_name=None):
        if file_name is None:
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog
            file_name, _ = QFileDialog.getOpenFileName(self, "Open PDF Document", "",
                                                       "PDF Files (*.pdf)", options=options)
        if file_name is not None and file_name != "":

            self.pdf_name = file_name
            self.doc = fitz.open(file_name)

            # Progress bar for large files
            progress = QProgressDialog("Opening file...", "Cancel", 0, len(self.doc), self)
            progress.setWindowModality(Qt.WindowModal)

            # Clear Annotations
            self.rects.clear()

            for pdf_page in range(len(self.doc)):
                progress.setValue(pdf_page)

                for annot in self.doc[pdf_page].annots():
                    r = self.Annotation(pdf_page)
                    r.fromAnnot(annot)
                    self.rects.append(r)

                if progress.wasCanceled():
                    break

                if len(self.pages) < pdf_page + 1:

                    # Prepare frames for Images and Miniatures
                    p = self.Pages(pdf_page)
                    p.image_frame = self.Image(pdf_page, self.mouse_event)
                    p.image_frame.setMouseTracking(True)
                    p.image_frame.setAlignment(Qt.AlignTop)
                    # p.image_frame.painted.connect(self.image_requested)
                    self.scroll_area_layout.addWidget(p.image_frame)

                    item = QListWidgetItem()
                    p.miniature_frame = self.Image(pdf_page, None)
                    # p.miniature_frame.painted.connect(self.miniature_requested)
                    p.miniature_frame.setContentsMargins(5, 5, 5, 5)
                    p.miniature_item = item
                    item.setSizeHint(p.miniature_frame.sizeHint())
                    self.miniature.addItem(item)
                    self.miniature.setItemWidget(item, p.miniature_frame)

                    # Fills frames with white images
                    p.fill(self.dpi, self.ratio, self.splitter.sizes()[0] - 25)

                    # Save pages created
                    self.pages.append(p)
                else:
                    self.pages[pdf_page].clear(self.dpi, self.ratio, self.splitter.sizes()[0] - 25)

            # Remove hypotetical excess pages
            for i in range(len(self.doc), len(self.pages)):
                widget: QWidget = self.pages[i].image_frame
                self.scroll_area_layout.removeWidget(widget)
                widget.deleteLater()
                item = self.miniature.takeItem(len(self.doc))
                del item
            self.pages = self.pages[0:len(self.doc)]

            # Progress done
            progress.setValue(len(self.doc))

            # This is delayed to avoid the calls to resizeEvent() when the frames are created
            # This delay give time to the framework to create and resize the frames correctly
            #QTimer.singleShot(10, self.check_visibility)
            self.check_visibility()

    def check_visibility(self):
        visible = []
        for p in self.pages:
            p.forceRepaint()
            if not p.image_frame.visibleRegion().isEmpty():
                self.load_single_page(p.index)
                if p.resized_image.width() != int(p.image.width()*self.ratio*72/self.dpi):
                    p.invalidate_image()
                    p.resize(self.ratio * 72 / self.dpi)
                p.show_image()
                visible.append(p.index)

            if not p.miniature_frame.visibleRegion().isEmpty():
                self.miniature_requested(p.index)

        # Preresize -5 and +5 images
        if visible:
            for i in range(min(visible) - 0, max(visible)+4):
                if 0 <= i < len(self.pages):
                    p = self.pages[i]
                    if p.resized_image.width() != int(p.image.width()*self.ratio*72/self.dpi):
                        p.invalidate_image()
                        p.resize(self.ratio * 72 / self.dpi)
                    p.show_image()

    def force_paint(self, index=None):
        if index is None:
            index = self.page

        # Extract page, image and prepare painter
        pag = self.pages[index]
        img = pag.resized_image.copy()
        painter = QPainter(img)

        # Paint all the existing rects in any case if not transparent
        for r in self.rects:
            if r.page == index and not r.is_transparent():
                pen = QPen(r.get_qcolor(), 3)
                painter.setPen(pen)
                painter.drawRect(r.get_rect(self.ratio))

        # Put the painted image up
        pag.image_frame.setPixmap(img)
        del painter



    def mouse_event(self, index, object, event):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            self.set_page(index)
            modifiers = QtWidgets.QApplication.keyboardModifiers()
            if modifiers == QtCore.Qt.ControlModifier:
                self.top_left = event.pos()

            for r in self.rects:
                if r.page == self.page and r.isPointWithin(event.pos(), self.ratio):
                    if self.annot_click_feedback is not None:
                        self.annot_click_feedback(r)

        elif event.type() == QtCore.QEvent.MouseMove:
            pos = event.pos()
            pag = self.pages[index]
            img = pag.resized_image.copy()
            painter = QPainter(img)

            # if we started drawing a rectangle, draw it
            if self.top_left is not None:
                self.rect = QRectF(self.top_left.x(), self.top_left.y(), pos.x() - self.top_left.x(), pos.y() - self.top_left.y())
                painter.drawRect(self.rect)

            # Paint all the existing rects anyway
            for r in self.rects:
                if r.page == index and not r.is_transparent():
                    pen = QPen(r.get_qcolor(), 3)
                    painter.setPen(pen)
                    painter.drawRect(r.get_rect(self.ratio))

            # Paint temporary rectangles
            for r in self.temp:
                pen = QPen(r.get_qcolor(), 3)
                painter.setPen(pen)
                painter.drawRect(r.get_rect(self.ratio))

            pag.image_frame.setPixmap(img)
            del painter

        elif event.type() == QtCore.QEvent.MouseButtonRelease:
            if self.rect is not None:
                a = self.Annotation(index)
                a.fromRect(self.rect, self.ratio)
                self.rects.append(a)
                self.rect = None
            self.top_left = None

        return False
