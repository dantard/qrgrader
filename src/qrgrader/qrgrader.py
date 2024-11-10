#!/usr/bin/env python
import argparse
import csv
import os.path
import re
from os.path import exists

import typing
import yaml
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QRectF, QEvent
from PyQt5.QtGui import QKeySequence, QIcon, QDrag, QPixmap, QPainter, QPen, QGuiApplication, QColor
from PyQt5.QtWidgets import (QWidget, QLineEdit, QLabel, QPushButton, QApplication,
                             QVBoxLayout, QMainWindow, QFrame, QListWidget,
                             QSplitter, QSpinBox, QToolBar, QSizePolicy, QTreeWidget, QTreeWidgetItem, QAbstractItemView, QShortcut, QHeaderView,
                             QListWidgetItem, QDialog, QDialogButtonBox, QFormLayout, QComboBox, QMenu, QMessageBox, QGraphicsRectItem, QGraphicsView,
                             QGraphicsItem)

# from python.PdfWidget import PdfWidget
import qrgrader.swik.resources
from qrgrader.easyconfig.EasyConfig import EasyConfig
from qrgrader.swik.annotations.annotation import Annotation
from qrgrader.swik.swik_config import SwikConfig
from qrgrader.swik.swik_widget import SwikWidget

from qrgrader.python.support import *


# from qrgrader.swik.LayoutManager import LayoutManager


