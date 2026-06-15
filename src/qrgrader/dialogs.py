from PyQt5 import QtWidgets, QtGui, Qt, QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (QLineEdit, QPushButton, QSpinBox, QDialog, QDialogButtonBox, QComboBox, QDoubleSpinBox,
                             QFormLayout, QCheckBox, QApplication, QDialog, QPushButton,
                             QGridLayout, QVBoxLayout, QHBoxLayout,
                             QDialogButtonBox, QLabel, QTreeWidget, QTreeWidgetItem, QHeaderView, QStatusBar)

from qrgrader.widget_utils import WidgetsRow, VBox


class ButtonEditDialog(QDialog):
    def __init__(self, draggable_list, button=None, existing_names=None):
        super().__init__()

        self.existing_names = existing_names if existing_names is not None else []

        if button is not None and button.get_name() in self.existing_names:
            self.existing_names.remove(button.get_name())

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

        self.layout.addWidget(WidgetsRow("Type", self.combo))

        self.le = QLineEdit()
        self.le.textChanged.connect(self.check_valid_name)  # type: ignore
        self.le.setText(button.get_name() if button is not None else "")
        self.le.setPlaceholderText("Unique name")
        self.layout.addWidget(WidgetsRow("Name", self.le))

        # self.value = QComboBox()
        self.value = QDoubleSpinBox()
        self.value.setDecimals(1)
        self.value.setMinimum(-20)
        self.value.setMaximum(20)
        self.value.setSingleStep(0.5)
        self.value.valueChanged.connect(self.spin_value_changed)  # type: ignore
        self.layout.addWidget(WidgetsRow("Value", self.value))

        self.steps = QSpinBox()
        self.steps.setMinimum(0)
        self.steps.setMaximum(10)

        self.layout.addWidget(WidgetsRow("Steps", self.steps))
        #
        self.percent = QSpinBox()
        self.percent.setMinimum(0)
        self.percent.setMaximum(100)
        self.layout.addWidget(WidgetsRow("Percent", self.percent))
        #
        self.weight = QDoubleSpinBox()
        self.weight.setDecimals(2)
        self.weight.setMinimum(-20)
        self.weight.setMaximum(20)
        self.weight.setSingleStep(0.5)
        self.layout.addWidget(WidgetsRow("Weight", self.weight))

        self.click_next_cb = QCheckBox("Next on click")
        self.layout.addWidget(self.click_next_cb)

        # Show the current color and a color picker button
        self.color = "#D4D4D4"
        self.colorButton = QPushButton('Choose color')
        self.colorButton.clicked.connect(self.pick_color)  # type: ignore
        self.layout.addWidget(WidgetsRow('Color', self.colorButton))

        self.layout.addWidget(self.buttonBox)
        self.combo.currentTextChanged.connect(self.cb_changed)  # type: ignore


        if button is not None:
            self.combo.setCurrentText(button.get_type())
            self.color = QColor(button.get_color())
            if button.get_type() in ['multiplier', 'cutter']:
                self.percent.setValue(int(button.get_percent() * 100))
            if button.get_type() in ['button']:
                self.steps.setValue(int(button.get_steps()))
                self.weight.setValue(float(button.get_weight()))
                self.click_next_cb.setChecked(button.get_click_next())

            self.value.setValue(float(button.get_full_value()))
            self.colorButton.setStyleSheet(f'background-color: {button.get_color()}')

        self.enable_widgets()



    def check_valid_name(self, text):
        ok = self.le.text() != "" and self.le.text() not in self.existing_names
        self.buttonBox.buttons()[0].setEnabled(ok)


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
        #self.layout.widgets['Percent'].setVisible(mc)
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
            res['color'] = self.color
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
        self.le.setValidator(QtGui.QDoubleValidator(0, 10, 2))

        self.le.textChanged.connect(
            lambda: self.buttonBox.buttons()[0].setEnabled(self.le.text() != ""))  # type: ignore
        self.le.setText(str(self.config.get("weight", 10)))
        self.layout.addRow("Weight", self.le)

        self.precision = QLineEdit()
        self.precision.setValidator(QtGui.QIntValidator(1, 4))
        self.layout.addRow("Precision", self.precision)
        self.precision.setText(str(self.config.get("precision", 2)))

        self.layout.addWidget(self.buttonBox)

    # if accepted, modify the config
    def accept(self):
        self.config["weight"] = float(self.le.text())
        self.config["page"] = int(self.combo.text())
        self.config["precision"] = int(self.precision.text())
        super().accept()


class ControlDialog(QDialog):
    def __init__(self, page, accepting, up, down, left, right, scale_up, scale_down, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f" ")
        self.setFixedSize(150, 170)
        self.accepting = accepting

        # Direction buttons
        btn_up = QPushButton("↑")
        btn_up.clicked.connect(up)
        btn_down = QPushButton("↓")
        btn_down.clicked.connect(down)
        btn_left = QPushButton("←")
        btn_left.clicked.connect(left)
        btn_right = QPushButton("→")
        btn_right.clicked.connect(right)

        # Scale buttons
        btn_scale_up = QPushButton("+")
        btn_scale_up.clicked.connect(scale_up)
        btn_scale_down = QPushButton("-")
        btn_scale_down.clicked.connect(scale_down)

        # Compact size
        for b in [btn_up, btn_down, btn_left, btn_right, btn_scale_up, btn_scale_down]:
            b.setFixedSize(28, 28)
            b.setAutoRepeat(True)
            b.setAutoRepeatInterval(25)

        grid = QGridLayout()
        # grid.setSpacing(2)
        # grid.setContentsMargins(2, 2, 2, 2)

        grid.addWidget(btn_up, 0, 1)
        grid.addWidget(btn_left, 1, 0)
        grid.addWidget(btn_right, 1, 2)
        grid.addWidget(btn_down, 2, 1)

        grid.addWidget(btn_scale_down, 0, 2)
        grid.addWidget(btn_scale_up, 2, 2)

        close = QPushButton("Done")
        close.clicked.connect(self.close)
        layout = QVBoxLayout()
        label = QLabel(f"Page {page + 1}")
        label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(label)
        layout.addLayout(grid)
        # buttons.setContentsMargins(2,10,2,2)
        layout.addWidget(close)

        self.setLayout(layout)

    # on ok clicked
    def closeEvent(self, a):
        super().closeEvent(a)
        self.accepting()


class NameListDialog(QDialog):
    def __init__(self, names, selecting=None, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        self.list = QTreeWidget()
        self.list.setColumnCount(2)
        self.list.setSortingEnabled(True)

        for n, g in names:
            tw = QTreeWidgetItem()
            tw.setText(0, str(n))
            tw.setText(1, str(g))
            self.list.addTopLevelItem(tw)
        self.list.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.list.headerItem().setText(0, "Name")
        self.list.headerItem().setText(1, "Group")
        if selecting is not None:
            for i in range(self.list.topLevelItemCount()):
                item = self.list.topLevelItem(i)
                if item.text(0) == selecting:
                    self.list.setCurrentItem(item)
        else:
            self.list.setCurrentIndex(0)

        dialog_ok_cancel_btn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonBox = QDialogButtonBox(dialog_ok_cancel_btn)
        self.buttonBox.accepted.connect(self.accept)  # type: ignore
        self.buttonBox.rejected.connect(self.reject)  # type: ignore
        layout.addWidget(self.list)
        layout.addWidget(self.buttonBox)
        self.setMinimumWidth(450)
        self.setLayout(layout)


    def get_selected(self):
        return self.list.currentItem().text(0)
