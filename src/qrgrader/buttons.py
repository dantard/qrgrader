from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QCursor, QGuiApplication, QFont
from PyQt5.QtWidgets import QWidget, QPushButton, QHBoxLayout, QSpinBox, QLabel, QTextEdit, QVBoxLayout



class ThirdButton(QPushButton):

    def __init__(self, name):
        super().__init__(name)
        self.which = Qt.NoButton

    def mousePressEvent(self, a0):
        super().mousePressEvent(a0)
        #a0.accept()
        self.which = a0.button()
        if self.which == Qt.MidButton:
            self.click()
            self.clicked.emit()

    def mouseReleaseEvent(self, a0):
        super().mouseReleaseEvent(a0)
        self.which = Qt.NoButton


class Button(QWidget):
    def __init__(self, name, **kwargs):
        super().__init__()
        self.name = name
        self.color = kwargs.get("color", "#D4D4D4")
        self.type = "button"
        self.data = {}

    def get_name(self):
        return self.name

    def set_color(self, color):
        pass

    def get_type(self):
        return self.type

    def get_color(self):
        return self.color

    def store(self, exam_id):
        pass

    def retrieve(self, exam_id):
        pass


class Shortcut(Button):
    clicked = pyqtSignal()

    def __init__(self, name, **kwargs):
        super().__init__(name)
        self.button = QPushButton(name)
        self.button.clicked.connect(self.clicked.emit)  # type: ignore
        self.buttons = kwargs.get("buttons", [])
        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self.button)
        font = self.button.font()
        font.setItalic(True)
        self.button.setFont(font)

    def get_buttons(self):
        return self.buttons



class Separator(Button):
    def __init__(self, name, **kwargs):
        super().__init__(name)
        self.setLayout(QHBoxLayout())
        self.label = QLabel(name)
        self.label.setFont(QFont("Arial", 10, QFont.Bold))
        self.label.setAlignment(Qt.AlignCenter)
        self.layout().addWidget(self.label)
        self.layout().setContentsMargins(5, 5, 5, 5)
        self.type = "separator"



class StateButton(Button):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)


class TextButton(StateButton):
    clicked = pyqtSignal()

    def __init__(self, name, **kwargs):
        super().__init__(name)
        self.button = QTextEdit(name)
        self.button.setMinimumWidth(10)
        self.setMinimumWidth(10)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(QLabel(name))
        self.layout().addWidget(self.button)
        self.layout().setContentsMargins(5, 2, 5, 2)
        self.type = "text"

    def get_value(self):
        return self.button.toPlainText()

    def get_xls_value(self):
        return self.button.toPlainText().replace("\n", ";")

    def set_value(self, value):
        self.button.setText(value)

    def set_xls_value(self, value):
        self.button.setText(value.replace(";","\n"))

class PushButton(StateButton):

    def __init__(self,name, **kwargs):
        super().__init__(name, **kwargs)
        self.button = ThirdButton(name)
        self.button.setMinimumWidth(10)
        self.button.setCheckable(True)

        if kwargs.get("height") is not None:
            self.button.setMinimumHeight(kwargs.get("height"))
        if kwargs.get("font") is not None:
            font = self.button.font()
            font.setPixelSize(int(kwargs.get("font")))
            self.button.setFont(font)
        self.set_color(self.color)

    def set_color(self, color):
        self.color = color
        self.button.setStyleSheet(f'background-color: {color}')

