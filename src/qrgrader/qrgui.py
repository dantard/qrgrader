import argparse
import os
import sys

from PyQt5.QtCore import Qt, QObject, pyqtSignal, QTimer
from PyQt5.QtGui import QPen, QKeySequence
from PyQt5.QtWidgets import QApplication, QInputDialog, QShortcut, QProgressDialog
from PyQt5.QtWidgets import QMainWindow, QHBoxLayout, QWidget, QTreeWidgetItem, QSplitter, QGraphicsRectItem, QTabWidget, QLabel, QVBoxLayout, \
    QSizePolicy, QFormLayout, QCheckBox, QGroupBox
from easyconfig2.easyconfig import EasyConfig2
from numpy.ma.core import maximum
from swikv4.widgets.swik_basic_widget import SwikBasicWidget

from qrgrader.utils import makedir
from qrgrader.code import Code
from qrgrader.code_set import CodeSet
from qrgrader.common import check_workspace, get_workspace_paths, Questions, Nia, StudentsData, get_prefix
from qrgrader.pdf_tree import PDFTree
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
        a, b = QInputDialog.getInt(self, "Edit Value", "Enter new value:", int(self.text().replace("X","0").replace("Y","0")))
        if b:
            self.setText(str(a))
            self.new_value.emit(a)

