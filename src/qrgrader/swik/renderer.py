import os
import shutil
import tempfile
import time
import traceback
from os.path import exists

import pymupdf
from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QRunnable, QThreadPool, pyqtSignal, QMutex, QRectF, QRect, QByteArray, QBuffer, QIODevice, \
    QTimer, QPointF, QFileSystemWatcher
from PyQt5.QtGui import QPixmap, QImage, QBrush, QPen, QColor
from PyQt5.QtWidgets import QLabel
from pymupdf import TEXTFLAGS_DICT, TEXT_PRESERVE_IMAGES, TextWriter, Font, Point, Document, Rect, Quad, Annot
from pymupdf.mupdf import PDF_ENCRYPT_KEEP, PDF_WIDGET_TYPE_TEXT, PDF_WIDGET_TYPE_CHECKBOX, PDF_ANNOT_IS_LOCKED, \
    PDF_ANNOT_HIGHLIGHT, \
    PDF_ANNOT_SQUARE, PDF_WIDGET_TYPE_RADIOBUTTON, PDF_WIDGET_TYPE_COMBOBOX

import qrgrader.swik.utils as utils
from qrgrader.swik.annotations.highlight_annotation import HighlightAnnotation
from qrgrader.swik.annotations.hyperlink import ExternalLink, InternalLink
from qrgrader.swik.annotations.square_annotation import SquareAnnotation
from qrgrader.swik.font_manager import Base14Font
from qrgrader.swik.span import Span
from qrgrader.swik.swik_text import SwikText, SwikTextReplace
from qrgrader.swik.utils import fitz_rect_to_qrectf
from qrgrader.swik.widgets.pdf_widget import PdfTextWidget, MultiLinePdfTextWidget, PdfCheckboxWidget, PdfWidget, \
    PdfRadioButtonWidget, PdfComboboxWidget
from qrgrader.swik.word import Word


class Image:
    def __init__(self, w, h):
        self.image = QPixmap(int(w), int(h))
        self.ratio = 1
        self.loaded = False
        self.image.fill(Qt.white)
        self.w = w
        self.h = h

    def update(self, w, h):
        self.image = QPixmap(int(w), int(h))
        self.ratio = 1
        self.loaded = False
        self.image.fill(Qt.white)
        self.w = w
        self.h = h

    def get_image(self, ratio):
        if self.ratio != ratio:
            res = self.image.scaledToWidth(int(self.w * ratio), QtCore.Qt.FastTransformation)
            return res
        else:
            return self.image

    def set_image(self, image, ratio):
        self.image = image
        self.ratio = ratio

    def get_orig_size(self):
        return self.w, self.h


def convert_box_to_upside_down(filename, index, rect):
    # The signing is not done using PyMuPDF, so we need to compute
    # the square in the pyhanko page (which to make everything
    # more complicated uses upside-down coordinates (notice dy))
    # We need to get some info from the file that is about to be signed
    # that can be different from the one we are seeing (e.g. flatten + sign)

    # Open the doc to sign
    doc_to_sign = pymupdf.open(filename)

    # The projection is necessary to take into account orientation
    # rot = self.renderer.get_rotation(page.index)
    rot = doc_to_sign[index].rotation

    # Get page size
    # w, h = self.renderer.get_page_size(page.index)
    w, h = doc_to_sign[index].rect[2], doc_to_sign[index].rect[3]

    # Get derotation matrix
    derot_matrix = doc_to_sign[index].derotation_matrix

    # Close the file, it is not needed anymore
    doc_to_sign.close()

    # Take into account that pyhanko uses upside-down coordinates
    dy = w if rot == 90 or rot == 270 else h

    # Rotate according to the orientation and create thw box
    # r1 = self.renderer.project(fitz.Point(rect.x(), rect.y()), page.index)
    r1 = Point(rect.x(), rect.y()) * derot_matrix
    box = (r1.x,
           dy - r1.y,
           r1.x + rect.width(),
           dy - (r1.y + rect.height())
           )
    return box


