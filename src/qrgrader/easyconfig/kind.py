class Kind:
    def __init__(self):
        pass

    STR = 1
    INT = 2
    FILE = 3
    CHECKBOX = 4
    FLOAT = 5
    COMBOBOX = 6
    SECTION = 7
    SUBSECTION = 8
    PASSWORD = 9
    EDITBOX = 10
    LIST = 11
    FILE_SAVE = 12
    CHOSE_DIR = 13
    LABEL = 14
    SLIDER = 15
    DOUBLE_TEXT = 16
    DICTIONARY = 17
    ROOT = 254

    @staticmethod
    def type2Kind(value):
        if type(value) == int:
            return 2
        elif type(value) == float:
            return 5
        elif type(value) == list:
            return 11
        else:
            return 1