class MainWindow(QMainWindow):
    def __init__(self, schema_filenames):
        super().__init__()

        makedir(os.path.expanduser("~") + os.sep + ".config/qrgrader/")
        self.config = EasyConfig2(filename=os.path.expanduser("~") + os.sep + ".config/qrgrader/qrgrader.yaml")
        self.cfg_geometry = self.config.root().addPrivate("geometry", default=[0, 0, 1200, 1000, False])
        self.cfg_buttons_height = self.config.root().addPrivate("buttons_height")
        self.cfg_buttons_font = self.config.root().addPrivate("buttons_font")
        self.config.load()

        self.current_exam = None
        self.detected = CodeSet()
        self.type_a = None
        self.type_n = None
        self.changed = CodeSet()

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
        self.xls_nia = Nia(self.dir_xls + self.prefix + "nia.csv")
        self.xls_data = StudentsData(self.dir_xls + self.prefix + "data.csv")

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
        self.name_lbl = QLabel()
        self.name_lbl.setMinimumWidth(300)
        self.name_lbl.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        self.nia_lbl = EditableLabel()
        self.nia_lbl.new_value.connect(self.change_nia)
        self.nia_lbl.setMinimumWidth(100)
        self.nia_lbl.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        self.group_lbl = QLabel()
        self.group_lbl.setMinimumWidth(100)
        self.group_lbl.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        details_layout = QHBoxLayout()
        details_layout.setAlignment(Qt.AlignLeft)
        details_layout.addWidget(QLabel("Name:"))
        details_layout.addWidget(self.name_lbl)
        details_layout.addWidget(QLabel("NIA:"))
        details_layout.addWidget(self.nia_lbl)
        details_layout.addWidget(QLabel("Group:"))
        details_layout.addWidget(self.group_lbl)

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

        self.setWindowTitle("QR Grader")
        self.shortcut = QShortcut(QKeySequence('Ctrl+F'), self)
        self.shortcut.activated.connect(self.find_people)
        self.show()

        files = os.listdir(self.dir_publish)
        files = [f for f in files if f.endswith(".pdf") and f.replace(".pdf", "").isdigit()]

        progress = QProgressDialog("Processing...", None, 0, 10 + len(files), self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setWindowTitle("QRGrader")
        progress.show()

        def delayed():
            # Show the progress bar
            self.load_tables()
            self.load_detected()
            self.load_schemas()
            progress.setValue(10)

            self.populate_pdf_tree()
            self.pdf_tree.currentItemChanged.connect(self.pdf_tree_selection_changed)

            if self.pdf_tree.topLevelItemCount() > 0:
                self.pdf_tree.setCurrentItem(self.pdf_tree.topLevelItem(0))

            for index in range(self.pdf_tree.topLevelItemCount()):
                progress.setValue(10 + index)
                item = self.pdf_tree.topLevelItem(index)
                exam_id = int(item.text(1))

                # Update scores
                score = self.get_full_score(exam_id)
                item.setText(3, str(score))

                # Check if multiple marks or bad NIA
                nia = self.xls_nia.get_nia(exam_id)
                if len(self.get_multiple_marks(exam_id)) > 0:
                    item.setText(2, "!")
                elif nia is None or type(nia) == str:
                    item.setText(2, "@")
                else:
                    item.setText(2, "")

                if len(self.rubrics) > 0:
                    self.update_done_color(item)
                    self.update_number_assessed()

            progress.hide()

            # add shortcut to find people
        QTimer.singleShot(100, delayed)

    def update_done_color(self, item):
        howmany = 0
        for rubric in self.rubrics:
            if rubric.assessed(int(item.text(1))):
                howmany += 1
        if howmany == 0:
            item.setForeground(1, Qt.red)
        elif howmany < len(self.rubrics):
            item.setForeground(1, Qt.magenta)
        else:
            item.setForeground(1, Qt.black)

    def update_number_assessed(self):
        rubric = self.rubrics_tabs.currentWidget()

        if rubric is not None:
            count = 0
            for index in range(self.pdf_tree.topLevelItemCount()):
                item = self.pdf_tree.topLevelItem(index)
                if rubric.assessed(int(item.text(1))):
                    count += 1
            self.number_assesed_lbl.setText(f"Done: {count}/{self.pdf_tree.topLevelItemCount()} ({count * 100 / self.pdf_tree.topLevelItemCount():.2f}%)")

    def show(self):
        x, y, w, h, fullscreen = self.cfg_geometry.get()
        if fullscreen:
            self.showFullScreen()
        else:
            self.setGeometry(x, y, w, h)
        super().show()


    def change_nia(self, nia):
        self.xls_nia.set_nia(self.current_exam, nia)
        self.xls_nia.save()
        item = self.pdf_tree.currentItem()
        exam_id = int(item.text(1))
        nia = self.xls_nia.get_nia(exam_id)
        if len(self.get_multiple_marks(exam_id)) > 0:
            item.setText(2, "!")
        elif nia is None or type(nia) == str:
            item.setText(2, "@")
        else:
            item.setText(2, "")

    def find_people(self):
        print("si")
        text, ok = QInputDialog.getText(self, "Find People", "Enter NIA or Name:")
        if ok:
            nia = self.xls_data.get_nia_from_name(text)
            nia = nia or int(text)
            exam_id = self.xls_nia.get_exam(nia)
            for index in range(self.pdf_tree.topLevelItemCount()):
                item = self.pdf_tree.topLevelItem(index)
                if int(item.text(1)) == exam_id:
                    self.pdf_tree.setCurrentItem(item)
                    self.pdf_tree.scrollToItem(item)
                    break

    def closeEvent(self, a0):
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

    def load_tables(self):

        if not self.xls_questions.load():
            print("ERROR: questions.csv file not present")
            sys.exit(1)

        if not self.xls_nia.load():
            print("ERROR: nia.csv file not present")
            sys.exit(1)

        if not self.xls_data.load():
            print("WARNING: data.csv file not present")

    def load_schemas(self):
        for filename in self.rubrics_files:
            name = os.path.basename(filename).replace(".scm", "")
            r1 = Rubric(filename, self.dir_xls, buttons_height=self.cfg_buttons_height.get(), buttons_font=self.cfg_buttons_font.get())
            r1.score_changed.connect(self.rubric_score_changed)
            r1.goto_next.connect(self.goto_next)
            self.rubrics_tabs.addTab(r1, name)
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

    def update_scores_layout(self):

        total = 0
        quiz_score = self.get_quiz_score(self.current_exam)
        self.quiz_score_lbl.setText(str(quiz_score))
        if self.quiz_cb.isChecked():
            total += quiz_score

        for index, r in enumerate(self.rubrics):
            value = r.compute_score(self.current_exam)
            self.rubrics_labels[index].setText(str(value))
            if self.rubrics_cb[index].isChecked():
                total += value

        self.total_score_lbl.setText(str(total))
        return total

    def pdf_tree_selection_changed(self, current, previous):

        self.pdf_tree.set_enabled(False)
        if previous is not None:
            if len(self.rubrics) > 0:
                self.update_done_color(previous)
                self.update_number_assessed()

            for rubric in self.rubrics:
                rubric.push(int(previous.text(1)))

        self.current_exam = int(current.text(1))

        ratio = self.swik.view.get_ratio()
        rubric = self.rubrics_tabs.currentWidget()
        index = rubric.get_page() if rubric is not None else 0



        self.swik.open(f"{self.dir_publish}{self.current_exam}.pdf", ratio=ratio, index=index)

    def load_finished(self):
        self.pdf_tree.set_enabled(True)

        self.process_exam()

        nia = self.xls_nia.get_nia(self.current_exam)
        self.nia_lbl.setText(str(nia))
        self.name_lbl.setText(str(self.xls_data.get_name(nia)))
        self.group_lbl.setText(str(self.xls_data.get_group(nia)))

        for rubric in self.rubrics:
            rubric.pull(self.current_exam)

        self.update_scores_layout()
        self.pdf_tree.set_enabled(True)


    def populate_pdf_tree(self):
        files = os.listdir(self.dir_publish)
        files = sorted([f.replace(".pdf", "") for f in files if f.endswith(".pdf") and f.replace(".pdf", "").isdigit()])

        for f in files:
            item = QTreeWidgetItem(["", f, ""])
            self.pdf_tree.addTopLevelItem(item)

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
            #type_a = page_codes.select(type=Code.TYPE_A)
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

            page_codes_type_n = self.type_n.select(exam=exam_id, pdf_page=index + 1)
            for code in page_codes_type_n:
                r = Mark(code)
                r.signal.double_click.connect(self.code_clicked)
                r.setParentItem(self.swik.view.get_page(index))
                if code.marked:
                    r.setPen(QPen(Qt.blue, 2))

        yellow = self.get_multiple_marks(exam_id)
        for answer in yellow:
            marks[answer].setPen(QPen(Qt.yellow, 2))

    def get_full_score(self, exam_id):
        total = 0
        for index, r in enumerate(self.rubrics):
            if self.rubrics_cb[index].isChecked():
                total += r.compute_score(exam_id)
        if self.quiz_cb.isChecked():
            total += self.get_quiz_score(exam_id)

        return total

    def update_all_pdf_tree_scores(self):
        for index in range(self.pdf_tree.topLevelItemCount()):
            item = self.pdf_tree.topLevelItem(index)
            score = self.get_full_score(int(item.text(1)))
            item.setText(3, str(score))

    def update_pdf_tree_score(self):
        for index in range(self.pdf_tree.topLevelItemCount()):
            item = self.pdf_tree.topLevelItem(index)
            if int(item.text(1)) == self.current_exam:
                score = self.get_full_score(self.current_exam)
                item.setText(3, str(score))
                break

    def get_quiz_score(self, exam_id):
        score = 0
        exam_codes = self.type_a.select(exam=exam_id % 1000)
        for code in exam_codes:
            if code.marked:
                score += self.xls_questions.get_value(code.question, code.answer)
        return score

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

    def code_clicked(self, code):
        self.changed.append(code)
        self.changed.save(self.dir_data + self.prefix + "changed.csv")
        code.marked = not code.marked
        self.process_exam()
        self.update_scores_layout()
        self.update_pdf_tree_score()
        self.detected.save(self.dir_data + self.prefix + "detected.csv")

        item = self.pdf_tree.currentItem()
        nia = self.xls_nia.get_nia(code.unique)

        if len(self.get_multiple_marks(int(code.exam))) > 0:
            item.setText(2, "!")
        elif nia is None or type(nia) == str:
            item.setText(2, "@")
        else:
            item.setText(2, "")



def main():
    app = QApplication(sys.argv)

    if not check_workspace():
        print("ERROR: qrgrader must be run from the workspace root")
        sys.exit(1)

    parser = argparse.ArgumentParser(description='qrgui.py')
    parser.add_argument('-s', '--schema', help='Schema to be used', default=[], action="append")
    parser.add_argument('-c', '--create', help="Create schema if doesn't exist", action="store_true")
    args = vars(parser.parse_args())

    filenames = []
    for schema in args["schema"]:
        if schema.endswith(".yaml"):
            print("WARNING: schema MUST NOT be a yaml file.")
            sys.exit(1)

        filename = schema.replace(".scm", "") + ".scm"

        if not os.path.exists(filename):
            if args["create"]:
                print("Creating schema", filename)
                with open(filename, "w", encoding='utf-8') as f:
                    f.write("{}\n")
            else:
                print(f"ERROR: schema {filename} not found")
                sys.exit(1)
        filenames.append(filename)

    main = MainWindow(filenames)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
