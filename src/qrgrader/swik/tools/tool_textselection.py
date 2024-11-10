from PyQt5.QtCore import Qt, QPointF, QUrl, QMimeData
from PyQt5.QtGui import QColor, QGuiApplication, QDesktopServices, QDrag
from PyQt5.QtWidgets import QMenu, QDialog, QMessageBox, QApplication, QInputDialog

from qrgrader.swik.action import Action
from qrgrader.swik.annotations.highlight_annotation import HighlightAnnotation
from qrgrader.swik.annotations.redact_annotation import RedactAnnotation
from qrgrader.swik.dialogs import FontAndColorDialog
from qrgrader.swik.font_manager import Font, Arial
from qrgrader.swik.interfaces import Shell
from qrgrader.swik.selector import SelectorRectItem
from qrgrader.swik.simplepage import SimplePage
from qrgrader.swik.swik_text import SwikText, SwikTextReplace
from qrgrader.swik.tools.tool import Tool
from qrgrader.swik.word import Word


class ToolTextSelection(Tool):
    SELECTION_MODE_NATURAL = 0
    SELECTION_MODE_RECT = 1

    def __init__(self, widget: Shell, **kwargs):
        super(ToolTextSelection, self).__init__(widget, **kwargs)
        self.rubberband = None
        self.font_manager = widget.get_font_manager()
        self.selection_mode = ToolTextSelection.SELECTION_MODE_RECT
        self.selected = []
        self.multiple_selection = []

    def iterate_selection_mode(self):
        self.selection_mode = (self.selection_mode + 1) % 2

    def clear_selection(self):
        zombies = []
        for word in self.selected:
            if word not in self.multiple_selection:
                word.set_selected(False)
                zombies.append(word)
        # self.selected.clear()
        for word in zombies:
            self.selected.remove(word)
        self.selected.clear()
        self.multiple_selection.clear()

    def selecting(self, selector: SelectorRectItem):
        p1 = selector.get_rect_on_scene().topLeft()
        p2 = selector.get_rect_on_scene().bottomRight()

        p1_on_view = self.view.mapFromScene(p1)
        p2_on_view = self.view.mapFromScene(p2)

        page1 = self.view.get_page_at_pos(p1_on_view)
        page2 = self.view.get_page_at_pos(p2_on_view)

        # print(page1.index, page2.index)

        self.clear_selection()

        if page1 is not None and page2 is not None:

            words = []

            for i in range(page1.index, page2.index + 1):
                page = self.view.get_page_item(i)

                for word in page.gather_words():
                    words.append(word)

            for i, word in enumerate(words):
                word.seq = i
                if word.get_rect_on_scene().intersects(selector.get_rect_on_scene()):
                    self.selected.append(word)

            if len(self.selected) > 0:
                if self.selection_mode == ToolTextSelection.SELECTION_MODE_NATURAL:
                    # Clear the selection to restore order
                    begin, end = self.selected[0].seq, self.selected[-1].seq
                    self.selected.clear()
                    for i in range(begin, end + 1):
                        words[i].set_selected(True)
                        self.selected.append(words[i])
                else:
                    for word in self.selected:
                        word.set_selected(True)

    def selecting_done(self, selector: SelectorRectItem):
        self.selecting(selector)
        self.view.setCursor(Qt.ArrowCursor)
        self.multiple_selection.extend(self.selected)

    def mouse_pressed(self, event):

        if event.button() == Qt.RightButton:
            return

        # if event.modifiers() & Qt.ShiftModifier:
        #     event.accept()
        #     drag = QDrag(self)
        #     mime_data = QMimeData()
        #     mime_data.setUrls([QUrl.fromLocalFile(self.renderer.get_filename())])
        #     drag.setMimeData(mime_data)
        #     drag.exec_(Qt.CopyAction)
        #     return

        if self.view.there_is_any_other_than(event.pos(), (SimplePage, Word)):
            return

        if self.rubberband is None:

            if event.modifiers() & Qt.ControlModifier:
                pass
            else:
                self.multiple_selection.clear()

            if self.selection_mode == ToolTextSelection.SELECTION_MODE_NATURAL:
                self.rubberband = SelectorRectItem(pen=Qt.transparent)
                self.view.viewport().setCursor(Qt.IBeamCursor)
            else:
                self.rubberband = SelectorRectItem()
                self.view.viewport().setCursor(Qt.CrossCursor)

            self.view.scene().addItem(self.rubberband)
            self.rubberband.signals.creating.connect(self.selecting)
            self.rubberband.signals.done.connect(self.selection_done)
            self.rubberband.view_mouse_press_event(self.view, event)

    def mouse_released(self, event):
        if self.rubberband is not None:
            self.rubberband.view_mouse_release_event(self.view, event)
        self.view.viewport().setCursor(Qt.ArrowCursor)

    def selection_done(self, rb):
        if rb.get_rect_on_parent().width() > 5 and rb.get_rect_on_parent().height() > 5:
            self.selecting_done(rb)
        elif not QApplication.keyboardModifiers() & Qt.ControlModifier:
            self.clear_selection()
        self.rubberband = None
        self.view.scene().removeItem(rb)

    def mouse_moved(self, event):
        if self.rubberband is not None:
            self.rubberband.view_mouse_move_event(self.view, event)

    def context_menu(self, event):
        page = self.view.get_page_at_pos(event.pos())

        if page is None:
            return

        if self.view.there_is_any_other_than(event.pos(), (SimplePage, Word)):
            return

        menu = QMenu()
        add_text = menu.addAction("Add Text")
        if len(self.selected) > 0:
            copy = menu.addAction("Copy")
            anon = menu.addAction("Anonymyze")
            highlight = menu.addAction("Highlight Annotation")
            replace = menu.addAction("Replace")
            menu.addSeparator()
            web_search = menu.addAction("Web Search")
        else:
            anon, highlight, copy, replace, web_search = None, None, None, None, None

        if QGuiApplication.clipboard().text() != "":
            paste = menu.addAction("Paste")
        else:
            paste = None

        res = menu.exec(event.globalPos())
        if res is None:
            pass
        elif res == paste:
            text = QGuiApplication.clipboard().text()
            for i, word in enumerate(text.split("\n")):
                st = SwikText(word.replace("\n", ""), page, self.font_manager, Arial(), 11)
                on_scene = self.view.mapToScene(event.pos())
                st.setPos(st.mapFromScene(on_scene) + QPointF(15 * i, 15 * i))

        elif res == web_search:
            text = str()
            for word in self.selected:
                text += word.get_text() + " "
            text.rstrip(" ")
            if (query := self.config.general.get("web_search")) is not None:
                QDesktopServices.openUrl(QUrl(query + text))

        elif res == anon:
            action = Action()
            for word in self.selected:  # type: Word
                word.set_selected(False)
                r = RedactAnnotation(word.parentItem(), brush=Qt.black)
                r.setRect(word.get_rect_on_parent())
                action.push(r, Action.ACTION_CREATE, r.parentItem())
            self.clear_selection()
            self.view.scene().action_added(action)


        elif res == highlight:
            annot = HighlightAnnotation(QColor(255, 0, 0, 80), self.selected[0].parentItem())
            for word in self.selected:  # type: Word
                word.set_selected(False)
                r = word.get_rect_on_parent()
                annot.add_quad(r)
            self.clear_selection()

        elif res == add_text:
            # inputbox to get text
            text, ok = QInputDialog().getText(self.view, "Input Text", "Enter text")
            if ok:
                st = SwikText(text, page, self.font_manager, Arial(), 11)
                on_scene = self.view.mapToScene(event.pos())
                st.setPos(st.mapFromScene(on_scene))

        elif res == copy:
            self.copy_selected_to_clipboard()

        elif res == replace:
            first_font, first_size, first_color = self.renderer.get_word_font_info(self.selected[0])
            for word in self.selected[1:]:
                font, size, color = self.renderer.get_word_font_info(word)
                if font != first_font or size != first_size or color != first_color:
                    QMessageBox.warning(self.view, "Warning", "Selected words have different font, size or color.")
                    break

            dialog = FontAndColorDialog(self.font_manager, first_font, first_size, first_color)
            if dialog.exec() == QDialog.Accepted:
                for word in self.selected:
                    sw = SwikTextReplace(word, self.font_manager, dialog.get_font(), dialog.get_font_size() / (96 / 72), dialog.get_text_color())
                    sw.set_border_color(Qt.blue)
                    sw.set_bg_color(Qt.white)
                self.clear_selection()

    def mouse_double_clicked(self, event):
        page = self.view.get_page_at_pos(event.pos())

        page.gather_words()

        scene_pos = self.view.mapToScene(event.pos())
        items = self.view.scene().items(scene_pos)
        if len(items) > 0 and type(items[0]) == Word:
            word = items[0]
            if not word in self.selected:
                self.selected.append(word)
                word.set_selected(True)
            else:
                self.selected.remove(word)
                word.set_selected(False)

    def finish(self):
        for word in self.selected + self.multiple_selection:
            word.set_selected(False)
        self.selected.clear()
        self.multiple_selection.clear()
        self.view.setCursor(Qt.ArrowCursor)

    def copy_selected_to_clipboard(self):
        text = ""
        for word in self.selected:
            text += word.get_text() + " "
        text.rstrip(" ")
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(text)

    def keyboard(self, combination):
        if combination == "Ctrl+C":
            self.copy_selected_to_clipboard()
        elif combination == "Ctrl+A":
            self.select_all()

    def select_all(self):
        self.clear_selection()
        page = self.view.get_current_page()
        page.gather_words()
        for word in page.get_words():
            word.set_selected(True)
            self.selected.append(word)
