import base64
import sys

from PyQt5 import QtGui
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIntValidator, QDoubleValidator, QValidator
from PyQt5.QtWidgets import (
    QPushButton,
    QWidget,
    QHBoxLayout,
    QFileDialog,
    QLineEdit,
    QLabel,
    QCheckBox,
    QComboBox,
    QTextEdit, QSlider, QStyle, QListWidget, QInputDialog, QVBoxLayout, QSizePolicy
)


class InteractorWidget(QWidget):
    value_changed = pyqtSignal()

    def __init__(self, elem):
        super().__init__(None)
        self.elem = elem
        self.kwargs = elem.kwargs
        self.elem.value_changed.connect(self.value_changed_external)
        self.elem.param_changed.connect(self.param_changed_external)

        if not self.check_kwargs():
            sys.exit(0)

        self.name = elem.key
        self.pretty = elem.get_pretty()
        self.layout = QHBoxLayout()
        ql = QLabel(self.pretty)
        ql.setMinimumWidth(100)
        ql.setAlignment(Qt.AlignLeft)
        self.layout.setContentsMargins(2, 2, 2, 2)
        self.setLayout(self.layout)
        self.setFocusPolicy(Qt.TabFocus)
        self.widget = None
        self.emit_cb = True
        self.add_widget(elem.get_value())

    def value_changed_external(self):
        self.set_value(self.elem.get_value())

    def param_changed_external(self, kwargs):
        # print("param_changed_external", kwargs)
        self.update(**kwargs)

    def set_value(self, value):
        raise NotImplementedError

    def get_elem(self):
        return self.elem

    def set_emit_callback(self, value):
        self.emit_cb = value

    def update(self, **kwargs) -> None:
        pass

    def get_valid(self):
        return self.get_common()

    def get_common(self):
        return {"default", "save", "fmt", "pretty", "callback", "editable"}

    def check_kwargs(self):
        for arg in self.kwargs:
            if arg not in self.get_valid():
                print("Parameter", arg, "not valid for ", type(self))
                return False
        return True

    def add_widget(self, value):
        raise NotImplementedError


class String(InteractorWidget):
    class MyLineEdit(QLineEdit):
        focusout = pyqtSignal()

        def focusOutEvent(self, a0) -> None:
            super().focusOutEvent(a0)
            self.focusout.emit()

    def __init__(self, elem):
        super().__init__(elem)
        self.prev_value = elem.get_value()
        self.widget.setReadOnly(not self.kwargs.get('editable', True))

    def get_valid(self):
        return self.get_common()

    def return_pressed(self):
        self.setStyleSheet("color: black")
        if self.get_value() != self.prev_value:
            self.value_changed.emit()
            self.prev_value = self.get_value()

    def text_changed(self):
        self.setStyleSheet("color: red")

    def validate(self):
        if (validator := self.widget.validator()) is not None:
            res, _, _ = validator.validate(self.widget.text(), 0)
            if res == QValidator.Acceptable:
                self.return_pressed()
        else:
            self.return_pressed()

    def add_widget(self, value):
        self.widget = self.MyLineEdit()
        self.widget.returnPressed.connect(self.return_pressed)
        self.widget.focusout.connect(self.validate)
        self.widget.textEdited.connect(self.text_changed)
        fmt = self.kwargs.get("fmt", "{}")
        if value is not None:
            self.widget.setText(fmt.format(value))
            self.widget.home(True)
            self.widget.setSelection(0, 0)
        self.layout.addWidget(self.widget)

    def get_value(self):
        return self.widget.text() if self.widget.text() != "" else None

    def set_value(self, value):
        self.widget.setText(str(value))

    def get_name(self):
        return self.name


class DoubleLabel(InteractorWidget):

    def add_widget(self, value):
        self.widget = QLabel()
        fmt = self.kwargs.get("fmt", "{}")
        if value is not None and value[0] is not None:
            self.widget.setText(fmt.format(value[0]))

        self.widget2 = QLabel()
        layout = QHBoxLayout()
        layout.addWidget(self.widget)
        layout.addWidget(self.widget2)

        self.layout.addLayout(layout)
        if value is not None and value[1] is not None:
            self.widget2.setText(fmt.format(value[1]))

    def set_value(self, value):
        if value is not None:
            if value[0] is not None:
                self.widget.setText(str(value[0]))
            if value[1] is not None:
                self.widget2.setText(str(value[1]))


