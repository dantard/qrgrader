from PyQt5.QtWidgets import QToolBar

from qrgrader.swik.graphview import GraphView


class Toolbar:
    def __init__(self, view: GraphView, toolbar: QToolBar = None):
        self.toolbar: QToolBar = toolbar
        self.view = view
        if toolbar is None:
            self.toolbar = QToolBar()
        else:
            self.toolbar = toolbar

    def get(self):
        return self.toolbar

    def setEnabled(self, value):
        pass

    def setButtonsEnabled(self, actions, value):
        for a in self.toolbar.actions():
            if a.text() in actions:
                a.setEnabled(value)
