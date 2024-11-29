from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QSizePolicy, QLabel, QVBoxLayout


class WidgetsRow(QWidget):
    def __init__(self, *args, **kwargs):
        super(WidgetsRow, self).__init__()
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        self.widgets = args
        self.name = None
        for widget in args: # type: QWidget
            if type(widget) == str:
                self.name = widget if self.name is None else self.name
                widget = QLabel(widget)
            widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            widget.setContentsMargins(0, 0, 0, 0)
            widget.setMaximumWidth(100)
            widget.setMinimumWidth(100)
            self.layout.addWidget(widget)
        self.name = kwargs.get("name", self.name)


class VBox(QVBoxLayout):
    def __init__(self):
        super(VBox, self).__init__()
        self.widgets = {}

    def addWidget(self, a0, *args, **kwargs):
        super().addWidget(a0, *args, **kwargs)
        self.setAlignment(a0, Qt.AlignTop)
        if hasattr(a0, 'name'):
            self.widgets[a0.name] = a0