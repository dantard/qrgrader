import os
import sys
import shutil
import zxingcpp
import pyzbar
import cv2
import pandas as pd
import math
import numpy as np


class Code:
    permut2 = [[6, 5, 9, 7], [6, 8, 5, 0], [0, 8, 5, 7], [0, 6, 9, 5], [5, 7, 0, 8], [0, 8, 9, 5], [5, 9, 8, 6], [8, 6, 9, 0], [0, 6, 7, 9], [9, 8, 5, 0],
              [0, 6, 5, 9], [7, 6, 5, 0], [0, 5, 7, 9], [9, 0, 6, 8], [6, 8, 9, 0], [0, 6, 9, 8], [0, 6, 5, 8], [8, 9, 6, 0], [8, 6, 9, 0], [8, 7, 0, 9],
              [8, 7, 9, 5], [8, 5, 7, 0], [0, 6, 8, 7], [0, 5, 6, 9], [6, 0, 7, 9], [8, 0, 9, 6], [9, 7, 8, 6], [7, 5, 9, 8], [0, 6, 5, 8], [0, 7, 5, 6],
              [6, 7, 9, 5], [7, 0, 8, 5], [0, 6, 8, 7], [7, 0, 6, 8], [0, 9, 7, 6], [9, 7, 5, 8], [7, 9, 8, 6], [8, 5, 7, 9], [9, 0, 8, 6], [9, 0, 6, 5],
              [7, 0, 5, 6], [8, 5, 7, 9], [6, 8, 7, 5], [6, 8, 0, 5], [8, 0, 9, 5], [6, 0, 5, 8], [9, 7, 6, 8], [8, 9, 5, 7], [8, 7, 6, 5], [9, 7, 0, 6],
              [8, 0, 9, 7], [7, 0, 5, 8], [5, 0, 7, 9], [5, 0, 9, 8], [0, 6, 9, 7], [0, 5, 9, 7], [6, 7, 5, 8], [5, 7, 9, 6], [7, 0, 9, 6], [6, 0, 7, 9],
              [8, 0, 9, 6], [6, 7, 8, 0], [9, 8, 6, 0], [7, 5, 9, 0], [0, 5, 6, 9], [8, 6, 7, 0], [8, 5, 7, 9], [8, 7, 5, 0], [0, 6, 8, 7], [6, 7, 8, 5],
              [8, 5, 7, 9], [6, 8, 9, 0], [9, 5, 6, 7], [0, 6, 5, 9], [7, 8, 6, 9], [5, 9, 6, 0], [5, 9, 6, 0], [5, 0, 6, 9], [7, 9, 6, 8], [9, 8, 0, 6],
              [7, 5, 6, 9], [0, 9, 5, 8], [8, 9, 6, 7], [6, 5, 8, 0], [8, 0, 9, 5], [0, 5, 7, 9], [0, 5, 6, 9], [5, 8, 0, 9], [8, 5, 0, 7], [8, 5, 7, 9],
              [7, 6, 9, 0], [6, 9, 5, 7], [5, 8, 0, 7], [9, 0, 7, 5], [7, 6, 5, 8], [5, 0, 9, 7], [5, 9, 7, 6], [0, 9, 7, 6], [0, 6, 9, 8]]

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

    def __init__(self, field1, field2, field3, field4, field5, field6, page=0, pdf_page=0):
        self.type = field1
        self.data = field2
        self.x = field3
        self.y = field4
        self.w = field5
        self.h = field6
        self.page = page
        self.pdf_page = pdf_page
        self.question = -1
        self.answer = -1

        if self.data.startswith("#") or self.data.startswith("P") or self.data.startswith("Q"):
            self.date = self.data[1:7]
            self.exam = self.data[7:10]

            if len(self.data) == 12:
                self.page = self.data[10:12]
            elif len(self.data) > 10:
                self.page = self.data[10]

            if self.data.startswith("Q"):
                self.type = 5
            else:
                self.type = 1
        elif self.data.startswith("@"):
            self.date = self.data[1:7]
            self.exam = self.data[7:10]
            self.type = 2
        elif self.data.startswith("M"):
            self.date = self.data[1:7]
            self.exam = self.data[7:10]
            self.type = 3
        elif self.data.startswith("N"):
            self.date = self.data[1:7]
            self.exam = self.data[7:10]
            self.type = 4
        else:
            self.date = self.data[0:6]
            self.exam = self.data[6:9]
            self.question = int(self.data[9:11])
            answ = int(self.data[11])
            if answ in [1, 2, 3, 4]:
                self.answer = answ
            else:
                permut = self.permut[self.question - 1]
                self.answer = int(permut.index(answ)) + 1
                self.data = self.data[:11] + str(self.answer)

            # self.answer = int(self.data[11])
            self.type = 0

    def get_data(self):
        return self.data

    def set_page(self, page):
        self.page = page

    def set_pdf_page(self, page):
        self.pdf_page = page


