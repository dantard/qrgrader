from PyQt5 import QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTreeWidget,
    QAbstractItemView,
    QScrollArea, QTreeWidgetItem, QLabel
)

from qrgrader.easyconfig.kind import Kind
from qrgrader.easyconfig.widgets import Integer, Label, Slider, File, SaveFile, FolderChoice, Checkbox, ComboBox, Float, Password, EditBox, List, DoubleLabel, String


class ConfigWidget(QWidget):
    def get_expanded(self):
        res = []

        def traver(node):
            res.append(1 if node.isExpanded() else 0)
            for i in range(node.childCount()):
                traver(node.child(i))

        traver(self.list.invisibleRootItem())
        return res

    def set_expanded(self, val):
        def traver(node, vec):
            if len(vec) > 0:
                node.setExpanded(vec.pop() == 1)
                for i in range(node.childCount()):
                    traver(node.child(i), vec)

        val.reverse()
        traver(self.list.invisibleRootItem(), val)

    def create_widget(self, elem, list, node):
        parent = node
        if elem.kind == Kind.INT:
            w = Integer(elem)
        elif elem.kind == Kind.LABEL:
            w = Label(elem)
        elif elem.kind == Kind.SLIDER:
            w = Slider(elem)
        elif elem.kind == Kind.FILE:
            w = File(elem)
        elif elem.kind == Kind.FILE_SAVE:
            w = SaveFile(elem)
        elif elem.kind == Kind.CHOSE_DIR:
            w = FolderChoice(elem)
        elif elem.kind == Kind.CHECKBOX:
            w = Checkbox(elem)
        elif elem.kind == Kind.COMBOBOX:
            w = ComboBox(elem)
        elif elem.kind == Kind.FLOAT:
            w = Float(elem)
        elif elem.kind == Kind.PASSWORD:
            w = Password(elem)
        elif elem.kind == Kind.EDITBOX:
            w = EditBox(elem)
            w.set_value(elem.value)
        elif elem.kind == Kind.LIST:
            w = List(elem)
        elif elem.kind == Kind.DICTIONARY:
            w = None
        elif elem.kind == Kind.DOUBLE_TEXT:
            w = DoubleLabel(elem)
        else:
            w = String(elem)

        if w is not None:
            elem.set_widget(w)
            w.value_changed.connect(lambda: elem.update_value(w.get_value()))
            child = QTreeWidgetItem()
            child.setText(0, elem.get_pretty())
            parent.addChild(child)
            list.setItemWidget(child, 1, w)
            self.widgets.append(w)

    def fill_tree_widget(self, elem, tree, node=None):
        if elem.kind == Kind.ROOT:
            node = tree.invisibleRootItem()
        elif elem.kind == Kind.SUBSECTION:
            if not elem.hidden:
                qtw = QTreeWidgetItem()
                node.addChild(qtw)
                label = QLabel(elem.get_pretty())
                label.setContentsMargins(2, 2, 2, 2)
                tree.setItemWidget(qtw, 0, label)
                node = qtw
        elif not elem.hidden and not elem.parent.hidden:
            self.create_widget(elem, tree, node)

        for c in elem.child:
            self.fill_tree_widget(c, tree, node)

    def collect(self):
        for w in self.widgets:
            w.elem.value = w.get_value()

    def __init__(self, node):
        super().__init__(None)
        self.setWindowTitle("EasyConfig")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.list = QTreeWidget()
        # self.list.setStyleSheet('background: palette(window)')
        self.list.header().setVisible(False)
        self.list.setSelectionMode(QAbstractItemView.NoSelection)
        self.list.setColumnCount(2)
        self.widgets = []

        self.setMinimumHeight(150)
        # self.list.setMinimumWidth(500)

        scroll = QScrollArea()
        scroll.setWidget(self.list)
        scroll.setWidgetResizable(True)

        layout.addWidget(scroll)
        self.fill_tree_widget(node, self.list, self.list.invisibleRootItem())
        self.list.expanded.connect(lambda: self.list.resizeColumnToContents(0))
        # self.list.expand()
        proxy = self.list.model()

        for row in range(proxy.rowCount()):
            index = proxy.index(row, 0)
            self.list.expand(index)

        # layout.addStretch(30)

        self.setLayout(layout)
        self.installEventFilter(self)
        self.list.resizeColumnToContents(0)
        # self.setMinimumWidth(500)

    def eventFilter(self, a0, a1) -> bool:
        if a1.type() == QtCore.QEvent.KeyPress:
            if a1.key() in [Qt.Key_Return]:
                return True
        return False
