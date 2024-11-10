from PyQt5 import QtGui
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QKeySequence, QBrush, QColor, QPainter, QIcon
from PyQt5.QtWidgets import QToolBar, QShortcut, QLineEdit, QLabel, QApplication, QGraphicsRectItem, QStyle

from qrgrader.swik.graphview import GraphView
from qrgrader.swik.finder import Finder
from qrgrader.swik.renderer import MuPDFRenderer
from qrgrader.swik.toolbars.toolbar import Toolbar


class Highlighter(QGraphicsRectItem):
    def __init__(self, word, color=QColor(250, 250, 80, 100)):
        super(Highlighter, self).__init__(word.parentItem())
        self.setRect(word.rect())
        self.setBrush(QBrush(color))
        self.setPos(word.pos())
        self.setPen(Qt.transparent)


class ProgressLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super(ProgressLineEdit, self).__init__(parent)
        self.percent = 0
        self.color = Qt.red

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        super(ProgressLineEdit, self).paintEvent(a0)
        if 0 < self.percent <= 1:
            color = Qt.red if self.percent < 1 else Qt.green
            painter = QPainter(self)
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.transparent)
            visible_width = self.width() - (self.contentsMargins().left() + self.contentsMargins().right())
            visible_width -= (self.style().pixelMetric(QStyle.PM_DefaultFrameWidth) * 2)
            painter.drawRect(1, self.height() - 4, int(visible_width * self.percent), 3)

        if self.percent == 1:
            self.percent = 0
            QTimer.singleShot(250, self.update)

    def set_percent(self, percent):
        self.percent = min(percent, 1)
        self.update()


class TextSearchToolbar(Toolbar):
    class Signals(QObject):
        page_processed = pyqtSignal(int, list)
        process_finished = pyqtSignal()

    def __init__(self, view: GraphView, renderer: MuPDFRenderer, toolbar: QToolBar = None):
        super().__init__(view, toolbar)
        self.prev_text = None
        self.renderer = renderer
        self.finder = Finder(self.view, renderer)
        self.finder.found.connect(self.found_word)
        self.sc = QShortcut(QKeySequence('Ctrl+F'), self.toolbar)
        self.sc.activated.connect(self.activated)
        self.widgets = []
        self.highlighted = []
        self.selected = []
        self.view.renderer.document_about_to_change.connect(self.document_changed)

        # Prepare find word-related widgets
        self.find_tb = toolbar
        self.find_tb.addSeparator()
        self.find_edit = ProgressLineEdit()
        self.find_edit.setMaximumWidth(200)
        cm = self.find_edit.contentsMargins()
        cm.setRight(10)
        self.find_edit.setContentsMargins(cm)
        self.find_edit.returnPressed.connect(self.find_text)
        self.finder.progress.connect(self.progress)

        self.find_label = QLabel("Not found")
        self.find_label.setMinimumWidth(80)
        self.find_label.setAlignment(Qt.AlignCenter)

        self.widgets.append(self.find_tb.addWidget(QLabel("Find ")))
        self.widgets.append(self.find_tb.addWidget(self.find_edit))

        self.case_sensitive_btn = self.find_tb.addAction("Cc", lambda: self.find_text(True))
        self.widgets.append(self.case_sensitive_btn)
        self.case_sensitive_btn.setCheckable(True)

        self.whole_word_btn = self.find_tb.addAction("W", lambda: self.find_text(True))
        self.whole_word_btn.setCheckable(True)
        self.widgets.append(self.whole_word_btn)

        self.find_prev_btn = self.find_tb.addAction("Prev", lambda: self.next_word(-1))
        self.widgets.append(self.find_tb.addWidget(self.find_label))
        self.find_next_btn = self.find_tb.addAction("Next", lambda: self.next_word(1))
        self.find_prev_btn.setIcon(QIcon(":/icons/left.png"))
        self.find_next_btn.setIcon(QIcon(":/icons/right.png"))
        self.widgets.append(self.find_next_btn)
        self.widgets.append(self.find_prev_btn)
        self.widgets.append(self.find_tb.addAction("×", self.close))
        self.setVisible(False)

    def progress(self, percent):
        if percent < 0:
            self.set_not_found()
            self.prev_text = None
        self.find_edit.set_percent(max(0, percent))

    def activated(self):
        self.setVisible(True)
        self.finder.clear()

    def document_changed(self):
        self.setVisible(False)
        self.finder.discard()

    def setEnabled(self, value):
        for w in self.widgets:
            w.setEnabled(value)
        self.widgets[-1].setEnabled(True)

    def setVisible(self, value):
        self.find_next_btn.setEnabled(False)
        self.find_prev_btn.setEnabled(False)
        for widget in self.widgets:
            widget.setVisible(value)
        self.find_edit.clear()
        self.find_edit.setFocus()

    def find_text(self, force=False):
        if self.prev_text != self.find_edit.text() or force:

            if self.case_sensitive_btn.isChecked() and self.whole_word_btn.isChecked():
                mode = Finder.MODE_Cc_W
            elif self.case_sensitive_btn.isChecked():
                mode = Finder.MODE_Cc
            elif self.whole_word_btn.isChecked():
                mode = Finder.MODE_W
            else:
                mode = Finder.MODE_NORMAL

            self.set_not_found()
            self.finder.find(self.find_edit.text(), mode, self.view.get_page())
            self.prev_text = self.find_edit.text()
        else:
            self.next_word(1)

    def set_not_found(self):
        for word in self.highlighted + self.selected:
            self.view.scene().removeItem(word)

        self.highlighted.clear()
        self.selected.clear()

        self.find_label.setText("Not found")
        self.find_next_btn.setEnabled(False)
        self.find_prev_btn.setEnabled(False)

    def close(self):
        self.finder.discard()
        self.setVisible(False)

    def found_word(self, count, sentence):
        for word in sentence:
            h = Highlighter(word)
            self.highlighted.append(h)

        self.find_label.setText(f"{self.finder.get_index() + 1}/{count}")
        if count > 0:
            self.find_next_btn.setEnabled(True)
            self.find_prev_btn.setEnabled(True)

        if count == 1:
            self.next_word(1)

    def next_word(self, direction):
        for s in self.selected:
            self.view.scene().removeItem(s)
        self.selected.clear()

        sentence = self.finder.next(direction)

        if len(sentence) == 0:
            return

        for word in sentence:
            s = Highlighter(word, QColor(255, 0, 0, 100))
            self.selected.append(s)

        self.view.ensureVisible(self.selected[0])

        self.find_label.setText(f"{self.finder.get_index() + 1}/{self.finder.get_count()}")

    def die(self):
        self.finder.die()
