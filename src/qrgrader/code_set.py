import os

from qrgrader.code import Code


class CodeSet:
    def __init__(self, codes=None):
        self.codes = {} if codes is None else codes

    def append(self, code):
        self.codes[code.data] = code

    def extend(self, codes):
        for code in codes:
            self.append(code)

    def clear(self):
        self.codes.clear()

    def __repr__(self):
        text = str()
        for code in self.codes.values():
            text += str(code) + "\n"
        return text

    def __len__(self):
        return len(self.codes)

    def __next__(self):
        return next(iter(self.codes.values()))

    def __iter__(self):
        return iter(self.codes.values())

    def select(self, **kwargs):
        # chatGPT replaced this
        # filtered = [x for x in self.codes.values() if all(getattr(x, key) == value for key, value in kwargs.items())]

        # with this for efficiency
        attrs = kwargs.items()
        filtered = []
        for x in self.codes.values():
            match = True
            for key, value in attrs:
                if getattr(x, key) != value:
                    match = False
                    break
            if match:
                filtered.append(x)

        # This also works, but is slightly less efficient
        # result = CodeSet({code.data: code for code in filtered})

        result = CodeSet()
        for code in filtered:
            result.append(code)
        return result

    def get(self, code):
        return self.codes.get(code.data)

    def get_exams(self):
        return sorted(list(set([x.exam for x in self.codes.values()])))

    def get_questions(self):
        return sorted(list(set([x.question for x in self.codes.values() if x.type == Code.TYPE_A])))

    def get_open(self):
        return sorted(list(set([x.question for x in self.codes.values() if x.type == Code.TYPE_O])))

    def get_answers(self):
        return sorted(list(set([x.answer for x in self.codes.values() if x.type == Code.TYPE_A])))

    def save(self, file_name):
        with open(file_name, "w", encoding='utf-8') as f:
            for code in self.codes.values():
                f.write(
                    code.data + ",{:.2f},{:.2f},{:.2f},{:.2f},{},{},{:d}\n".format(code.x, code.y, code.w, code.h, code.page, code.pdf_page, int(code.marked)))

    def load(self, file_name):
        if not os.path.exists(file_name):
            return False

        with open(file_name, "r", encoding='utf-8') as f:
            for line in f:
                fields = line.strip().split(",")
                data, x, y, w, h, page, pdf_page = fields[:7]
                code = Code(data, float(x), float(y), float(w), float(h), int(page), int(pdf_page))
                if len(fields) > 7:
                    code.set_marked(int(fields[7]))
                self.append(code)
        return True

    def get_date(self):
        if len(self.codes.values()) > 0:
            return next(iter(self.codes.values())).date
        return None

    def empty(self):
        return len(self) == 0

    def first(self, **kwargs) -> Code:
        return next(iter(self.select(**kwargs)), None)


class PageCodeSet(CodeSet):

    def __init__(self, codeset=None):
        super().__init__()
        if codeset is not None:
            self.codes = codeset.codes

    def get_q(self):
        return next((x for x in self.codes.values() if x.type == Code.TYPE_Q), None)

    def get_p(self):
        return next((x for x in self.codes.values() if x.type == Code.TYPE_P), None)

    def get_page(self):
        source = self.get_p() or self.get_q()
        if source is not None:
            return source.page
        return None

    def get_exam_id(self):
        if len(self.codes.values()) > 0:
            return next(iter(self.codes.values())).exam
        return None

    def get_date(self):
        if len(self.codes.values()) > 0:
            return next(iter(self.codes.values())).date
        return None