class List(InteractorWidget):
    def __init__(self, elem):
        super().__init__(elem)
        self.value_type = elem.kwargs.get("type", "str")

    def ask_value(self): # retry submit
        default = self.widget.currentItem().text() if self.widget.currentItem() is not None else ""
        if self.value_type == "str":
            default = str(default) if default is not None else ""
            text, ok = QInputDialog.getText(None, "Input", "Enter item", QLineEdit.Normal, default)
            return str(text), ok
        elif self.value_type == "int":
            try:
                default = int(default)
            except ValueError:
                default = 0
            text, ok = QInputDialog.getInt(None, "Input", "Enter item", value=default)
            return str(text), ok
        elif self.value_type == "float":
            try:
                default = float(default)
            except ValueError:
                default = 0.0
            text, ok = QInputDialog.getDouble(None, "Input", "Enter item", value=default)
            return str(text), ok
        elif self.value_type == "file":
            default = str(default) if default is not None else ""
            text, ok = QFileDialog.getOpenFileName(None, "Open file", default, "All files (*)")
            return text, ok

    def add_item(self):
        text, ok = self.ask_value()
        if ok:
            self.widget.addItem(str(text))

    def del_item(self):
        if self.widget.currentItem():
            self.widget.takeItem(self.widget.currentRow())

    def edit_item(self):
        if self.widget.currentItem():
            text, ok = self.ask_value()
            if ok:
                self.widget.currentItem().setText(text)

    def add_widget(self, value):
        helper = QWidget()
        helper.setContentsMargins(0, 0, 0, 0)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        helper.setLayout(layout)
        button_add = QPushButton("+")
        button_del = QPushButton("−")
        button_edit = QPushButton("✎")
        button_add.clicked.connect(self.add_item)
        button_edit.clicked.connect(self.edit_item)
        button_del.clicked.connect(self.del_item)

        for button in [button_add, button_del, button_edit]:
            button.setFixedSize(25, 25)
            button.setStyleSheet("font-size: 14px")

        h_layout = QHBoxLayout()
        h_layout.addWidget(button_add)
        h_layout.addWidget(button_edit)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        h_layout.addWidget(spacer)
        h_layout.addWidget(button_del)
        h_layout.setAlignment(Qt.AlignLeft)

        self.widget = QListWidget()
        layout.addWidget(self.widget)

        if self.kwargs.get("editable", True):
            layout.addLayout(h_layout)

        self.widget.addItems([str(v) for v in value] if value is not None else [])
        self.layout.addWidget(helper)
        self.widget.setMaximumHeight(self.kwargs.get("height", 100))
        self.widget.setFont(QFont("Courier New", 10))

    def get_valid(self):
        return self.get_common().union(["height", "frame", "type"])

    def get_value(self):
        if self.value_type == "int":
            return [int(self.widget.item(i).text()) for i in range(self.widget.count())]
        elif self.value_type == "float":
            return [float(self.widget.item(i).text()) for i in range(self.widget.count())]
        return [self.widget.item(i).text() for i in range(self.widget.count())]

    def set_value(self, value):
        self.widget.clear()
        self.widget.addItems(value)

    def update(self, **kwargs) -> None:
        # print("List update", kwargs)
        if "items" in kwargs:
            self.widget.clear()
            self.widget.addItems(kwargs["items"])

        if "on_selection" in kwargs:
            self.widget: QListWidget
            self.widget.doubleClicked.connect(kwargs["on_selection"])

class EditBox(String):

    def add_widget(self, value):
        self.widget = QTextEdit()
        self.widget.textChanged.connect(lambda: self.value_changed.emit())
        font = QFont(self.kwargs.get("font", "Monospace"))

        if self.kwargs.get("bold", False):
            font.setBold(True)
        if self.kwargs.get("italic", False):
            font.setItalic(True)
        if self.kwargs.get("typewriter", False):
            font.setStyleHint(QFont.TypeWriter)

        font.setPointSize(self.kwargs.get("size", 10))

        self.widget.setFont(font)
        self.widget.setMaximumHeight(self.kwargs.get("height", 100))

        if value is not None:
            self.widget.setText(str(value))

        self.layout.addWidget(self.widget)

    def get_valid(self):
        return self.get_common().union(["font", "bold", "italic", "typewriter", "size", "height"])

    def set_value(self, value):
        self.widget.setText(str(value).replace("&&", "\n"))

    def get_value(self):
        text = self.widget.toPlainText().replace("\n", "&&")
        return text if text != "" else None


