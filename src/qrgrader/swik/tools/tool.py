from PyQt5.QtCore import QObject, pyqtSignal

from qrgrader.swik.interfaces import Shell
from qrgrader.swik.manager import Manager


class BasicTool(QObject):
    finished = pyqtSignal(int, object)

    def __init__(self, widget: Shell, **kwargs):
        super(BasicTool, self).__init__()
        self.view = widget.get_view()
        self.miniature_view = widget.miniature_view
        self.renderer = widget.get_renderer()
        self.config = widget.get_config()
        self.widget = widget

    @staticmethod
    def configure(self):
        pass

    def init(self):
        pass

    def finish(self):
        pass

    def keyboard(self, combination):
        pass

    def context_menu(self, event):
        pass

    def emit_finished(self, status=Manager.FINISHED, data=None):
        self.finished.emit(status, data)


class Tool(BasicTool):

    def mouse_pressed(self, event):
        pass

    def mouse_released(self, event):
        pass

    def mouse_moved(self, event):
        pass

    def mouse_double_clicked(self, event):
        pass

    def key_pressed(self, event):
        pass

    def key_released(self, event):
        pass