class StepButton(PushButton):
    score_changed = pyqtSignal()

    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        self.weight = kwargs.get('weight', 1)
        self.full_value = kwargs.get('full_value', 1)
        self.n_steps = kwargs.get('steps', 0)
        self.click_next = kwargs.get("click_next", False)

        self.comment = None
        self.step = int(100 / self.n_steps) if self.n_steps > 0 else 100

        layout = QHBoxLayout()
        layout.setContentsMargins(5, 2, 5, 2)

        self.button.clicked.connect(self.clicked)
        self.spinner = QSpinBox()

        if kwargs.get("height") is not None:
            self.spinner.setMinimumHeight(kwargs.get("height"))

        if kwargs.get("font") is not None:
            font = self.button.font()
            font.setPixelSize(int(kwargs.get("font")))
            self.spinner.setFont(font)

        self.spinner.setEnabled(False)
        self.spinner.lineEdit().setReadOnly(True)
        self.spinner.setMinimum(0)
        self.spinner.setSingleStep(self.step)
        self.spinner.setMaximum(100)
        self.spinner.setMaximumWidth(50)
        self.spinner.valueChanged.connect(self.score_changed.emit)  # type: ignore

        layout.addWidget(self.button)
        self.comment_lbl = QLabel(self.button)
        self.comment_lbl.setGeometry(5, 5, 15, 15)
        self.comment_lbl.setText("*")
        self.comment_lbl.setStyleSheet('background-color: #00FFFF00;')
        self.comment_lbl.setMaximumWidth(10)
        self.comment_lbl.setVisible(False)

        self.start_with = kwargs.get('start_with', 100)

        if self.n_steps > 0:
            layout.addWidget(self.spinner)

        self.setLayout(layout)

    def get_steps(self):
        return self.n_steps

    def get_weight(self):
        return self.weight

    def toggle_show_points(self):
        self.points_lb.setVisible(not self.points_lb.isVisible())

    def is_checked(self):
        return self.button.isChecked()

    def get_value(self):
        if self.is_checked():
            if self.n_steps == 0:
                value = 100
            else:
                value = self.spinner.value()
        else:
            value = -1

        return value

    def get_xls_value(self):
        value = self.get_value()
        return "" if value == -1 else str(value)

    def clicked(self):
        self.spinner.blockSignals(True)
        if QGuiApplication.queryKeyboardModifiers() == Qt.ControlModifier:
            self.spinner.setValue(0)
        elif self.button.which == Qt.MidButton:
            self.spinner.setValue(0)
        else:
            self.spinner.setValue(self.start_with if self.button.isChecked() else 0)
        self.spinner.setEnabled(self.button.isChecked())
        self.spinner.blockSignals(False)

        font = self.button.font()
        font.setBold(self.button.isChecked())
        self.button.setFont(font)

        self.score_changed.emit()  # type: ignore

    def store(self, exam_id):
        self.data[exam_id] = self.get_value()
        return self.data[exam_id]



    def retrieve(self, exam_id):
        self.set_value(self.data.get(exam_id, -1))

    def insert(self, exam_id, value):
        self.data[exam_id] = value

    def query(self, exam_id):
        return self.data.get(exam_id, -1)

    def set_value(self, value):
        self.button.blockSignals(True)
        self.button.setChecked(value >= 0 if self.n_steps > 0 else value > 0)
        self.button.blockSignals(False)

        self.spinner.blockSignals(True)
        self.spinner.setMinimum(0)
        self.spinner.setValue(value if value > 0 else 0)
        self.spinner.setEnabled(self.button.isChecked())
        self.spinner.blockSignals(False)

        font = self.button.font()
        font.setBold(self.button.isChecked())
        self.button.setFont(font)

        self.score_changed.emit()  # type: ignore

    def get_full_value(self):
        return self.full_value

    def click(self):
        self.button.click()

    def get_click_next(self):
        return self.click_next and self.button.isChecked()


class PercentButton(PushButton):
    score_changed = pyqtSignal()

    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        self.percent = kwargs.get('percent', 1)
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(5, 2, 5, 2)
        self.button.clicked.connect(self.score_changed.emit)
        self.layout().addWidget(self.button)
        self.type = "percent"

    def get_value(self):
        return 1 if self.button.isChecked() else 0

    def get_xls_value(self):
        return str(self.get_value())

    def get_percent(self):
        return self.percent

    def set_value(self, state):
        self.button.setChecked(state == 1)

    def set_xls_value(self, value):
        self.set_value(int(value))


class MultiplierButton(PercentButton):

    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.type = "multiplier"


class CutterButton(PercentButton):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.type = "cutter"
