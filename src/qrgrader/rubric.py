#!/usr/bin/env python
import csv
import os

import gspread.utils
import pandas
import yaml
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QSize, QEvent
from PyQt5.QtGui import QDrag, QPixmap, QPainter
from PyQt5.QtWidgets import (QListWidget,
                             QAbstractItemView, QListWidgetItem, QMenu, QMessageBox,
                             QInputDialog, QColorDialog, QPushButton, QWidget, QVBoxLayout, QFrame, QProgressDialog,
                             QApplication)
from gspread.utils import a1_to_rowcol, rowcol_to_a1

from qrgrader.common import get_date, get_workspace_path

from qrgrader.dialogs import ButtonEditDialog, RubricEditDialog
from qrgrader.buttons import StepButton, Shortcut, Button, TextButton, StateButton, Separator, CutterButton, MultiplierButton
from qrgrader.filter_dialog import FilterDialog

from qrgrader.gdrive import Sheets
from qrgrader.utils import run_with_progress, get_pd


class Rubric(QListWidget):
    score_changed = pyqtSignal(object, int)
    goto_next = pyqtSignal()
    button_or_value_changed = pyqtSignal()
    filtered = pyqtSignal()

    def __init__(self, name, dir_xls, **kwargs):
        super().__init__()

        self.pd = None
        self.filters = None
        self.exam_id = None
        self.config = kwargs.get("config")
        self.name = name

        self.table_filename = dir_xls + get_date() + "_" + self.name + ".csv"
        self.current_exam_id = None
        self.modified = False

        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setMinimumWidth(115)

        self.schemaChanged.connect(self.schema_changed) # type: ignore
        self.customContextMenuRequested.connect(self.button_list_right_click)

        self.filter_btn = QPushButton("Apply Filter")
        #self.filter_btn.setFlat(True)
        self.filter_btn.setCheckable(True)
        self.filter_btn.setStyleSheet("background-color: #F0A0A0")
        self.filter_btn.clicked.connect(self.toggle_filter)

        self.upload_btn = QPushButton("Upload")
        self.upload_btn.setStyleSheet("background-color: #00A0A0")
        self.upload_btn.clicked.connect(self.upload_xls)
        print("jjj")
        #self.populate()
        self.load_table()

    def get_filter_button(self):
        return self.filter_btn

    def get_upload_button(self):
        return self.upload_btn

    def flush(self):
        exams = []
        schema = {}
        for button in self.filter_buttons(None): # type: Button
            exams.extend(button.data.keys())
            schema[button.get_name()] = {"type": button.get_type()}
            if button.get_type() == "button":
                schema[button.get_name()].update({
                                         "color": button.get_color(),
                                         "weight": button.get_weight(),
                                         "steps": button.get_steps(),
                                         "full": button.get_full_value(),
                                         "click": int(button.get_click_next())})
        exams = list(set(exams))
        scores = {}
        for exam in exams:
            if exam not in scores:
                scores[exam] = {}
            for button in self.filter_buttons(None): # type: Button
                data = button.data.get(exam)
                scores[exam].update({button.get_name(): data})

        print(schema)

    # A bit messy should use a worker thread but it works
    # and I don't want to add more complexity right now
    def upload_xls(self):
        folder = get_workspace_path("config")
        with open(folder + os.sep + "config.yaml", "r", encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if config.get("workbook") in [None, "none"]:
                QMessageBox().critical(self, "Error", "No workbook specified in config.yaml")
                return

        sheet_name = str(os.path.basename(self.table_filename).replace(".csv", ""))
        sheet = Sheets(config_dir=folder, yes=True)

        self.pd = get_pd("Checking...", self)
        def check():
            sheet.open(config.get("workbook"))
            self.pd.close()

            if sheet.worksheet_exists(sheet_name):
                ret = QMessageBox().question(self, '', f"A sheet named '{sheet_name}' already exists in the workbook\nDo you want to overwrite it?", QMessageBox.Yes | QMessageBox.No)
                if ret != QMessageBox.Yes:
                    return

            run_with_progress(self, "Uploading " + sheet_name + " to Google Sheets...", lambda: sheet.upload(self.table_filename, sheet_name))

        QTimer.singleShot(100, check)


    def toggle_filter(self):
        if not self.filter_btn.isChecked():
            self.filters = None
            self.filtered.emit()
        else:
            filter_dialog = FilterDialog(self)
            if filter_dialog.exec() == QInputDialog.Accepted:
                self.set_filter(filter_dialog.get_selection())
                self.filtered.emit()
            else:
                self.filter_btn.setChecked(False)
                self.filters = None
                self.filtered.emit()


    def set_filter(self, filters):
        self.filters = filters
        self.filtered.emit()

    def comply_with_filter(self, exam_id):
        if self.filters is None:
            return True

        exam_scores = self.scores.get(exam_id, {})

        ok = True
        for k, v in self.filters.items():
            button_score = exam_scores.get(k, {})
            ok = ok and button_score.get("value", -1) == v.get("value")
        return ok

    def load_table(self):

        NUM_OF_HEADER_ROWS = 6

        if os.path.exists(self.table_filename):
            table = pandas.read_csv(self.table_filename, sep="\t", header=0, index_col=0)
            table = table.fillna("")

            for name in table.columns:
                kind = table.loc["type", name]
                color = table.loc["color", name]
                steps = table.loc["steps", name]
                click_next = table.loc["click", name]
                weight = table.loc["weight", name]
                full = table.loc["full", name]
                if kind == 'button':
                    button = StepButton(name,
                                        weight=float(weight),
                                        full_value=float(full),
                                        steps=int(steps),
                                        color=color,
                                        click_next=int(click_next))
                    button.score_changed.connect(self.button_clicked)
                elif kind == 'text':
                    button = TextButton(name)
                elif kind == 'cutter':
                    button = CutterButton(name, percent=float(full),  color=color)
                    button.score_changed.connect(self.button_clicked)
                elif kind == 'multiplier':
                    button = MultiplierButton(name,percent=float(full),  color=color)
                    button.score_changed.connect(self.button_clicked)
                elif kind == 'separator':
                    button = Separator(name)
                elif kind == 'shortcut':
                    buttons = table.loc["full", name]
                    button = Shortcut(name, buttons=buttons.split(";"), color=color)
                    button.clicked.connect(self.shortcut_activated)  # type: ignore
                else:
                    button = None

                if button is not None:
                    item = QListWidgetItem()
                    self.addItem(item)
                    self.setItemWidget(item, button)
                    item.setSizeHint(button.sizeHint())

                    for exam_id in table.index[NUM_OF_HEADER_ROWS:]:
                        value = table.loc[exam_id, name] or ""
                        if button.get_type() in ["button", "cutter", "multiplier"]:
                            value = -1 if value == "" else float(value)*100
                        if button.get_type() in ["button", "cutter", "multiplier", "text"]:
                            button.insert(int(exam_id), value)


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

    def schema_changed(self):
        self.save_xls()

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

        self.schema_changed()
        self.button_or_value_changed.emit()

    def get_dialog(self, button=None):
        dialog = ButtonEditDialog(self, button, [button.get_name() for button in self.filter_buttons(None)])

        if not dialog.exec():
            return None

        name, kind, config = dialog.get()

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
        self.schema_changed()
        self.button_or_value_changed.emit()

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


    def save_xls(self):
        df = pandas.DataFrame()
        for button in self.filter_buttons(None):
            df[button.get_name()] = pandas.NA
            df.loc['type', button.get_name()] = button.get_type()
            df.loc['color', button.get_name()] = ""
            df.loc['steps', button.get_name()] = ""
            df.loc['click', button.get_name()] = ""
            df.loc['weight', button.get_name()] = ""
            df.loc['full', button.get_name()] = ""


            if button.get_type() in ["button","cutter","multiplier", "shortcut"]:
                df.loc['color', button.get_name()] = button.get_color()

            if button.get_type() == "button":
                df.loc['weight', button.get_name()] = f"{button.get_weight():g}"
                df.loc['steps', button.get_name()] = button.get_steps()
                df.loc['full', button.get_name()] = f"{button.get_full_value():g}"
                df.loc['click', button.get_name()] = int(button.get_click_next())

            if button.get_type() in ["cutter","multiplier"]:
                df.loc['full', button.get_name()] = f"{button.get_percent():g}"

            if button.get_type() == "shortcut":
                df.loc['full', button.get_name()] = ";".join(button.get_buttons())

            for exam_id in button.data:
                value = button.query(exam_id)
                if button.get_type() in ["button", "cutter", "multiplier"]:
                    df.loc[exam_id, button.get_name()] = f"{value/100:g}" if value > 0 else ""
                elif button.get_type() == "separator":
                    pass
                else:
                    df.loc[exam_id, button.get_name()] = str(value)

        df.insert(0, "Score", "")
        df.fillna("", inplace=True)

        full = next(i for i, x in enumerate(df.index) if x == "full") + 2
        weight = next(i for i, x in enumerate(df.index) if x == "weight") + 2

        button_col_idx = df.columns.get_indexer(df.columns[df.loc["type"] == "button"])
        multiplier_col_idx = df.columns.get_indexer(df.columns[df.loc["type"] == "multiplier"])
        cutter_col_idx = df.columns.get_indexer(df.columns[df.loc["type"] == "cutter"])

        denominator = "/sumif({0"
        for col in button_col_idx:
            denominator += "," + rowcol_to_a1(weight, int(col) + 2) +"*" + rowcol_to_a1(full, int(col) + 2)
        denominator += '}, ">0")'

        for row, exam_id in enumerate(df.index.tolist()):
            if str(exam_id).isdigit():
                numer = "(0"
                for col in button_col_idx:
                    numer += "+" + rowcol_to_a1(row + 2, int(col) + 2) + "*" + rowcol_to_a1(full, int(col) + 2)
                numer += ")"
                multiplier = ""
                for col in multiplier_col_idx:
                    multiplier += "*if(" + rowcol_to_a1(row + 2, int(col) + 2) + ">0," + rowcol_to_a1(full, int(col) + 2) + ",1)"

                formula = numer + denominator + multiplier
                for col in cutter_col_idx:
                    cell = rowcol_to_a1(row + 2, int(col) + 2)
                    limit = rowcol_to_a1(full, int(col) + 2)
                    formula = f"LET(x,{formula},IF({cell}>0,MIN(x,{limit}),x))"


                df.loc[exam_id, "Score"] = "=" + formula



        df.to_csv(self.table_filename, sep="\t", index=True)

        self.flush()

    def compute_score(self, exam_id):
        total = 0
        points = 0
        text = "="

        for button in self.filter_buttons(StepButton):
            value = button.query(exam_id)
            value = 0 if value == -1 else float(value)
            if value >= 0:
                value = value * button.get_full_value() / 100.0
                text = text + 'N("' + button.get_name() + '")+' + str(value) + ' + '
                points = points + value

            total = total + button.get_full_value() * button.get_weight()
        text += "0"

        cut = 1
        for button in self.filter_buttons(CutterButton):
            cut = min(cut, button.get_percent())

        if cut < 1:
            points = min(points, total * cut)

        multiplier = 1
        for button in self.filter_buttons(MultiplierButton):
            multiplier = button.get_percent()

        points = points * multiplier
        if total > 0:
            points = points / total * self.config.get("weight", 10)
        points = round(points, self.config.get("precision", 2))
        return points, self.config.get("weight", 10)

    def lock(self, value):
        self.setAttribute(Qt.WA_TransparentForMouseEvents, value)

    def save_scores(self):
        # with open(self.table_filename, "w", encoding='utf-8') as f:
        #     self.table.to_csv(f, sep="\t", index=True)
        # print("Saved scores to", self.table_filename)
        return

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
            self.schema_changed()

    #
    def delete_button(self, position):
        ret = QMessageBox().question(self, '', "Are you sure?", QMessageBox.Yes | QMessageBox.No)

        if ret == QMessageBox.Yes:
            item = self.takeItem(position)
            del item
            self.schema_changed()
            self.button_or_value_changed.emit()

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
            button = widget.__class__(name)#, **widget.get_config().copy())
            button.score_changed.connect(self.button_clicked)
            item = QListWidgetItem()
            self.addItem(item)
            self.setItemWidget(item, button)
            item.setSizeHint(button.sizeHint())
            self.schema_changed()

    def edit_rubric_config(self):
        dialog = RubricEditDialog(self.config)
        if dialog.exec():
            self.schema_changed()
            self.button_or_value_changed.emit()

    def set_shortcut_color(self, position):
        item = self.item(position)
        widget = self.itemWidget(item)
        color = QColorDialog.getColor()
        if color.isValid():
            widget.set_color(color.name())
            self.schema_changed()

    def remove_shortcut(self, position):
        self.takeItem(position)
        self.schema_changed()

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
        for button in self.filter_buttons(StateButton):  # type: Score
            print("rrr", button.get_name())
            assessed = button.store(exam_id) > 0 or assessed

        self.save_xls()
        return assessed


    def assessed(self, exam_id):
        assessed = False
        for button in self.filter_buttons(StepButton):  # type: Score
            assessed = button.query(exam_id) > 0 or assessed
        for button in self.filter_buttons(TextButton):  # type: Score
            assessed = len(button.query(exam_id)) > 0 or assessed
        return assessed

    def retrieve(self, exam_id):
        self.current_exam_id = exam_id
        for button in self.filter_buttons(StateButton):
            button.blockSignals(True)
            button.retrieve(exam_id)
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
            if kind is None or isinstance(widget, kind):
                buttons.append(widget)
        return buttons