# Subclass QMainWindow to customize your application's main window
class MainWindow(QMainWindow):
    class CustomDialog(QDialog):
        def __init__(self, name=None, schema={}):
            super().__init__()


            self.setWindowTitle("Edit")

            QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel

            self.buttonBox = QDialogButtonBox(QBtn)
            self.buttonBox.accepted.connect(self.accept)
            self.buttonBox.rejected.connect(self.reject)
            self.buttonBox.buttons()[0].setEnabled(False)

            self.layout = QFormLayout()
            self.le = QLineEdit()
            self.le.textChanged.connect(lambda: self.buttonBox.buttons()[0].setEnabled(self.le.text() != ""))
            self.le.setText(name if name is not None else "")
            self.layout.addRow("Title", self.le)

            self.combo = QComboBox()
            self.combo.addItems(['button', 'text'])
            self.combo.setCurrentText(schema.get('type', 'button'))
            self.combo.currentTextChanged.connect(lambda: self.steps.setEnabled(self.combo.currentText() == "button"))
            self.layout.addRow("Type", self.combo)

            self.steps = QSpinBox()
            self.steps.setMinimum(1)
            self.steps.setMaximum(10)
            self.steps.setValue(schema.get('steps', 1))
            self.layout.addRow("Steps", self.steps)

            self.score = QLineEdit()
            self.score.setText(str(schema.get('score', 1)))
            self.layout.addRow("Score", self.score)

            # Show the current color and a color picker button
            self.color = QColor(0, 0, 0)
            self.colorButton = QPushButton('Choose color')
            self.colorButton.clicked.connect(self.pickColor)
            self.layout.addRow('Color', self.colorButton)
            self.colorButton.setStyleSheet(f'background-color: {schema.get("color", "#D4D4D4")}')

            self.position = QSpinBox()
            # self.layout.addRow("Position", self.position)
            self.layout.addWidget(self.buttonBox)
            self.setLayout(self.layout)

        def pickColor(self, button):
            color = QtWidgets.QColorDialog.getColor()
            if color.isValid():
                self.color = color
                self.colorButton.setStyleSheet(f'background-color: {color.name()}')

        def get_stylesheet(self):
            return f'background-color: {self.color.name()}'

        def get(self):
            # return self.le.text(), int(self.position.value()), {'steps': int(self.steps.value()), 'type': self.combo.currentText()}
            return self.le.text(), 1000, {'steps': int(self.steps.value()), 'type': self.combo.currentText(), 'score': float(self.score.text()), 'color': self.color.name()}



    class Text(QWidget):
        def getType(self):
            return 0

        def get_value(self):
            return self.lineedit.text()

        def get_name(self):
            return self.name

        def set_value(self, v):
            if type(v) == str:
                self.lineedit.setText(v)
            else:
                self.lineedit.setText("")

        def __init__(self, name, steps, *args, **kwargs):
            super(QWidget, self).__init__(*args, **kwargs)

            self.lineedit = QLineEdit()
            self.name = name
            layout = QtWidgets.QVBoxLayout()
            frame = QFrame()
            frame.setStyleSheet('QFrame{ border: 1px solid gray}')

            frame.setFrameStyle(QFrame.Panel)
            layout.addWidget(frame)
            layout2 = QVBoxLayout()
            frame.setLayout(layout2)
            label = QLabel(name)
            layout2.addWidget(label)
            label.setStyleSheet('border: 0px solid gray')

            layout2.addWidget(self.lineedit)
            layout.setContentsMargins(15, 5, 15, 5)
            self.setLayout(layout)

        def get_score(self):
            return 0

        def get_full_score(self):
            return 0

        def get_schema(self):
            return {'type': 'text'}

    class Score(QWidget):
        def getType(self):
            return 1

        def get_value(self):
            return self.spinner.value() if self.button.isChecked() else -1

        def get_name(self):
            return self.name

        def clicked(self):
            self.spinner.blockSignals(True)
            self.spinner.setMinimum(0)  # @alex if not self.button.isChecked() else int(self.step))
            if QGuiApplication.queryKeyboardModifiers() == Qt.ControlModifier:
                self.spinner.setValue(0)
            else:
                self.spinner.setValue(100 if self.button.isChecked() else 0)
            self.spinner.setEnabled(self.button.isChecked())
            self.spinner.blockSignals(False)
            self.internal_callback(self.click_next)

        def set_callback(self, cb):
            self.cb = cb

        def internal_callback(self, click_next):
            if self.cb is not None:
                self.cb(self, click_next)

        def set_value(self, v):
            v = v if v is not None else -1
            self.button.blockSignals(True)
            self.button.setChecked(v >= 0)
            self.button.blockSignals(False)
            self.spinner.blockSignals(True)
            self.spinner.setMinimum(0)  # @alex if not self.button.isChecked() else self.step)
            self.spinner.setValue(v if v > 0 else 0)
            self.spinner.setEnabled(self.button.isChecked())
            self.spinner.blockSignals(False)
            self.internal_callback(False)

        def __init__(self, text, schema, *args, **kwargs):
            super(QWidget, self).__init__(*args, **kwargs)
            layout = QtWidgets.QHBoxLayout()
            self.name = text
            self.button = QPushButton(text)
            self.schema = schema
            steps = self.schema.get('steps', 1) if schema is not None else 1
            self.score = self.schema.get('score', 1) if schema is not None else 1
            self.click_next = self.schema.get('click_next', False) if schema is not None else False
            # self.button.setMaximumWidth(300)
            self.button.setCheckable(True)
            # self.button.clicked.connect(self.internal_callback)
            self.step = int(100 / steps)
            self.button.clicked.connect(self.clicked)
            self.spinner = QSpinBox()
            self.spinner.setEnabled(False)
            self.spinner.lineEdit().setReadOnly(True)
            self.spinner.setMinimum(0)
            self.spinner.setSingleStep(self.step)
            self.spinner.setMaximum(100)
            self.spinner.setMaximumWidth(50)
            self.spinner.valueChanged.connect(lambda: self.internal_callback(False))
            layout.addWidget(self.button)

            if steps > 1:
                layout.addWidget(self.spinner)
            layout.setContentsMargins(15, 5, 15, 5)
            self.setLayout(layout)
            self.cb = None
            color = self.schema.get("color", None) if schema is not None else None
            if color is not None:
                self.button.setStyleSheet('background-color: {}'.format(color))

        def get_score(self):
            return self.score * self.spinner.value() / 100

        def get_full_score(self):
            return self.score

        def click(self):
            self.button.click()

        def get_click_next(self):
            return self.click_next and self.button.isChecked()

        def get_schema(self):
            return self.schema

    def change_mode(self):
        mode = self.pdfw.get_mode()
        mode = (mode + 1) % len(LayoutManager.modes)
        self.pdfw.set_mode(mode)

    #        self.layout_label.setText(LayoutManager.modes[mode])

    def set_mode_move(self):

        self.pdfw.setDragMode(QGraphicsView.ScrollHandDrag if self.mode_move.isChecked() else QGraphicsView.NoDrag)

    def set_magnifier(self):
        self.magnifier = Magnifier(self.pdfw, self.pdfw)
        self.pdfw.scene().addItem(self.magnifier)
        self.magnifier.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.timer = QTimer()
        self.timer.timeout.connect(self.magnifier.update_pose)
        self.timer.start(100)

    def __init__(self):
        super().__init__()

        #m_file = self.menuBar().addMenu("File")
        #m_file.addAction("Open Schema", self.open_schema)

        exe_name = os.path.basename(sys.argv[0])
        dir_name = os.path.basename(os.getcwd())
        self.annots = []

        x_mode = QShortcut(QKeySequence('Ctrl+M'), self)
        x_mode.activated.connect(self.change_mode)

        if re.match("qrgrading-[0-9][0-9][0-9][0-9][0-9][0-9]", dir_name) == None:
            print("ERROR: {} must be run in the root of the workspace".format(exe_name))
            sys.exit(0)

        self.exam_date = dir_name[-6:]

        self.home = os.path.expanduser('~')
        if not os.path.exists(self.home + os.sep + ".qrgrader.py"):
            os.makedirs(self.home + os.sep + ".qrgrader.py")

        try:
            f = open(self.home + os.sep + ".qrgrader.py" + os.sep + "qrgrader.py.cfg", "r")
            self.config = yaml.full_load(f)
        except:
            self.config = {}

        self.config = self.config if self.config is not None else {}

        parser = argparse.ArgumentParser(description='qrgrader.py')
        parser.add_argument('-s', '--schema', help='Schema to be used', default=None)
        parser.add_argument('-t', '--table-name', help='Output table name', default=None)
        parser.add_argument('-p', '--pdf-page', help='Open PDF on this page', default=1, type=int)
        parser.add_argument('-m', '--mode', help='horizontal or vertical', default="horizontal")
        parser.add_argument('-q', '--questions', help='Number of multiple answer questions', type=int, default=20)
        parser.add_argument('-C', '--pattern', help='Pattern of correct and incorrect answers', type=str, default=None)

        args = vars(parser.parse_args())

        self.open_pdf_page = args["pdf_page"] - 1
        self.schema = args["schema"]
        self.pattern = args["pattern"]

        if self.config.get("mode") is None:
            mode = Qt.Vertical if args["mode"].lower() == "vertical" else Qt.Horizontal
        else:
            mode = Qt.Vertical if self.config.get("mode").lower() == "vertical" else Qt.Horizontal

        table_name = args["table_name"]
        self.ma_questions = args["questions"]

        if self.schema is not None:
            if table_name is None:
                table_name = self.schema.split(".")[0]

            self.data_file = table_name + ".yaml"
            self.table_name = self.exam_date + "_" + table_name

        # Setup GUI
        config = SwikConfig()
        self.pdfw = SwikWidget(self, config)

        # self.pdfw = PdfWidget(mode, self.config.get('ratio', 1))
        # self.pdfw.set_annot_click_feedback(self.annot_click)

        self.pdf_list = QTreeWidget()
        self.pdf_list.setHeaderLabels(["", ""])
        self.pdf_list.setHeaderHidden(True)
        self.pdf_list.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.pdf_list.setColumnWidth(1, 1)
        self.pdf_list.currentItemChanged.connect(self.pdf_selection_changed)

        pdf_bar = QToolBar()

        self.auto_exam = pdf_bar.addAction("Auto Exam", lambda: self.pdf_list.collapseAll())
        self.auto_exam.setIcon(QApplication.style().standardIcon(QApplication.style().SP_ToolBarVerticalExtensionButton))
        self.auto_exam.setCheckable(True)

        self.auto_question = pdf_bar.addAction("Auto Question", lambda: self.pdf_list.expandAll())
        self.auto_question.setIcon(QApplication.style().standardIcon(QApplication.style().SP_ToolBarHorizontalExtensionButton))
        self.auto_question.setCheckable(True)

        self.auto_question = pdf_bar.addAction("Undo", lambda: self.undo_mark())
        self.auto_question.setIcon(QApplication.style().standardIcon(QApplication.style().SP_ArrowBack))

        self.questions_list = QListWidget()
        self.questions_list.currentItemChanged.connect(self.question_list_changed)
        self.remaining_lbl = QLabel("")
        self.remaining_lbl.setAlignment(Qt.AlignCenter)

        pdf_list_layout = QVBoxLayout()
        pdf_list_layout.addWidget(pdf_bar)
        pdf_list_layout.addWidget(self.remaining_lbl)

        class DraggableListWidget(QListWidget):
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
                self.schemaChanged.emit()

        self.button_list = DraggableListWidget()
        self.button_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.button_list.setDragEnabled(True)
        self.button_list.setAcceptDrops(True)
        self.button_list.setDropIndicatorShown(True)
        self.button_list.schemaChanged.connect(self.save_schema)
        self.button_list.customContextMenuRequested.connect(self.button_list_right_click)
        self.button_list.setContextMenuPolicy(Qt.CustomContextMenu)

        splitter = QSplitter()
        splitter.setOrientation(Qt.Vertical)
        splitter.addWidget(self.pdf_list)
        splitter.addWidget(self.questions_list)

        pdf_list_layout.addWidget(splitter)
        splitter.setStretchFactor(0, 10)
        splitter.setStretchFactor(1, 1)

        pdf_list_helper = QWidget()
        pdf_list_helper.setLayout(pdf_list_layout)

        self.button_layout = QVBoxLayout()

        ## Toolbar
        buttons_tb = QToolBar()
        buttons_tb.addAction("+", self.add_button).setIcon(QIcon.fromTheme("list-add"))
        buttons_tb.addSeparator()
        e = QWidget()
        e.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        buttons_tb.addWidget(e)
        self.score_label = QLabel("Score: 0")
        buttons_tb.addWidget(self.score_label)
        e = QWidget()
        e.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        buttons_tb.addWidget(e)
        buttons_tb.addSeparator()
        buttons_tb.addAction("<", self.prev).setIcon(QApplication.style().standardIcon(QApplication.style().SP_ArrowBack))
        buttons_tb.addAction(">", self.next).setIcon(QApplication.style().standardIcon(QApplication.style().SP_ArrowForward))

        self.button_layout.addWidget(buttons_tb)

        helper = QWidget()
        helper.setLayout(self.button_layout)
        self.button_layout.addWidget(self.button_list)
        self.button_list.setMinimumWidth(215)

        self.main_splitter = QSplitter()
        self.main_splitter.addWidget(pdf_list_helper)
        swik_helper = QWidget()
        swik_helper.setLayout(QVBoxLayout())
        swik_helper.layout().addWidget(self.pdfw)

        self.main_splitter.addWidget(swik_helper)
        self.main_splitter.addWidget(helper)

        self.main_splitter.setStretchFactor(0, 2)
        self.main_splitter.setStretchFactor(1, 18)
        self.main_splitter.setStretchFactor(2, 6)

        self.setCentralWidget(self.main_splitter)

        # Class Variables
        self.data = {}
        self.dir_path = r'results/publish/'
        self.xls_path = r'results/xls/'
        self.exam_id = None

        if self.schema is None:
            helper.setVisible(False)
        else:
            try:
                self.load_data()
            except:
                pass
            self.fill_buttons()

        # Init
        self.load_raw()
        self.load_generated()
        self.fill_pdf_list()
        self.check_multiple_answers()
        self.show_problematic_exams()

        self.shortcut_right = QShortcut(QKeySequence('Esc'), self)
        self.shortcut_right.activated.connect(self.next_multi)

        for i in range(10):
            self.shortcut_right = QShortcut(QKeySequence(str(i)), self)
            self.shortcut_right.activated.connect(lambda x=i, y=i: self.shortcut(y))

        if self.config.get('splitter') is not None:
            def delayed():
                self.main_splitter.setSizes(self.config.get('splitter'))

            QTimer.singleShot(100, delayed)

        if self.config.get('maximized', False):
            self.showMaximized()
        else:
            self.show()

    def keyPressEvent(self, a0: typing.Optional[QtGui.QKeyEvent]) -> None:
        super().keyPressEvent(a0)
        if a0.key() == Qt.Key_Right:
            self.next()
        elif a0.key() == Qt.Key_Left:
            self.prev()

    def mouseDoubleClickEvent(self, a0: typing.Optional[QtGui.QMouseEvent]) -> None:
        super().mouseDoubleClickEvent(a0)
        pos = self.pdfw.view.mapFrom(self, a0.pos())
        item = self.pdfw.view.itemAt(pos)
        if type(item) == QGraphicsRectItem:
            self.annot_click(item)

    def button_list_right_click(self, pos):
        menu = QMenu()
        if len(self.button_list.selectedItems()) == 0:
            menu.addAction("Add", self.add_button)
        else:
            menu.addAction("Edit", lambda: self.edit_button(self.button_list.currentRow()))
            menu.addAction("Remove", lambda: self.delete_button(self.button_list.currentRow()))

        menu.exec(self.button_list.mapToGlobal(pos))
        self.button_list.clearSelection()
        self.button_list.clearFocus()

    def closeEvent(self, event):
        self.config['splitter'] = self.main_splitter.sizes()
        self.config['ratio'] = self.pdfw.view.ratio
        self.config['maximized'] = self.isMaximized()
        try:
            f = open(self.home + os.sep + ".qrgrader.py" + os.sep + "qrgrader.py.cfg", "w")
            self.config = yaml.dump(self.config, f)
        except:
            pass
        event.accept()  # let the window close

    def shortcut(self, idx):
        if 0 <= idx - 1 < self.button_list.count():
            item = self.button_list.item(idx - 1)
            widget = self.button_list.itemWidget(item)
            widget.click()

    def delete_button(self, position):
        qm = QMessageBox()
        ret = qm.question(self, '', "Are you sure?", qm.Yes | qm.No)

        if ret == qm.Yes:
            item = self.button_list.takeItem(position)
            del item
            self.save_schema()

    def edit_button(self, position):
        item = self.button_list.item(position)
        widget = self.button_list.itemWidget(item)
        prev_name = widget.get_name()

        b2 = self.get_dialog(widget.get_name(), widget.get_schema())

        if b2 is None:
            return

        self.button_list.setItemWidget(item, b2)

        if prev_name is not None:
            for k in self.data:
                if prev_name in self.data[k].keys():
                    self.data[k][b2.get_name()] = self.data[k].pop(prev_name)

        self.save_schema()

    def get_dialog(self, name=None, schema={}):
        dialog = self.CustomDialog(name, schema)
        if not dialog.exec():
            return None

        name, pos, dic = dialog.get()


        self.schema_dic[name] = dic
        if dic.get('type', 'button') == 'button':
            b2 = self.Score(name, dic)
            b2.set_callback(self.score_callback)
        else:
            b2 = self.Text(name, dic)

        return b2

    def add_button(self):

        b2 = self.get_dialog()

        if b2 is None:
            return

        # Create Item in ListWidget
        item = QListWidgetItem()
        # item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
        self.button_list.addItem(item)

        self.button_list.setItemWidget(item, b2)
        # b2.setContentsMargins(15, 5, 15, 5)
        item.setSizeHint(b2.sizeHint())

        if isinstance(b2, self.Score):
            self.score_callback(b2)

        self.save_schema()

    def next_multi(self):
        if self.questions_list.count() > 0:
            self.questions_list.setCurrentRow(0)
        else:
            if self.auto_advance_exam():
                self.questions_list.setCurrentRow(0)
            else:
                self.next()

    def annot_click(self, a):
        print(a.name, a.pen().color() == Qt.transparent, a.orig_color == Qt.transparent, a.orig_color == Qt.red)
        if a.pen().color() == Qt.transparent:
            a.setPen(QPen(a.orig_color, 3))
        else:
            a.setPen(Qt.transparent)
        # self.pdfw.force_paint()

        exam_num, quest, answ = code_fields_from_data(a.name)
        idx = (quest - 1) * 4 + (answ - 1)
        self.raw[exam_num][idx] = 0 if a.pen() == Qt.transparent else 1
        self.check_multiple_answers()
        self.show_problematic_exams()
        self.paint_wrong_yellow()
        self.show_problematic_questions(self.exam_id)
        self.save_raw()

        self.prev_state = 1 if a.pen() == Qt.transparent else 0
        self.prev_exam_num = exam_num
        self.prev_idx = idx
        self.prev_page = self.pdfw.view.page

    def undo_mark(self):
        self.raw[self.prev_exam_num][self.prev_idx] = 1 if self.prev_state else 0
        self.check_multiple_answers()
        self.show_problematic_exams()

        if self.exam_id != self.prev_exam_num:
            self.goto_exam(self.prev_exam_num)

        self.pdfw.view.move_to_page(self.prev_page)

        self.paint_wrong_yellow()
        self.show_problematic_questions(self.exam_id)
        # self.pdfw.force_paint()
        self.save_raw()

    def load_generated(self):
        self.native = codes_read("generated" + os.sep + "qr" + os.sep + "generated.txt")

    def load_raw(self):
        if exists(self.xls_path + os.sep + self.exam_date + "_raw.fix"):
            name = self.xls_path + os.sep + self.exam_date + "_raw.fix"
            print("WARNING: Opening '.fix' file")
        else:
            name = self.xls_path + os.sep + self.exam_date + "_raw.csv"

        with open(name) as f:
            reader = csv.reader(f)
            self.raw = {}
            for row in reader:
                exam_id = int("{}{:03d}".format(row[0], int(row[1])))
                self.raw[exam_id] = [int(x) for x in row[2:]]

    class PageQuestionItem(QTreeWidgetItem):
        def __init__(self, page, quest):
            super(QTreeWidgetItem, self).__init__()
            self.page = page
            self.question = quest

    def check_multiple_answers(self):
        self.problematic_exams = {}
        for k in self.raw:
            row = self.raw[k]
            for j in range(0, len(row), 4):
                quest_number = int(j / 4) + 1
                if sum(row[j:j + 4]) > 1 and quest_number <= self.ma_questions:
                    if self.problematic_exams.get(k) is None:
                        self.problematic_exams[k] = []
                    self.problematic_exams[k].append(quest_number)

    def show_problematic_exams(self):
        for i in range(self.pdf_list.topLevelItemCount()):
            exam_id = int(self.pdf_list.topLevelItem(i).text(0))
            parent = self.pdf_list.topLevelItem(i)
            if exam_id in self.problematic_exams.keys():
                parent.setText(1, "!")
            else:
                parent.setText(1, "")

    def question_list_changed(self, new, old):
        if new is not None:
            self.pdfw.view.move_to_page(new.page)

    def goto_exam(self, exam_id):
        for i in range(self.pdf_list.topLevelItemCount()):
            if self.pdf_list.topLevelItem(i).text(0) == str(exam_id):
                self.pdf_list.setCurrentItem(self.pdf_list.topLevelItem(i))
                return

    def auto_advance_exam(self):
        self.questions_list.setVisible(False)
        if len(self.problematic_exams.keys()) > 0:
            for i in range(self.pdf_list.topLevelItemCount()):
                if self.pdf_list.topLevelItem(i).text(1) == "!":
                    self.pdf_list.setCurrentItem(self.pdf_list.topLevelItem(i))
                    return True
        return False

    def show_problematic_questions(self, exam_id):

        questions = self.problematic_exams.get(exam_id)

        self.questions_list.clear()
        self.questions_list.setVisible(questions is not None)

        if self.auto_exam.isChecked() and questions is None and QtWidgets.QApplication.keyboardModifiers() != Qt.ControlModifier:
            self.auto_advance_exam()
        elif questions is not None:
            annots = self.annots

            helper = []

            for a in annots:
                # print(a.name)
                if True or a.name.isnumeric():  # is an answer QR
                    exam, quest, answ = code_fields_from_data(a.name)
                    # print(exam, quest, answ)
                    if (quest, a.page) not in helper:
                        helper.append((quest, a.page))

            class ListItem(QListWidgetItem):
                def __init__(self, page):
                    super().__init__()
                    self.page = page

            helper2 = []

            for q in questions:
                quest_number = [h[0] for h in helper].index(q)
                page_number = helper[quest_number][1]
                helper2.append((quest_number, page_number))
                pass

            helper2.sort(key=lambda x: x[1])

            for p in helper2:
                item = ListItem(p[1])
                item.setText("Page: {}, Quest: {}".format(p[1] + 1, p[0] + 1))
                self.questions_list.addItem(item)

            if self.auto_question.isChecked() and self.questions_list.count() > 0 and QtWidgets.QApplication.keyboardModifiers() != Qt.ControlModifier:
                self.questions_list.setCurrentRow(0)

    def save_raw(self):
        with open("results/xls/{}_raw.fix".format(self.exam_date), "w") as f:
            csv_writer = csv.writer(f)
            for exam_id in self.raw:
                row = [int(exam_id / 1000), "{:03d}".format(exam_id % 1000)]
                row.extend(self.raw[exam_id])
                csv_writer.writerow(row)

    def load_data(self):
        with open(self.data_file) as file:
            self.data = yaml.full_load(file)

    def prev(self):
        index = self.pdf_list.indexOfTopLevelItem(self.pdf_list.currentItem())
        if index - 1 >= 0:
            self.pdf_list.setCurrentItem(self.pdf_list.topLevelItem(index - 1))

    def next(self):
        index = self.pdf_list.indexOfTopLevelItem(self.pdf_list.currentItem())
        if index + 1 < self.pdf_list.topLevelItemCount():
            self.pdf_list.setCurrentItem(self.pdf_list.topLevelItem(index + 1))

    def save_schema(self):
        dic = {}
        for b in self.buttons():
            dic[b.get_name()] = b.get_schema()
        with open(self.schema, "w") as f:
            yaml.dump(dic, f, sort_keys=False)

    def score_callback(self, obj: Score, click_next=False):
        points, total = 0, 0
        for b in self.buttons():
            points = points + b.get_score()
            total = total + b.get_full_score()

        self.score_label.setText("Score: {:.2f}".format(10 * points / total))

        if click_next and obj.button.isChecked():
            self.next()

    def save(self):
        with open(self.data_file, 'w') as file:
            yaml.dump(self.data, file)

        with open(self.xls_path + self.table_name + ".csv", 'w') as file:
            writer = csv.writer(file)
            header = ["Exam #"]
            header.extend([b.get_name() for b in self.buttons()])
            writer.writerow(header)

            for k in self.data:
                row = [k]

                for i in range(self.button_list.count()):
                    item = self.button_list.item(i)
                    b = self.button_list.itemWidget(item)
                    v = self.data[k].get(b.get_name())
                    if v is None:
                        v = 0 if b.getType() == 1 else " "
                    if not isinstance(v, str):
                        if v == -1:
                            v = " "
                        else:
                            v = v / 100
                            v = int(v) if v.is_integer() else v
                    if isinstance(v, str):
                        v = v if v != "" else " "
                    row.append(v)
                writer.writerow(row)

    def fill_buttons(self):

        with open(self.schema, newline='') as csvfile:
            # pointreader = csv.reader(csvfile, delimiter=',', quotechar='|')
            self.schema_dic = yaml.full_load(csvfile)

            for k in self.schema_dic:
                if self.schema_dic[k] is None or self.schema_dic[k].get('type', 'button') == 'button':
                    b2 = self.Score(k, self.schema_dic[k])
                    b2.set_callback(self.score_callback)
                else:
                    b2 = self.Text(k, self.schema_dic[k])

                # Create Item in ListWidget
                item = QListWidgetItem()
                # item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
                self.button_list.addItem(item)
                self.button_list.setItemWidget(item, b2)
                # b2.setContentsMargins(15, 5, 15, 5)
                item.setSizeHint(b2.sizeHint())

    def fill_pdf_list(self):
        # Iterate directory
        all_files = []
        for path in os.listdir(self.dir_path):
            # check if current path is a file
            if os.path.isfile(os.path.join(self.dir_path, path)):
                exam_id = path.replace(".pdf", "")
                if exam_id.isnumeric():
                    all_files.append(exam_id)

        all_files.sort()
        for f in all_files:
            item = QTreeWidgetItem()
            item.setText(0, f)
            self.pdf_list.addTopLevelItem(item)

    def buttons(self):
        buttons = []
        for i in range(self.button_list.count()):
            item = self.button_list.item(i)
            widget = self.button_list.itemWidget(item)
            buttons.append(widget)
        return buttons

    def pdf_selection_changed(self, new, old):
        if old is not None:
            id_old = int(old.text(0))
            self.data[id_old] = {}
            for b in self.buttons():
                self.data[id_old][b.get_name()] = b.get_value()

        if new is not None:
            def do():
                self.pdfw.open_file(self.dir_path + new.text(0) + ".pdf")
                # self.pdfw.move_to_page(0)
                self.annots.clear()
                self.pdfw.view.move_to_page(self.open_pdf_page)
                self.exam_id = int(new.text(0))

                if self.data.get(self.exam_id) is not None:
                    for b in self.buttons():
                        value = self.data[self.exam_id].get(b.get_name())
                        b.set_value(value)
                else:
                    for b in self.buttons():
                        b.set_value(-1)

                for i in range(self.pdfw.renderer.get_num_of_pages()):
                    # annots = self.pdfw.renderer.get_annotations_fitz(i)
                    page = self.pdfw.view.pages[i]
                    annots = page.items(Annotation)

                    for annot in annots:
                        annot.setVisible(False)
                        # x, y = annot.rect[0], annot.rect[1]
                        # rect = QRectF(0, 0, annot.rect[2] - annot.rect[0], annot.rect[3] - annot.rect[1])

                        square = QGraphicsRectItem(annot.rect(), page)
                        square.setPos(annot.pos())
                        square.name = annot.name
                        exam_num, quest, answ = code_fields_from_data(square.name)
                        square.page = i

                        # Mark red if incorrect, green if correct
                        if self.pattern is None:
                            if answ == 1:
                                color = Qt.green
                            else:
                                color = Qt.red
                        else:
                            if answ == ord(self.pattern[quest - 1].lower()) - 96:
                                color = Qt.green
                            else:
                                color = Qt.red

                        # Compute the index on the raw table
                        square.idx = (quest - 1) * 4 + (answ - 1)
                        square.orig_color = color
                        square.setPen(square.orig_color)
                        self.annots.append(square)

                self.paint_wrong_yellow()
                self.show_problematic_questions(self.exam_id)

                if self.schema is not None:
                    self.redify_not_graded()
                    self.save()

            QTimer.singleShot(100, do)

    def eventFilter(self, a0: typing.Optional['QObject'], a1: typing.Optional['QEvent']) -> bool:
        # if a1.type() == QEvent.KeyPress:
        #     if a1.key() == Qt.Key_Right:
        #         self.next()
        #         return True
        #     elif a1.key() == Qt.Key_Left:
        #         self.prev()
        #         return True
        return False

    def redify_not_graded(self):
        num_done = 0
        for i in range(self.pdf_list.topLevelItemCount()):
            id = int(self.pdf_list.topLevelItem(i).text(0))
            if self.data.get(id) is not None:
                done = False
                for b in self.buttons():
                    v = self.data[id].get(b.get_name())
                    v = v if v is not None else 0
                    done = done or (type(v) == str and v != "") or (type(v) != str and v > 0)
                if done:
                    self.pdf_list.topLevelItem(i).setForeground(0, Qt.black)
                    num_done += 1
                else:
                    self.pdf_list.topLevelItem(i).setForeground(0, Qt.red)
            else:
                self.pdf_list.topLevelItem(i).setForeground(0, Qt.red)
        self.remaining_lbl.setText(f"{num_done}/{self.pdf_list.topLevelItemCount()} ({num_done / self.pdf_list.topLevelItemCount() * 100:.2f}%)")

    def paint_wrong_yellow(self):
        answers = self.raw.get(self.exam_id)
        if answers is not None:

            for a in self.annots:
                exam_num, quest, answ = code_fields_from_data(a.name)

                idx = a.idx
                color = a.orig_color

                # Set Transparent if not marked
                if idx < len(answers):
                    if answers[idx] != 1:
                        color = Qt.transparent
                    else:

                        # Check if this is problematic exam
                        if exam_num in self.problematic_exams.keys():
                            # In that case, paint the square yellow
                            for v in self.problematic_exams.get(exam_num):
                                if quest == v:
                                    color = Qt.yellow

                    a.setPen(QPen(color, 3))


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    app.installEventFilter(window)
    app.exec()


if __name__ == '__main__':
    main()
