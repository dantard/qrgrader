from PyQt5.QtCore import QTimer, pyqtSignal, QThread
from PyQt5.QtWidgets import QProgressDialog, QApplication


class Worker(QThread):
    done = pyqtSignal(object)

    def __init__(self, func, *args):
        super().__init__()
        self.func = func
        self.args = args

    def run(self):
        res = self.func(*self.args)
        self.done.emit(res)


class Progressing(QProgressDialog):
    done = pyqtSignal(object)

    def __init__(self, parent, max_value=0, title=None, cancel=False):
        super().__init__(parent)
        self.setMaximum(max_value)
        self.callback = None
        self.setLabelText(title)
        self.setModal(True)
        if not cancel:
            self.setCancelButton(None)
        self.show()

    def set_progress(self, value):
        self.setValue(int(value))
        QApplication.processEvents()
        return not self.wasCanceled()

    def run(self):
        self.ret_value = self.func(*self.args)
        self.done.emit(self.ret_value)
        if self.callback:
            self.callback(self.ret_value, *self.args)
        self.hide()

    def get_return_value(self):
        return self.ret_value

    def start(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.callback = kwargs.get("callback", None)
        QTimer.singleShot(50, self.run)
