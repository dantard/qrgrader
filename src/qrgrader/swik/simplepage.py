import typing

from PyQt5.QtCore import Qt, QRectF, pyqtSignal, QObject, QMutex, QTimer
from PyQt5.QtGui import QBrush, QColor, QTransform, QPixmap
from PyQt5.QtWidgets import QWidget, QGraphicsView, QGraphicsRectItem, QGraphicsItem, QGraphicsEllipseItem

from qrgrader.swik import utils
from qrgrader.swik.annotations.hyperlink import InternalLink


class SimplePage(QGraphicsRectItem):
    STATE_BLANK = 0
    STATE_WAITING_FINAL = 1
    STATE_FINAL = 2
    STATE_INVALID = 3
    STATE_FORCED = 4
    STATE_IMAGE_REQUESTED = 5

    class Shadow(QGraphicsRectItem):
        pass

    class Box(QGraphicsRectItem):
        pass

    class Signals(QObject):
        image_prepared = pyqtSignal(QPixmap, float)

    def __init__(self, index, view: QGraphicsView, manager, renderer, ratio):
        super().__init__()
        self.words = None
        self.blocks = None
        self.number = None
        self.index = index
        self.manager = manager
        self.renderer = renderer
        self.signals2 = SimplePage.Signals()
        self.signals2.image_prepared.connect(self.image_ready)
        # self.renderer.image_ready.connect(self.image_ready)
        self.ratio = ratio
        self.view = view
        self.state = SimplePage.STATE_INVALID
        self.image = None
        self.w, self.h = self.renderer.get_page_size(index)

        self.setRect(QRectF(0, 0, self.w, self.h))
        self.setAcceptTouchEvents(True)

        self.setBrush(Qt.white)
        self.setPen(Qt.transparent)
        self.lock = QMutex()

        self.box = self.Box(self)
        self.box.setRect(QRectF(0, 0, self.w, self.h))
        self.box.setBrush(QBrush(QColor(80, 80, 80, 80)))
        self.box.setVisible(False)
        # self.box.setFlag(QGraphicsItem.ItemIgnoresTransformations)

        # Shadow
        brush = QBrush(QColor(80, 80, 80, 255))
        self.shadow_right = self.Shadow(self)
        self.shadow_right.setFlag(QGraphicsItem.ItemIgnoresTransformations)

        self.shadow_right.setBrush(brush)
        self.shadow_right.setPen(Qt.transparent)

        self.shadow_bottom = self.Shadow(self)
        self.shadow_bottom.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.shadow_bottom.setBrush(brush)
        self.shadow_bottom.setPen(Qt.transparent)

        self.request_image_timer = QTimer()
        self.request_image_timer.setSingleShot(True)
        self.request_image_timer.timeout.connect(self.process_requested_image)
        self.requested_image_ratio = 1
        self.image_ratio = 0
        self.setTransform(QTransform(ratio, 0, 0, 0, ratio, 0, 0, 0, 1))
        self.original_info = {"page": index}

    def update_original_info(self, info):
        self.original_info.update(info)

    def shine(self, color=QColor(0, 255, 0, 60), delay=1000):
        visible, brush = self.box.isVisible(), self.box.brush()
        self.box.setBrush(QBrush(color))
        self.box.setVisible(True)

        def restore():
            self.box.setBrush(brush)
            self.box.setVisible(visible)

        QTimer.singleShot(delay, restore)

    def get_original_info(self):
        return self.original_info

    def get_index(self):
        return self.index

    def get_view(self):
        return self.view

    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mouseReleaseEvent(event)

    def get_scaled_width(self):
        return self.get_orig_width() * self.get_scaling_ratio()

    def get_scaled_height(self):
        return self.get_orig_height() * self.get_scaling_ratio()

    def update_ratio(self, ratio):
        # print("Updating image for page", self.index, "with ratio", ratio, "and state", self.state)
        # No need to do anything else, the paint called in
        # response to the scale method will take care of it
        self.ratio = ratio
        self.setTransform(QTransform(ratio, 0, 0, 0, ratio, 0, 0, 0, 1))
        self.state = SimplePage.STATE_INVALID
        # self.paint_accessories()

    def get_scaling_ratio(self):
        return self.transform().m11()

    def request_image(self, ratio, now=False):
        self.requested_image_ratio = ratio
        self.request_image_timer.stop()
        self.request_image_timer.start(200 if not now else 5)

    def process_requested_image(self):
        if self.isShown():
            image = self.renderer.render_page(self.index, self.requested_image_ratio)
            self.image_ready(image, self.requested_image_ratio)

    def paint(self, painter, option, widget: typing.Optional[QWidget] = ...) -> None:
        super().paint(painter, option, widget)
        if self.image is None or self.ratio != self.image_ratio:
            # print('Requesting image for page', self.index, self.view)
            self.request_image(self.ratio, self.image is None)
            self.state = SimplePage.STATE_IMAGE_REQUESTED

        if self.image is not None:
            painter.drawImage(QRectF(0, 0, self.rect().width(), self.rect().height()), self.image.toImage())

    def get_image_by_rect(self, rect):
        return self.image.copy(int(rect.x() * self.image_ratio), int(rect.y() * self.image_ratio), int(rect.width() * self.image_ratio),
                               int(rect.height() * self.image_ratio))

    def image_ready(self, image, ratio):
        # print("Image ready for page", self.index, "with state", self.state, "and image", image.width(), "x", image.height())
        self.image = image
        self.image_ratio = ratio
        self.state = SimplePage.STATE_FINAL
        if self.isShown():
            self.update()

    def invalidate(self):
        # print('Invalidating page', self.index)
        self.state = self.STATE_FORCED
        self.image = None
        self.w, self.h = self.renderer.get_page_size(self.index)
        self.setRect(QRectF(0, 0, self.w, self.h))
        self.box.setRect(QRectF(0, 0, self.w, self.h))
        # self.paint_accessories()
        self.update()

    def get_orig_size(self):
        return self.w, self.h

    def get_orig_width(self):
        return self.get_orig_size()[0]

    def get_orig_height(self):
        return self.get_orig_size()[1]

    def paint_accessories(self):
        # Selection Box
        self.box.setRect(self.rect())
        self.box.setBrush(QBrush(QColor(128, 128, 128, 80)))

        # Shadow
        shadow_width = 10
        self.shadow_right.setRect(QRectF(self.get_scaled_width(), shadow_width, shadow_width, self.get_scaled_height()))
        self.shadow_bottom.setRect(
            QRectF(shadow_width, self.get_scaled_height(), self.get_scaled_width(), shadow_width))

    def get_size(self):
        return self.rect().width(), self.rect().height()

    def visible_area(self):
        port_rect = self.view.viewport().rect()
        scene_rect = self.view.mapToScene(port_rect).boundingRect()
        item_rect = self.mapRectFromScene(scene_rect)
        intersection = item_rect.intersected(self.boundingRect())
        return intersection.width() * intersection.height(), intersection

    def items(self, kind=None):
        all = self.scene().items(self.sceneBoundingRect())
        return all if kind is None else [item for item in all if isinstance(item, kind)]

    def isShown(self):
        views = self.scene().views()
        shown = False
        for view in views:
            port_rect = view.viewport().rect()
            scene_rect = view.mapToScene(port_rect).boundingRect()
            item_rect = self.mapRectFromScene(scene_rect)
            intersection = item_rect.intersected(self.boundingRect())
            shown = shown or (not intersection.isEmpty())
        return shown

    def is_completely_shown(self):
        port_rect = self.view.viewport().rect()
        scene_rect = self.view.mapToScene(port_rect).boundingRect()
        item_rect = self.mapRectFromScene(scene_rect)
        intersection = item_rect.intersected(self.boundingRect())
        if intersection.height() < self.rect().height() or intersection.width() < self.rect().width():
            return False
        return True

    def visibleRect(self):
        port_rect = self.view.viewport().rect()
        scene_rect = self.view.mapToScene(port_rect).boundingRect()
        item_rect = self.mapRectFromScene(scene_rect)
        isec = item_rect.intersected(self.boundingRect())
        return isec

    def is_selected(self):
        return self.box.isVisible()

    def set_selected(self, true):
        self.box.setVisible(true)