class Patch():
    def __init__(self, field1, field2, field3, field4):
        self.x = field1
        self.y = field2
        self.w = field3
        self.h = field4


def scan_page(orig, use_zxing, use_zbar, use_debug, debug_path, output_file, ppm, size_mm, verbose,
              tolerance, thresholds, pdf_page, allnative):
    # Create directories
    makedir(output_file + os.sep + "unrecognized", False)
    (use_debug & 1) and makedir(debug_path + os.sep + "recognized", False)
    (use_debug & 2) and makedir(debug_path + os.sep + "all", False)

    # List for the codes
    codes = []
    seen = []
    for i in thresholds:

        # List for the patches
        patches = []

        if i == 0:
            img = orig.copy()
        else:
            ret, img = cv2.threshold(orig, 255 * float(i) / 100, 255, cv2.THRESH_BINARY)

        # (use_debug & 1) and cv2.imwrite(debug_path + os.sep + filename + "_th_" + str(i) + ".png", img)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ret, thresh = cv2.threshold(gray, 200, 255, 1)

        # Find patches
        contours, h = cv2.findContours(thresh, 1, 2)

        # Full image
        patches.append(Patch(0, 0, gray.shape[1], gray.shape[0]))

        # Get other patches
        for cnt in contours:

            leng = cv2.arcLength(cnt, True)

            if leng < 0:
                continue

            approx = cv2.approxPolyDP(cnt, 0.01 * cv2.arcLength(cnt, True), True)

            if (len(approx) > 8) or (len(approx) < 4):
                continue

            x, y, w, h = cv2.boundingRect(cnt)

            if (w > ppm * size_mm * (1 - tolerance)) and (h > ppm * size_mm * (1 - tolerance)) and (
                    w < ppm * size_mm * (1 + tolerance)) and (
                    h < ppm * size_mm * (1 + tolerance)):  # and (y - ppm > 0) and (x - ppm > 0):
                patches.append(Patch(x, y, w, h))
            else:
                if (w > ppm * size_mm * 0.2) and (h > ppm * size_mm * 0.2) \
                        and (w < ppm * size_mm * 0.5) and (h < ppm * size_mm * 0.5):
                    a = int(ppm * size_mm / 2)
                    patches.append(Patch(x - a, y - a, w + 2 * a, h + 2 * a))

        # Process all patches
        for p in patches:
            patch = img[p.y:p.y + p.h, p.x:p.x + p.w]
            # (use_debug & 2) and cv2.imwrite(
            #    debug_path + os.sep + "all" + os.sep + filename + "_patch_th_" + str(i) + "_pos_" + str(
            #        p.x) + "_" + str(p.y) + ".png", patch)

            if use_zbar:
                decoded = pyzbar.decode(patch)
                for elem in decoded:
                    data = elem.data.decode("utf-8")
                    if data not in seen:
                        m = Code(elem.type, data, elem.rect.left + p.x, elem.rect.top + p.y,
                                 elem.rect.width, elem.rect.height)
                        codes.append(m)
                        seen.append(m.get_data())

                        # Debug
                        (use_debug & 1) and cv2.imwrite(
                            debug_path + os.sep + "recognized" + os.sep + elem.data.decode("utf-8") + ".png", patch)

            if use_zxing:
                results = zxingcpp.read_barcodes(patch, formats=zxingcpp.BarcodeFormat.Aztec | zxingcpp.BarcodeFormat.QRCode)
                for result in results:
                    if result.text not in seen:
                        topleftx = min(result.position.top_left.x, result.position.bottom_right.x)
                        toplefty = min(result.position.top_left.y, result.position.bottom_right.y)
                        width = abs(result.position.top_left.x - result.position.bottom_right.x)
                        height = abs(result.position.top_left.y - result.position.bottom_right.y)

                        m = Code(str(result.format).replace("BarcodeFormat.", ""), result.text, topleftx + p.x,
                                 toplefty + p.y, width, height)
                        codes.append(m)
                        seen.append(m.get_data())

                        (use_debug & 1) and cv2.imwrite(
                            debug_path + os.sep + "recognized" + os.sep + result.text + ".png",
                            patch)

    code_set = set(code.data for code in codes)
    if verbose:
        print("Detected {} codes ({} unique) and {} patches:".format(len(codes), len(code_set), len(patches)))
        for m in codes:
            print(m.type, m.data, m.x, m.y, m.w, m.h)

    # get page_id code
    page_number_code = next((x for x in codes if x.type == 1 or x.type == 5), None)

    # Get number of page
    if page_number_code is not None:
        page = page_number_code.page
        exam = page_number_code.exam
        date = page_number_code.date
    elif len(codes) > 0:
        exam = codes[0].exam
        date = codes[0].date
        page = 0
    else:
        exam = 'XXX'
        date = 'XXXXXX'
        page = -2

    # If the page can't be found, we can try con allnative QRs if it exists
    if page == 0 and allnative is not None and codes is not None and len(codes) > 0:

        # codes_print(codes)
        any_code = codes_filter_by(allnative, date=date, exam=exam, quest=codes[0].question, elem=0)
        print("Trying to recover page number", any_code)
        codes_print(codes)
        if any_code is not None:
            page = int(any_code.page)
            print("Recovered page number ({}) from native QRs for exam {} (pdf page {})".format(page, exam, pdf_page))

    # Set the page and pdf_page on all the codes in this page
    for c in codes:
        c.set_page(page)
        c.set_pdf_page(pdf_page)

    return date, exam, page, codes


