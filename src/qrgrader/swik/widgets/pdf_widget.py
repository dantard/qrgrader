from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtWidgets import QGraphicsProxyWidget, QTextEdit, QLineEdit, QCheckBox, QComboBox, QRadioButton
from qrgrader.swik.action import Action

from qrgrader.swik.interfaces import Undoable


class PdfWidget(QGraphicsProxyWidget, Undoable):
    count = 0

    def __init__(self, parent, content, rect, font_size):
        super(QGraphicsProxyWidget, self).__init__(parent)
        self.content = content
        self.widget = self.set_widget(content)
        font = self.widget.font()
        font.setPointSizeF(font_size if font_size else 9)
        self.widget.setFont(font)
        self.widget.setContentsMargins(0, 0, 0, 0)
        self.widget.setFixedSize(int(rect.width()), int(rect.height()))
        self.setWidget(self.widget)
        self.resize(rect.width(), rect.height())
        self.setPos(rect.topLeft())
        self.name = ""
        self.flags = 0
        self.xref = -1
        self.on_state = "Yes"
        self.current_state = content
        PdfWidget.count += 1

    def set_info(self, name, flags):
        self.name = name
        self.flags = flags

    def get_content(self):
        return self.content

    def get_rect(self):
        return QRectF(self.pos(), self.size())

    def set_content(self, content):
        self.content = content

    def set_widget(self, content):
        raise NotImplementedError("Subclasses must implement this method")

    def get_value(self):
        raise NotImplementedError("Subclasses must implement this method")

    def clear(self):
        raise NotImplementedError("Subclasses must implement this method")


class PdfTextWidget(PdfWidget):
    def __init__(self, parent, content, rect, font_size):
        super(PdfTextWidget, self).__init__(parent, content.strip(" "), rect, font_size)
        self.widget.setStyleSheet("background-color: lightblue;")

    def keyPressEvent(self, event):
        # Check if the key press is Ctrl+Z
        print(event.key(), event.modifiers())
        if event.key() == Qt.Key_Z and event.modifiers() == Qt.ControlModifier:
            self.scene().tracker().undo()
        elif event.key() == Qt.Key_Z and event.modifiers() | Qt.ControlModifier and event.modifiers() | Qt.ShiftModifier:
            self.scene().tracker().redo()
        super().keyPressEvent(event)  #

    def set_widget(self, content):
        le = QLineEdit()
        le.setText(content)
        le.textEdited.connect(self.text_changed)
        return le

    def text_changed(self, text):
        self.notify_change(Action.FULL_STATE, {"text": self.current_state}, {"text": text})
        self.current_state = text

    def undo(self, kind, info):
        self.widget.setText(info["text"])

    def get_value(self):
        return self.widget.text() if self.widget.text() != "" else " "

    def clear(self):
        self.widget.setText("")


class MultiLinePdfTextWidget(PdfTextWidget):
    def __init__(self, parent, content, rect, font_size):
        super().__init__(parent, content, rect, font_size)
        # self.widget.setStyleSheet("background-color: #FFC0CB;")

    def set_widget(self, content):
        te = QTextEdit()
        te.setText(content)
        te.textChanged.connect(self.te_text_changed)
        return te

    def te_text_changed(self):
        text = self.widget.document().toPlainText()
        self.notify_change(Action.FULL_STATE, {"text": self.current_state}, {"text": text})
        self.current_state = text

    def get_value(self):
        return self.widget.document().toPlainText()

    def clear(self):
        self.widget.document().setPlainText(" ")

    def undo(self, kind, info):
        self.widget.blockSignals(True)
        self.widget.document().setPlainText(info["text"])
        self.widget.blockSignals(False)


class PdfComboboxWidget(PdfTextWidget):

    def __init__(self, parent, content, rect, font_size, items):
        super().__init__(parent, content, rect, font_size)
        self.add_items(items)
        self.widget.setCurrentText(content)
        self.setZValue(1)

    def set_widget(self, content):
        cb = QComboBox()
        cb.setCurrentText(content)
        cb.currentTextChanged.connect(self.text_changed)
        return cb

    def undo(self, kind, info):
        self.widget.blockSignals(True)
        self.widget.setCurrentText(info["text"])
        self.widget.blockSignals(False)

    def add_items(self, items):
        self.widget.blockSignals(True)
        self.widget.addItems(items)
        self.widget.blockSignals(False)

    def get_value(self):
        return self.widget.currentText()

    def clear(self):
        self.widget.setCurrentIndex(0)


class PdfCheckboxWidget(PdfWidget):
    def set_widget(self, content):
        # print("Content: ", content)
        cb = QCheckBox()
        cb.setChecked(content == "On" or content == "Yes" or content == "True" or content == "1" or content == True)
        self.current_state = cb.isChecked()
        cb.stateChanged.connect(self.checkbox_changed)
        return cb

    def checkbox_changed(self, state):
        self.notify_change(Action.FULL_STATE, {"state": self.current_state}, {"state": self.widget.isChecked()})
        self.current_state = self.widget.isChecked()

    def undo(self, kind, info):
        self.widget.blockSignals(True)
        self.widget.setChecked(info["state"])
        self.widget.blockSignals(False)

    def get_value(self):
        # return self.widget.isChecked()
        return self.widget.isChecked()

    def clear(self):
        self.widget.setChecked(False)


class PdfRadioButtonWidget(PdfWidget):
    def set_widget(self, content):
        cb = QRadioButton()
        cb.setChecked(content == "On" or content == "Yes" or content == "True" or content == "1" or content == True)
        self.current_state = cb.isChecked()
        cb.setAutoExclusive(False)
        cb.clicked.connect(self.radiobutton_changed)
        return cb

    def radiobutton_changed(self, state):
        self.notify_change(Action.FULL_STATE, {"state": self.current_state}, {"state": self.widget.isChecked()})
        self.current_state = self.widget.isChecked()

    def undo(self, kind, info):
        self.widget.blockSignals(True)
        self.widget.setChecked(info["state"])
        self.widget.blockSignals(False)

    def get_value(self):
        return self.widget.isChecked()

    def clear(self):
        self.widget.setChecked(False)
