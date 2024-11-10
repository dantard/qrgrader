import os
import shutil

from PyQt5 import QtGui
from PyQt5.QtCore import QObject, pyqtSignal, QDir, QItemSelectionModel, QModelIndex, Qt
from PyQt5.QtWidgets import QWidget, QTreeView, QFileSystemModel, QVBoxLayout, QPushButton, QHBoxLayout, QLabel, QMenu, QMessageBox, QToolBar


class Tree(QTreeView):
    delete_requested = pyqtSignal(str)

    # def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
    #     print("mousePressEvent")
    #     if e.button() != Qt.RightButton:
    #         super().mousePressEvent(e)

    def contextMenuEvent(self, a0: QtGui.QContextMenuEvent) -> None:
        super().contextMenuEvent(a0)
        indexes = self.selectedIndexes()
        if indexes:
            index = self.indexAt(a0.pos())
            if index.isValid():
                dirModel = self.model()
                path = dirModel.fileInfo(index).absoluteFilePath()
                menu = QMenu()
                delete = menu.addAction("Delete")
                res = menu.exec_(self.viewport().mapToGlobal(a0.pos()))
                if res == delete:
                    self.delete_requested.emit(path)


class FileBrowser(QWidget):
    class Signals(QObject):
        file_selected = pyqtSignal(str)

    def __init__(self, path, filters=["*.pdf"], hide_details=True):
        super().__init__()
        self.signals = self.Signals()
        self.treeview = Tree()
        self.treeview.delete_requested.connect(self.delete_requested)
        self.dirModel = QFileSystemModel()
        self.dirModel.setNameFilters(filters)
        self.dirModel.setNameFilterDisables(False)
        # self.dirModel.setRootPath(path)
        self.treeview.setModel(self.dirModel)
        self.treeview.setRootIndex(self.dirModel.setRootPath(path))
        vlayout = QVBoxLayout(self)
        self.setLayout(vlayout)
        tb = QToolBar()
        tb.addAction("↑", self.btn_up_clicked)
        tb.addAction("⟳", self.refresh)
        tb.addSeparator()
        self.label = QLabel()
        self.label.setContentsMargins(10, 0, 0, 0)
        tb.addWidget(self.label)

        vlayout.addWidget(tb)

        self.label.setText(os.path.dirname(path) if os.path.isfile(path) else path)

        self.layout().addWidget(self.treeview)
        self.treeview.selectionModel().selectionChanged.connect(self.on_current_changed)
        self.treeview.doubleClicked.connect(self.on_double_clicked)
        if hide_details:
            for i in range(1, self.treeview.model().columnCount()):
                self.treeview.header().hideSection(i)

    def delete_requested(self, path):
        if QMessageBox.question(self, "Delete", f"Are you sure you want to delete {path}?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.No:
            return
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        self.treeview.model().remove(path)

    def on_double_clicked(self, index):
        path = self.dirModel.fileInfo(index).absoluteFilePath()
        if os.path.isdir(path):
            self.set_root_index(index)

    def btn_up_clicked(self):
        index = self.treeview.rootIndex()
        if index.isValid():
            index = index.parent()
            self.set_root_index(index)

    def set_root(self, path):
        self.treeview.setRootIndex(self.dirModel.setRootPath(path))

    def set_root_index(self, index):
        self.treeview.setRootIndex(index)
        path = self.dirModel.fileInfo(index).absoluteFilePath()
        self.label.setText(path)

    def select(self, filename, emit=True):
        if not emit:
            self.treeview.selectionModel().blockSignals(True)
        index = self.dirModel.index(filename)
        indices = []
        while index.isValid():
            indices.append(index)
            index = index.parent()

        for index in reversed(indices):
            self.treeview.setExpanded(index, True)

        self.treeview.setCurrentIndex(index)
        self.treeview.selectionModel().blockSignals(False)

    def on_current_changed(self, selected, deselected):
        if deselected.indexes():
            # Check if the deselected index is valid
            for index in deselected.indexes():
                if not os.path.isfile(self.dirModel.filePath(index)):
                    self.treeview.clearSelection()
                    return

        if selected is None or len(selected.indexes()) < 1:
            return
        path = self.dirModel.fileInfo(selected.indexes()[0]).absoluteFilePath()
        # self.listview.setRootIndex(self.fileModel.setRootPath(path))
        if os.path.isfile(path):
            self.signals.file_selected.emit(path)

    def refresh(self):
        current_path = self.dirModel.rootPath()
        self.dirModel.setRootPath('')
        self.dirModel.setRootPath(current_path)
