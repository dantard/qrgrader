import os
import pathlib
import time
from os.path import expanduser

import pymupdf

from qrgrader.swik import utils

from qrgrader.swik.changes_tracker import ChangesTracker

import qrgrader.swik.resources

from PyQt5 import QtGui
from PyQt5.QtCore import Qt, pyqtSignal, QRectF
from PyQt5.QtGui import QPainter, QIcon, QPalette
from PyQt5.QtWidgets import QApplication, QFileDialog, QDialog, QMessageBox, QHBoxLayout, \
    QWidget, QTabWidget, QVBoxLayout, QToolBar, \
    QSplitter, QGraphicsScene, QProgressBar, QTreeWidget, QTreeWidgetItem, QPushButton, QLabel, QFrame, QSizePolicy, \
    QScrollBar
from pymupdf import Document

from qrgrader.swik.file_browser import FileBrowser
from qrgrader.swik.swik_graphview import SwikGraphView
from qrgrader.swik.dialogs import PasswordDialog, DictDialog, TextBoxDialog
from qrgrader.swik.font_manager import FontManager
from qrgrader.swik.groupbox import GroupBox
from qrgrader.swik.interfaces import Shell
from qrgrader.swik.manager import Manager
from qrgrader.swik.miniature_view import MiniatureView
from qrgrader.swik.page import Page
from qrgrader.swik.progressing import Progressing
from qrgrader.swik.renderer import MuPDFRenderer
from qrgrader.swik.scene import Scene
from qrgrader.swik.title_widget import AppBar
from qrgrader.swik.toolbars.navigation_toolbar import NavigationToolbar
from qrgrader.swik.toolbars.search_toolbar import TextSearchToolbar
from qrgrader.swik.toolbars.zoom_toolbar import ZoomToolbar
from qrgrader.swik.tools.tool_textselection import ToolTextSelection
from qrgrader.swik.widgets.pdf_widget import PdfWidget


class Splitter(QSplitter):

    def __init__(self, a):
        super().__init__(a)

    def moveEvent(self, a0: QtGui.QMoveEvent) -> None:
        super().moveEvent(a0)

    def mousePressEvent(self, a0: QtGui.QMouseEvent) -> None:
        super().mousePressEvent(a0)
        # print("Moveevntnt")

    def releaseMouse(self) -> None:
        super().releaseMouse()
        # print("splitter released")


class MyScrollBar(QScrollBar):

    def __init__(self):
        super().__init__()
        self.installEventFilter(self)
        self.hover = False

    def eventFilter(self, obj, event):
        if event.type() == event.Enter:
            self.hover = True
            self.update()
        elif event.type() == event.Leave:
            self.hover = False
            self.update()
        return False

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:

        if self.maximum() == 0:
            painter = QPainter(self)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

            qr = QRectF(self.rect().x(), self.rect().y(), self.rect().width(), self.rect().height())
            painter.fillRect(qr, Qt.transparent)
        else:
            super().paintEvent(a0)

        # print("paintevent")


