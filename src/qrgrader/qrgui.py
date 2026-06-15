import argparse
import os
import sys
import signal

from random import shuffle
import pyqtgraph as pg
import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QCheckBox

from PyQt5.QtCore import Qt, QObject, pyqtSignal, QTimer
from PyQt5.QtGui import QPen, QKeySequence, QColor, QPalette
from PyQt5.QtWidgets import QApplication, QInputDialog, QShortcut, QProgressDialog, QMessageBox, QPushButton, QMenu, \
    QComboBox
from PyQt5.QtWidgets import QMainWindow, QHBoxLayout, QWidget, QTreeWidgetItem, QSplitter, QGraphicsRectItem, \
    QTabWidget, QLabel, QVBoxLayout, \
    QSizePolicy, QFormLayout, QCheckBox, QGroupBox
from easyconfig2.easyconfig import EasyConfig2
from swikv4.pages.swik_page import SwikPage

from qrgrader.dialogs import ControlDialog, NameListDialog
from swikv4.widgets.swik_basic_widget import SwikBasicWidget

from qrgrader.filter_dialog import FilterDialog
from qrgrader.utils import makedir, SortedSet
from qrgrader.code import Code
from qrgrader.code_set import CodeSet
from qrgrader.common import check_workspace, get_workspace_paths, Questions, StudentsData, get_prefix, Nia
from qrgrader.pdf_tree import PDFTree, NumericTreeWidgetItem
from qrgrader.rubric import Rubric


class Mark(QGraphicsRectItem):
    class Signal(QObject):
        double_click = pyqtSignal(object)

    def __init__(self, code):
        super().__init__()
        self.signal = Mark.Signal()
        self.code = code
        self.setRect(code.x, code.y, code.w, code.h)
        if code.marked:
            self.setPen(QPen(Qt.red, 2))
        else:
            self.setPen(QPen(Qt.transparent, 2))

    def mouseDoubleClickEvent(self, event):
        self.signal.double_click.emit(self.code)


class EditableLabel(QLabel):
    new_value = pyqtSignal(int)

    def __init__(self):
        super().__init__()

    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        a, b = QInputDialog.getInt(self, "Edit Value", "Enter new value:",
                                   int(self.text().replace("X", "0").replace("Y", "0")))
        if b:
            self.setText(str(a))
            self.new_value.emit(a)


class DoubleClickableLabel(QLabel):
    double_click = pyqtSignal()

    def __init__(self):
        super().__init__()

    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        self.double_click.emit()

class EnhancedLabel(QLabel):

    def set(self, color=Qt.black, bold=False):
        palette = self.palette()
        palette.setColor(QPalette.WindowText, color)
        self.setPalette(palette)
        font = self.font()
        font.setBold(bold)
        self.setFont(font)

