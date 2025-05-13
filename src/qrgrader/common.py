import os

import pandas

from qrgrader.code import Code
from qrgrader.code_set import CodeSet


def get_workspace_paths(base):
    dir_workspace = base + os.sep
    dir_data = dir_workspace + "data" + os.sep
    dir_scanned = dir_workspace + "scanned" + os.sep
    dir_generated = dir_workspace + "generated" + os.sep
    dir_xls = dir_workspace + "results" + os.sep + "xls" + os.sep
    dir_publish = dir_workspace + "results" + os.sep + "pdf" + os.sep
    dir_source = dir_workspace + "source" + os.sep
    return dir_workspace, dir_data, dir_scanned, dir_generated, dir_xls, dir_publish, dir_source


def get_temp_paths(date, base):
    dir_scanner = base + os.sep + "__qrgrading__" + date + os.sep + "scanner" + os.sep
    dir_generator = base + os.sep + "__qrgrading__" + date + os.sep + "generator" + os.sep
    return dir_scanner, dir_generator


def get_date():
    if not check_workspace():
        raise Exception("get_date must be used from within a workspace directory")
    current_dir = os.path.basename(os.getcwd())
    date = current_dir.split("-")[1].strip("/")
    return date


def check_workspace():
    current_dir = os.getcwd()
    dir_name = os.path.basename(current_dir)
    name = dir_name.split("-")
    if len(name) != 2 or name[0] != "qrgrading" or len(name[1]) != 6 or not name[1].isdigit():
        return False
    return True


def get_prefix():
    date = get_date()
    return str(date) + "_"


class Questions:
    def __init__(self, filename):
        self.filename = filename
        self.questions = None

    def load(self):
        if os.path.exists(self.filename):
            self.questions = pandas.read_csv(self.filename, sep='\t', header=0)
            return True
        return False

    def get_text(self, question):
        return self.questions.loc[question - 1, "BRIEF"]

    def get_value(self, question, answer):
        return self.questions.loc[question - 1, chr(answer + 64)]

    def get_type(self, question):
        return self.questions.loc[question - 1, "TYPE"]

    def get_questions(self):
        return self.questions.iloc[:, 0].tolist()


class Generated(CodeSet):

    def __init__(self, ppm):
        super().__init__()
        self.ppm = ppm

    def load(self, filename):
        if not os.path.exists(filename):
            return False

        with open(filename, "rb") as f:
            for line in f.readlines():
                data, x, y, w, h, pag, pdf_pag = line.decode().strip().split(",")
                x = int(int(x) / 65535 * 0.351459804 * self.ppm)
                y = int(297 * self.ppm - int(int(y) / 65535 * 0.351459804 * self.ppm))  # 297???
                self.append(Code(data, int(x), int(y), 120, 120, int(pag), int(pdf_pag)))
        return True


class StudentsData:
    def __init__(self, filename):
        self.filename = filename
        self.data = None

    def load(self):
        if os.path.exists(self.filename):
            self.data = pandas.read_csv(self.filename, sep='\t', header=0)
            return True
        return False

    def get_name(self, nia):
        if self.data is None:
            return None
        by_nia = self.data[self.data["NIA"] == nia]
        if by_nia.empty:
            return None

        return by_nia.iloc[0]["NAME"]

    def get_group(self, nia):
        if self.data is None:
            return None
        by_nia = self.data[self.data["NIA"] == nia]
        if by_nia.empty:
            return None

        return by_nia.iloc[0]["GROUP"]

    def get_nia_from_name(self, name):
        if self.data is None:
            return None
        by_name = self.data[self.data["NAME"].str.contains(name, case=False, regex=False)]
        if by_name.empty:
            return None

        return by_name.iloc[0]["NIA"]


class Nia:

    def __init__(self, filename):
        self.filename = filename
        self.nia = None

    def load(self):
        if os.path.exists(self.filename):
            self.nia = pandas.read_csv(self.filename, sep='\t', header=0)
            return True
        return False

    def get_nia(self, exam):
        # EXAM FORMAT: 240509002
        by_exam = self.nia[self.nia["EXAM"] == int(exam)]
        if by_exam.empty or by_exam.iloc[0]["NIA"] is None:
            return None
        nia = by_exam.iloc[0]["NIA"]
        return int(nia) if str(nia).isdigit() else str(nia)

    def get_exam(self, nia):
        by_nia = self.nia[self.nia["NIA"] == nia]
        if by_nia.empty:
            return None

        return by_nia.iloc[0]["EXAM"]

    def set_nia(self, exam_id, nia):
        # EXAM FORMAT: 240509002
        self.nia.loc[self.nia['EXAM'] == int(exam_id), 'NIA'] = int(nia)


    def save(self):
        if self.nia is None:
            return False
        self.nia.to_csv(self.filename, sep='\t', index=False)
        return True


def get_narrowest_type(cell):
    try:
        res = int(cell)
    except ValueError:
        try:
            res = float(cell)
        except ValueError:
            res = str(cell)

    return res
