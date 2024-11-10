from multiprocessing.pool import ThreadPool

from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal, QCoreApplication, Qt, QEvent, QPoint, QTimer, QMutex, QRectF
from PyQt5.QtGui import QWheelEvent, QPainter, QColor, QKeyEvent
from PyQt5.QtWidgets import QGraphicsView, QGraphicsRectItem, QApplication, QScrollBar, QGraphicsEllipseItem
from qrgrader.swik.miniature_page import MiniaturePage

from qrgrader.swik import utils
from qrgrader.swik.annotations.hyperlink import InternalLink
# import EnhancedPage
from qrgrader.swik.sync_dict import SyncDict
from qrgrader.swik.simplepage import SimplePage
from qrgrader.swik.word import Word


class SB(QScrollBar):
    pass


class GraphView(QGraphicsView):
    # ## Layout modes
    MODE_VERTICAL = 0
    MODE_VERTICAL_MULTIPAGE = 1
    MODE_HORIZONTAL = 2
    MODE_SINGLE_PAGE = 3
    MODE_FIT_WIDTH = 4
    MODE_FIT_PAGE = 5

    modes = {MODE_VERTICAL: 'Vertical', MODE_VERTICAL_MULTIPAGE: 'Multi page',
             MODE_HORIZONTAL: 'Horizontal', MODE_SINGLE_PAGE: 'Single Page', MODE_FIT_WIDTH: 'Fit Width',
             MODE_FIT_PAGE: 'Fit Page'}

    Vertical = [MODE_VERTICAL, MODE_VERTICAL_MULTIPAGE, MODE_SINGLE_PAGE, MODE_FIT_WIDTH, MODE_FIT_PAGE]

    ratio_max = 5
    ratio_min = 0.25

    # ## Signals
    mouseEvent = pyqtSignal(QEvent)
    page_changed = pyqtSignal(int, int)
    processing = pyqtSignal(str, int, int)
    ratio_changed = pyqtSignal(float)
    drop_event = pyqtSignal(QtGui.QDropEvent)
    document_ready = pyqtSignal()
    page_created = pyqtSignal(SimplePage)
    page_clicked = pyqtSignal(int)

    def eventFilter(self, a0: QtCore.QObject, a1: QtCore.QEvent) -> bool:
        if self.scene().focusItem() is not None:
            return False

        if a1.type() == QKeyEvent.KeyPress:
            if a1.key() == Qt.Key_Left:
                self.move_to_page(self.page - 1)
                return True
            elif a1.key() == Qt.Key_Right:
                self.move_to_page(self.page + 1)
                return True

        return False

    def __init__(self, manager, renderer, scene, page=SimplePage, mode=MODE_VERTICAL_MULTIPAGE,
                 align=Qt.AlignVCenter | Qt.AlignHCenter,
                 page_sep=27):
        super().__init__()
        self.on_document_ready = []
        self.previous_state = 0, 0, None
        self.page_object = page
        self.ratio = 1
        self.natural_hscroll = False
        self.renderer = renderer
        self.manager = manager
        self.page = 0
        self.pages = SyncDict()
        self.immediate_resize = False
        self.page_sep = page_sep

        self.installEventFilter(self)

        self.setScene(scene)
        self.scene().setBackgroundBrush(Qt.gray)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.align = Qt.AlignVCenter
        self.setVerticalScrollBar(SB())
        # ## Connect signals
        # self.renderer.document_changed.connect(self.document_changed)
        self.renderer.page_updated.connect(self.page_updated)

        # Mode and alignment
        self.mode = mode
        self.scene_width, self.scene_height = 0, 0
        self.max_width, self.max_height = 0, 0
        self.scene().setSceneRect(QRectF())
        self.align = align

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.delayed_resize)

    def finish(self):
        self.pages.clear()

    def set_one_shot_immediate_resize(self):
        self.immediate_resize = True

    def get_show_state(self):
        if self.get_mode() != self.MODE_SINGLE_PAGE:
            value = self.get_scroll_value()
        else:
            value = self.page
        return value

    # ## EVENTS
    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        self.timer.stop()
        if event.oldSize().width() != event.size().width():
            if self.immediate_resize:
                self.delayed_resize()
                self.immediate_resize = False
            else:
                self.timer.start(50)

    def delayed_resize(self):
        scrollbar = self.horizontalScrollBar() if self.get_mode() == self.MODE_HORIZONTAL else self.verticalScrollBar()
        value = scrollbar.value()
        #        self.fully_update_layout2()
        self.fully_update_layout()
        scrollbar.setValue(value)

    # ## DOCUMENT

    #    def dropEvent(self, event: QtGui.QDropEvent) -> None:
    #        self.drop_event.emit(event)

    def get_width(self):
        return self.geometry().width()

    def get_ratio(self):
        return self.ratio

    def set_mode2(self, mode, ratio=None):

        if mode not in [self.MODE_FIT_WIDTH, self.MODE_FIT_PAGE]:
            if ratio is not None:
                self.ratio = ratio
            for page in self.pages.values():
                page.update_ratio(self.ratio)
            self.ratio_changed.emit(self.ratio)
        elif mode == self.MODE_FIT_WIDTH:
            self.ratio_changed.emit(-1)
        elif mode == self.MODE_FIT_PAGE:
            self.ratio_changed.emit(-2)

        self.mode = mode
        self.fully_update_layout()

        if mode == self.MODE_FIT_PAGE:
            self.move_to_page(self.page)

    def update_ratio(self, delta):
        # If we are in fit width mode, we need to change
        # to vertical mode and fix the zoom to the actual
        # ratio to avoid strange visual effects
        if self.mode == self.MODE_FIT_WIDTH:
            ratio = (self.viewport().width() - 17) / self.renderer.get_page_width(self.page) + delta
            self.set_mode2(self.MODE_VERTICAL, ratio)
        elif self.mode == self.MODE_FIT_PAGE:
            ratio = (self.viewport().height() - 17) / self.renderer.get_page_height(self.page) + delta
            self.set_mode2(self.MODE_VERTICAL, ratio)
        else:
            self.set_ratio2(self.ratio + delta)

    def set_ratio2(self, ratio):
        ratio = min(max(self.ratio_min, ratio), self.ratio_max)

        # Record radio change
        self.ratio = ratio

        if self.is_vertical():
            percent = self.verticalScrollBar().value() / self.scene().height() if self.scene().height() != 0 else 1
        else:
            percent = self.horizontalScrollBar().value() / self.scene().width() if self.scene().width() != 0 else 1

        self.reset()

        for page in self.pages.values():
            page.update_ratio(self.ratio)
            self.apply_layout(page)

        if self.is_vertical():
            self.verticalScrollBar().setValue(int(self.scene().height() * percent))
            self.horizontalScrollBar().setValue(int(self.horizontalScrollBar().maximum() / 2))
        else:
            self.horizontalScrollBar().setValue(int(self.scene().width() * percent))

        # Avoid visual artifacts
        self.scene().setBackgroundBrush(Qt.gray)

        # Inform toolbar
        self.ratio_changed.emit(self.get_ratio())

    def set_natural_hscroll(self, value):
        self.natural_hscroll = value

    def clear(self):
        self.pages.clear()
        self.scene().clear()

    def create_page(self, i, ratio):
        self.pages[i] = self.page_object(i, self, self.manager, self.renderer, ratio)
        self.scene().addItem(self.pages[i])
        return self.pages[i]

    def get_page(self):
        return self.page

    def get_scroll_value(self):
        if self.mode in [self.MODE_VERTICAL, self.MODE_VERTICAL_MULTIPAGE, self.MODE_SINGLE_PAGE]:
            return self.verticalScrollBar().value()
        else:
            return self.horizontalScrollBar().value()

    def set_scroll_value(self, value):
        if self.mode in [self.MODE_VERTICAL, self.MODE_VERTICAL_MULTIPAGE, self.MODE_SINGLE_PAGE]:
            self.verticalScrollBar().setValue(value)
        else:
            self.horizontalScrollBar().setValue(value)

    def get_num_of_pages(self):
        return len(self.pages)

    def get_page_count(self):
        return self.renderer.get_num_of_pages()

    def page_scrolled(self):
        max_area = 0
        for i, p in self.pages.items():  # type: SimplePage
            area, isec = p.visible_area()
            if area > max_area:
                max_area = area
                self.page = i
            if max_area > 0 and area == 0:
                break
            # if p.isShown():
            #    self.page = i
            #    break
        self.page_changed.emit(self.page, self.renderer.get_num_of_pages())

    def get_current_page(self):
        return self.pages.get(self.page)

    def move_to_page(self, index, offset=None):
        if (page := self.pages.get(index)) is not None:
            offset = -10 if offset is None else offset

            self.page = index

            if self.mode == self.MODE_SINGLE_PAGE:
                for p in self.pages.values():
                    p.setVisible(False)
                self.apply_layout(page)

            # Must be here because of the fit_width that changes the scrollbars
            if self.get_mode() in [self.MODE_VERTICAL_MULTIPAGE, self.MODE_VERTICAL, self.MODE_FIT_WIDTH,
                                   self.MODE_FIT_PAGE]:
                self.verticalScrollBar().setValue(int((page.pos().y() + offset * self.get_ratio())))
            else:
                self.horizontalScrollBar().setValue(int((page.pos().x() + offset * self.get_ratio())))

            page.update()
            self.page_changed.emit(index, self.renderer.get_num_of_pages())

    def page_updated(self, index):
        print("page updated on", self)

        self.pages[index].invalidate()
        v, h = self.verticalScrollBar().value(), self.horizontalScrollBar().value()

        QApplication.processEvents()

        self.fully_update_layout()
        self.verticalScrollBar().setValue(v)
        self.horizontalScrollBar().setValue(h)

    # ## UTILITY METHODS

    def get_page_at_pos(self, pos):
        item = self.items(pos)
        for i in item:
            if isinstance(i, SimplePage):
                return i
        return None

    # Get items at specific point, It is possible to filter
    # by Item type and index
    def get_items_at_pos(self, point, kind=None, index=-1, strict=True):
        items = self.items(point)
        if kind is None:
            return items if len(items) > 0 else None
        else:
            if strict:
                items_of_type_kind = [it for it in items if type(it) == kind]
            else:
                items_of_type_kind = [it for it in items if isinstance(it, kind)]

            if len(items_of_type_kind) == 0:
                return None
            elif index == -1:
                return items_of_type_kind
            elif 0 <= index < len(items_of_type_kind):
                return items_of_type_kind[index]
            else:
                return None

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def there_is_any_other_than(self, pos, check_items):
        items = self.scene().items(self.mapToScene(pos))
        if len(items) == 0:
            return True
        for item in items:
            if not isinstance(item, check_items):
                return True
        return False

    def over_a_page(self, event):
        if self.there_is_any_other_than(event.pos(), (SimplePage, Word)):
            return None
        else:
            return self.get_page_at_pos(event.pos())

    # ## REIMPLEMENTED METHODS
    def scrollContentsBy(self, dx: int, dy: int) -> None:
        super().scrollContentsBy(dx, dy)
        try:
            self.page_scrolled()
        except Exception as e:
            pass

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:

        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers != QtCore.Qt.ControlModifier:
            if self.get_mode() in self.Vertical:
                super().wheelEvent(event)
            else:
                modifiers = QtWidgets.QApplication.keyboardModifiers()
                if not self.natural_hscroll:
                    if modifiers == QtCore.Qt.ShiftModifier:
                        super().wheelEvent(event)
                    else:
                        QCoreApplication.sendEvent(self.horizontalScrollBar(), event)
                else:
                    if modifiers == QtCore.Qt.ShiftModifier:
                        QCoreApplication.sendEvent(self.horizontalScrollBar(), event)
                    else:
                        super().wheelEvent(event)
        else:
            # if not self.fitting_width:
            delta = int((event.angleDelta().y() / 1200) * 100) / 100
            mouse_on_scene = self.mapToScene(event.pos())
            page = self.get_items_at_pos(event.pos(), SimplePage, 0, False)
            self.update_ratio(delta)

        index = self.page
        page = self.pages.get(index)

    def get_page_item(self, index):
        return self.pages[index]

    # ## SLOTS

    def update_layout(self):
        self.fully_update_layout()

    def set_page(self, index):
        self.move_to_page(index)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        # print("View mouse pressed")
        super().mousePressEvent(event)
        self.manager.mouse_pressed(event)
        page = self.get_items_at_pos(event.pos(), SimplePage, 0, False)
        if page is not None:
            self.page_clicked.emit(page.index)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseReleaseEvent(event)
        self.manager.mouse_released(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        self.manager.mouse_moved(event)

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent) -> None:
        super().contextMenuEvent(event)
        if not event.isAccepted():
            self.manager.context_menu(event)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseDoubleClickEvent(event)
        self.manager.mouse_double_clicked(event)

    def rearrange(self, indices):
        # self.renderer.rearrange_pages(indices, False)
        class Element:
            def __init__(self, page, count=0):
                self.page = page
                self.count = count
                self.prev_pos = page.index
                self.current_pos = page.index

        buffer = []

        for page in self.pages.values():
            buffer.append(Element(page))
        self.pages.clear()

        for i in range(len(indices)):
            elem = buffer[indices[i]]
            if elem.count == 0:
                # print("page", i, "copy")
                self.pages[i] = elem.page

                if self.pages[i].index != i:
                    self.pages[i].shine()

                self.pages[i].index = i

            else:
                # Going to duplicate the page
                # print("page", i, "create")
                page = self.page_object(i, self, self.manager, self.renderer, self.ratio)
                page.update_original_info({"page": "+"})
                self.pages[i] = page
                self.scene().addItem(page)
                page.shine(QColor(255, 0, 0, 100))

            elem.current_pos = i
            elem.count += 1

        for elem in buffer:
            if elem.count == 0:
                self.scene().removeItem(elem.page)
            elif elem.current_pos != elem.prev_pos:
                elem.page.invalidate()

    def insert_page(self, index):
        pages = {}
        for i in range(len(self.pages) + 1):
            if i < index:
                pages[i] = self.pages[i]
            elif i == index:
                pages[i] = self.page_object(index, self, self.manager, self.renderer, self.get_ratio())
                pages[i].update_original_info({"page": "+"})
                self.scene().addItem(pages[i])
                pages[i].shine(QColor(255, 0, 0, 100))
            else:
                pages[i] = self.pages[i - 1]
                pages[i].index = i

        self.pages = pages
        return self.pages[index]

    # Mode and ratio
    def is_vertical(self):
        return self.mode in self.Vertical

    def get_mode(self):
        return self.mode

    # def set_mode(self, mode, force=False):
    #
    #     if mode == self.MODE_FIT_WIDTH:
    #         self.ratio_changed.emit(-1)
    #     elif mode == self.MODE_FIT_PAGE:
    #         self.ratio_changed.emit(-2)
    #     elif self.get_mode() == self.MODE_FIT_WIDTH:
    #         self.ratio_changed.emit(self.ratio)
    #         for page in self.pages.values():
    #             page.update_ratio(self.ratio)
    #
    #     self.set_mode(mode, force)

    def fully_update_layout(self):
        self.reset()
        for i in range(self.renderer.get_num_of_pages()):
            if (p := self.pages.get(i)) is not None:
                self.apply_layout(p)
        self.update()
        QApplication.processEvents()

    def reset(self):
        if self.mode != self.MODE_SINGLE_PAGE:
            self.scene_width, self.scene_height = 0, 0
            self.max_width, self.max_height = self.renderer.get_max_pages_size()
            rect = self.compute_scene_rect()
            self.update_scene_rect(rect)

    def update_scene_rect(self, rect):
        self.scene().setSceneRect(rect)
        self.setAlignment(Qt.AlignBottom | Qt.AlignRight)
        self.setAlignment(self.align)

    def compute_scene_rect(self, page=None):
        if self.mode == self.MODE_SINGLE_PAGE:
            w, h = self.renderer.get_page_size(page.index)
            w = w * self.ratio
            h = h * self.ratio
            return QRectF(0, 0, w, h + 40)

        elif self.mode == self.MODE_FIT_WIDTH:
            max_width, max_height = 0, 20
            for index in range(self.renderer.get_num_of_pages()):
                w, h = self.renderer.get_page_size(index)
                ratio = 1 / (w / (self.viewport().width() - 20))
                w = w * ratio
                h = h * ratio
                max_width = max(max_width, w)
                max_height = max_height + h + self.page_sep
            return QRectF(0, 0, max_width, max_height)

        elif self.mode == self.MODE_FIT_PAGE:
            max_width, max_height = 0, 20
            for index in range(self.renderer.get_num_of_pages()):
                w, h = self.renderer.get_page_size(index)
                ratio = 1 / (h / (self.viewport().height() - 17))
                w = w * ratio
                h = h * ratio
                max_width = max(max_width, w)
                max_height = max_height + h + self.page_sep
            return QRectF(0, 0, max_width, max_height)
        elif self.mode == self.MODE_HORIZONTAL:
            max_width, max_height = 0, 20
            for index in range(self.renderer.get_num_of_pages()):
                w, h = self.renderer.get_page_size(index)
                w = w * self.ratio
                h = h * self.ratio
                max_width = max_width + w + self.page_sep
                max_height = max(max_height, h)
            return QRectF(0, 0, max_width, max_height)
        else:
            max_width, max_height = 0, 20
            for index in range(self.renderer.get_num_of_pages()):
                w, h = self.renderer.get_page_size(index)
                w = w * self.ratio
                h = h * self.ratio
                max_width = max(max_width, w)
                max_height = max_height + h + self.page_sep
            return QRectF(0, 0, max_width, max_height)

    def single_row(self, page):
        x_pos = 20 if page.index == 0 else self.pages[page.index - 1].pos().x() + self.pages[
            page.index - 1].get_scaled_width() + self.page_sep
        self.scene_width = max(self.scene_width, x_pos + page.get_scaled_width() + self.page_sep)
        self.scene().setSceneRect(0, 0, self.scene_width, self.max_height * page.get_scaling_ratio())
        page.setPos(x_pos, self.max_height * page.get_scaling_ratio() / 2 - page.get_scaled_height() / 2)

    def single_column_fit_width(self, page):
        ratio = page.get_orig_width() / (self.viewport().width() - 17)
        page.update_ratio(1 / ratio)
        y_pos = 20 if page.index == 0 else self.pages[page.index - 1].pos().y() + self.pages[
            page.index - 1].get_scaled_height() + self.page_sep
        self.scene_height = max(self.scene_height, y_pos + page.get_scaled_height() + self.page_sep)
        page.setPos(0, y_pos)
        page.setVisible(True)

    def single_column_fit_page(self, page):
        w, h = page.get_orig_width(), page.get_orig_height()
        ratio = (h / (self.viewport().height() - 17))
        page.update_ratio(1 / ratio)
        y_pos = 20 if page.index == 0 else self.pages[page.index - 1].pos().y() + self.pages[
            page.index - 1].get_scaled_height() + self.page_sep
        self.scene_height = max(self.scene_height, y_pos + page.get_scaled_height() + self.page_sep)
        # self.scene().setSceneRect(0, 0, page.get_scaled_width(), self.scene_height)
        page.setPos(self.scene().sceneRect().width() / 2 - page.get_scaled_width() / 2, y_pos)
        page.setVisible(True)

    def single_column(self, page):
        y_pos = 20 if page.index == 0 else self.pages[page.index - 1].pos().y() + self.pages[
            page.index - 1].get_scaled_height() + self.page_sep
        self.scene_height = max(self.scene_height, y_pos + page.get_scaled_height() + self.page_sep)
        # self.scene().setSceneRect(0, 0, self.max_width * page.get_scaling_ratio(), self.scene_height)

        sw, sh = self.scene().sceneRect().width(), self.scene().sceneRect().height()
        pw = page.get_scaled_width()

        page.setPos(sw / 2 - pw / 2, y_pos)
        page.setVisible(True)

    def vertical_multipage(self, page):
        page.setVisible(True)
        s_max_width, s_max_height = self.max_width * page.get_scaling_ratio(), self.max_height * page.get_scaling_ratio()
        max_num_horiz_pages = max(self.viewport().width() // (s_max_width + 2 * self.page_sep), 1)
        num_cols = min(self.renderer.get_num_of_pages(), max_num_horiz_pages)

        if num_cols == 1:
            self.single_column(page)
        else:
            row = page.index // max_num_horiz_pages
            col = page.index % max_num_horiz_pages
            dx = (s_max_width - page.get_scaled_width()) / 2
            x = self.page_sep + col * (s_max_width + self.page_sep) + dx
            dy = (s_max_height - page.get_scaled_height()) / 2
            y = row * (s_max_height + self.page_sep) + dy
            page.setPos(x, self.page_sep + y)
            self.scene_height = max(self.scene_height, y + page.get_scaled_height() + self.page_sep)
            self.scene_width = max(self.scene_width, x + page.get_scaled_width() + self.page_sep)
            self.scene().setSceneRect(0, 0, self.scene_width, self.scene_height + self.page_sep)

    def apply_layout(self, page):

        if self.mode == self.MODE_SINGLE_PAGE:
            if page.index == self.get_page():
                rect = self.compute_scene_rect(page)
                self.update_scene_rect(rect)
                page.setPos(0, 20)
                page.setVisible(True)
            else:
                page.setVisible(False)

        elif self.mode == self.MODE_FIT_WIDTH:
            self.single_column_fit_width(page)
        elif self.mode == self.MODE_FIT_PAGE:
            self.single_column_fit_page(page)
        elif self.mode == self.MODE_VERTICAL_MULTIPAGE:
            self.vertical_multipage(page)
        elif self.mode == self.MODE_VERTICAL:
            self.single_column(page)
        elif self.mode == self.MODE_HORIZONTAL:
            self.single_row(page)

        if type(page) == MiniaturePage:
            page.number.setPlainText(str(page.index + 1))
