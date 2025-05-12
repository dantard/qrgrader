class Code:
    TYPE_A = 0
    TYPE_P = 1
    TYPE_Q = 2
    TYPE_N = 3
    TYPE_O = 4

    def __init__(self, data, x, y, w, h, page=None, pdf_page=None):
        self.data = data
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.marked = False
        self.exam = None
        self.page = page
        self.pdf_page = pdf_page
        if self.data[0] == "O":
            self.unique = int(self.data[1:10])
            self.date = int(self.data[1:7])
            self.exam = int(self.data[7:10])
            self.question = int(self.data[10:12])
            self.type = self.TYPE_O
        elif self.data[0] == "P":
            self.unique = int(self.data[1:10])
            self.date = int(self.data[1:7])
            self.exam = int(self.data[7:10])
            self.page = int(self.data[10:12])
            self.type = self.TYPE_P
        elif self.data[0] == "Q":
            self.unique = int(self.data[1:10])
            self.date = int(self.data[1:7])
            self.exam = int(self.data[7:10])
            self.page = int(self.data[10:12])
            self.type = self.TYPE_Q
        elif self.data[0] == "N":
            self.unique = int(self.data[1:10])
            self.date = int(self.data[1:7])
            self.exam = int(self.data[7:10])
            self.number = int(self.data[10:12])
            self.type = self.TYPE_N
        else:
            self.unique = int(self.data[0:9])
            self.date = int(self.data[0:6])
            self.exam = int(self.data[6:9])
            self.question = int(self.data[9:11])
            self.answer = int(self.data[11])
            if self.answer not in [1, 2, 3, 4]:
                permut = self.permut[self.question - 1]
                self.answer = int(permut.index(self.answer)) + 1
                self.data = self.data[:11] + str(self.answer)
            self.type = self.TYPE_A

    def set_marked(self, marked):
        self.marked = marked

    def set_page(self, page):
        self.page = page

    def set_pdf_page(self, page):
        self.pdf_page = page

    def set_pos(self, pos):
        self.x = pos[0]
        self.y = pos[1]

    def move(self, delta):
        self.x += delta[0]
        self.y += delta[1]

    def get_exam_id(self):
        return self.exam

    def get_date(self):
        return self.date

    def get_page(self):
        return self.page

    def get_type(self):
        return self.type

    def get_data(self):
        return self.data

    def get_pos(self):
        return self.x, self.y

    def get_size(self):
        return self.w, self.h

    def set_size(self, *args):
        self.w, self.h = args

    def scale(self, factor):
        self.x, self.y = self.x * factor, self.y * factor
        self.w, self.h = self.w * factor, self.h * factor

    def __repr__(self):
        if self.type == self.TYPE_A:
            return f"({self.data}, {self.exam}, {self.x}, {self.y}, {self.w}, {self.h}, PAG:{self.page}, Q:{self.question}, A:{self.answer}), M:{self.marked}"
        elif self.type in [self.TYPE_P, self.TYPE_Q]:
            return f"({self.data}, {self.exam}, {self.x}, {self.y}, {self.w}, {self.h}, PAG:{self.page})"
        elif self.type == self.TYPE_N:
            return f"({self.data}, {self.exam}, {self.x}, {self.y}, {self.w}, {self.h}, PAG:{self.page}, NUM:{self.number})"
        elif self.type == self.TYPE_O:
            return f"({self.data}, {self.exam}, {self.x}, {self.y}, {self.w}, {self.h}, PAG:{self.page}, Q:{self.question})"

    permut = [[5, 6, 7, 8],
              [5, 6, 8, 7],
              [5, 7, 6, 8],
              [5, 7, 8, 6],
              [5, 8, 6, 7],
              [5, 8, 7, 6],  # 6
              [6, 5, 7, 8],  # 7
              [6, 5, 8, 7],  # 8
              [6, 7, 5, 8],  # 9
              [6, 7, 8, 5],  # 10
              [6, 8, 5, 7],  # 11
              [6, 8, 7, 5],  # 12
              [7, 5, 6, 8],  # 13
              [7, 5, 8, 6],  # 14
              [7, 6, 5, 8],  # 15
              [7, 6, 8, 5],  # 16
              [7, 8, 5, 6],  # 17
              [7, 8, 6, 5],  # 18
              [8, 5, 6, 7],  # 19
              [8, 5, 7, 6],  # 20
              [8, 6, 5, 7],  # 21
              [8, 6, 7, 5],
              [8, 7, 5, 6],
              [8, 7, 6, 5],
              [5, 6, 7, 8],
              [5, 6, 8, 7],
              [5, 7, 6, 8],
              [5, 7, 8, 6],
              [5, 8, 6, 7],
              [5, 8, 7, 6],
              [6, 5, 7, 8],
              [6, 5, 8, 7],
              [6, 7, 5, 8],
              [6, 7, 8, 5],
              [6, 8, 5, 7],
              [6, 8, 7, 5],
              [7, 5, 6, 8],
              [7, 5, 8, 6],
              [7, 6, 5, 8],
              [7, 6, 8, 5],
              [7, 8, 5, 6],
              [7, 8, 6, 5],
              [8, 5, 6, 7],
              [8, 5, 7, 6],
              [8, 6, 5, 7],
              [8, 6, 7, 5],
              [8, 7, 5, 6],
              [8, 7, 6, 5]]
