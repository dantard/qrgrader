from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QButtonGroup, QPushButton, QToolBar, QWidget, QSizePolicy


class GroupBox:
    class Action:
        def __init__(self, button, param, separator=False):
            self.button = button
            self.param = param
            self.separator = separator

    def __init__(self, common_callback=None):
        self.actions = []
        self.group = QButtonGroup()
        self.default_action = None
        self.toolbar2 = QToolBar()
        self.param = None
        self.current = None
        self.common_callback = common_callback

    def set_common_callback(self, callback):
        self.common_callback = callback

    def on_any_button_clicked(self, callback):
        self.group.buttonClicked.connect(callback)

    def local_callback(self, action):
        # This is to return to default button if
        # the button already checked if pressed
        if self.default_action and action.button == self.current:
            action = self.default_action
            action.button.blockSignals(True)
            action.button.setChecked(True)
            action.button.blockSignals(False)
        self.current = action.button

        # Here we call the proper function
        if callable(action.param):
            action.param()
        elif self.common_callback is not None:
            self.common_callback(action.param)

    def add(self, param, default=False, text="", icon=None, separator=False):
        btn = QPushButton()
        btn.setContentsMargins(0, 0, 0, 0)
        btn.setIconSize(QSize(24, 24))
        btn.setFlat(True)
        btn.setCheckable(True)
        action = self.Action(btn, param, separator)
        btn.clicked.connect(lambda: self.local_callback(action))

        if (icon := QIcon(icon)) is not None:
            btn.setIcon(icon)
            btn.setToolTip(text)
        else:
            btn.setText(text)
        btn.setToolTip(text)
        if default:
            btn.setChecked(True)
            self.default_action = action
        self.actions.append(action)
        self.group.addButton(btn)
        return btn

    def click(self, value):
        self.actions[value].click()

    def select(self, name):
        for action in self.actions:
            if action.button.toolTip() == name:
                action.button.click()
                break

    def reset(self):
        self.default_action.button.click()

    def get_selected(self):
        for i, actions in enumerate(self.actions):
            if actions.button.isChecked():
                return i

    def append(self, toolbar: QToolBar):
        for action in self.actions:
            # action.button.setContentsMargins(0, 40, 0, 0)
            toolbar.addWidget(action.button)
            spacer2 = QWidget()
            spacer2.setMinimumHeight(5)
            spacer2.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            toolbar.addWidget(spacer2)
            if action.separator:
                toolbar.addSeparator()

    def set_enabled(self, value):
        self.toolbar2.setEnabled(value)
