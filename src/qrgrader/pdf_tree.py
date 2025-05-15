from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QTreeWidget, QHeaderView


class MyTreeHeader(QHeaderView):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)

    def mousePressEvent(self, event):
        # Get the clicked column index
        column = self.logicalIndexAt(event.pos())
        if column != 0:
            super().mousePressEvent(event)


class PDFTree(QTreeWidget):

    def __init__(self):
        super().__init__()

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
        self.sortByColumn(1, Qt.AscendingOrder)
        self.renumber()

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

    def set_enabled(self, value):
        self.enabled = value
