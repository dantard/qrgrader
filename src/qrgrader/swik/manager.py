from PyQt5.QtCore import QObject, pyqtSignal, Qt, QUrl, QMimeData
from PyQt5.QtGui import QDrag
from PyQt5.QtWidgets import QGraphicsRectItem
from qrgrader.swik.word import Word

from qrgrader.swik.simplepage import SimplePage

from qrgrader.swik.interfaces import Copyable


class Manager(QObject):
    FINISHED = 0
    OPEN_REQUESTED = 1

    tool_done = pyqtSignal(int, object)

    def __init__(self, renderer, config):
        super(Manager, self).__init__()
        self.tools = {}
        self.default = None
        self.current = None
        self.config = config
        self.view: QGraphicsRectItem = None
        self.renderer = renderer
        self.copy_buffer = []

    def clear(self):
        self.current.finish()

    def set_view(self, view):
        self.view = view

    def keyboard(self, action):
        if action == "Ctrl+C":
            self.copy_buffer.clear()
            items = self.view.scene().selectedItems()
            if len(items) == 0:
                self.current.keyboard("Ctrl+C")
            else:
                for item in items:
                    if isinstance(item, Copyable):
                        r, parent = item.duplicate()
                        self.copy_buffer.append((r, parent))
        elif action == "Ctrl+V":
            self.view.scene().clearSelection()
            for r, parent in self.copy_buffer:
                # self.view.scene().addItem(r)
                r.setParentItem(parent)
                r.setSelected(True)
        else:
            self.current.keyboard(action)

    def register_tool(self, tool, default=False):
        self.tools[type(tool)] = tool

        # Propagate signals to outside the manager
        tool.finished.connect(self.tool_done.emit)

        if default:
            self.default = tool
            self.use_tool(tool)
        return tool

    def get_tool(self, kind):
        return self.tools[kind]

    def use_tool(self, name):
        if self.current is not None:
            self.current.finish()
        self.current = name
        self.current.init()

    def select_tool(self, name):
        self.use_tool(self.tools[name])

    def mouse_pressed(self, event):
        # TODO:if not self.top_is(event.pos(), [SimplePage, SimplePage.MyImage, Word]):
        # return
        # if event.modifiers() & Qt.ShiftModifier:

        if event.modifiers() & Qt.ShiftModifier:
            event.accept()
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setUrls([QUrl.fromLocalFile(self.renderer.get_filename())])
            drag.setMimeData(mime_data)
            drag.exec_(Qt.CopyAction)
            return

        if self.current is not None:
            self.current.mouse_pressed(event)

    def mouse_released(self, event):
        if self.current is not None:
            self.current.mouse_released(event)

    def mouse_moved(self, event):
        if self.current is not None:
            self.current.mouse_moved(event)

    def mouse_double_clicked(self, event):
        if self.current is not None:
            self.current.mouse_double_clicked(event)

    def context_menu(self, event):
        if self.current is not None:
            self.current.context_menu(event)

    def key_pressed(self, event):
        if self.current is not None:
            self.current.key_pressed(event)

    def key_released(self, event):
        if self.current is not None:
            self.current.key_released(event)

    def reset(self):
        self.tool_done.emit(Manager.FINISHED, None)