class Password(String):
    def __init__(self, elem):
        super().__init__(elem)
        # value = base64.decodebytes(value.encode()).decode() if value else None
        self.widget.setEchoMode(QLineEdit.Password)

    def get_value(self):
        if self.widget.text() != "":
            return (
                base64.encodebytes(self.widget.text().encode())
                    .decode()
                    .replace("\n", "")
            )
        else:
            return None


class ComboBox(InteractorWidget):
    class MyComboBox(QComboBox):
        def wheelEvent(self, e: QtGui.QWheelEvent) -> None:
            e.ignore()

    def add_widget(self, value):
        self.widget = self.MyComboBox()
        self.widget.currentIndexChanged.connect(lambda: self.value_changed.emit())
        self.widget.addItems(self.kwargs.get("items", []))
        self.widget.setEditable(self.kwargs.get("editable", False))
        self.layout.addWidget(self.widget, stretch=2)
        self.widget.setCurrentIndex(value if value is not None else 0)

    def update(self, **kwargs):
        # print("List update", kwargs)

        items = kwargs.get("append")
        if items is not None:
            self.widget.addItems(items)

        items = kwargs.get("items")
        if items is not None:
            self.widget.clear()
            self.widget.addItems(items)

        color = kwargs.get("color")
        if color is not None:
            self.widget.setStyleSheet("QComboBox { color: %s }" % color)

    def get_valid(self):
        return self.get_common().union(["items"])

    def get_item_text(self):
        return self.widget.currentText()

    def get_value(self):
        return self.widget.currentIndex() if self.widget.currentText() != "" else None

    def set_value(self, value):
        if value is not None and value < self.widget.count():
            self.widget.setCurrentIndex(value)
        else:
            self.widget.setCurrentIndex(0)


class Integer(String):
    def add_widget(self, value):
        super().add_widget(value)
        validator = QIntValidator()
        if self.kwargs.get("max") is not None:
            validator.setTop(self.kwargs.get("max"))
        if self.kwargs.get("min") is not None:
            validator.setBottom(self.kwargs.get("min"))
        self.widget.setValidator(validator)

    def get_valid(self):
        return super().get_common().union(["max", "min"])

    def get_value(self):
        return int(self.widget.text()) if self.widget.text().isnumeric() else None


class Slider(InteractorWidget):
    class MySlider(QSlider):
        def wheelEvent(self, e: QtGui.QWheelEvent) -> None:
            e.ignore()

    class MyLabel(QLabel):
        double_click = pyqtSignal()

        def mouseDoubleClickEvent(self, a0: QtGui.QMouseEvent) -> None:
            self.double_click.emit()

    def update(self, **kwargs):
        if 'maximum' in kwargs:
            self.widget.setMaximum(kwargs.get('maximum', 100))

    def add_widget(self, value):
        self.layout.setContentsMargins(6, 6, 6, 6)
        hbox = QHBoxLayout()

        def clicked():
            min = self.kwargs.get('min', 0) / self.kwargs.get('den', 1)
            num, ok = QInputDialog.getDouble(self, "Set value", "Value", min=min, value=1)
            if ok:
                self.set_value(num)

        self.den = self.kwargs.get('den', 1)
        self.widget = self.MySlider()
        self.lbl = self.MyLabel()
        self.lbl.double_click.connect(clicked)
        self.lbl.setMinimumWidth(self.kwargs.get("label_width", 25))
        self.lbl.setMaximumWidth(self.kwargs.get("label_width", 25))
        self.widget.setOrientation(Qt.Horizontal)
        self.widget.setMinimum(self.kwargs.get('min', 0))
        self.widget.setMaximum(self.kwargs.get('max', 100))
        self.widget.valueChanged.connect(self.slider_moved)
        self.widget.setContentsMargins(2, 2, 2, 2)
        # self.layout.addWidget(self.widget)
        hbox.addWidget(self.lbl)
        hbox.addWidget(self.widget)
        self.layout.addLayout(hbox)
        self.set_value(value)

    def get_valid(self):
        return self.get_common().union(["min", "max", "den", "label_width", "grow"])

    def slider_moved(self, value):
        fmt = self.kwargs.get("fmt", "{}")

        if self.emit_cb:
            self.value_changed.emit()

        if type(fmt) == int:
            self.lbl.setText(str(round(self.widget.value() / self.den, int(fmt))).rstrip('0').rstrip('.'))
        else:
            self.lbl.setText(fmt.format(self.widget.value() / self.den))

    def set_value(self, value):
        self.widget: QSlider
        if self.kwargs.get("grow", False) and int(value * self.den) > self.widget.maximum():
            self.widget.setMaximum(int(value * self.den))
        fmt = self.kwargs.get("fmt", "{}")
        self.widget.setValue(int(value * self.den))
        if type(fmt) == int:
            self.lbl.setText(str(round(self.widget.value() / self.den, int(fmt))).rstrip('0').rstrip('.'))
        else:
            self.lbl.setText(fmt.format(self.widget.value() / self.den))

    def reset(self):
        self.widget.setMaximum(self.kwargs.get("max", 100))

    def get_value(self):
        return float(self.widget.value() / self.den)


