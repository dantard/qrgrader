from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (QLineEdit, QPushButton, QSpinBox, QDialog, QDialogButtonBox, QComboBox, QDoubleSpinBox, QFormLayout, QCheckBox)

from qrgrader.widget_utils import WidgetsRow, VBox


class ButtonEditDialog(QDialog):
    def __init__(self, draggable_list, button=None):
        super().__init__()

        schema = button.get_config() if button is not None else {}

        self.draggable_list = draggable_list
        self.setWindowTitle("Edit")

        dialog_ok_cancel_btn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonBox = QDialogButtonBox(dialog_ok_cancel_btn)
        self.buttonBox.accepted.connect(self.accept)  # type: ignore
        self.buttonBox.rejected.connect(self.reject)  # type: ignore
        self.buttonBox.buttons()[0].setEnabled(False)

        self.layout = VBox()
        self.setLayout(self.layout)

        self.combo = QComboBox()
        self.combo.addItems(['button', 'multiplier', 'cutter', 'text', 'separator'])
        self.combo.setCurrentText(schema.get('type', 'button'))
        self.layout.addWidget(WidgetsRow("Type", self.combo))

        self.le = QLineEdit()
        self.le.textChanged.connect(lambda: self.buttonBox.buttons()[0].setEnabled(self.le.text() != ""))  # type: ignore
        self.le.setText(button.get_name() if button is not None else "")
        self.layout.addWidget(WidgetsRow("Name", self.le))

        # self.value = QComboBox()
        self.value = QDoubleSpinBox()
        self.value.setDecimals(1)
        self.value.setMinimum(-20)
        self.value.setMaximum(20)
        self.value.setValue(float(schema.get('full_value', 1)))
        self.value.setSingleStep(0.5)
        self.value.valueChanged.connect(self.spin_value_changed)  # type: ignore

        # self.fill_cb(schema.get("type", 'button'), schema.get('value', 1))
        self.layout.addWidget(WidgetsRow("Value", self.value))

        self.steps = QSpinBox()
        self.steps.setMinimum(0)
        self.steps.setMaximum(10)
        self.steps.setValue(int(schema.get('steps', 0)))
        self.layout.addWidget(WidgetsRow("Steps", self.steps))
        #
        self.percent = QSpinBox()
        self.percent.setMinimum(0)
        self.percent.setMaximum(100)
        self.percent.setValue(int(schema.get('percent', 1) * 100))
        self.layout.addWidget(WidgetsRow("Percent", self.percent))
        #
        self.weight = QDoubleSpinBox()
        self.weight.setDecimals(1)
        self.weight.setMinimum(-20)
        self.weight.setMaximum(20)
        self.weight.setValue(float(schema.get('weight', 1)))
        self.weight.setSingleStep(0.5)
        self.layout.addWidget(WidgetsRow("Weight", self.weight))

        self.click_next_cb = QCheckBox("Next on click")
        self.click_next_cb.setChecked(schema.get('click_next', False))
        self.layout.addWidget(self.click_next_cb)

        # Show the current color and a color picker button
        self.color = QColor(schema.get('color', "#D4D4D4"))
        self.colorButton = QPushButton('Choose color')
        self.colorButton.clicked.connect(self.pick_color)  # type: ignore
        self.layout.addWidget(WidgetsRow('Color', self.colorButton))
        self.colorButton.setStyleSheet(f'background-color: {schema.get("color", "#D4D4D4")}')

        self.layout.addWidget(self.buttonBox)
        self.combo.currentTextChanged.connect(self.cb_changed)  # type: ignore

        self.enable_widgets()

    def spin_value_changed(self, value):
        if value < 0:
            self.weight.setStyleSheet('background-color: red')
            self.weight.setValue(0)
            QTimer.singleShot(1000, lambda: self.weight.setStyleSheet(''))

    def cb_changed(self, text):
        #        self.fill_cb(self.combo.currentText(), 1)
        self.enable_widgets()

    def enable_widgets(self):
        b = self.combo.currentText() in ['button']
        bm = self.combo.currentText() in ['button', 'multiplier']
        bmc = self.combo.currentText() in ['button', 'multiplier', 'cutter']
        mc = self.combo.currentText() in ['multiplier', 'cutter']

        self.layout.widgets['Value'].setVisible(b)
        self.layout.widgets['Steps'].setVisible(b)
        self.layout.widgets['Weight'].setVisible(b)
        self.layout.widgets['Color'].setVisible(bmc)
        self.layout.widgets['Percent'].setVisible(mc)
        self.click_next_cb.setVisible(b)

        self.adjustSize()

    def pick_color(self, button):
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            self.color = color
            self.colorButton.setStyleSheet(f'background-color: {color.name()}')

    def get_stylesheet(self):
        return f'background-color: {self.color.name()}'

    def get(self):
        res = {'type': self.combo.currentText()}
        if self.combo.currentText() in ['button', 'multiplier', 'cutter']:
            res['color'] = self.color.name()
        if self.combo.currentText() in ['multiplier', 'cutter']:
            res['percent'] = float(self.percent.value() / 100.0)
        if self.combo.currentText() in ['button']:
            res['steps'] = self.steps.value()
            res['weight'] = float(self.weight.value())
            res['full_value'] = float(self.value.value())
            res['click_next'] = self.click_next_cb.isChecked()

        return self.le.text(), self.combo.currentText(), res


class RubricEditDialog(QDialog):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.setWindowTitle("Edit")

        dialog_ok_cancel_btn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonBox = QDialogButtonBox(dialog_ok_cancel_btn)
        self.buttonBox.accepted.connect(self.accept)  # type: ignore
        self.buttonBox.rejected.connect(self.reject)  # type: ignore
        self.buttonBox.buttons()[0].setEnabled(False)

        self.layout = QFormLayout()
        self.setLayout(self.layout)

        self.combo = QLineEdit()
        self.combo.setValidator(QtGui.QIntValidator(1, 99))
        self.layout.addRow("Page", self.combo)
        self.combo.setText(str(self.config.get("page", 1)))

        self.le = QLineEdit()

        # limit to 1 decimal
        self.le.setValidator(QtGui.QDoubleValidator(0, 10, 1))

        self.le.textChanged.connect(lambda: self.buttonBox.buttons()[0].setEnabled(self.le.text() != ""))  # type: ignore
        self.le.setText(str(self.config.get("weight", 10)))
        self.layout.addRow("Weight", self.le)

        self.layout.addWidget(self.buttonBox)

    # if accepted, modify the config
    def accept(self):
        self.config["weight"] = float(self.le.text())
        self.config["page"] = int(self.combo.text())
        super().accept()