def codes_write(codes_file_name, codes, type='a'):
    f = open(codes_file_name, type)
    for m in codes:
        f.write(m.data + ",{},{},{},{},{},{}\n".format(m.x, m.y, m.w, m.h, m.page, m.pdf_page))
    f.close()


def codes_read(codes_file_name):
    try:
        f = open(codes_file_name, "r")
    except:
        return None

    codes = []
    for line in f:
        [data, x, y, w, h, page, pdf_page] = line.strip().split(",")
        codes.append(Code(0, data, int(x), int(y), int(w), int(h), int(page), int(pdf_page)))
    f.close()
    return codes


def write_page_image(output_file, orig, date, exam, page, pdf_page):
    if page == 0:
        cv2.imwrite(output_file + os.sep + "page-{}-{}-{:03d}-{}.png".format(date, exam, int(0), pdf_page), orig)
    elif page == -2:
        cv2.imwrite(
            output_file + os.sep + "unrecognized" + os.sep + "page-{}-{}-{:03d}-{}.png".format(date, exam, int(0), pdf_page), orig)
    else:
        cv2.imwrite(output_file + os.sep + "page-{}-{}-{:03d}.png".format(date, exam, int(page)), orig)


def makedir(path, delete=True):
    if delete:
        try:
            shutil.rmtree(path)
        except OSError:
            pass
    try:
        os.makedirs(path)
        return path
    except FileExistsError:
        return path
        pass
    except OSError:
        print("Creation of the directory %s failed, exiting") % path
        sys.exit(1)