class MainWindow(QMainWindow):
    def __init__(self, schema_filenames, args):
        super().__init__()
        makedir(os.path.expanduser("~") + os.sep + ".config/qrgrader/")

        self.randomize = args["random"]
        self.locked = args["lock"]
        self.config = EasyConfig2(filename=os.path.expanduser("~") + os.sep + ".config/qrgrader/qrgrader.yaml")
        self.cfg_geometry = self.config.root().addPrivate("geometry", default=[0, 0, 1200, 1000, False])
        self.cfg_buttons_height = self.config.root().addPrivate("buttons_height")
        self.cfg_buttons_font = self.config.root().addPrivate("buttons_font")
        self.config.load()

        self.multiple_marked_exams = SortedSet()
        self.auto_avance = False
        self.current_exam = None
        self.detected = CodeSet()
        self.type_a = None
        self.type_n: CodeSet = None
        self.changed = CodeSet()

        self.file_menu = self.menuBar().addMenu("File")
        self.file_menu.addAction("Export", self.export_data)
        self.file_menu.addAction("Graphs", self.show_graphs)

        # Rubrics
        self.rubrics = []
        self.rubrics_files = schema_filenames
        self.rubrics_labels = []
        self.rubrics_cb = []

        (self.dir_workspace,
         self.dir_data,
         self.dir_scanned, _,
         self.dir_xls,
         self.dir_publish, _) = get_workspace_paths(os.getcwd())

        self.prefix = get_prefix()
        self.xls_questions = Questions(self.dir_xls + self.prefix + "questions.csv")
        self.xls_data = StudentsData(self.dir_xls + self.prefix + "data.csv")
        self.xls_nia = Nia(self.type_n)

        self.central_widget = QWidget()
        self.main_layout = QVBoxLayout()
        self.central_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.central_widget)
        self.pdf_tree = PDFTree()
        self.pdf_tree.setColumnCount(4)
        self.swik = SwikBasicWidget()
        self.swik.view.document_ready.connect(self.load_finished)
        self.splitter = QSplitter()

        # Prepare Details layout
        self.name_lbl = DoubleClickableLabel()
        self.name_lbl.setMinimumWidth(300)
        self.name_lbl.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.name_lbl.double_click.connect(self.name_double_clicked)


        self.nia_lbl = EditableLabel()
        self.nia_lbl.new_value.connect(self.nia_changed)
        self.nia_lbl.setMinimumWidth(100)
        self.nia_lbl.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        self.group_lbl = QLabel()
        self.group_lbl.setMinimumWidth(100)
        self.group_lbl.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        self.exam_id_lbl = EnhancedLabel()
        self.exam_id_lbl.setMinimumWidth(100)
        self.exam_id_lbl.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        details_layout = QHBoxLayout()
        details_layout.setAlignment(Qt.AlignLeft)
        details_layout.addWidget(QLabel("Name:"))
        details_layout.addWidget(self.name_lbl)
        details_layout.addWidget(QLabel("NIA:"))
        details_layout.addWidget(self.nia_lbl)
        details_layout.addWidget(QLabel("Group:"))
        details_layout.addWidget(self.group_lbl)
        details_layout.addWidget(QLabel("Exam ID:"))
        details_layout.addWidget(self.exam_id_lbl)

        self.main_layout.addWidget(self.splitter)
        self.main_layout.addLayout(details_layout)

        self.rubrics_tabs = QTabWidget()

        helper = QWidget()
        helper.setLayout(QVBoxLayout())

        self.scores_layout = QFormLayout()
        framebox = QGroupBox("Scores")
        framebox.setLayout(self.scores_layout)

        helper.layout().addWidget(framebox)
        helper.layout().addWidget(self.rubrics_tabs)

        self.quiz_score_lbl = QLabel("0")
        self.total_score_lbl = QLabel("0")
        self.quiz_cb = QCheckBox("Quiz")
        self.quiz_cb.setChecked(True)
        self.quiz_cb.stateChanged.connect(self.score_checkbox_changed)
        self.scores_layout.addRow(self.quiz_cb, self.quiz_score_lbl)
        self.scores_layout.addRow("Total: ", self.total_score_lbl)

        done_info_helper = QWidget()
        done_info_helper.setLayout(QVBoxLayout())
        self.number_assesed_lbl = QLabel("")
        done_info_helper.layout().addWidget(self.number_assesed_lbl)
        done_info_helper.layout().addWidget(self.pdf_tree)
        done_info_helper.setMaximumWidth(280)

        self.splitter.addWidget(done_info_helper)
        self.splitter.addWidget(self.swik)
        self.splitter.addWidget(helper)

        self.setWindowTitle("QRGrader" + (" - Locked" if self.locked else ""))
        self.shortcut = QShortcut(QKeySequence('Ctrl+F'), self)
        self.shortcut.activated.connect(self.find_people)
        self.shortcut2 = QShortcut(QKeySequence('Ctrl+L'), self)
        self.shortcut2.activated.connect(self.toggle_locked)
        self.shortcut3 = QShortcut(QKeySequence('Esc'), self)
        self.shortcut3.activated.connect(self.go_next_exam)
        self.shortcut4 = QShortcut(QKeySequence('Ctrl+A'), self)
        self.shortcut4.activated.connect(self.toggle_auto_advance)

        self.show()

        files = os.listdir(self.dir_publish)
        files = [f for f in files if f.endswith(".pdf") and f.replace(".pdf", "").isdigit()]

        progress = QProgressDialog("Processing...", None, 0, 10 + len(files), self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setWindowTitle("QRGrader")
        progress.show()

        def delayed():
            # Show the progress bar
            self.load_detected()
            self.load_tables()
            self.load_schemas()
            progress.setValue(10)

            self.populate_pdf_tree(self.randomize)
            self.pdf_tree.currentItemChanged.connect(self.pdf_tree_selection_changed)

            if self.pdf_tree.topLevelItemCount() > 0:
                self.pdf_tree.setCurrentItem(self.pdf_tree.topLevelItem(0))

            for index in range(self.pdf_tree.topLevelItemCount()):
                progress.setValue(10 + index)
                item = self.pdf_tree.topLevelItem(index)
                exam_id = int(item.text(1))

                # Update scores
                score = self.get_full_score(exam_id)
                item.setText(3, str(round(score, 2)))

                self.update_exclamation_column(item, exam_id)

                if len(self.rubrics) > 0:
                    self.update_done_color(item)
                    self.update_number_assessed()

            self.rubrics_tabs.currentChanged.connect(self.rubric_tab_changed)

            progress.hide()

            # add shortcut to find people

        QTimer.singleShot(100, delayed)

    def update_exclamation_column(self, item, exam_id):
        # Check if multiple marks or bad NIA
        nia_symbol, _, nia = self.xls_nia.get_nia(exam_id)
        multiple = self.get_number_of_multiple_marked_questions(exam_id)

        query = self.changed.select(exam=exam_id % 1000, type=Code.TYPE_A)

        if multiple > 0:
            multiple_symbol =  str(multiple)
            self.multiple_marked_exams.append(exam_id)
            if self.current_exam ==  exam_id:
                self.exam_id_lbl.set(color=Qt.red, bold=True)
        else:
            multiple_symbol =  ""
            self.multiple_marked_exams.remove(exam_id)
            if self.current_exam ==  exam_id:
                self.exam_id_lbl.set()

        symbol = multiple_symbol if nia_symbol == "" else nia_symbol

        if symbol == "" and len(query) > 0:
            symbol = chr(64 + len(query))

        item.setText(2, symbol)
        return multiple

    def toggle_auto_advance(self):
        self.auto_avance = not self.auto_avance

    def go_next_exam(self):

        current = self.pdf_tree.currentItem()
        if current is None:
            print("current none")
            return

        exam_id = int(current.text(1)) if current is not None else None
        if len(self.multiple_marked_exams) > 0:
            print("len not none")

            if exam_id in self.multiple_marked_exams:
                position = self.multiple_marked_exams.index(exam_id)
                next_exam_id = self.multiple_marked_exams[(position + 1) % len(self.multiple_marked_exams)]
            else:
                next_exam_id = self.multiple_marked_exams[0]
        else:
            print("len none")
            current_index = self.pdf_tree.indexOfTopLevelItem(current)
            next_index = (current_index + 1) % self.pdf_tree.topLevelItemCount()
            next_exam_id = int(self.pdf_tree.topLevelItem(next_index).text(1))

        for index in range(self.pdf_tree.topLevelItemCount()):
            item = self.pdf_tree.topLevelItem(index)
            exam_id = int(item.text(1))
            if exam_id == next_exam_id:
                self.pdf_tree.setCurrentItem(item)
                self.pdf_tree.scrollToItem(item)
                break

    def name_label_changed(self, name):
        nia = self.xls_data.get_nia_from_name(name)
        self.nia_changed(nia)

    def nia_changed(self, nia):
        nia = str(nia)
        codes = self.type_n.select(exam=self.current_exam % 1000)
        if codes is not None:
            for code in codes:
                code.marked = False
            for i, char in enumerate(nia):
                code = "N" + str(self.current_exam) + f"{i}{char}"
                code = self.type_n.get_code_by_data(code)
                code.marked = True
            self.detected.save(self.dir_data + self.prefix + "detected.csv")
            # self.xls_nia.set_nia(self.current_exam, nia)
            self.xls_nia.update_exam(self.current_exam)
            self.process_exam()
            self.update_labels()


    def toggle_locked(self):
        self.locked = not self.locked
        self.setWindowTitle("QRGrader" + (" - Locked" if self.locked else ""))

        for rubric in self.rubrics:
            rubric.lock(self.locked)

    def contextMenuEvent(self, event):
        pos = self.swik.view.mapFrom(self, event.pos())
        item = self.swik.view.get_item_at_position(pos, SwikPage)
        if item is not None:
            menu = QMenu(self)
            move_action = menu.addAction("Move Codes")
            action = menu.exec_(self.mapToGlobal(event.pos()))
            if action == move_action:
                dialog = ControlDialog(item.index,
                                       lambda: self.detected.save(self.dir_data + self.prefix + "detected.csv"),
                                       lambda: self.move_codes(item.index, 0, -2),
                                       lambda: self.move_codes(item.index, 0, 2),
                                       lambda: self.move_codes(item.index, -2, 0),
                                       lambda: self.move_codes(item.index, 2, 0),
                                       lambda: self.move_codes(item.index, 0, 0, 1.01),
                                       lambda: self.move_codes(item.index, 0, 0, 0.99), self)
                dialog.show()

    def rubric_tab_changed(self, index):
        rubric = self.get_current_rubric()
        if rubric is not None:
            index = rubric.get_page()
            #try:
            self.swik.view.move_to_page(index, 10)
            #except Exception as e:
            #    pass

    def update_done_color(self, item):
        howmany = 0
        for rubric in self.rubrics:
            if rubric.assessed(int(item.text(1))):
                howmany += 1
        if howmany == 0:
            item.setForeground(1, Qt.red)
            symb = ""
        elif howmany < len(self.rubrics):
            item.setForeground(1, Qt.magenta)
            symb = "⏳"
        else:
            item.setForeground(1, Qt.black)
            symb = "✓"

        if item.text(2) not in ["!", "@", "?", "D"]:
            item.setText(2, symb)

    def get_current_rubric(self):
        return self.rubrics[self.rubrics_tabs.currentIndex()] if self.rubrics_tabs.currentIndex() >= 0 else None

    def update_number_assessed(self):
        rubric = self.get_current_rubric()

        if rubric is not None:
            count = 0
            for index in range(self.pdf_tree.topLevelItemCount()):
                item = self.pdf_tree.topLevelItem(index)
                if rubric.assessed(int(item.text(1))):
                    count += 1
            self.number_assesed_lbl.setText(
                f"Done: {count}/{self.pdf_tree.topLevelItemCount()} ({count * 100 / self.pdf_tree.topLevelItemCount():.2f}%)")

    def show(self):
        x, y, w, h, fullscreen = self.cfg_geometry.get()
        if fullscreen:
            self.showFullScreen()
        else:
            self.setGeometry(x, y, w, h)
        super().show()

    def find_people(self):
        text, ok = QInputDialog.getText(self, "Find People", "Enter NIA or Name:")
        if ok:
            nia = self.xls_data.get_nia_from_name(text)
            if nia is None:
                nia = int(text) if text.isdigit() else -1
            exam_id = self.xls_nia.get_exam(nia)
            for index in range(self.pdf_tree.topLevelItemCount()):
                item = self.pdf_tree.topLevelItem(index)
                if int(item.text(1)) == exam_id:
                    self.pdf_tree.setCurrentItem(item)
                    self.pdf_tree.scrollToItem(item)
                    break
            else:
                QMessageBox.information(self, "Not Found", "No exam found for NIA or Name: " + text)

    def closeEvent(self, a0):
        current = self.pdf_tree.currentItem()
        if current is not None:
            for rubric in self.rubrics:
                rubric.push(int(current.text(1)))

        self.cfg_geometry.set(
            [self.geometry().x(), self.geometry().y(), self.geometry().width(), self.geometry().height(),
             self.isFullScreen()])
        self.config.save()

    def load_detected(self):
        self.detected.load(self.dir_data + self.prefix + "detected.csv")
        # Pre-select codes to improve performance
        # type_a and type_n contain the codes pointer so
        # any modification in them will be reflected in detected
        self.type_a = self.detected.select(type=Code.TYPE_A)
        self.type_n = self.detected.select(type=Code.TYPE_N)

        self.type_p = self.detected.select(type=Code.TYPE_P)
        self.type_q = self.detected.select(type=Code.TYPE_Q)

        self.changed.load(self.dir_data + self.prefix + "changed.csv")

    def load_tables(self):

        if not self.xls_questions.load():
            print("ERROR: questions.csv file not present")
            sys.exit(1)

        if not self.xls_nia.load(self.type_n):
            print("ERROR: nia.csv file not present")
            sys.exit(1)

        if not self.xls_data.load():
            print("WARNING: data.csv file not present")
        else:
            self.xls_nia.set_valid_nias(self.xls_data.get_all_nias())
    def name_double_clicked(self):
        names = self.xls_data.get_all_names()
        group = self.xls_data.get_all_groups()

        dialog = NameListDialog(zip(names,group), selecting=self.name_lbl.text())
        if dialog.exec():
            self.name_label_changed(dialog.get_selected())
    def rubric_filtered(self):
        for index in range(self.pdf_tree.topLevelItemCount()):
            item = self.pdf_tree.topLevelItem(index)
            exam_id = int(item.text(1))
            comply = True
            for rubric in self.rubrics:
                comply = comply and rubric.comply_with_filter(exam_id)
                item.setHidden(not comply)
        self.pdf_tree.renumber()

    def load_schemas(self):
        for filename in self.rubrics_files:
            print("fukenameo", filename)

            name = os.path.basename(filename).replace(".scm", "")
            r1 = Rubric(filename, self.dir_xls, buttons_height=self.cfg_buttons_height.get(),
                        buttons_font=self.cfg_buttons_font.get())
            r1.score_changed.connect(self.rubric_score_changed)
            r1.button_or_value_changed.connect(self.rubric_button_or_value_changed)
            r1.goto_next.connect(self.goto_next)
            r1.filtered.connect(self.rubric_filtered)
            r1.lock(self.locked)

            helper = QWidget()
            helper.setLayout(QVBoxLayout())
            #helper.setContentsMargins(0, 0, 0, 0)
            #helper.layout().setContentsMargins(0, 0, 0, 0)
            helper.layout().addWidget(r1.get_filter_button())
            helper.layout().addWidget(r1.get_upload_button())
            helper.layout().addWidget(r1)
            self.rubrics_tabs.addTab(helper, name)
            self.rubrics.append(r1)

            label = QLabel("0")
            rubric_cb = QCheckBox(name + ":")
            rubric_cb.setChecked(True)
            rubric_cb.stateChanged.connect(self.score_checkbox_changed)

            self.rubrics_labels.append(label)
            self.rubrics_cb.append(rubric_cb)

            self.scores_layout.insertRow(1, rubric_cb, label)

    def goto_next(self):
        current = self.pdf_tree.currentItem()
        if current is not None:
            index = self.pdf_tree.indexOfTopLevelItem(current)
            if index < self.pdf_tree.topLevelItemCount() - 1:
                self.pdf_tree.setCurrentItem(self.pdf_tree.topLevelItem(index + 1))

    def score_checkbox_changed(self, state):
        self.update_all_pdf_tree_scores()
        self.update_scores_layout()

    def rubric_score_changed(self, rubric, exam_id):
        self.update_scores_layout()
        self.update_pdf_tree_score()

    def rubric_button_or_value_changed(self):
        # dialog with progress bar no advancement
        progress = QProgressDialog("Processing...", "", 0, 0)
        progress.setWindowModality(Qt.WindowModal)
        progress.setCancelButton(None)
        progress.setWindowTitle("QRGrader")
        progress.show()

        def delayed():
            self.update_all_pdf_tree_scores()
            self.update_scores_layout()
            progress.hide()

        QTimer.singleShot(100, delayed)

    def update_scores_layout(self):
        # TODO
        return
        total = 0
        quiz_score, full_score = self.get_quiz_score(self.current_exam)
        if full_score != 0:
            self.quiz_score_lbl.setText("<b>" + str(quiz_score) + "</b>/" + str(round(full_score, 1)) + " (" + str(
                round(10 * quiz_score / full_score, 2)) + "/10)")
        else:
            self.quiz_score_lbl.setText("<b>0</b>")

        if self.quiz_cb.isChecked():
            total += quiz_score

        for index, r in enumerate(self.rubrics):
            value, full_value = r.compute_score(self.current_exam)
            over_10 = round(10 * value / full_value, 2)
            self.rubrics_labels[index].setText(
                "<b>" + str(value) + "</b>/" + str(full_value) + " (" + str(over_10) + "/10)")
            self.rubrics_labels[index].setStyleSheet("color: red;" if over_10 > 10 else "")

            if self.rubrics_cb[index].isChecked():
                total += value

        total = round(total, 2)
        self.total_score_lbl.setText("<b>" + str(total) + "</b>")
        self.total_score_lbl.setStyleSheet("color: red;" if total > 10 else "")


        return total

    def pdf_tree_selection_changed(self, current, previous):
        # this is to prevent the timer from being triggered when the
        # user clicks on another exam while the timer is still running
        self.progress_dialog = QProgressDialog("Loading exam...", None, 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.ApplicationModal)
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.setAutoReset(False)
        self.progress_dialog.show()
        def do():
            self.pdf_tree.set_enabled(False)
            if previous is not None:
                if len(self.rubrics) > 0:
                    self.update_done_color(previous)
                    self.update_number_assessed()

                for rubric in self.rubrics:
                    rubric.push(int(previous.text(1)))

            self.current_exam = int(current.text(1))

            ratio = self.swik.view.get_ratio()
            rubric = self.get_current_rubric()
            index = rubric.get_page() if rubric is not None else 0

            self.swik.open(f"{self.dir_publish}{self.current_exam}.pdf", ratio=ratio, index=index)
        QTimer.singleShot(50, do)

    def update_labels(self):
        symbol, text, nia = self.xls_nia.get_nia(self.current_exam)
        self.nia_lbl.setText(str(nia))
        self.name_lbl.setText(str(self.xls_data.get_name(nia)))
        self.group_lbl.setText(str(self.xls_data.get_group(nia)))
        self.exam_id_lbl.setText(str(self.current_exam))
        multiple = self.get_number_of_multiple_marked_questions(self.current_exam)
        if multiple > 0:
            self.exam_id_lbl.set(color=Qt.red, bold=True)
        else:
            self.exam_id_lbl.set()


    def load_finished(self):
        self.process_exam()
        self.update_labels()
        for rubric in self.rubrics:
            rubric.pull(self.current_exam)

        self.update_scores_layout()
        self.rubric_tab_changed(0)
        self.pdf_tree.set_enabled(True)
        self.progress_dialog.hide()


    def populate_pdf_tree(self, randomize=False):
        files = os.listdir(self.dir_publish)
        # shuffle files

        files = sorted([f.replace(".pdf", "") for f in files if f.endswith(".pdf") and f.replace(".pdf", "").isdigit()])
        if randomize:
            shuffle(files)
        for i, f in enumerate(files):
            item = NumericTreeWidgetItem([str(i+1), f, ""])
            self.pdf_tree.addTopLevelItem(item)

        # if not randomize:
        self.pdf_tree.sortByColumn(0, Qt.AscendingOrder)
        # self.pdf_tree.renumber()

        # Not updating the scores here, as it is done somewhere else
        # self.update_all_pdf_tree_scores()

    def process_exam(self):
        marks = [x for x in self.swik.view.items() if isinstance(x, Mark)]

        while len(marks) > 0:
            mark = marks.pop()
            self.swik.view.scene().removeItem(mark)

        marks = {}
        exam_id = self.current_exam % 1000

        for index in range(self.swik.renderer.get_document_length()):
            page_codes_type_a = self.type_a.select(exam=exam_id, pdf_page=index + 1)
            # type_a = page_codes.select(type=Code.TYPE_A)
            for code in page_codes_type_a:
                r = Mark(code)
                r.signal.double_click.connect(self.code_clicked)
                r.setParentItem(self.swik.view.get_page(index))
                marks[code] = r
                if code.marked:
                    if self.xls_questions.get_value(code.question, code.answer) > 0:
                        r.setPen(QPen(Qt.green, 2))
                    else:
                        r.setPen(QPen(Qt.red, 2))
                else:
                    if self.changed.get(code) is not None:
                        r.setPen(QPen(Qt.cyan, 2))

            page_codes_type_n = self.type_n.select(exam=exam_id, pdf_page=index + 1)
            for code in page_codes_type_n:
                r = Mark(code)
                r.signal.double_click.connect(self.code_clicked)
                r.setParentItem(self.swik.view.get_page(index))
                if code.marked:
                    r.setPen(QPen(Qt.magenta, 2))

        yellow = self.get_multiple_marks(exam_id)
        for answer in yellow:
            marks[answer].setPen(QPen(Qt.yellow, 2))

            if answer == yellow[0]:
                def delayed():
                    try:
                        # The Mark may have disappeared if the user
                        # selected another exam, so we need to try
                        # self.swik.view.ensureVisible(marks[answer])
                        self.swik.view.centerOn(marks[answer])
                    except RuntimeError:
                        pass

                # It gives the user a chance to see the yellow mark removed
                # before moving the view, which can be disorienting if it moves suddenly
                QTimer.singleShot(500, delayed)


    def export_data(self):
        with open(self.dir_xls + self.prefix + "export.csv", "w", encoding='utf-8') as f:
            f.write("EXAM ID\tTOTAL\tQUIZ")
            for r in self.rubrics:
                f.write(f"\t{r.name}")
            f.write("\n")
            total = 0
            for index in range(self.pdf_tree.topLevelItemCount()):
                item = self.pdf_tree.topLevelItem(index)
                exam_id = int(item.text(1))
                quiz, _ = self.get_quiz_score(exam_id)
                total = self.get_full_score(exam_id)
                f.write(f"{exam_id}\t{round(total,2)}\t{round(quiz,2)}")
                for r in self.rubrics:
                    value, _ = r.compute_score(exam_id)
                    f.write(f"\t{round(value,2)}")
                f.write("\n")

    def get_full_score(self, exam_id):
        total = 0
        for index, r in enumerate(self.rubrics):
            if self.rubrics_cb[index].isChecked():
                rubric_value, _ = r.compute_score(exam_id)
                total += rubric_value
        if self.quiz_cb.isChecked():
            quiz_score, quiz_full_value = self.get_quiz_score(exam_id)
            total += quiz_score

        return total


    def update_all_pdf_tree_scores(self):
        progress = QProgressDialog("Updating scores...", None, 0, self.pdf_tree.topLevelItemCount()-1, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setWindowTitle("QRGrader")
        progress.show()
        def delayed():
            for index in range(self.pdf_tree.topLevelItemCount()):
                item = self.pdf_tree.topLevelItem(index)
                score = self.get_full_score(int(item.text(1)))
                item.setText(3, str(round(score, 2)))
                progress.setValue(index)
            progress.hide()
        QTimer.singleShot(100, delayed)


    def update_pdf_tree_score(self):
        for index in range(self.pdf_tree.topLevelItemCount()):
            item = self.pdf_tree.topLevelItem(index)
            if int(item.text(1)) == self.current_exam:
                score = self.get_full_score(self.current_exam)
                item.setText(3, str(round(score, 2)))
                break

    def get_quiz_score(self, exam_id):
        score = 0
        full_value = 0
        exam_codes = self.type_a.select(exam=exam_id % 1000)
        for code in exam_codes:
            value = self.xls_questions.get_value(code.question, code.answer)
            full_value += value if value > 0 else 0
            if code.marked:
                score += value
        score = max(score, 0)  # Ensure score is not negative
        score = round(score, 4)  # Round to 4 decimal places
        return score, full_value

    def get_multiple_marks(self, exam_id):
        yellow = []
        exam_id = exam_id % 1000
        type_a = self.type_a.select(exam=exam_id)
        for question in type_a.get_questions():
            answers = type_a.select(question=question)
            marked = sum([1 for x in answers if x.marked])
            if marked > 1:
                for answer in answers:
                    if answer.marked:
                        yellow.append(answer)
        return yellow

    def get_number_of_multiple_marked_questions(self, exam_id):
        count = 0
        exam_id = exam_id % 1000
        type_a = self.type_a.select(exam=exam_id)
        for question in type_a.get_questions():
            answers = type_a.select(question=question)
            marked = sum([1 for x in answers if x.marked])
            if marked > 1:
                count += 1
        return count


    def get_missing_pq_marks(self, exam_id):
        exam_id = exam_id % 1000
        type_p = self.type_p.select(exam=exam_id, marked=1)
        type_q = self.type_q.select(exam=exam_id, marked=1)
        return len(type_p) != len(type_q)

    def code_clicked(self, code):
        changed = self.changed.get(code)
        if changed is None:
            self.changed.append(code)
        else:
            self.changed.remove(code)


        code.marked = not code.marked
        self.process_exam()
        if code.data.startswith("N"):
            self.xls_nia.update_exam(self.current_exam)
            self.update_labels()
        else:
            self.update_scores_layout()
            self.update_pdf_tree_score()

        if self.update_exclamation_column(self.pdf_tree.currentItem(), code.unique) == 0:
            if self.auto_avance:
                self.go_next_exam()



        self.changed.save(self.dir_data + self.prefix + "changed.csv")
        self.detected.save(self.dir_data + self.prefix + "detected.csv")


    def move_codes(self, page, x, y, scale=1):
        page_codes_type_a = self.type_a.select(exam=self.current_exam % 1000, pdf_page=page + 1)
        page_codes_type_n = self.type_n.select(exam=self.current_exam % 1000, pdf_page=page + 1)
        a_plus_n = page_codes_type_n + page_codes_type_a

        if len(a_plus_n) == 0:
            return

        most_left, selected = 1e6, None

        for code in [c for c in a_plus_n if c.marked]:
            if code.x < most_left:
                selected = code
                most_left = code.x

        if scale != 1 and selected is not None:
            # the selected code maintain its position and the others are scaled around it
            x = selected.x * (1 - scale)
            y = selected.y * (1 - scale)

        for code in a_plus_n:
            code.x = code.x * scale + x
            code.y = code.y * scale + y

        self.process_exam()

    def show_graphs(self):

        rubrics = {"quiz": [], "total": []}
        for r in self.rubrics:
            rubrics[r.name] = []

        for index in range(self.pdf_tree.topLevelItemCount()):
            exam_id = int(self.pdf_tree.topLevelItem(index).text(1))

            quiz_score, quiz_full_value = self.get_quiz_score(exam_id)
            rubrics["quiz"].append(round(10.0*quiz_score/quiz_full_value,2) if quiz_full_value != 0 else 0)

            total = round(quiz_score,2)
            for r in self.rubrics:
                rubric_value, rubric_full_value = r.compute_score(exam_id)
                total += round(rubric_value,2)
                rubrics[r.name].append(round(10.0*rubric_value/rubric_full_value,2) if rubric_full_value != 0 else 0)

            rubrics["total"].append(total)

        self.win = pg.GraphicsLayoutWidget(show=True, title="Distribution Graph")
        self.win.resize(800, 600)

        plot = self.win.addPlot(title="Distribution")
        plot.addLegend()

        brushes = ['r', 'g', 'b', 'c', 'm', 'y']

        for i, (name, data) in enumerate(rubrics.items()):
            y, x = np.histogram(data + [0,10], bins=10, density=True)
            bg_item = pg.BarGraphItem(x=x[:-1], height=y, width=np.diff(x), brush=brushes[i % len(brushes)], pen='w', name=f'{name}')
            plot.addItem(bg_item)

def main():
    app = QApplication(sys.argv)

    # Let Python's signal handler run every 500ms
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    if not check_workspace():
        print("ERROR: qrgrader must be run from the workspace root")
        sys.exit(1)

    parser = argparse.ArgumentParser(description='qrgui.py')
    parser.add_argument('-s', '--schema', help='Schema to be used', default=[], nargs="+")
    parser.add_argument('-c', '--create', help="Create schema if doesn't exist", action="store_true")
    parser.add_argument('-r', '--random', help="Randomize exam order", action="store_true")
    parser.add_argument('-l', '--lock', help="Lock Rubrics", action="store_true")
    args = vars(parser.parse_args())

    filenames = []
    for schema in args["schema"]:
        if schema.endswith(".yaml"):
            print("WARNING: schema MUST NOT be a yaml file.")
            sys.exit(1)

        filename = schema.replace(".scm", "") + ".scm"

        # if not os.path.exists(filename):
        #     if args["create"]:
        #         print("Creating schema", filename)
        #         with open(filename, "w", encoding='utf-8') as f:
        #             f.write("{}\n")
        #     else:
        #         print(f"ERROR: schema {filename} not found")
        #         sys.exit(1)
        filenames.append(filename)

    main = MainWindow(filenames, args)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
