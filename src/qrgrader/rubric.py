#!/usr/bin/env python
import csv
import os

import yaml
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QDrag, QPixmap, QPainter
from PyQt5.QtWidgets import (QListWidget,
                             QAbstractItemView, QListWidgetItem, QMenu, QMessageBox,
                             QInputDialog, QColorDialog)

from qrgrader.dialogs import ButtonEditDialog, RubricEditDialog
from qrgrader.buttons import StepButton, Shortcut, Button, TextButton, StateButton, Separator, CutterButton, MultiplierButton


class Rubric(QListWidget):
    score_changed = pyqtSignal(object, int)
    goto_next = pyqtSignal()

    def __init__(self, schema_filename, dir_xls, **kwargs):
        super().__init__()

        self.exam_id = None
        self.config = {}
        self.scores = {}
        self.schema_dictionary = {}
        self.schema_filename = schema_filename
        name = self.schema_filename.split(".")[0]
        self.scores_filename = name + ".yaml"
        self.xls_filename = dir_xls + name + ".csv"
        self.current_exam_id = None
        self.modified = False
        self.buttons_height = kwargs.get("buttons_height")
        self.buttons_font = kwargs.get("buttons_font")

        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setMinimumWidth(115)

        # self.schemaChanged.connect(self.save_schema) # type: ignore
        self.customContextMenuRequested.connect(self.button_list_right_click)
        self.populate()
        self.load_scores()

    def load_scores(self):
        if os.path.exists(self.scores_filename):
            with open(self.scores_filename) as file:
                self.scores = yaml.safe_load(file)

    def push(self, exam_id):
        if exam_id is not None:
            if self.store(exam_id):
                self.save_scores()

    def pull(self, exam_id):
        self.exam_id = exam_id
        self.retrieve(self.exam_id)

    # def exam_changed(self, exam_id, prev_exam_id):
    #     self.exam_id = exam_id
    #     if prev_exam_id is not None:
    #         self.store(prev_exam_id)
    #     self.save_scores()
    #
    #     self.retrieve(self.exam_id)

    def get_page(self):
        return self.config.get("page", 1) - 1

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Down:
            self.goto_next.emit()
        else:
            super().keyPressEvent(e)

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
                        button.score_changed.connect(self.button_clicked)  # type: ignore
                    elif button_config.get("type") == 'text':
                        button = TextButton(button_name, **button_config)
                    elif button_config.get("type") == 'cutter':
                        button = CutterButton(button_name, **button_config)
                        button.score_changed.connect(self.button_clicked)
                    elif button_config.get("type") == 'multiplier':
                        button = MultiplierButton(button_name, **button_config)
                        button.score_changed.connect(self.button_clicked)
                    elif button_config.get("type") == 'shortcut':
                        button = Shortcut(button_name, **button_config)
                        button.clicked.connect(self.shortcut_activated)
                    elif button_config.get("type") == 'separator':
                        button = Separator(button_name, **button_config)
                    else:
                        button = None

                    if button is not None:
                        # Create Item in ListWidget
                        item = QListWidgetItem()
                        self.addItem(item)
                        self.setItemWidget(item, button)
                        item.setSizeHint(button.sizeHint())

    def save_schema(self):
        buttons = {}
        for b in self.filter_buttons(Button):
            buttons[b.get_name()] = b.get_config()

        self.schema_dictionary = buttons

        with open(self.schema_filename, "w", encoding='utf-8') as f:
            schema = {"buttons": buttons, "config": self.config}
            yaml.dump(schema, f, sort_keys=False)

    def button_clicked(self):
        self.store(self.exam_id)
        self.score_changed.emit(self, self.exam_id)
        button = self.sender()
        if button.get_click_next() and button.is_checked():
            QTimer.singleShot(500, self.goto_next.emit)

    def add_button(self):

        button = self.get_dialog()

        if button is None:
            return

        # Create Item in ListWidget
        item = QListWidgetItem()
        self.addItem(item)

        self.setItemWidget(item, button)
        item.setSizeHint(button.sizeHint())
        self.save_schema()

    def get_dialog(self, button=None):

        dialog = ButtonEditDialog(self, button)

        if not dialog.exec():
            return None

        name, kind, config = dialog.get()

        self.schema_dictionary[name] = config

        if kind == 'button':
            button = StepButton(name, **config)
            button.score_changed.connect(self.button_clicked)
        elif kind == 'text':
            button = TextButton(name, **config)
        elif kind == 'cutter':
            button = CutterButton(name, **config)
            button.score_changed.connect(self.button_clicked)
        elif kind == 'multiplier':
            button = MultiplierButton(name, **config)
            button.score_changed.connect(self.button_clicked)
        elif kind == 'separator':
            button = Separator(name, **config)
        else:
            button = None

        return button

    def edit_button(self, position):
        item = self.item(position)
        widget = self.itemWidget(item)
        prev_name = widget.get_name()

        button = self.get_dialog(widget)

        if button is None:
            return

        self.setItemWidget(item, button)

        # Rename the key in the dictionary
        if prev_name is not None:
            for exam_id in self.scores:
                if prev_name in self.scores[exam_id].keys():
                    self.scores[exam_id][button.get_name()] = self.scores[exam_id].pop(prev_name)

        self.save_schema()

    def button_list_right_click(self, pos):
        menu = QMenu()
        item = self.item(self.currentRow())
        widget = self.itemWidget(item)

        if isinstance(widget, StateButton):
            menu.addAction("Edit", lambda: self.edit_button(self.currentRow()))
            menu.addAction("Duplicate", lambda: self.duplicate_button(self.currentRow()))
            menu.addAction("Remove", lambda: self.delete_button(self.currentRow()))
            menu.addAction("Add Comment", lambda: self.add_comment(self.currentRow()))
            menu.addSeparator()
        elif isinstance(widget, Shortcut):
            menu.addAction("Remove", lambda: self.remove_shortcut(self.currentRow()))
            menu.addAction("Change Color", lambda: self.set_shortcut_color(self.currentRow()))
            menu.addSeparator()
        menu.addAction("Edit Rubric Config", self.edit_rubric_config)
        menu.addAction("Add Button", self.add_button)
        menu.addAction("Add Shortcut", self.add_shortcut)

        menu.exec(self.mapToGlobal(pos))
        self.clearSelection()
        self.clearFocus()

    def compute_score(self, exam_id):
        this_exam_data = self.scores.get(int(exam_id), {})

        total = 0
        points = 0
        for button in self.filter_buttons(StepButton):
            this_button_data = this_exam_data.get(button.get_name(), {})
            value = this_button_data.get("value", 0)
            if value >= 0:
                value = value * button.get_full_value() / 100.0
                points = points + value

            total = total + button.get_full_value() * button.get_weight()

        cut = 1
        for button in self.filter_buttons(CutterButton):
            cut = min(cut, button.get_percent())

        points = min(points, total * cut)

        multiplier = 1
        for button in self.filter_buttons(MultiplierButton):
            multiplier = button.get_percent()

        points = points * multiplier

        return points

    def save_scores(self):
        with open(self.scores_filename, "w", encoding='utf-8') as file:
            yaml.dump(self.scores, file)

        self.save_xls()

    def save_xls(self):

        with open(self.xls_filename, "w", encoding='utf-8') as f:
            row = "EXAM_ID"
            for button_name, _ in self.schema_dictionary.items():
                row += "\t" + button_name

            f.write(row + "\n")

            row = " "
            for button_name, button_config in self.schema_dictionary.items():
                if button_config.get("type") == 'button':
                    row += "\t" + "{:.2f}".format(button_config.get("full_value", 1))
                elif button_config.get("type") == 'text':
                    row += "\t "
                else:
                    row += "\t?"

            f.write(row + "\n")

            for exam_id, exam_score_items in self.scores.items():
                row = str(exam_id)
                for button_name, button_config in self.schema_dictionary.items():

                    button_type = button_config.get("type")
                    button_state = exam_score_items.get(button_name)  # value and comment or text

                    if button_state is not None:
                        if button_type == 'button':
                            value = button_state.get("value")
                            value = " " if value == -1 else round(value / 100, 2)
                        elif button_type == 'text':
                            value = button_state.get("text")
                        else:
                            value = "?"
                    else:
                        value = " "

                    row += "\t {:4s}".format(str(value))

                f.write(row + "\n")

    def shortcut_activated(self):
        buttons = self.sender().get_buttons()

        for b in self.filter_buttons(StepButton):  # type: StepButton
            b.button.setChecked(b.get_name() in buttons)
            b.clicked()

    def add_shortcut(self):
        text, ok = QInputDialog.getText(self, "Shortcut", "Name:")
        if ok:

            buttons = []
            for b in self.filter_buttons(StepButton):  # type: StepButton
                if b.button.isChecked():
                    buttons.append(b.get_name())

            b2 = Shortcut(text, buttons=buttons)
            b2.clicked.connect(self.shortcut_activated)  # type: ignore

            item = QListWidgetItem()
            self.addItem(item)
            self.setItemWidget(item, b2)
            item.setSizeHint(b2.sizeHint())
            item.setFlags(item.flags() & ~Qt.ItemIsDragEnabled)
            self.save_schema()

    #
    def delete_button(self, position):
        ret = QMessageBox().question(self, '', "Are you sure?", QMessageBox.Yes | QMessageBox.No)

        if ret == QMessageBox.Yes:
            item = self.takeItem(position)
            del item
            self.save_schema()
            self.score_changed.emit(self, self.exam_id)

    def add_comment(self, position):
        # help me get text comment with dialog
        item = self.item(position)
        widget = self.itemWidget(item)
        text, ok = QInputDialog.getText(self, 'Add Comment', 'Comment:', text=widget.get_comment())
        if ok:
            item = self.item(position)
            widget = self.itemWidget(item)
            widget.setToolTip(text)
            widget.set_comment(text)

    def duplicate_button(self, position):

        # button = self.get_dialog()
        #
        # if button is None:
        #     return
        #
        # # Create Item in ListWidget
        # item = QListWidgetItem()
        # self.addItem(item)
        #
        # self.setItemWidget(item, button)
        # item.setSizeHint(button.sizeHint())
        # self.save_schema()

        item = self.item(position)
        widget = self.itemWidget(item)
        name, valid = QInputDialog.getText(self, 'Duplicate', 'Name:', text=widget.get_name() + "_copy")
        if valid:
            button = widget.__class__(name, **widget.get_config().copy())
            button.score_changed.connect(self.button_clicked)
            item = QListWidgetItem()
            self.addItem(item)
            self.setItemWidget(item, button)
            item.setSizeHint(button.sizeHint())
            self.save_schema()

    def edit_rubric_config(self):
        dialog = RubricEditDialog(self.config)
        if dialog.exec():
            self.save_schema()

    def set_shortcut_color(self, position):
        item = self.item(position)
        widget = self.itemWidget(item)
        color = QColorDialog.getColor()
        if color.isValid():
            widget.set_color(color.name())
            self.save_schema()

    def remove_shortcut(self, position):
        self.takeItem(position)
        self.save_schema()

    # def is_done(self, exam_id):
    #     done = False
    #     grades_for_this_exam = self.rubric_grades_data.get(exam_id)
    #     if grades_for_this_exam is None:
    #         return False
    #
    #     for b in self.buttons(StepButton):  # type: Score
    #         this_button = grades_for_this_exam.get(b.get_name(), {})
    #         value = this_button.get("value", -1)
    #         done = done or value != -1
    #     for b in self.buttons(Text):
    #         this_button = grades_for_this_exam.get(b.get_name(), {})
    #         value = this_button.get("text", "")
    #         done = done or value != ""
    #
    #     return done
    #
    def store(self, exam_id):
        assessed = False

        # Remove previous scores for this exam_if in case
        # the exam_id has been "uncorrected"
        self.scores.pop(exam_id, None)
        for b in self.filter_buttons(StateButton):  # type: Score
            state = b.get_state()
            # Only store if a button has been pressed or there is some text
            if state.get("value", -1) != -1 or state.get("text", "") != "":
                if self.scores.get(exam_id) is None:
                    self.scores[exam_id] = {}
                self.scores[exam_id][b.get_name()] = state
                assessed = True
        return assessed

    def assessed(self, exam_id):
        return self.scores.get(exam_id) is not None



    def retrieve(self, exam_id):
        self.current_exam_id = exam_id
        rubric_data = self.scores.get(exam_id, {})

        if rubric_data is not None:
            for button in self.filter_buttons(StateButton):  # type: Score
                button.blockSignals(True)
                button.set_state(rubric_data.get(button.get_name(), {}))
                button.blockSignals(False)

    def startDrag(self, ev):
        selected = self.selectedIndexes()[0].row()
        item = self.item(selected)
        widget = self.itemWidget(item)
        qd = QDrag(self)
        qd.setMimeData(self.model().mimeData(self.selectedIndexes()))
        pm = QPixmap(400, 20)
        pm.fill(Qt.transparent)
        qp = QPainter(pm)
        qp.drawText(10, 15, widget.get_name())
        qd.setPixmap(pm)
        qd.exec(ev, Qt.MoveAction)
        del qp

    schemaChanged = pyqtSignal()

    def dropEvent(self, event):
        super().dropEvent(event)
        self.schemaChanged.emit()  # type: ignore

    def filter_buttons(self, kind=StepButton):
        buttons = []
        for i in range(self.count()):
            item = self.item(i)
            widget = self.itemWidget(item)
            if isinstance(widget, kind):
                buttons.append(widget)
        return buttons
