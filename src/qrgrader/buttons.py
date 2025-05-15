from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QCursor, QGuiApplication, QFont
from PyQt5.QtWidgets import QWidget, QPushButton, QHBoxLayout, QSpinBox, QLabel, QTextEdit, QVBoxLayout


class Button(QWidget):
    def __init__(self, name):
        super().__init__()
        self.name = name

    def get_name(self):
        return self.name

class Shortcut(Button):
    clicked = pyqtSignal()

    def __init__(self, name, **kwargs):
        super().__init__(name)
        self.button = QPushButton(name)
        self.button.clicked.connect(self.clicked.emit)  # type: ignore
        self.buttons = kwargs.get("buttons", [])
        self.set_color(kwargs.get("color", "#FF0000"))
        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self.button)
        font = self.button.font()
        font.setItalic(True)
        self.button.setFont(font)

    def set_color(self, color):
        self.setStyleSheet('background-color:' + color)

    def get_buttons(self):
        return self.buttons

    def get_config(self):
        return {"type": "shortcut", "buttons": self.buttons, "color": self.styleSheet().split(":")[1]}



class Separator(Button):
    def __init__(self, name, **kwargs):
        super().__init__(name)
        self.setLayout(QHBoxLayout())
        self.label = QLabel(name)
        self.label.setFont(QFont("Arial", 10, QFont.Bold))
        self.label.setAlignment(Qt.AlignCenter)
        self.layout().addWidget(self.label)
        self.layout().setContentsMargins(5, 5, 5, 5)

    def get_config(self):
        return {"type": "separator"}


class StateButton(Button):
    pass


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

    def get_config(self):
        return {"type": "text"}

    def get_state(self):
        return {"text": self.button.toPlainText()}

    def set_state(self, state):
        self.button.setText(state.get("text", ""))

class PushButton(StateButton):

    def __init__(self,name, **kwargs):
        super().__init__(name)
        self.button = QPushButton(name)
        self.button.setMinimumWidth(10)
        self.button.setCheckable(True)

        if kwargs.get("height") is not None:
            self.button.setMinimumHeight(kwargs.get("height"))
        if kwargs.get("font") is not None:
            font = self.button.font()
            font.setPixelSize(int(kwargs.get("font")))
            self.button.setFont(font)

class StepButton(PushButton):
    score_changed = pyqtSignal()

    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        self.weight = kwargs.get('weight', 1)
        self.full_value = kwargs.get('full_value', 1)
        self.n_steps = kwargs.get('steps', 0)
        color = kwargs.get("color", "#D4D4D4")
        self.click_next = kwargs.get("click_next", False)

        self.comment = None
        self.step = int(100 / self.n_steps) if self.n_steps > 0 else 100

        layout = QHBoxLayout()
        layout.setContentsMargins(5, 2, 5, 2)

        if color is not None:
            self.button.setStyleSheet('background-color: {}'.format(color))
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

        self.set_comment(kwargs.get('comment', ""))
        self.start_with = kwargs.get('start_with', 100)

        if self.n_steps > 0:
            layout.addWidget(self.spinner)

        self.setLayout(layout)

    def get_weight(self):
        return self.weight

    def get_color(self):
        return self.button.styleSheet().split(":")[1].strip()

    def get_config(self):
        return {"type": "button", "steps": self.n_steps, "weight": self.weight, "full_value": self.full_value,
                "color": self.get_color(), "comment": self.comment, "start_with": self.start_with,
                "click_next": self.click_next}

    # kwargs = {"weight": 1, "full_value": 1,
    #                "steps": 0, "color": None,
    #                "comment": "", "start_with": 100,
    #                "click_next": False, "type": "button"}

    def toggle_show_points(self):
        self.points_lb.setVisible(not self.points_lb.isVisible())

    def is_checked(self):
        return self.button.isChecked()

    def get_state(self):
        if self.is_checked():
            if self.n_steps == 0:
                value = 100
            else:
                value = self.spinner.value()
        else:
            value = -1

        return {"value": value, "comment": self.comment}

    def get_xls_value(self):
        state = self.get_state()
        value = state.get("value")
        if value == -1:
            return " "
        else:
            return value / 100

    def get_value(self):
        if self.is_checked():
            if self.n_steps == 0:
                return self.get_full_value()
            else:
                return float(self.spinner.value() / 100.0) * self.get_full_value()
        else:
            return None

    def clicked(self):
        self.spinner.blockSignals(True)
        if QGuiApplication.queryKeyboardModifiers() == Qt.ControlModifier:
            self.spinner.setValue(0)
        else:
            self.spinner.setValue(self.start_with if self.button.isChecked() else 0)
        self.spinner.setEnabled(self.button.isChecked())
        self.spinner.blockSignals(False)

        font = self.button.font()
        font.setBold(self.button.isChecked())
        self.button.setFont(font)

        self.score_changed.emit()  # type: ignore

    def set_state(self, state):
        self.set_comment(state.get("comment", ""))
        value = state.get("value", -1)

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

    def set_comment(self, text):
        self.comment_lbl.setVisible(text != "")
        self.setToolTip(text)
        self.comment = text

    def get_comment(self):
        return self.comment

    def clear_comment(self):
        self.set_comment("")

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
        color = kwargs.get("color", "#D4D4D4")
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(5, 2, 5, 2)
        self.button.setStyleSheet('background-color: {}'.format(color))
        self.button.clicked.connect(self.score_changed.emit)
        self.layout().addWidget(self.button)

    def get_config(self):
        return {"percent": self.percent, "color": self.get_color()}

    def get_state(self):
        return {"percent": self.percent if self.button.isChecked() else 1}

    def set_state(self, state):
        self.button.setChecked(state.get("percent", 1) < 1)

    def get_xls_value(self):
        return self.percent if self.is_checked() else 1

    def get_color(self):
        return self.button.styleSheet().split(":")[1].strip()

    def get_percent(self):
        return self.percent if self.button.isChecked() else 1

    def get_click_next(self):
        return False

class MultiplierButton(PercentButton):

    def get_config(self):
        config = super().get_config()
        config["type"] = "multiplier"
        return config


class CutterButton(PercentButton):

    def get_config(self):
        config = super().get_config()
        config["type"] = "cutter"
        return config