class Label(InteractorWidget):
    def add_widget(self, value):
        self.widget = QLabel()
        self.widget.setContentsMargins(2, 2, 2, 2)
        self.layout.addWidget(self.widget)
        fmt = self.kwargs.get("fmt", "{}")
        if value is not None:
            self.set_value(fmt.format(value))

    def set_value(self, value):
        fmt = self.kwargs.get("fmt", "{}")
        if value is not None:
            self.widget.setText(fmt.format(value))
        else:
            self.widget.setText("")

    def get_value(self):
        return self.widget.text()


class Float(String):
    def add_widget(self, value):
        super().add_widget(value)
        validator = QDoubleValidator()
        self.widget.setValidator(validator)

    def get_value(self):
        return (
            float(self.widget.text())
            if self.widget.text().replace(".", "").isnumeric()
            else None
        )


class Checkbox(InteractorWidget):
    def state_changed(self):
        self.value_changed.emit()

    def add_widget(self, value):
        self.layout.setContentsMargins(6, 6, 6, 6)
        self.widget = QCheckBox()
        self.widget.stateChanged.connect(self.state_changed)
        self.layout.addWidget(self.widget)
        self.set_value(value)

    def get_name(self):
        return self.name

    def get_value(self):
        return self.widget.isChecked()

    def set_value(self, value):
        self.widget.setChecked(value if value is not None else False)


class File(String):
    def __init__(self, elem):
        super().__init__(elem)
        self.btn = QPushButton()
        self.btn.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
        self.btn_discard = QPushButton()
        self.btn_discard.setMaximumWidth(25)
        self.btn_discard.setIcon(self.style().standardIcon(QStyle.SP_DialogCancelButton))
        self.btn_discard.clicked.connect(self.discard)
        self.btn.setMaximumWidth(30)
        self.btn.clicked.connect(self.open_file)
        self.layout.addWidget(self.btn)
        self.layout.addWidget(self.btn_discard)
        self.widget.setReadOnly(True)

    def get_valid(self):
        return self.get_common().union(["extension", "extension_name"])

    def discard(self):
        self.widget.setText("")

    def open_file(self):
        extension = self.kwargs.get("extension", "txt")
        extension_name = self.kwargs.get("extension_name", extension if type(extension) == str else "")

        ext_filter = "("
        if type(extension) == list:
            for ext in extension:
                ext_filter += "*." + ext + " "
        else:
            ext_filter += "*." + extension

        ext_filter = ext_filter.rstrip() + ")"

        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open " + extension_name + " Document",
            self.widget.text(),
            extension_name.upper() + " Files " + ext_filter,
        )
        if file_name != "":
            self.widget.setText(file_name)
            self.value_changed.emit()


class FolderChoice(File):
    def open_file(self):
        file_name = QFileDialog.getExistingDirectory(self, "Select Directory", "")
        if file_name != "":
            self.widget.setText(file_name)
            self.value_changed.emit()


class SaveFile(File):
    def open_file(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Open " + self.extension.upper() + " Document", "",
                                                   self.extension.upper() + " Files (*." + self.extension + ")")
        if file_name != "":
            self.widget.setText(file_name)
            self.value_changed.emit()
