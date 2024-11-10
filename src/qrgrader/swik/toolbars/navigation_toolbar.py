from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QToolBar, QLineEdit, QLabel

from qrgrader.swik.graphview import GraphView
from qrgrader.swik.toolbars.toolbar import Toolbar


class NavigationToolbar(Toolbar):
    zoom_changed = pyqtSignal(float)

    def __init__(self, view: GraphView, toolbar: QToolBar = None):
        super().__init__(view, toolbar)
        self.view.page_changed.connect(self.page_changed)

        self.toolbar.addAction("Page Down", lambda: self.view.move_to_page(self.view.get_page() - 1)).setIcon(QIcon(":/icons/left.png"))
        self.ed_page = QLineEdit()
        self.ed_page.setMaximumWidth(40)
        self.ed_page.setAlignment(Qt.AlignRight)
        self.ed_page.returnPressed.connect(self.page_number_entered)

        self.lb_page = QLabel()
        self.toolbar.addWidget(self.ed_page)
        self.toolbar.addWidget(self.lb_page)
        self.toolbar.addAction("Page Up", lambda: self.view.move_to_page(self.view.get_page() + 1)).setIcon(QIcon(":/icons/right.png"))

    def page_number_entered(self):
        number = int(self.ed_page.text()) - 1 if self.ed_page.text().isnumeric() else -1
        self.view.move_to_page(number)

    def page_changed(self, page, num):
        self.ed_page.setText(str(self.view.get_page() + 1))
        self.lb_page.setText("/" + str(num))

    def setEnabled(self, value):
        self.ed_page.setEnabled(value)
        self.setButtonsEnabled(["Page Up", "Page Down"], value)