def codes_filter_by(codes, data=None, date=None, exam=None, page=None, quest=None, type=-1, elem=-1, answ=None):
    result = []

    for c in codes:
        # print(c.data, c.date==date, c.exam == exam, int(c.page)==page, page, c.page)
        if (date is None or c.date == date) and \
                (exam is None or c.exam == exam) and \
                (page is None or int(c.page) == page) and \
                (data is None or c.data == data) and \
                (type == -1 or type == c.type) and \
                (answ is None or c.answer == answ):
            if quest is None:
                result.append(c)
            else:
                if c.type == 0 and c.question == quest:
                    result.append(c)

    if elem == -1:
        return result
    elif 0 <= elem < len(result):
        return result[elem]
    else:
        return None


def codes_unique(codes):
    seen = []
    result = []
    idx = 0
    size = len(codes)
    for c in codes:
        print("Processing {} of {}".format(idx + 1, size))
        if not c.data in seen:
            seen.append(c.data)
            result.append(c)
        idx += 1
    return result


def codes_to_list(codes, field='data', sort=True, unique=True):
    result = list()
    for c in codes:
        if field == 'data':
            result.append(c.data)
        elif field == 'page':
            result.append(int(c.page))
        elif field == 'pdf_page':
            result.append(int(c.page))
    if unique:
        result = list(set(result))

    sort and result.sort()

    return result


def write_list(mylist, name):
    with open(name, 'w') as f:
        for item in mylist:
            f.write(str(item) + "\n")
    f.close()


def read_list(name, type=0):
    mylist = []
    with open(name, 'r') as f:
        for line in f:
            if type == 0:
                mylist.append(line.strip('\n'))
            else:
                mylist.append(int(line.strip('\n')))
    f.close()
    return mylist


def read_csv(table_path, table_name):
    try:
        df = pd.read_csv(table_path + os.sep + table_name, sep=',', header=None, dtype=object)
    except FileNotFoundError:
        # print("Skipping table '{}' (does not exist)".format(table_name))
        return None
    except pd.errors.EmptyDataError:
        # print("Skipping table '{}' (no data)".format(table_name))
        return None
    except pd.errors.ParserError:
        # print("Skipping table '{}' (parse error)".format(table_name))
        return None
    except Exception:
        # print("Skipping table '{}' (unknown error)".format(table_name))
        return None
    return df


def pix2np(pix):
    im = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
    im = np.ascontiguousarray(im[..., [2, 1, 0]])  # rgb to bgr
    return im


def read_user_answers(table_path, file):
    df = read_csv(table_path, file)
    if df is not None:
        user_answers = []
        (rows, cols) = df.shape
        for row in range(rows):
            exam = "{}{:03d}".format(df.loc[row, 0], int(df.loc[row, 1]))
            ans = 1
            for col in range(2, cols):
                if int(df.loc[row, col]) == 1:
                    data = "{}{:02d}{:1d}".format(exam, math.floor((col - 2) / 4) + 1, ans)
                    user_answers.append(data)
                ans = ans + 1 if ans < 4 else 1
        return user_answers
    else:
        return None


# returns
def code_fields_from_data(data, cast_exam=int, cast_quest=int, cast_answer=int):
    if data.isnumeric:
        return cast_exam(data[0:9]), cast_quest(data[9:11]), cast_answer(data[11:12])
    else:
        return None, None, None, None


def codes_print(codes):
    for c in codes:
        print("code:", c.data, "exam:", c.exam, "page:", c.page, "pdf_page:", c.pdf_page, "type:", c.type, "quest:", c.question, "answ", c.answer, "size:", c.x,
              c.y, c.w, c.h)


def strip(text, base):
    return "'" + text[len(base) + 1:] + "'"
