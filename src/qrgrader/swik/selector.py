import typing

from PyQt5 import QtGui
from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QFont, QFontMetrics, QImage, QPainter
from PyQt5.QtWidgets import QWidget

from qrgrader.swik.coloreable import ColoreableRectItem
from qrgrader.swik.utils import Signals, check_parent_limits


class SelectorRectItem(ColoreableRectItem):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.signals = Signals()
        self.p1 = None
        self.p2 = None
        if (event := kwargs.get("event", None)) is not None:
            self.view_mouse_press_event(event[0], event[1])

    def get_click_pos(self):
        return self.p1

    def view_mouse_press_event(self, view, event):

        if self.parentItem() is None:
            self.p1 = view.mapToScene(event.pos())
        else:
            self.p1 = self.parentItem().mapFromScene(view.mapToScene(event.pos()))

        self.setPos(self.p1)
        self.setRect(QRectF(0, 0, 0, 0))

    def view_mouse_move_event(self, view, event):
        if self.p1 is not None:
            scene_x, scene_y = view.mapToScene(event.pos()).x(), view.mapToScene(event.pos()).y()
            x, y = check_parent_limits(self.parentItem(), scene_x, scene_y)
            if self.parentItem() is not None:
                pose_on_parent = self.parentItem().mapFromScene(x, y)
                x, y = pose_on_parent.x(), pose_on_parent.y()

            self.setRect(QRectF(0, 0, x - self.p1.x(), y - self.p1.y()).normalized())
            self.signals.creating.emit(self)

    def get_mouse_pos(self):
        return self.p2

    def view_mouse_release_event(self, view, event):
        if self.p1 is not None:
            self.p1 = None
            self.signals.done.emit(self)


class PaintableSelectorRectItem(SelectorRectItem):
    TEXT_MODE_STRETCH = 0
    TEXT_MODE_KEEP = 1
    IMAGE_MODE_STRETCH = 3
    IMAGE_MODE_MAINTAIN_RATIO = 1
    IMAGE_MODE_MAINTAIN_SIZE = 2

    def __init__(self, parent=None, **kwargs):
        # Do NOT change the order of the super() call
        # because it apply_kwargs() and copy() methods would be
        # called before the initialization of the attributes
        self.image_mode, self.image, self.text, self.image_filename = None, None, None, None
        self.text_mode, self.max_font_size, self.font = None, None, None
        super().__init__(parent, **kwargs)
        self.image_rect = self.rect()

    def apply_kwargs(self, **kwargs):
        super().apply_kwargs(**kwargs)
        self.image_mode = kwargs.get("image_mode", self.IMAGE_MODE_MAINTAIN_RATIO)
        self.image = kwargs.get("image", None)
        self.image_filename = kwargs.get("image_filename", None)

        if self.image_filename is not None and self.image is not None:
            raise ValueError("You can't set both image and image_filename")
        elif self.image_filename is not None:
            self.image = QImage(self.image_filename)

        self.text = kwargs.get("text", "")
        self.text_mode = kwargs.get("text_mode", self.TEXT_MODE_STRETCH)
        self.max_font_size = kwargs.get("max_font_size", 100)
        self.font = kwargs.get("font", QFont("Monospace", 12))

    def copy(self, item, **kwargs):
        super().copy(item, **kwargs)
        self.image_mode = item.get_image_mode()
        self.image = item.get_image()
        self.text = item.get_text()
        self.text_mode = item.get_text_mode()
        self.max_font_size = item.get_max_font_size()
        self.font = item.get_font()

    def get_image_mode(self):
        return self.image_mode

    def set_image_mode(self, mode):
        self.image_mode = mode
        self.update()

    def get_source_image(self):
        return self.image

    def set_image(self, image):
        self.image = image
        self.update()

    def get_text(self):
        return self.text

    def set_text(self, text):
        self.text = text
        self.update()

    def get_text_mode(self):
        return self.text_mode

    def set_text_mode(self, mode):
        self.text_mode = mode
        self.update()

    def get_max_font_size(self):
        return self.max_font_size

    def set_max_font_size(self, size):
        self.max_font_size = size
        self.update()

    def get_font(self):
        return self.font

    def set_font(self, font):
        self.font = font
        self.update()

    def compute_image(self):
        image_rect, img = self.rect(), self.image

        if self.image_mode == self.IMAGE_MODE_MAINTAIN_RATIO:
            rw, rh = self.rect().width(), self.rect().height()
            iw, ih = self.image.width(), self.image.height()
            if rw != 0 and iw != 0 and ih != 0:
                i_ratio = ih / iw
                r_ratio = rh / rw
                if r_ratio > i_ratio:
                    ratio = rw / iw
                else:
                    ratio = rh / ih

                qr = QRectF(self.rect().x(), self.rect().y(), iw * ratio, ih * ratio)
                image_rect, img = qr, self.image
                # painter.drawImage(qr, self.image)
        elif self.image_mode == self.IMAGE_MODE_STRETCH:
            image_rect, img = self.rect(), self.image
            # painter.drawImage(self.rect(), self.image)
        elif self.image_mode == self.IMAGE_MODE_MAINTAIN_SIZE:
            w = self.image.width()  # min(self.rect().width(), self.image.width())
            h = self.image.height()  # min(self.rect().height(), self.image.height())
            img = self.image.copy(0, 0, int(w), int(h))
            image_rect = QRectF(self.rect().x(), self.rect().y(), w, h)
            self.setRect(QRectF(0, 0, w, h))

        return image_rect, img

    def get_image(self):
        rect, img = self.compute_image()
        image = QImage(rect.size().toSize(), QImage.Format_ARGB32)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.HighQualityAntialiasing)
        painter.drawImage(rect, img)
        '''
        self.label = QLabel()
        self.label.setPixmap(QtGui.QPixmap(image))
        self.label.show()
        '''
        return image

    def paint(self, painter: QtGui.QPainter, option, widget: typing.Optional[QWidget] = ...) -> None:
        super().paint(painter, option, widget)

        if self.image is not None:
            rect, image = self.compute_image()
            painter.drawImage(rect, image)

        if self.text is not None:

            font_size = self.max_font_size  # * self.init_pos_item.get_scaling_ratio()
            if self.text_mode == self.TEXT_MODE_STRETCH:
                while True:
                    self.font.setPixelSize(max(int(font_size), 1))
                    fm = QFontMetrics(self.font)
                    maxi, lines = 0, self.text.split("\n")
                    for line in lines:
                        maxi = max(fm.horizontalAdvance(line), maxi)

                    font_size = font_size - 1
                    if (maxi <= self.rect().width() and len(lines) * fm.height() <= self.rect().height() + 4) or font_size <= 1:
                        break
            else:
                self.font.setPixelSize(int(max(font_size, 1)))

            painter.setFont(self.font)
            painter.setPen(Qt.black)
            painter.drawText(self.rect(), 0, self.text)

    def get_image_filename(self):
        return self.image_filename

    def get_image_rect_on_parent(self):
        rect, image = self.compute_image()
        if self.parentItem() is None:
            return rect
        else:
            return self.parentItem().mapRectFromItem(self, rect)
