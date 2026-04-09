#!/usr/bin/env python
import csv
import os

import gspread.utils
import yaml
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QDrag, QPixmap, QPainter
from PyQt5.QtWidgets import (QListWidget,
                             QAbstractItemView, QListWidgetItem, QMenu, QMessageBox,
                             QInputDialog, QColorDialog, QWidget, QCheckBox, QVBoxLayout, QDialog, QPushButton,
                             QDialogButtonBox)
from qrgrader.common import get_date

from qrgrader.dialogs import ButtonEditDialog, RubricEditDialog
from qrgrader.buttons import StepButton, Shortcut, Button, TextButton, StateButton, Separator, CutterButton, MultiplierButton


class FilterListWidget(QListWidget):
    score_changed = pyqtSignal(object, int)
    goto_next = pyqtSignal()
    button_or_value_changed = pyqtSignal()

    def __init__(self, rubric, **kwargs):
        super().__init__()

        self.exam_id = None
        self.config = {}
        self.scores = {}
        self.schema_dictionary = {}
        self.schema_filename = rubric.schema_filename
        name = self.schema_filename.split(".")[0]
        self.scores_filename = name + ".yaml"

        self.current_exam_id = None
        self.modified = False
        self.buttons_height = kwargs.get("buttons_height")
        self.buttons_font = kwargs.get("buttons_font")

        self.setMinimumWidth(115)

        self.populate()
        #self.load_scores()

    def load_scores(self):
        if os.path.exists(self.scores_filename):
            with open(self.scores_filename) as file:
                self.scores = yaml.safe_load(file)


    def get_selection(self):
        selected_filters = {}
        for index in range(self.count()):
            item = self.item(index)
            button: Button = self.itemWidget(item)
            cb: QCheckBox = button.layout().itemAt(0).widget()
            if cb.isChecked():
                selected_filters[button.name] = button.get_state()
        return selected_filters

    def populate(self):
        if os.path.exists(self.schema_filename):
            # Load schema
            with open(self.schema_filename, newline='') as csvfile:
                content = yaml.full_load(csvfile)
                self.config = content.get("config", {})
                self.schema_dictionary = content.get("buttons", {})

                # Create lateral panel and buttons
                for button_name in self.schema_dictionary:
                    button_config = self.schema_dictionary[button_name]
                    button_config["height"] = self.buttons_height
                    button_config["font"] = self.buttons_font

                    if button_config.get("type") == 'button':
                        button = StepButton(button_name, **button_config)
                        #button.score_changed.connect(self.button_clicked)  # type: ignore
                    #elif button_config.get("type") == 'text':
                    #    button = TextButton(button_name, **button_config)
                    elif button_config.get("type") == 'cutter':
                        button = CutterButton(button_name, **button_config)
                        #button.score_changed.connect(self.button_clicked)
                    elif button_config.get("type") == 'multiplier':
                        button = MultiplierButton(button_name, **button_config)
                        #button.score_changed.connect(self.button_clicked)
                    elif button_config.get("type") == 'separator':
                        button = Separator(button_name, **button_config)
                    else:
                        button = None

                    if button is not None:
                        lay: QVBoxLayout = button.layout()
                        cb = QCheckBox()
                        cb.setMaximumWidth(20)
                        lay.insertWidget(0, cb)

                        # Create Item in ListWidget
                        item = QListWidgetItem()
                        self.addItem(item)
                        self.setItemWidget(item, button)
                        item.setSizeHint(button.sizeHint())



class FilterDialog(QDialog):
    filter_changed = pyqtSignal(list)

    def __init__(self, rubric, **kwargs):
        super().__init__()

        self.setWindowTitle("Filter Questions")
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.rubric = rubric

        self.filter_list = FilterListWidget(rubric, **kwargs)
        self.layout.addWidget(self.filter_list)

        # add standard OK cancel dialog buttons at the bottom

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons)
        QTimer.singleShot(10, self.adjustSize)

    def get_selection(self):
        return self.filter_list.get_selection()