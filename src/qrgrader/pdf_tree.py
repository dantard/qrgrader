from random import random, seed

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QTreeWidget, QHeaderView,QTreeWidgetItem


class MyTreeHeader(QHeaderView):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)

    def mousePressEvent(self, event):
        # Get the clicked column index
        column = self.logicalIndexAt(event.pos())
        if column != 0:
            super().mousePressEvent(event)

class NumericTreeWidgetItem(QTreeWidgetItem):
    def __lt__(self, other):
        column = self.treeWidget().sortColumn()
        try:
            return float(self.text(column)) < float(other.text(column))
        except ValueError:
            return self.text(column) < other.text(column)


class PDFTree(QTreeWidget):

    def __init__(self):
        super().__init__()
        seed(0)
        self.enabled = True
        self.setHeaderLabels(["#", "Exam Id", "!", "Score"])
        self.setSortingEnabled(True)
        self.setHeader(MyTreeHeader(Qt.Horizontal, self))
        self.header().setMinimumSectionSize(15)
        self.header().resizeSection(2, 15)  # Set initial width for column 0
        self.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.header().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.header().sortIndicatorChanged.connect(self.sort)

    def sort(self, index, order):
        if index > 0:
            self.renumber()

    def renumber(self):
        j = 1
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if not item.isHidden():
                item.setText(0, str(j))
                j = j + 1

    def addTopLevelItem(self, item):
        super().addTopLevelItem(item)


    def keyPressEvent(self, event):
        if self.enabled:
            super().keyPressEvent(event)
        else:
            event.ignore()

    def mousePressEvent(self, event):
        if self.enabled:
            super().mousePressEvent(event)
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        if self.enabled:
            super().mouseMoveEvent(event)
        else:
            event.ignore()

    def set_enabled(self, value):
        self.enabled = value