class SwikWidget(Shell):
    interaction_changed = pyqtSignal(QWidget)
    open_requested = pyqtSignal(str, int, float)
    close_requested = pyqtSignal(Shell)
    file_changed = pyqtSignal(Shell)
    dirtiness_changed = pyqtSignal(object, bool)
    progress = pyqtSignal(float)
    dying = pyqtSignal()

    def __init__(self, window, config):
        super().__init__()
        self.interaction_enabled = False
        #         self.setStyleSheet('''
        #
        #
        #             /* VERTICAL SCROLLBAR */
        #             QScrollBar:vertical {
        #                 border: none;
        #                 background: rgb(0, 0, 0,0);
        #                 width: 14px;
        #                 margin: 15px 0 15px 0;
        #                 border-radius: 0px;
        #             }
        #             /*  HANDLE BAR VERTICAL */
        #             QScrollBar::handle:vertical {
        #                 background-color: rgb(80, 80, 80, 0);
        #                 min-height: 30px;
        #                 border-radius: 0px;
        #             }
        #             QScrollBar::handle:vertical:hover {
        #                 background-color: rgb(255, 0, 127);
        #             }
        #             QScrollBar::handle:vertical:pressed {
        #                 background-color: rgb(185, 0, 92);
        #             }
        #             /* BTN TOP - SCROLLBAR */
        #             QScrollBar::sub-line:vertical {
        #                 border: none;
        #                 background-color: rgb(59, 59, 90);
        #                 height: 0px;
        #                 border-top-left-radius: 7px;
        #                 border-top-right-radius: 7px;
        #                 subcontrol-position: top;
        #                 subcontrol-origin: margin;
        #             }
        #             QScrollBar::sub-line:vertical:hover {
        #                 background-color: rgb(255, 0, 127);
        #             }
        #             QScrollBar::sub-line:vertical:pressed {
        #                 background-color: rgb(185, 0, 92);
        #             }
        #
        #             /* BTN BOTTOM - SCROLLBAR */
        #             QScrollBar::add-line:vertical {
        #                 border: none;
        #                 background-color: rgb(59, 59, 90);
        #                 height: 0px;
        #                 border-bottom-left-radius: 7px;
        #                 border-bottom-right-radius: 7px;
        #                 subcontrol-position: bottom;
        #                 subcontrol-origin: margin;
        #             }
        #             QScrollBar::add-line:vertical:hover {
        #                 background-color: rgb(255, 0, 127);
        #             }
        #             QScrollBar::add-line:vertical:pressed {
        #                 background-color: rgb(185, 0, 92);
        #             }
        #
        #
        # /* RESET ARROW  vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv       */
        #             QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
        #                 background: none;
        #             }
        #             QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        #                 background: none;
        #             }
        # /* ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^       */
        #
        #         ''')
        self.win = window
        self.config = config
        self.params = []
        self.placeholder = None
        self.renderer = MuPDFRenderer()
        self.renderer.document_changed.connect(self.document_changed)
        self.renderer.file_changed.connect(self.file_modified)

        self.changes_tracker = ChangesTracker()
        self.changes_tracker.dirty.connect(self.dirtiness_has_changed)

        self.scene = Scene(self.changes_tracker)
        self.manager = Manager(self.renderer, self.config)
        self.view = SwikGraphView(self.manager, self.renderer, self.scene, page=Page,
                                  mode=self.config.private.get('mode', default=SwikGraphView.MODE_VERTICAL))
        self.view.setVerticalScrollBar(MyScrollBar())
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setRenderHint(QPainter.TextAntialiasing)
        self.view.set_natural_hscroll(self.config.general.get('natural_hscroll'))
        self.view.drop_event.connect(self.drop_event_received)
        self.view.document_ready.connect(self.document_ready)

        self.miniature_view = MiniatureView(self.manager, self.renderer, QGraphicsScene())
        self.miniature_view.setVerticalScrollBar(MyScrollBar())
        self.miniature_view.setRenderHint(QPainter.Antialiasing)
        self.miniature_view.setRenderHint(QPainter.TextAntialiasing)
        self.miniature_view.setRenderHint(QPainter.SmoothPixmapTransform)
        self.miniature_view.setRenderHint(QPainter.HighQualityAntialiasing)
        self.miniature_view.setRenderHint(QPainter.NonCosmeticDefaultPen)
        self.miniature_view.setMaximumWidth(350)
        self.miniature_view.setMinimumWidth(180)
        self.miniature_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.view.page_clicked.connect(self.miniature_view.set_page)
        self.miniature_view.page_clicked.connect(self.view.set_page)
        self.manager.set_view(self.view)
        self.font_manager = FontManager(self.renderer)

        self.vlayout, self.hlayout, self.ilayout, self.app_layout = QVBoxLayout(), QHBoxLayout(), QHBoxLayout(), QVBoxLayout()

        self.file_changed_frame = QToolBar()
        self.file_changed_frame.setContentsMargins(0, 0, 0, 0)
        self.file_changed_frame.addWidget(QLabel("File has changed on disk"))
        stretch = QWidget()
        stretch.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.file_changed_frame.addWidget(stretch)
        file_changed_reload_btn = QPushButton("⟳")
        file_changed_reload_btn.setFixedSize(25, 25)
        file_changed_close_btn = QPushButton("✕")
        file_changed_close_btn.setFixedSize(25, 25)
        file_changed_close_btn.clicked.connect(self.file_changed_frame.hide)
        file_changed_reload_btn.clicked.connect(self.reload_file)
        self.file_changed_frame.addWidget(file_changed_reload_btn)
        self.file_changed_frame.addWidget(file_changed_close_btn)
        self.file_changed_frame.hide()

        self.vlayout.addWidget(self.file_changed_frame)
        self.vlayout.addLayout(self.hlayout)
        self.hlayout.addLayout(self.ilayout)

        self.main_view = QWidget()
        self.main_view.setLayout(self.vlayout)

        self.app_bar = AppBar()
        self.app_bar.close.connect(self.app_closed)

        sp = QSplitter(Qt.Horizontal)
        sp.addWidget(self.app_bar)

        sp.addWidget(self.view)
        sp.setSizes([20, 100])
        self.ilayout.addWidget(sp)
        self.app_handle = sp.handle(1)
        self.app_handle.setDisabled(True)

        tool_text = self.manager.register_tool(ToolTextSelection(self), True)

        self.toolbar = QToolBar()
        self.toolbar.addAction("Open", self.open_button).setIcon(QIcon(":/icons/open.png"))
        self.save_btn = self.toolbar.addAction("Save", self.save_file)
        self.save_btn.setIcon(QIcon(":/icons/save.png"))
        # self.toolbar.addSeparator()
        # self.toolbar.addWidget(LongPressButton())

        self.mode_group = GroupBox(self.manager.use_tool)
        self.mode_group.add(tool_text, icon=":/icons/text_cursor.png", text="Select Text", default=True)

        self.manager.tool_done.connect(self.tool_done)

        self.zoom_toolbar = ZoomToolbar(self.view, self.toolbar)
        self.toolbar.addSeparator()
        self.toolbar.addAction("ɱ", self.iterate_mode)
        self.toolbar.addSeparator()

        self.nav_toolbar = NavigationToolbar(self.view, self.toolbar)
        self.finder_toolbar = TextSearchToolbar(self.view, self.renderer, self.toolbar)
        self.load_progress = QProgressBar()
        self.load_progress.setMaximumWidth(100)
        # self.load_progress.setFormat("Loading...")
        self.load_progress_action = self.toolbar.addWidget(self.load_progress)
        self.load_progress_action.setVisible(False)

        self.splitter = Splitter(Qt.Horizontal)

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.toolbar)
        self.layout().addWidget(self.splitter)

        for w in [self.vlayout, self.hlayout, self.ilayout, self.app_layout, self.splitter, self.main_view]:
            w.setContentsMargins(0, 0, 0, 0)

        self.outline = QTreeWidget()
        self.outline.setHeaderHidden(True)
        self.outline.itemSelectionChanged.connect(self.toc_selected)

        self.file_browser = FileBrowser(expanduser("~"))
        self.file_browser.signals.file_selected.connect(self.file_selected)

        # self.rclone_browser = RCloneBrowser()

        self.tab = QTabWidget()
        self.tab.addTab(self.miniature_view, "Miniature")
        self.tab.addTab(self.outline, "ToC")
        self.tab.addTab(self.file_browser, "Files")
        self.tab.setTabVisible(1, False)
        self.tab.setMaximumWidth(self.miniature_view.maximumWidth())

        self.update_miniature_bar_position()

        self.set_interactable(False)
        self.preferences_changed()
        QApplication.processEvents()

    def file_selected(self, file):
        self.push_params(self.view.get_mode(), self.view.ratio, 0, self.splitter.sizes())
        self.open_file(file)

    def push_params(self, mode=0, ratio=1, scroll=0, splitter=None):
        self.params.append((mode, ratio, scroll, splitter))

    def dirtiness_has_changed(self, dirty):
        self.dirtiness_changed.emit(self, dirty)
        # self.save_btn.setEnabled(dirty)

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        super(SwikWidget, self).keyPressEvent(a0)
        self.manager.key_pressed(a0)

    def keyReleaseEvent(self, a0: QtGui.QKeyEvent) -> None:
        super(SwikWidget, self).keyReleaseEvent(a0)
        self.manager.key_released(a0)

    def is_dirty(self):
        return self.changes_tracker.is_dirty()

    def reload_file(self):
        self.file_changed_frame.setVisible(False)
        if os.path.isfile(self.renderer.get_filename()):
            self.open_file(self.renderer.get_filename())
        else:
            QMessageBox.critical(self, "Error", "File " + self.renderer.get_filename() + " has been deleted")
            self.close_requested.emit(self)

    def file_modified(self):
        self.file_changed_frame.setVisible(True)

    def get_renderer(self):
        return self.renderer

    def get_view(self):
        return self.view

    def get_manager(self):
        return self.manager

    def get_config(self):
        return self.config

    def get_font_manager(self):
        return self.font_manager

    def get_other_views(self):
        return [self.miniature_view]

    def toc_selected(self):
        s: Document = self.renderer.document
        selected = self.outline.selectedItems()
        if len(selected) == 0:
            return
        selected = selected[0]
        page = self.view.pages[selected.item.page]
        if self.view.get_mode() == SwikGraphView.MODE_SINGLE_PAGE:
            self.view.move_to_page(page.index)
        p = page.mapToScene(selected.item.to)
        self.view.centerOn(p.x(), p.y() + self.view.viewport().height() / 2)

    def app_closed(self):
        self.view.set_one_shot_immediate_resize()
        self.mode_group.reset()

    def set_app_widget(self, widget, width=500, title=""):
        self.view.set_one_shot_immediate_resize()
        self.app_bar.set_item(widget, title)
        self.app_bar.set_suggested_width(width)
        self.app_handle.setDisabled(False)

    def remove_app_widget(self):
        self.view.set_one_shot_immediate_resize()
        self.app_bar.remove_item()
        self.app_bar.setMaximumWidth(0)
        self.app_handle.setDisabled(True)

    def tool_done(self, action, data):
        if action == Manager.OPEN_REQUESTED:
            self.open_file(data)
            self.manager.use_tool(self.tool_sign)
        else:
            self.mode_group.reset()

    def set_ratio(self, ratio):
        self.view.set_ratio(ratio, True)

    def set_page(self, page):
        self.view.set_page(page)

    def set_mode(self, mode):
        self.view.set_mode(mode, False)

    def document_ready(self):
        pass

    def drop_event_received(self, vector):
        for file in vector:
            self.open_requested.emit(file, 0, self.view.get_ratio())

    def set_interactable(self, enable):
        self.mode_group.set_enabled(enable)
        self.zoom_toolbar.setEnabled(enable)
        self.nav_toolbar.setEnabled(enable)
        self.finder_toolbar.setEnabled(enable)
        self.save_btn.setEnabled(enable)
        self.interaction_enabled = enable
        self.interaction_changed.emit(self)

    def set_protected_interaction(self, status):
        self.interaction_enabled = status
        self.save_btn.setEnabled(status)
        self.interaction_changed.emit(self)

    def is_interaction_enabled(self):
        return self.interaction_enabled

    def preferences_changed(self):
        self.update_miniature_bar_position()

    def statusBar(self):
        return self.win.statusBar()

    def iterate_mode(self):
        mode = (self.view.get_mode() + 1) % (len(SwikGraphView.modes))
        self.view.set_mode2(mode)
        self.statusBar().showMessage("Mode " + SwikGraphView.modes[mode], 2000)

    def flatten(self, open=True):
        filename = self.renderer.get_filename().replace(".pdf", "-flat.pdf")

        res = self.renderer.flatten(filename)

        if open:
            self.open_requested.emit(filename, self.view.page, self.view.ratio)

    def extract_fonts(self):
        fonts = self.renderer.save_fonts(".")
        QMessageBox.information(self, "Fonts extracted", "Extracted " + str(len(fonts)) + "fonts")

    def document_changed(self):

        # Clear views and fonts
        self.changes_tracker.clear()
        self.manager.clear()
        self.view.clear()
        self.miniature_view.clear()
        self.font_manager.clear_document_fonts()

        if len(self.params) > 0:
            mode, ratio, scroll, splitter = self.params.pop()
        else:
            scroll = 0
            ratio = self.config.get_default_ratio()
            mode = self.config.get_default_mode()
            splitter = [self.config.get_default_bar_width(), self.width() - self.config.get_default_bar_width()]

        self.splitter.setSizes(splitter)

        # Force splitter adjustment
        QApplication.processEvents()

        self.load_progress_action.setVisible(True)
        self.load_progress.setMaximum(self.renderer.get_num_of_pages())

        # Create pages
        self.view.set_mode2(mode, ratio)

        self.view.reset()
        self.miniature_view.reset()

        for i in range(self.renderer.get_num_of_pages()):
            # Create Page
            page = self.view.create_page(i, self.view.get_ratio())
            self.view.apply_layout(page)

            # Create Miniature Page
            mini_page = self.miniature_view.create_page(i, 1)
            self.miniature_view.apply_layout(mini_page)

            # Update progress bar
            self.load_progress.setValue(i + 1)

            # Process events every 20 pages
            # to avoid freezing the interface
            if i % 20 == 0:
                QApplication.processEvents()

        self.load_progress_action.setVisible(False)
        self.mode_group.reset()
        self.update_toc()

        pdf_widgets = [item for item in self.view.scene().items() if isinstance(item, PdfWidget)]

        if len(pdf_widgets) > 0:
            self.tool_form_btn.click()

        # Important otherwise the
        # view is not ready to be used
        QApplication.processEvents()

        if mode != SwikGraphView.MODE_SINGLE_PAGE:
            self.view.set_scroll_value(scroll)
        else:
            self.view.move_to_page(scroll)

    def get_state(self):
        if (filename := self.get_filename()) is not None:
            value = self.view.get_show_state()
            return [filename, self.view.get_mode(), self.view.get_ratio(), value, self.splitter.sizes()]

    class TocWidgetItem(QTreeWidgetItem):
        def __init__(self, item):
            super().__init__([item.title, str(item.page)])
            self.item = item

    def update_toc(self):
        ##### TODO: WARNING TOC DISABLED:
        return
        self.outline.clear()
        items = self.renderer.get_toc()
        self.tab.setTabVisible(1, len(items) > 0)

        parents = {}
        for item in items:
            twi = self.TocWidgetItem(item)
            if item.level == 1:
                self.outline.addTopLevelItem(twi)
                parents[2] = twi
            else:
                parents[item.level].addChild(twi)
                parents[item.level + 1] = twi

    def get_filename(self):
        return self.renderer.get_filename()

    def open_button(self):
        self.push_params(self.view.get_mode(), self.view.ratio, 0, self.splitter.sizes())
        self.open_file()

    def open_file(self, filename=None, warn=True):
        if filename is None:
            last_dir_for_open = self.config.private.get('last_dir_for_open')
            filename, ext = QFileDialog.getOpenFileName(self, 'Open file', last_dir_for_open, 'PDF (*.pdf)')

        if filename:
            _, ext = os.path.splitext(filename)

            if ext in ['.doc', '.docx', '.odt', '.rtf', '.html',
                       '.htm', '.xml', '.pptx', '.ppt', '.xls', '.xlsx']:
                result = utils.word_to_pdf(filename)
                if result == 0:
                    pass
                elif result == -4:
                    warn and QMessageBox.warning(self, "Error", "Libreoffice does not seem to be installed.")
                    self.close_requested.emit(self)
                    return
                elif result == -1:
                    warn and QMessageBox.warning(self, "Error", "Libreoffice Writer does not seem to be installed.")
                    self.close_requested.emit(self)
                    return
                elif result == -2:
                    warn and QMessageBox.warning(self, "Error", "Libreoffice Draw does not seem to be installed.")
                    self.close_requested.emit(self)
                    return
                elif result == -3:
                    warn and QMessageBox.warning(self, "Error", "Libreoffice Calc does not seem to be installed.")
                    self.close_requested.emit(self)
                    return
                else:
                    warn and QMessageBox.warning(self, "Error", "Error converting file")
                    self.close_requested.emit(self)
                    return
                filename = filename.replace(ext, '.pdf')

            elif ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.pnm',
                         '.pgm', '.ppm', '.xps', '.svg', '.epub', '.mobi', '.txt']:
                try:
                    file = pymupdf.open(filename)
                    pdf_bytes = file.convert_to_pdf()
                    pdf = pymupdf.open("pdf", pdf_bytes)
                    filename = filename.replace(ext, '.pdf')
                    pdf.save(filename)
                except:
                    warn and QMessageBox.warning(self, "Error", "Error converting file")
                    self.close_requested.emit(self)
                    return

            if not os.path.exists(filename):
                warn and QMessageBox.warning(self, "Error", "File {} does not exist".format(filename))
                self.close_requested.emit(self)
                return

            self.mode_group.reset()
            res = self.renderer.open_pdf(filename)
            if res == MuPDFRenderer.OPEN_REQUIRES_PASSWORD:
                dialog = PasswordDialog(False, parent=self)
                if dialog.exec() == QDialog.Accepted:
                    res = self.renderer.open_pdf(filename, dialog.getText())

            if res == MuPDFRenderer.OPEN_OK:
                self.set_interactable(True)
                self.file_changed.emit(self)
                # To update the number of page
                self.view.page_scrolled()
                self.config.update_recent(self.renderer.get_filename())
                self.config.flush()
                self.file_browser.select(self.renderer.get_filename(), False)

            else:
                warn and QMessageBox.warning(self, "Error", "Error opening file")
                self.close_requested.emit(self)

    def save_file(self, name=None):
        name = self.renderer.get_filename() if name is None else name
        print("in save_file: ", name)

        if self.renderer.get_num_of_pages() > 100:
            self.placeholder = Progressing(self, title="Saving PDF...")
            self.placeholder.show()
            result = self.renderer.save_pdf(name, False)
            self.placeholder.close()
        else:
            result = self.renderer.save_pdf(name, False)

        if result:
            self.file_browser.select(self.renderer.get_filename(), False)
            self.file_changed.emit(self)
            self.changes_tracker.clear()
            self.mode_group.reset()

            # Update miniature page view (not especially efficient)
            for page in self.miniature_view.pages.values():
                page.invalidate()

        return result

    def apply_post_save_artifacts(self, filename):
        # Signature
        signature = next((sig for sig in self.view.items() if isinstance(sig, SignerRectItem)), None)
        if signature is not None:
            output_filename = ToolSign.sign_document(signature, filename)
            if output_filename:
                self.open_requested.emit(output_filename, self.view.page, self.view.get_ratio())

        # self.manager.clear()

    def saved(self, ret_code, name):
        self.apply_post_save_artifacts(name)

    def save_file_as(self):
        name = self.renderer.get_filename()
        name, _ = QFileDialog.getSaveFileName(self, "Save PDF Document", name, "PDF Files (*.pdf)")
        print("name chosen", name)
        if name:
            return self.save_file(name)
        return False

    def rename(self):
        current_name = self.renderer.get_filename()
        name, _ = QFileDialog.getSaveFileName(self, "Save PDF Document", current_name, "PDF Files (*.pdf)")
        print("name chosen", name)
        if name:
            if self.save_file(name):
                pathlib.Path.unlink(pathlib.Path(current_name))
        return False

    def open_with_other(self, command):
        if command is not None:
            os.system(command + " '" + self.renderer.get_filename() + "' &")
        else:
            self.config.edit()

    def deleteLater(self):
        self.finder_toolbar.close()
        super().deleteLater()

    def edit_metadata(self):
        dialog = DictDialog(self.renderer.get_metadata(), ["format", "encryption"], parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.renderer.set_metadata(dialog.get_dict())

    def edit_xml_metadata(self):
        dialog = TextBoxDialog(self.renderer.get_xml_metadata(), parent=self, title="Edit XML Metadata")
        if dialog.exec() == QDialog.Accepted:
            self.renderer.set_xml_metadata(dialog.get_text())

    def die(self):
        self.finder_toolbar.die()
        self.dying.emit()

    def update_miniature_bar_position(self):
        widgets = [self.splitter.widget(i) for i in range(self.splitter.count())]
        for widget in widgets:
            if widget is not None:
                widget.setParent(None)

        if self.config.lateral_bar_side.get_value() == 0:
            self.splitter.addWidget(self.tab)
            self.splitter.addWidget(self.main_view)
        elif self.config.lateral_bar_side.get_value() == 1:
            self.splitter.addWidget(self.main_view)
            self.splitter.addWidget(self.tab)
        else:
            self.splitter.addWidget(self.main_view)