class MuPDFRenderer(QLabel):
    # Signals
    document_changed = pyqtSignal()
    document_about_to_change = pyqtSignal()
    image_ready = pyqtSignal(int, float, QImage)
    sync_requested = pyqtSignal()
    sync_dynamic = pyqtSignal()
    page_updated = pyqtSignal(int)
    words_changed = pyqtSignal(int)
    file_changed = pyqtSignal(str)

    # Constants
    OPEN_OK = 1
    OPEN_ERROR = 2
    OPEN_REQUIRES_PASSWORD = 3

    FLATTEN_OK = 0
    FLATTEN_WORKAROUND = 1
    FLATTEN_ERROR = 2

    def __init__(self):
        super().__init__()
        self.filename = None
        self.images = []
        self.document = None
        self.mutex = []
        self.max_width = 0
        self.max_height = 0
        self.h = QThreadPool()
        self.h.setMaxThreadCount(100)
        self.request_queue_timer = QTimer()
        self.request_queue_timer.setSingleShot(True)
        self.request_queue_timer.timeout.connect(self.process_request_queue)
        self.request_queue = {}
        self.watcher = QFileSystemWatcher()
        self.password = None
        self.watcher.fileChanged.connect(self.file_has_changed)

    def file_has_changed(self, file):
        self.file_changed.emit(file)

    def open_pdf(self, file, password=None):
        self.filename = file

        if self.watcher.files():
            self.watcher.removePaths(self.watcher.files())
        self.watcher.addPath(self.filename)

        try:
            self.document = Document(file)
            if self.document.needs_pass:
                self.password = password

                if password is None:
                    return self.OPEN_REQUIRES_PASSWORD
                else:
                    self.document.authenticate(password)

            self.set_document(self.document, True)
            return self.OPEN_OK

        except:
            traceback.print_exc()
            return self.OPEN_ERROR

    def save_pdf(self, filename, emit=True):
        print("Saving to in renderer", filename)
        if self.watcher.files():
            self.watcher.removePaths(self.watcher.files())

        self.sync_requested.emit()
        orig_data = self.document.tobytes(encryption=PDF_ENCRYPT_KEEP, deflate=True, garbage=3)
        orig_doc = pymupdf.open("pdf", orig_data)

        self.sync_dynamic.emit()

        if filename != self.get_filename():
            self.document.save(filename, encryption=PDF_ENCRYPT_KEEP, deflate=True, garbage=3)
        else:
            tmp_dir = tempfile.gettempdir() + os.sep
            temp_filename = tmp_dir + "swik_{}.tmp".format(int(time.time()))

            self.document.save(temp_filename, encryption=PDF_ENCRYPT_KEEP, deflate=True, garbage=3)
            self.document.close()

            shutil.copy2(temp_filename, filename)

            if exists(temp_filename):
                os.remove(temp_filename)

        self.filename = filename
        self.watcher.addPath(self.filename)

        self.set_document(orig_doc, False)
        return True

    def get_page_size(self, index):
        return self.document[index].rect[2], self.document[index].rect[3]

    def get_page_width(self, index):
        return self.document[index].rect[2]

    def get_page_height(self, index):
        return self.document[index].rect[3]

    def set_image(self, index, image, ratio):
        self.images[index].set_image(image, ratio)
        self.images[index].loaded = True

    def get_num_of_pages(self):
        return len(self.document) if self.document else 0

    def get_max_pages_size(self):
        return self.max_width, self.max_height

    def set_document(self, document, emit):
        self.document_about_to_change.emit()
        self.document = document
        self.images.clear()
        self.mutex.clear()
        self.max_width = 0
        self.max_height = 0

        for i in range(self.get_num_of_pages()):
            w, h = self.get_page_size(i)
            self.max_width = max(self.max_width, w)
            self.max_height = max(self.max_height, h)
            self.images.append(Image(w, h))
            self.mutex.append(QMutex())

        if emit:
            self.document_changed.emit()

    def process_request_queue(self):
        for index, ratio in self.request_queue.items():
            self.load(index, ratio, True)
        # self.request_queue.clear()

    def request_image(self, index, ratio, force=False):
        # print("Requesting image", index, ratio, force)
        if not self.images[index].loaded or force:
            self.load(index, ratio, force)
        elif self.images[index].ratio != ratio:
            self.request_queue_timer.stop()
            self.request_queue_timer.start(100)
            self.request_queue[index] = ratio

    def get_image(self, index, ratio):
        return self.images[index].get_image(ratio)

    def render_page(self, index, ratio):
        mat = pymupdf.Matrix(ratio, ratio)
        pix = self.get_document()[index].get_pixmap(matrix=mat, alpha=False, annots=True)
        return QPixmap.fromImage(QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888))

    def render_image(self, index, ratio):
        mat = pymupdf.Matrix(ratio, ratio)
        pix = self.get_document()[index].get_pixmap(matrix=mat, alpha=False, annots=True)
        return QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)

    def load(self, index, ratio, force):
        class Loader(QRunnable):
            def __init__(self, renderer: MuPDFRenderer, index, ratio, mutex):
                super().__init__()
                self.renderer = renderer
                self.index = index
                self.ratio = ratio
                self.force = force

            def get_pixmap(self):
                mat = pymupdf.Matrix(self.ratio, self.ratio)

                pix = self.renderer.get_document()[self.index].get_pixmap(matrix=mat, alpha=False, annots=True)
                image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)

                # pixmap = QPixmap.fromImage(image)
                self.renderer.set_image(index, image, ratio)
                self.renderer.image_ready.emit(self.index, self.ratio, image)

            def run(self):
                image = self.renderer.images[self.index]
                if self.force:
                    self.get_pixmap()
                elif image.ratio == self.ratio and image.loaded:
                    # print("As is ", self.index, self.key)
                    self.renderer.image_ready.emit(self.index, self.ratio, image.image)
                elif image.ratio > self.ratio and image.loaded:
                    # print("Scaling down ", self.index, self.key)
                    pixmap = image.image.scaledToWidth(int(image.w * ratio), QtCore.Qt.SmoothTransformation)
                    self.renderer.image_ready.emit(self.index, self.ratio, pixmap)
                else:
                    self.get_pixmap()

        loader = Loader(self, index, ratio, self.mutex[index])
        self.h.start(loader)

    def get_document(self):
        return self.document

    def get_filename(self):
        return self.filename

    def extract_spans(self, page_id):

        spans = []
        boxes = self.document[page_id].get_text("dict", sort=True, flags=TEXTFLAGS_DICT & ~TEXT_PRESERVE_IMAGES)[
            "blocks"]

        for box in boxes:
            for line in box.get("lines", []):
                for span in line.get("spans", []):
                    sp = Span()
                    x1, y1, x2, y2 = span["bbox"]

                    fitz_rect = Rect(x1, y1, x2, y2) * self.document[page_id].rotation_matrix
                    x1, y1, x2, y2 = fitz_rect.x0, fitz_rect.y0, fitz_rect.x1, fitz_rect.y1

                    sp.text = span["text"]
                    sp.rect = QRectF(x1, y1, x2 - x1, y2 - y1)
                    sp.font = span["font"]
                    sp.size = span["size"]
                    sp.ascender = span["ascender"]
                    sp.descender = span["descender"]

                    h = span["color"]
                    b = h & 255
                    g = (h >> 8) & 255
                    r = (h >> 16) & 255
                    sp.color = QColor(r, g, b)

                    '''
                    a = span["ascender"]
                    d = span["descender"]
                    r = fitz.Rect(span["bbox"])
                    o = fitz.Point(span["origin"])  # its y-value is the baseline
                    r.y1 = o.y - span["size"] * d / (a - d)
                    r.y0 = r.y1 - span["size"]
                    sp.rect = QRectF(r.x0, r.y0, r.x1 - r.x0, r.y1 - r.y0)
                    # r now is a rectangle of height 'fontsize'
                    '''

                    spans.append(sp)
        return spans

    def extract_words(self, page_id):

        boxes = self.document[page_id].get_text("words", sort=True, flags=TEXTFLAGS_DICT & ~TEXT_PRESERVE_IMAGES)

        word_objs = list()

        for i, w in enumerate(boxes):
            x1, y1, x2, y2, text, block_no, line_no, word_no = w

            # Compute rectangle taking into account orientation
            fitz_rect = Rect(x1, y1, x2, y2) * self.document[page_id].rotation_matrix
            rect = fitz_rect_to_qrectf(fitz_rect)

            word = Word(page_id, i, text, rect, word_no=word_no, line_no=line_no, block_no=block_no)
            word_objs.append(word)

        return word_objs

    def get_word_font_info(self, word: Word):
        data = self.document[word.page_id].get_text("dict", sort=False, flags=TEXTFLAGS_DICT & ~TEXT_PRESERVE_IMAGES)
        if data is not None:
            blocks = data.get('blocks', [])
            # print(blocks)
            if len(blocks) > word.block_no:
                lines = blocks[word.block_no]
                if lines is not None:
                    lines = lines.get('lines', [])
                    if len(lines) > word.line_no:
                        line = lines[word.line_no]
                        # print(line)
                        for span in line.get("spans", []):
                            # print(span)
                            x1, y1, x2, y2 = span["bbox"]
                            rect2 = QRectF(int(x1), int(y1), int(x2 - x1), int(y2 - y1))
                            # rect = QRectF(word.pos().x(), word.pos().y(), word.rect().width(), word.rect().height())
                            pr = word.get_rect_on_parent()
                            rect = QRectF(pr.x(), pr.y(), pr.width(), pr.height())
                            if rect2.intersected(rect):
                                h = span.get("color")
                                b = h & 255
                                g = (h >> 8) & 255
                                r = (h >> 16) & 255
                                return span.get('font'), span.get('size'), QColor(r, g, b)
        return "helv", 11, QColor(0, 0, 0)

    def rearrange_pages(self, order, emit):
        self.document.select(order)
        self.set_document(self.document, emit)

    def set_cropbox(self, page, rect: QRect, absolute=False):

        x, y, w, h = int(rect.x()), int(rect.y()), int(rect.width()), int(rect.height())

        if not absolute:
            # in this case the square is relative to the current cropbox
            cx, cy = self.document[page].cropbox.x0, self.document[page].cropbox.y0
        else:
            cx, cy = 0, 0

        mx1, my1, mx2, my2 = self.document[page].mediabox

        self.document[page].set_cropbox(Rect(max(x + cx, mx1),
                                             max(y + cy, my1),
                                             min(x + cx + w, mx2),
                                             min(y + cy + h, my2)) * self.document[
                                            page].derotation_matrix)
        w, h = self.get_page_size(page)
        self.images[page].update(w, h)
        self.page_updated.emit(page)

        return True

    def get_cropbox(self, page):
        x0, y0 = self.document[page].cropbox.x0, self.document[page].cropbox.y0
        x1, y1 = self.document[page].cropbox.x1, self.document[page].cropbox.y1
        return QRectF(x0, y0, x1 - x0, y1 - y0)

    def add_redact_annot(self, index, rect, color=None, minimize=False, apply=True):
        if minimize:
            # Create a 1 pixel high rect to avoid removing adjacent text
            rect = QRectF(rect.x(), rect.center().y(), rect.width(), 1)
        page = self.document[index]
        rect = utils.qrectf_to_fitz_rect(rect)
        if color is not None:
            color = utils.qcolor_to_fitz_color(QColor(color))
        page.add_redact_annot(rect, fill=color)
        if apply:
            page.apply_redactions(1)

    def apply_redactions(self, index):
        self.document[index].apply_redactions()

    annoting = None

    def add_highlight_annot(self, index, swik_annot):
        # For some reason, the annoting page must be stored
        annoting = self.document[index]
        quads = []
        for r in swik_annot.get_quads():  # type: QRectF
            q = Quad((r.x(), r.y()),
                     (r.x() + r.width(), r.y()),
                     (r.x(), r.y() + r.height()),
                     (r.x() + r.width(), r.y() + r.height()))
            quads.append(q)
        fitz_annot: Annot = annoting.add_highlight_annot(quads=quads)
        color = swik_annot.get_color()
        stroke = utils.qcolor_to_fitz_color(color)
        fitz_annot.set_info(None, swik_annot.get_content(), "", "", "", "")
        fitz_annot.set_colors(stroke=stroke)
        fitz_annot.set_opacity(color.alpha() / 255 if stroke is not None else 0.0)

        fitz_annot.update()

    def uncrop(self, index):
        self.document[index].set_cropbox(self.document[index].mediabox)
        self.page_updated.emit(index)

    def is_cropped(self, index):
        return self.document[index].cropbox != self.document[index].mediabox

    def get_annotations(self, index):

        annots = list()
        for annot in self.document[index].annots():  # type: Annot

            if annot.type[0] == PDF_ANNOT_SQUARE:
                opacity = annot.opacity if 1 > annot.opacity > 0 else 0.999
                stroke = utils.fitz_color_to_qcolor(annot.colors['stroke'], opacity) if annot.colors[
                                                                                            'stroke'] is not None else Qt.transparent
                fill = utils.fitz_color_to_qcolor(annot.colors['fill'], opacity) if annot.colors[
                                                                                        'fill'] is not None else Qt.transparent
                border_width = annot.border['width']
                pen = QPen(stroke, border_width)

                swik_annot = SquareAnnotation(None, brush=fill, pen=pen)

                annot.set_rect(annot.rect * self.document[index].rotation_matrix)

                swik_annot.setRect(QRectF(0, 0, annot.rect[2] - annot.rect[0], annot.rect[3] - annot.rect[1]))
                swik_annot.set_content(annot.info["content"])
                swik_annot.set_name(annot.info["name"])
                swik_annot.setToolTip(swik_annot.get_content())
                locked = annot.flags & PDF_ANNOT_IS_LOCKED
                swik_annot.set_movable(not locked)
                swik_annot.setPos(annot.rect[0], annot.rect[1])

                annots.append(swik_annot)
                self.document[index].delete_annot(annot)
            elif annot.type[0] == PDF_ANNOT_HIGHLIGHT:
                color = utils.fitz_color_to_qcolor(annot.colors["stroke"], annot.opacity)
                # print(annot.colors, annot.opacity)
                swik_annot = HighlightAnnotation(color, None)
                swik_annot.set_content(annot.info["content"])
                swik_annot.setRect(QRectF(0, 0, annot.rect[2] - annot.rect[0], annot.rect[3] - annot.rect[1]))
                swik_annot.setPos(annot.rect[0], annot.rect[1])
                points = annot.vertices
                if points is not None:
                    quad_count = int(len(points) / 4)
                    for i in range(quad_count):
                        rect = Quad(points[i * 4: i * 4 + 4]).rect
                        rect = rect * self.document[index].rotation_matrix
                        quad = utils.fitz_rect_to_qrectf(rect)
                        swik_annot.add_quad(quad)
                annots.append(swik_annot)
                self.document[index].delete_annot(annot)

            '''
            elif a.type[0] == fitz.PDF_ANNOT_HIGHLIGHT:
                annot = HighlightAnnotation()
                annot.fromHighlight(a, self.document[index])
                # print("--------------->", a.colors["stroke"], a.opacity)
                annot.setBrush(utils.qcolor_from_stroke(a.colors["stroke"]))
                annot.setOpacity(a.opacity)
                annots.append(annot)
                self.document[index].delete_annot(a)
            elif a.type[0] == fitz.PDF_ANNOT_FREE_TEXT:
                a.set_rect(a.rect * self.document[index].rotation_matrix)
                annot = FreeTextAnnot()
                # print(self.document.xref_object(a.xref))
                annot.fromFitzAnnot(a)
                fields = self.document.xref_get_key(a.xref, "DA")[1].strip().split(" ")

                r, g, b = 0, 0, 0
                font, font_size = "/Helv", 11
                for i, f in enumerate(fields):
                    if f == "rg":
                        r, g, b = float(fields[i - 3]), float(fields[i - 2]), float(fields[i - 1])
                    elif f == "g":
                        r, g, b = float(fields[i - 1]), float(fields[i - 1]), float(fields[i - 1])
                    elif f == "Tf":
                        font = fields[i - 2]
                        font_size = float(fields[i - 1])

                pen = annot.pen()
                pen.setColor(QColor(Qt.transparent))
                annot.setPen(pen)
                annot.set_font(font, font_size, QColor(int(r * 255), int(g * 255), int(b * 255)))
                annot.set_border_color(QColor(int(r * 255), int(g * 255), int(b * 255)))

                annots.append(annot)
                self.document[index].delete_annot(a)
            '''
        return annots

    def add_annot(self, index, annot):
        if type(annot) == SquareAnnotation:
            # print("adding", index, annot.rect(), annot.pos())
            page = self.document[index]
            fitz_rect = utils.qrectf_and_pos_to_fitz_rect(annot.rect(), annot.pos())
            pen: QPen = annot.pen()
            brush: QBrush = annot.brush()
            fitz_annot = page.add_rect_annot(fitz_rect)  # 'Square'
            fitz_annot.set_border(width=pen.width())
            fitz_annot.set_colors(stroke=utils.qcolor_to_fitz_color(pen.color()),
                                  fill=utils.qcolor_to_fitz_color(brush.color()))
            opacity = min(brush.color().alpha() / 255, 0.999)
            fitz_annot.set_opacity(opacity)
            fitz_annot.set_info(None, annot.get_content(), "", "", "", "")
            fitz_annot.update()

    def add_text(self, index, item: SwikText):
        self.document[index].clean_contents()
        color = utils.qcolor_to_fitz_color(item.defaultTextColor())
        tw = TextWriter(self.document[index].rect, color=color)
        x, y, h = item.pos().x(), item.pos().y(), item.sceneBoundingRect().height()

        if type(item.get_font_info()) == Base14Font:
            font = Font(fontname=item.get_font_info().nickname)
        else:
            font = Font(fontfile=item.get_font_info().path)

        # tw.append((x,y + h), item.get_text(), font=font, fontsize=item.font().pointSizeF()*1.32)
        rect = utils.qrectf_and_pos_to_fitz_rect(item.get_rect_on_parent(), item.pos())

        rect.x1 = rect.x1 + 5
        rect.x0 = rect.x0 - item.font().pointSizeF() / 3.5
        # rect.y0 += item.font().pointSizeF() / 4
        # rect.y1 += item.font().pointSizeF() / 4

        page: pymupdf.Page = self.document[index]

        # align=pymupdf.TEXT_ALIGN_JUSTIFY
        if False:
            css = """
            @font-face {font-family: comic; src: url(""" + item.get_font_info().path + """);}            
            * {font-family: comic; font-size: """ + str(item.font().pointSizeF() * 96.0 / 72.0) + """px; color: rgb(255,0,0);}
            """
            tw.fill_textbox(rect, item.get_text(), font=font, fontsize=item.font().pointSizeF() * 96 / 72)
            # align=pymupdf.TEXT_ALIGN_JUSTIFY)  ## TODO: 1.325
            #            text = "<div>Some text</div>"

            # rect.x0 = rect.x0 + item.font().pointSizeF() / 3.5
            # page.insert_htmlbox(rect, item.get_text(), css=css)
            #                                css="* {font-family:" + item.font().family() + ";font-size:" + str(item.font().pointSizeF() * 96 / 72) + "px;}")
            # css=)

        else:
            tw.fill_textbox(rect, item.get_text(), font=font, fontsize=item.font().pointSizeF() * 96 / 72)
            tw.write_text(self.document[index])
        # page: pymupdf.Page = self.document[index]
        # page.draw_rect(rect, color=(1, 0, 0), width=1)

    def replace_word(self, index, text: SwikTextReplace):
        self.document[index].clean_contents()
        self.add_redact_annot(index, text.get_rect_on_parent(), minimize=True)
        self.add_text(index, text)

    def get_widgets(self, index):
        doc_page = self.document[index]
        pdf_widgets = list()
        widgets = doc_page.widgets()
        count = 0
        for field in widgets:  # type: pymupdf.Widget

            swik_widget = None
            rect = QRectF(field.rect[0], field.rect[1], field.rect[2] - field.rect[0],
                          field.rect[3] - field.rect[1])

            if field.field_type == PDF_WIDGET_TYPE_TEXT:
                if field.field_flags & 4096:
                    swik_widget = MultiLinePdfTextWidget(None, field.field_value, rect, field.text_fontsize)
                else:
                    swik_widget = PdfTextWidget(None, field.field_value, rect, field.text_fontsize)

            elif field.field_type == PDF_WIDGET_TYPE_CHECKBOX:
                swik_widget = PdfCheckboxWidget(None, field.field_value == field.on_state().replace("#20", " "), rect,
                                                field.text_fontsize)

            elif field.field_type == PDF_WIDGET_TYPE_RADIOBUTTON:
                swik_widget = PdfRadioButtonWidget(None, field.field_value == field.on_state().replace("#20", " "),
                                                   rect, field.text_fontsize)

            elif field.field_type == PDF_WIDGET_TYPE_COMBOBOX:
                items = [str(item) for item in field.choice_values]
                swik_widget = PdfComboboxWidget(None, field.field_value, rect, field.text_fontsize, items)
                swik_widget.setZValue(1000 - count)
                count = count + 1
                # combo_field.set_info(field.field_name, field.field_flags)
                # pdf_widgets.append(combo_field)
                # self.document[page.index].delete_widget(field)
                # self.to_remove.append(field)

            if swik_widget is not None:
                '''swik_widget.set_info(field.field_name, field.field_flags)
                swik_widget.user_data = field.__dict__.copy()                
                self.document[page.index].delete_widget(field)
                '''
                swik_widget.xref = str(field.field_type) + "_" + str(field.field_name) + "_" + str(
                    field.rect[0]) + "_" + str(field.rect[1])
                swik_widget.on_state = field.on_state()
                pdf_widgets.append(swik_widget)

            '''
            
            '''

        return pdf_widgets

    def add_widget(self, index, swik_widget: PdfWidget):
        page = self.document[index]
        widgets = page.widgets()
        for field in widgets:
            xref = str(field.field_type) + "_" + str(field.field_name) + "_" + str(field.rect[0]) + "_" + str(
                field.rect[1])
            if xref == swik_widget.xref:

                value = swik_widget.get_value()
                if isinstance(swik_widget, PdfCheckboxWidget) and value:

                    try:
                        field.field_value = field.on_state()
                        field.update()
                    except TypeError:
                        self.document.xref_set_key(field.xref, "AS", "/Yes")
                else:
                    field.field_value = value
                    field.update()

                return

    def sanitize(self):
        clean_doc_data = self.document.tobytes(encryption=PDF_ENCRYPT_KEEP, deflate=True, garbage=3)
        clean_doc = pymupdf.open("pdf", clean_doc_data)
        return clean_doc

    def flatten(self, filename):

        # Save the old document, to be restored later
        original = self.document

        # Sanitize the document that is gonna be
        # flattened, establish it as the current
        # document (necessary for sync_request)
        self.set_document(self.sanitize(), False)

        # Prepare for baking
        self.sync_requested.emit()
        self.sync_dynamic.emit()

        # Bake document
        self.document.bake()
        self.document.save(filename, encryption=PDF_ENCRYPT_KEEP, deflate=True, garbage=3)
        self.document.close()

        # Restore original document and
        # set it as the current document
        self.set_document(original, False)

        return self.FLATTEN_OK

    def save_elsewhere(self, filename):
        current_doc_data = self.document.tobytes(encryption=PDF_ENCRYPT_KEEP, deflate=True, garbage=3)
        self.sync_requested.emit()
        self.document.save(filename, encryption=PDF_ENCRYPT_KEEP, deflate=True, garbage=3)
        current_doc = pymupdf.open("pdf", current_doc_data)
        self.set_document(current_doc, False)

    def save_fonts(self, out_dir):
        font_xrefs = set()
        font_names = set()
        for pno in range(self.get_num_of_pages()):
            itemlist = self.document.get_page_fonts(pno)
            for item in itemlist:
                xref = item[0]
                if xref not in font_xrefs:
                    font_xrefs.add(xref)
                    fontname, ext, k, buffer = self.document.extract_font(xref)
                    # print("Extracting", fontname, ext)
                    font_names.add(fontname)
                    if ext == "n/a" or not buffer:
                        continue
                    outname = os.path.join(
                        out_dir, f"{fontname.replace(' ', '-')}-{xref}.{ext}"
                    )
                    outfile = open(outname, "wb")
                    outfile.write(buffer)
                    outfile.close()
        return font_names

    def export_pages(self, order, filename):
        doc = pymupdf.open()
        for i in order:
            doc.insert_pdf(self.document, from_page=i, to_page=i)
        try:
            doc.save(filename, encryption=PDF_ENCRYPT_KEEP, deflate=True, garbage=3)
            doc.close()
        except Exception as e:
            return False
        return True

    def insert_blank_page(self, index, width, height):
        self.document.new_page(index, width=width, height=height)

    def insert_image(self, index, rect, qimage):
        self.document[index].clean_contents()
        rect = Rect(rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height())
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.WriteOnly)
        qimage.save(buffer, "PNG")

        # Create a fitz.Pixmap from the bytes
        pixmap = pymupdf.Pixmap(byte_array.data())
        self.document[index].insert_image(rect, pixmap=pixmap)

    def insert_image_from_file(self, index, rect, filename):
        self.document[index].clean_contents()
        rect = Rect(rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height())
        self.document[index].insert_image(rect, filename=filename, keep_proportion=False)

    def insert_image2(self, index, rect, qimage):
        rect = pymupdf.Rect(rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height())
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.WriteOnly)
        qimage.save(buffer, "PNG")

        # Create a fitz.Pixmap from the bytes
        pixmap = pymupdf.Pixmap(byte_array.data())
        self.document[index].insert_image(rect, pixmap=pixmap)

    def append_blank_page(self, width=595, height=842):
        self.document.new_page(-1, width=width, height=height)
        self.set_document(self.document, False)

    def rotate_page(self, index, angle):
        self.document[index].set_rotation(self.document[index].rotation + angle)
        self.set_document(self.document, False)

    def get_links(self, index):
        x0, y0 = self.document[index].cropbox.x0, self.document[index].cropbox.y0
        x1, y1 = self.document[index].cropbox.x1, self.document[index].cropbox.y1

        self.page_links = self.document[index]
        pdf_link = self.page_links.first_link
        links = []
        while pdf_link is not None:
            rx, ry = pdf_link.rect[0], pdf_link.rect[1]
            if rx < 0 or rx > x1 - x0 or ry < 0 or ry > y1 - y0:
                pdf_link = pdf_link.next
                continue

            rect = utils.fitz_rect_to_qrectf(pdf_link.rect)

            if pdf_link.is_external:
                link = ExternalLink(rect, pdf_link.uri)
            else:
                index, x, y = self.document.resolve_link(pdf_link.uri)
                link = InternalLink(rect, (index, x, y))

            links.append(link)
            pdf_link = pdf_link.next

        return links

    def get_toc(self):
        class TOC:
            def __init__(self, level, title, page, to, kind):
                self.level = level
                self.title = title
                self.page = page
                self.to = to
                self.kind = kind

        doc_toc = self.document.get_toc(False)
        toc_items = []

        names = self.document.resolve_names()

        for item in doc_toc:
            page_no = item[2] - 1

            point = item[3].get("to", Point(0, 0))

            if item[3].get('kind', -1) == 4 and item[3].get("nameddest", None) is not None:
                to = names.get(item[3]["nameddest"], None)
                if to is not None:
                    x, y = to.get("to", (0, 0))
                    point = Point(x, y) * self.document[page_no].transformation_matrix

            toc_item = TOC(item[0], item[1], page_no, QPointF(point.x, point.y), item[3]['kind'])
            toc_items.append(toc_item)
        return toc_items

    def set_metadata(self, metadata):
        self.document.set_metadata(metadata)

    def get_metadata(self):
        return self.document.metadata

    def get_xml_metadata(self):
        try:
            md = self.document.get_xml_metadata()
        except:
            md = ""
        return md

    def set_xml_metadata(self, xml):
        self.document.set_xml_metadata(xml)

    def get_images(self, index):
        images = list()

        p = self.document[index]
        image_list = p.get_images(full=True)
        for image_index, img in enumerate(image_list):
            # get the XREF of the image
            xref = img[0]
            rect = p.get_image_bbox(img)
            rect2 = QRectF(0, 0, rect.x1 - rect.x0, rect.y1 - rect.y0)

            # extract the image bytes
            base_image = self.document.extract_image(xref)
            image_bytes = base_image["image"]
            w, h = base_image["width"], base_image["height"]
            # get the image extension
            image_ext = base_image["ext"]

            pix = pymupdf.Pixmap(image_bytes)
            # doc[-1].insert_image(rect, pixmap=fitz.Pixmap(image_bytes))
            image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            images.append((image, rect.x0, rect.y0, rect2))

        # for _, _, _, rect in images:
        #    p.add_redact_annot(rect)  # cover top-left image with aredaction
        #    p.apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE)
        #    # p.delete_image(img[0])

        # self.refresh()
        return images
