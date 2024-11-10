#!/usr/bin/env python
from __future__ import print_function
import json as jjson
import argparse
import csv
import multiprocessing
import os.path
import re
import secrets
import shutil
import string
import sys
import threading
import warnings
from os import listdir
from random import randint
from threading import Lock

import pymupdf as fitz
import gspread
import pyminizip

from qrgrader.python.support import *

def main():

    warnings.filterwarnings("ignore", category=DeprecationWarning)

    from pydrive.drive import GoogleDrive

    from pydrive.auth import GoogleAuth

    secrets_path = os.path.dirname(os.path.realpath(__file__)) + os.sep + "client_secrets.json"
    credentials_path = os.path.dirname(os.path.realpath(__file__)) + os.sep + "credentials.txt"
    GoogleAuth.DEFAULT_SETTINGS['client_config_file'] = secrets_path

    def join_pages(jpg_files, date, ex):
        doc = fitz.open()
        jpg_files.sort()

        for f in jpg_files:
            # Open JPG image
            img = fitz.open(os.path.join(jpg_dir, f))
            pdfbytes = img.convert_to_pdf()
            img.close()

            # Create PDF page and add to PDF document
            imgPDF = fitz.open("pdf", pdfbytes)
            page = doc.new_page()  # width=rect.width/4.16, height=rect.height/4.16)
            page.show_pdf_page(fitz.Rect(0, 0, 595.28, 842), imgPDF, 0)  # image fills the page
            # page.insert_image(rect=fitz.Rect(0,0,595.28,841.89), filename=os.path.join(jpg_dir, f))
            imgPDF.close()

        doc.save(os.path.join(dir_publish, date + ex + ".pdf"))


    def iter_pd(df):
        for val in df.columns:
            yield val
        for row in df.to_numpy():
            for val in row:
                if pd.isna(val):
                    yield ""
                else:
                    yield val


    def pandas_to_sheets(pandas_df, sheet, clear=False, corner="A1"):
        # Updates all values in a workbook to match a pandas dataframe
        if clear:
            sheet.clear()
        (row, col) = pandas_df.shape

        (a, b) = gspread.utils.a1_to_rowcol(corner)
        a = a - 2
        b = b - 1

        cells = sheet.range((corner + ":{}").format(gspread.utils.rowcol_to_a1(row + 1 + a, col + b)))
        #    print((corner+":{}").format(gspread.utils.rowcol_to_a1(row + 1 + a, col + b)))
        #    for cell, val in zip(cells, iter_pd(pandas_df)):
        i = 0
        j = 0
        for cell in cells:
            #        print(i,j)
            cell.value = pandas_df.loc[i, j]
            j = j + 1
            if j >= col:
                j = 0
                i = i + 1

            #        cell.value = val
        sheet.update_cells(cells, value_input_option='USER_ENTERED')


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


    def ask_user(text):
        reply = input(text + " ")
        return len(reply) == 0 or reply[0] == 'y' or reply[0] == 'Y'


    def get_pnc_orientation(page_number_code, shape):
        if page_number_code is not None:
            sw = page_number_code.x < shape[0] / 2 and page_number_code.y > shape[1] / 2
            nw = page_number_code.x < shape[0] / 2 and page_number_code.y < shape[1] / 2
            se = page_number_code.x > shape[0] / 2 and page_number_code.y > shape[1] / 2
            ne = page_number_code.x > shape[0] / 2 and page_number_code.y < shape[1] / 2
            return [sw, nw, se, ne]
        else:
            return [0, 0, 0, 0]


    def rotate(page_number_code, orig, codes):
        if page_number_code is not None:
            if page_number_code.type == 1:
                sw = page_number_code.x < orig.shape[0] / 2 and page_number_code.y > orig.shape[1] / 2
                nw = page_number_code.x < orig.shape[0] / 2 and page_number_code.y < orig.shape[1] / 2
                se = page_number_code.x > orig.shape[0] / 2 and page_number_code.y > orig.shape[1] / 2
                ne = page_number_code.x > orig.shape[0] / 2 and page_number_code.y < orig.shape[1] / 2
            else:
                ne = page_number_code.x < orig.shape[0] / 2 and page_number_code.y > orig.shape[1] / 2
                se = page_number_code.x < orig.shape[0] / 2 and page_number_code.y < orig.shape[1] / 2
                nw = page_number_code.x > orig.shape[0] / 2 and page_number_code.y > orig.shape[1] / 2
                sw = page_number_code.x > orig.shape[0] / 2 and page_number_code.y < orig.shape[1] / 2

            # TODO: WARNING
            if (sw):
                orig2 = cv2.rotate(orig, cv2.ROTATE_180)
                # print("rot:180")
                for c in codes:
                    cx, cy = c.x, c.y
                    c.x = int(orig.shape[1] - c.h + cx * math.cos(math.pi) - cy * math.sin(math.pi))
                    c.y = int(orig.shape[0] - c.w + cx * math.sin(math.pi) + cy * math.cos(math.pi))
            elif (se):
                # print("rot:90CCW")
                orig2 = cv2.rotate(orig, cv2.ROTATE_90_COUNTERCLOCKWISE)
                for c in codes:
                    cx, cy = c.x, c.y
                    c.x = int(cx * math.cos(-math.pi / 2) - cy * math.sin(-math.pi / 2))
                    c.y = orig.shape[1] + int(cx * math.sin(-math.pi / 2) + cy * math.cos(-math.pi / 2) - c.h)
            elif (nw):
                # print("rot:180CW")
                orig2 = cv2.rotate(orig, cv2.ROTATE_90_CLOCKWISE)
                for c in codes:
                    cx, cy = c.x, c.y
                    c.x = orig.shape[0] + int(cx * math.cos(math.pi / 2) - cy * math.sin(math.pi / 2) - c.w)
                    c.y = int(cx * math.sin(math.pi / 2) + cy * math.cos(math.pi / 2))
            else:
                # print("rot:None")
                orig2 = orig
        else:
            orig2 = orig

        return orig2


    def get_delta(c, pnc_up=None, pnc_dw=None, pnc_native_up=None, pnc_native_dw=None):
        delta_x_up = 0
        delta_y_up = 0
        if pnc_up is not None:
            delta_x_up = pnc_up.x - pnc_native_up.x
            delta_y_up = pnc_up.y - pnc_native_up.y

        if pnc_dw is not None:
            delta_x_dw = pnc_dw.x - pnc_native_dw.x
            delta_y_dw = pnc_dw.y - pnc_native_dw.y

        # mark_one(c, orig, int(delta_x_up), int(delta_y_up), a, b, 1)

        if pnc_up is not None and pnc_dw is not None:
            delta_x = (c.y - pnc_up.y) * (delta_x_dw - delta_x_up) / (pnc_dw.y - pnc_up.y) + delta_x_up
            delta_y = (c.x - pnc_up.x) * (delta_y_dw - delta_y_up) / (pnc_dw.x - pnc_up.x) + delta_y_up
        elif pnc_up is not None:
            delta_x = delta_x_up
            delta_y = delta_y_up
        elif pnc_dw is not None:
            delta_x = delta_x_dw
            delta_y = delta_y_dw
        else:
            delta_x = 0
            delta_y = 0
        return delta_x, delta_y


    def mark(codes, orig, pnc_up=None, pnc_dw=None, pnc_native_up=None, pnc_native_dw=None, a=0, b=0, monochrome=False):
        # Tries to align QRs
        delta_x_up = 0
        delta_y_up = 0
        if pnc_up is not None:
            delta_x_up = pnc_up.x - pnc_native_up.x
            delta_y_up = pnc_up.y - pnc_native_up.y

        if pnc_dw is not None:
            delta_x_dw = pnc_dw.x - pnc_native_dw.x
            delta_y_dw = pnc_dw.y - pnc_native_dw.y

        for c in codes:
            # mark_one(c, orig, int(delta_x_up), int(delta_y_up), a, b, 1)

            if pnc_up is not None and pnc_dw is not None:
                delta_x = (c.y - pnc_up.y) * (delta_x_dw - delta_x_up) / (pnc_dw.y - pnc_up.y) + delta_x_up
                delta_y = (c.x - pnc_up.x) * (delta_y_dw - delta_y_up) / (pnc_dw.x - pnc_up.x) + delta_y_up
            elif pnc_up is not None:
                delta_x = delta_x_up
                delta_y = delta_y_up
            elif pnc_dw is not None:
                delta_x = delta_x_dw
                delta_y = delta_y_dw
            else:
                delta_x = 0
                delta_y = 0

            return mark_one(c, orig, int(delta_x), int(delta_y), a, b, monochrome=monochrome)


    def mark_one(m, orig, delta_x=0, delta_y=0, a=0, b=0, k=0, monochrome=False):
        if monochrome:
            color = (255, 0, 0)
        elif m.type == 0:
            green = (len(correct_answer) > 1 and 0 <= (m.question - 1) < len(correct_answer)) or \
                    (len(correct_answer) == 1 and int(m.answer) == int(correct_answer))
            if green:
                color = (0, 255, 0)
            else:
                color = (0, 0, 255)
        else:
            if k == 0:
                color = (255, 0, 0)
            else:
                color = (255, 255, 0)
        if orig is not None:
            cv2.rectangle(orig, (delta_x + m.x - a, m.y - b + delta_y),
                          (delta_x + m.x + m.w + a, m.y + m.h + b + delta_y), color, 8)
        else:
            return (delta_x + m.x - a, m.y - b + delta_y), (delta_x + m.x + m.w + a, m.y + m.h + b + delta_y), color


    # def direxist(dir, parent="."):
    #    dirs = [f for f in listdir(parent)]
    #    return dir in dirs

    def direxist(path):
        return os.path.isdir(path)


    parser = argparse.ArgumentParser(description='Patching and detection')

    parser.add_argument('-A', '--Annotation', type=str, help='Annotate files and flatten (all|answers|correct)', default=None)
    parser.add_argument('-a', '--annotation', type=str, help='Annotate files (all|answers|correct)', default=None)
    parser.add_argument('-B', '--first-page', type=int, help='First page to be processed (default: 1)', default=1)
    parser.add_argument('-C', '--correct', help='Specify correct answer for annotation (default: A) (may be string of answers: ABBACDC...)', default="A")
    parser.add_argument('-c', '--cleanup', help='Clear pool files', action='store_true')
    parser.add_argument('-d', '--dpi', type=float, help='Input file DPI (default: 400)', default=400)
    parser.add_argument('-D', '--debug',
                        help='Debug type (1: write recognized patches, 2: write all patches, 4: draw patches)', default=0)
    parser.add_argument('-E', '--last-page', type=int, help='Last page to be processed (default: last)', default=-1)
    parser.add_argument('-f', '--filename', default=None, help='File to process', nargs="+")
    parser.add_argument('-F', '--format', help='Last exam format as DDDDDDEEEQQA (e.g. 211025300144)', default=None)
    parser.add_argument('-g', '--generated-from-pdf', default=False, help='Specify generated.txt file location', action='store_true', )
    parser.add_argument('-i', '--fix', type=str, help='Additional correct answers format: qn=a,qn=a...(ex: 1=A,1=B,2=C)', default=None)
    parser.add_argument('-j', '--threads', help='Disable parallel execution', type=int, default=8)
    parser.add_argument('-k', '--generate-feedback', help='Generate feedback csv file', action='store_true')
    parser.add_argument('-K', '--use-updated-raw', help='Use updated RAW', default=False, action='store_true')
    parser.add_argument('-l', '--get-files-gid', help='Export Google Drive files id', default=None)
    parser.add_argument('-n', '--native-pdf', help='Input file is native PDF', action='store_true',
                        default=False)
    parser.add_argument('-N', '--shrink', help='Ratio with which the PDF has been shrinked when printed', default=1.0, type=float)
    parser.add_argument('-p', '--process', help='Process PDF Files', action='store_true',
                        default=False)
    parser.add_argument('-P', '--disable-patches', help='Disable patches analysis', action='store_true',
                        default=False)
    # parser.add_argument('-r', '--reconstruct-exams', help='Reconstruct exams in PDF files', action='store_true')
    parser.add_argument('-R', '--resize', type=float, help='Resize percent', default=30.0)
    parser.add_argument('-s', '--size', type=int, help='Code size (mm)', default=8)
    parser.add_argument('-t', '--tolerance', type=float, help='Patch size tolerance percent', default=0.25)
    parser.add_argument('-T', '--threshold', nargs="+", help='Thresholding values (default: {50, 55, 60, 65, 70, 75, 80}, 0: no thresholding)',
                        default={50, 55, 60, 65, 70, 75, 80})
    parser.add_argument('-u', '--upload', help='gid of the directory to upload the files to (forces -l)', default=None)
    parser.add_argument('-U', '--update-raw', help='Download updated raw table', default=None)
    parser.add_argument('-v', '--verbose', help='Show extra data (with duplicates)', action='store_true')
    parser.add_argument('-w', '--workbook', help='Google sheet workbook to upload the table to', default=None)
    parser.add_argument('-W', '--table', help='Only upload this table (matching *name*)', default=None)
    parser.add_argument('-x', '--show', help='Show result', action='store_true', default=False)
    parser.add_argument('-y', '--yes', help='Yes to all questions', action='store_true', default=False)
    parser.add_argument('-Z', '--zip-encode-file', help='Create encrypted zip file', action='store_true',
                        default=False)
    parser.add_argument('-M', '--use-temp-dir', help='Use /tmp directory for temp files', action='store_true', default=False)
    group = parser.add_argument_group("Methods (at least one)")
    group.add_argument('-z', '--zxing', help='Use ZXing', action='store_true')
    group.add_argument('-b', '--zbar', help='Use Zbar', action='store_true')
    group.add_argument('-S', '--simulate', help='Simulate using generated files', default=0, type=int)
    group.add_argument('-r', '--clear', help='Clear workspace', action='store_true')



    args = vars(parser.parse_args())

    exe_name = os.path.basename(sys.argv[0])
    dir_name = os.path.basename(os.getcwd())

    if re.match("qrgrading-[0-9][0-9][0-9][0-9][0-9][0-9]", dir_name) is None:
        print("ERROR: {} must be run in the root of the workspace".format(exe_name))
        sys.exit(0)

    use_zxing = args["zxing"]
    use_zbar = args["zbar"]
    use_debug = int(args["debug"])
    debug_path = "debug"
    dpi = args["dpi"]
    ppm = dpi / 25.4
    size_mm = args["size"]
    filename = args["filename"]
    verbose = args["verbose"]
    tolerance = args["tolerance"]
    resize = args["resize"] / 100.0
    show = args["show"]
    workbook = args["workbook"]
    exam_format = args["format"]
    zip_encode = args["zip_encode_file"]
    yes = args["yes"]
    correct_answer = args["correct"]
    first_page = args["first_page"]
    last_page = args["last_page"]
    reconstruct_exams = False
    generate_feedback = args["generate_feedback"]
    upload = args["upload"]
    get_files_gid = args["get_files_gid"]
    is_native_pdf = args["native_pdf"]
    update_raw = args["update_raw"]
    shrink = args["shrink"]
    generated_from_pdf = args["generated_from_pdf"]
    process = args["process"]
    table_to_upload = args["table"]
    use_parallel = args["threads"]
    use_patches = not args["disable_patches"]
    thresholds = {int(n) for n in args["threshold"]}
    cleanup = args["cleanup"]
    clear = args["clear"]
    user_temp_dir = args["use_temp_dir"]
    fix = args["fix"]
    simulate = args["simulate"]



    # Setting up directories
    base = os.getcwd()
    dir_publish = base + os.sep + "results" + os.sep + "publish"
    dir_xls = base + os.sep + "results" + os.sep + "xls"
    dir_detected = base + os.sep + "scanned" + os.sep + "detected"

    if generated_from_pdf:
        if user_temp_dir:
            pool_dir = "/tmp/qgrading" + os.sep + "generated" + os.sep + "pool"
        else:
            pool_dir = base + os.sep + "generated" + os.sep + "pool"
    else:
        if user_temp_dir:
            pool_dir = "/tmp/qgrading" + os.sep + "scanned" + os.sep + "pool"
        else:
            pool_dir = base + os.sep + "scanned" + os.sep + "pool"

    output_dir = pool_dir + os.sep + "output"
    jpg_dir = pool_dir + os.sep + "jpg"


    def clear_workspace():
        makedir(base + os.sep + "scanned")
        #makedir(dir_xls)
        makedir(dir_publish)



    if cleanup:
        print("Cleaning pool directory")
        shutil.rmtree(pool_dir, ignore_errors=True)
        sys.exit(0)

    if clear:
        print("Cleaning workspace")
        clear_workspace()
        sys.exit(0)




    flatten = False

    annotations = args["annotation"]
    if annotations is None:
        annotations = args["Annotation"]
        if annotations is not None:
            flatten = True

    # Variables
    notified = False
    mutex = Lock()

    if process:
        generate_feedback = True
        reconstruct_exams = True
        annotations = "answers"

    if generated_from_pdf:
        process = True
        is_native_pdf = True
        generate_feedback = False

    if process and use_zxing is False and use_zbar is False:
        use_zxing = True

    if not process and not annotations \
            and workbook is None \
            and not reconstruct_exams \
            and not generate_feedback \
            and not zip_encode \
            and not upload \
            and not get_files_gid \
            and update_raw is None \
            and not cleanup\
            and not simulate\
            and not clear:
        parser.print_help()
        sys.exit(0)

    if upload is not None:
        get_files_gid = upload







    def clear_finished_processes(proc):
        for q in proc:
            if not q.is_alive():
                # q.terminate()
                proc.remove(q)


    def wait_lagging_processes(proc):
        for p in proc:
            if p.is_alive():
                p.join()


    allnative = None


    class Scanner(threading.Thread):
        def __init__(self, img, pdf_page):
            self.im = img.copy()
            self.pdf_page = pdf_page
            threading.Thread.__init__(self)

        def run(self):

            global allcodes
            try:
                date, exam, page, codes = scan_page(self.im, use_zxing, use_zbar, use_debug, debug_path, pool_dir, ppm,
                                                    size_mm, verbose, tolerance, thresholds, self.pdf_page, allnative)
                write_page_image(pool_dir, self.im, date, exam, page, self.pdf_page)

                # Mutex protected operation
                mutex.acquire()
                # codes_write(pool_dir + os.sep + "detected.txt", codes)
                allcodes.extend(codes)

                print("STEP: Done processing page {}/{} "
                      "(found {} unmarked answers)".format(self.pdf_page + 1,
                                                           end_page - begin_page,
                                                           len(set([q.data for q in codes if q.data[0].isdigit()]))))
                mutex.release()

            finally:
                threadLimiter.release()


    def read_native(filename, shrink=1.0):
        native_codes = codes_read(filename)

        if native_codes is not None:
            print("Read native codes from {} files ({} rows {})".format(strip(filename, base), len(native_codes), shrink))
            for c in native_codes:
                # WARNING: this scales the measurements as if it were taken on a dpi specified (400)
                if c.h == 0 and c.w == 0:
                    c.x = int(c.x / 65535 * 0.351459804 * ppm)
                    c.y = int(297 * ppm - int(c.y / 65535 * 0.351459804 * ppm))  # 297???
                    c.w = int(size_mm * ppm)
                    c.h = int(size_mm * ppm)

                '''
                if shrink != 1.0:
                    shrink = float(shrink)
                    c.x = int(c.x * shrink)
                    c.y = int(c.y * shrink)
                    c.w = int(c.w * shrink)
                    c.h = int(c.h * shrink)
                # print(c.data, c.x, c.y, c.w, c.h)
                '''
            return native_codes

        return None

    if simulate > 0:
        print("Simulation in progress ({} files)".format(simulate))
        clear_workspace()


        allnative = read_native(base + os.sep + "generated/qr/generated.txt", shrink)

        pdf_filenames = [f for f in listdir(base + os.sep + "generated/pdf/") if f.endswith(".pdf")]
        pdf_filenames.sort()

        for pdf_filename in pdf_filenames[0:simulate]:
            print("Marking random answers in {}".format(pdf_filename), end="\r")
            exam = pdf_filename[6:9]
            filtered = codes_filter_by(allnative, exam=exam)
            document = fitz.open(base + os.sep + "generated/pdf/" + pdf_filename)
            for i, page in enumerate(document):
                filtered2 = [f2 for f2 in filtered if f2.page == i+1]
                questions = set([q.question for q in filtered2])

                for question in questions:

                    qrs = [q for q in filtered2 if q.question == question]

                    for qr in qrs:
                        if qr.answer == randint(1,4):
                            div = dpi/72.0
                            x = qr.x/ div
                            y = qr.y/ div - 12
                            w = qr.w/ div
                            h = qr.h/ div
                            annot = page.add_redact_annot(fitz.Rect(x, y, x + w, y + h), fill=(0,0,0), cross_out=False)
                            break
                page.apply_redactions()
            document.save(base + os.sep + "scanned/" + pdf_filename)
            document.close()
        print("\nSimulation done.\n")
        process = True
        is_native_pdf = True
        generated_from_pdf = False
        generate_feedback = True
        reconstruct_exams = True
        annotations = "answers"
        use_zxing = True

    allcodes, allseen = [], []

    if process:
        if filename is None:
            if generated_from_pdf:
                filename = ["generated" + os.sep + "pdf" + os.sep + x for x in listdir(base + os.sep + "generated" + os.sep + "pdf") if x.endswith(".pdf")]
            else:
                filename = ["scanned" + os.sep + x for x in listdir(base + os.sep + "scanned") if x.endswith(".pdf")]

        print("Processing files: ")
        for f in filename:
            print(f)
        print()

        # Prepares pool and output dirs
        makedir(pool_dir)
        makedir(output_dir)
        makedir(dir_detected, False)

        if not generated_from_pdf:
            allnative = read_native(base + os.sep + "generated/qr/generated.txt", shrink)

        # This starts n parallel scan_page processes
        for fname in filename:
            proc = []
            doc = fitz.open(fname)

            begin_page = first_page - 1
            end_page = last_page if last_page > 0 else len(doc)

            print("INFO: Processing {}, {} pages document".format(fname, end_page - begin_page))

            threadLimiter = multiprocessing.BoundedSemaphore(use_parallel)

            for pdf_page in range(begin_page, end_page):
                mat = matrix = fitz.Matrix(dpi / 72, dpi / 72)
                pix = doc[pdf_page].get_pixmap(matrix=mat)  # render page to an image

                im = pix2np(pix)

                # Ant slot for another Thread?
                threadLimiter.acquire()

                # Yes, clear the threads that left the spot (they must have finished)
                clear_finished_processes(proc)

                # Launch Another Thread
                p = Scanner(im, pdf_page)
                p.start()
                proc.append(p)

            doc.close()
            wait_lagging_processes(proc)

        if generated_from_pdf:
            codes_write(base + os.sep + "generated" + os.sep + "qr" + os.sep + "generated.txt", allcodes, "w")
        else:
            codes_write(dir_detected + os.sep + "detected.txt", allcodes, "w")

        allseen = codes_to_list(allcodes)

    else:
        detected_file = dir_detected + os.sep + "detected.txt"
        if os.path.isfile(detected_file):
            allcodes = codes_read(detected_file)
            allseen = codes_to_list(allcodes)
        else:
            print("Can't open file {}, have you processed the input files (option -p)?".format(strip(detected_file, base)))
            sys.exit(1)

    # WARNING: PATCH FOR NEW NIA QRs that start with N
    allseen = [a.replace('N', '@') for a in allseen]

    # Extract questions in format DDDDDDEEEQQA (discard pages and NIAs QRs)
    questions = set([q[0:12] for q in allseen if q[0].isdigit()])

    dates, exams, quest, answr = set(), set(), set(), set()

    # If specified format, extract limits
    if exam_format is not None:
        ok_date = exam_format[0:6]
        max_exam = int(exam_format[6:9])
        max_qust = int(exam_format[9:11])
        max_aswr = int(exam_format[11])

    for q in questions:
        try:
            date = q[0:6]
            exam = q[6:9]
            qust = q[9:11]
            aswr = q[11]
        except:
            print("WARNING: Incorrect data, discarding", q)
            continue

        if exam_format is not None and (
                ok_date != date or int(exam) > max_exam or int(qust) > max_qust or int(aswr) > max_aswr):
            print("WARNING: Incorrect data, date: {}, exam: {}, quest: {}, answer: {}".format(date, exam, qust, aswr))
        else:
            dates.add(date)
            exams.add(exam)
            quest.add(int(qust))
            answr.add(int(aswr))

    dates = list(dates)
    exams = list(sorted(exams))

    if not quest:
        print("ERROR: No questions have been found, exiting.")
        sys.exit(1)

    nquest = max(quest)
    nanswr = max(answr)
    date = dates[0]

    if generate_feedback:

        # Create grades-mat matrix
        ones = 0
        grades_csv_path = dir_xls + os.sep + "{}_raw.csv".format(date)
        grades_csv = open(grades_csv_path, 'w+')
        for ex in exams:
            grades_csv.write(date + "," + ex),
            for quest in range(nquest):
                for answr in range(nanswr):
                    key = "" + date + ex + "{:02d}".format(quest + 1) + "{:01d}".format(answr + 1)
                    if key in questions:
                        grades_csv.write(",0")
                    else:
                        grades_csv.write(",1")
                        ones = ones + 1
            grades_csv.write("\n")

        print(
            "INFO: Read {} QRs, {} unique. Found {} exams, {} questions and {} possile answers per question".format(
                len(questions), ones, len(exams), nquest, nanswr))
        print("STEP: Creating file {}".format(strip(grades_csv.name, base)))

        grades_csv.close()

        # NIA: Format @210826 030 1 2

        nia_csv_path = dir_xls + os.sep + "{}_nia.csv".format(date)
        nia_csv = open(nia_csv_path, 'w+')

        print("STEP: Creating file {}".format(strip(nia_csv.name, base)))

        nias = [q for q in allseen if q.startswith('@')]

        for ex in exams:
            nia = ""
            # First row
            row_elements = []
            for figure in [5, 6, 7, 8, 9]:
                key = "@" + date + ex + "{:01d}".format(0) + "{:01d}".format(figure)
                if key not in nias:
                    row_elements.append(figure)

            if len(row_elements) == 1:
                nia = nia + str(row_elements[0])
            else:
                nia = nia + 'X'

            # Rest of rows
            for row in range(1, 6):
                row_elements = []
                for figure in range(0, 10):
                    key = "@" + date + ex + "{:01d}".format(row) + "{:01d}".format(figure)
                    if key not in nias:
                        row_elements.append(figure)

                if len(row_elements) == 1:
                    nia = nia + str(row_elements[0])
                else:
                    nia = nia + 'X'

            examid = date + ex
            nia_csv.write(examid + "," + nia + "\n")

        nia_csv.close()


    class Reconstructor(threading.Thread):
        notified = False

        def __init__(self, date, ex):
            self.date = date
            self.ex = ex
            threading.Thread.__init__(self)

        def get_pnc(self, codes):
            pnc = None
            for c in codes:
                if c.type == 1:
                    pnc = c
                    break
            return pnc

        def run(self):

            jpg_files = []
            codes_of_this_exam = codes_filter_by(allcodes, date=self.date, exam=self.ex)
            pages = codes_to_list(codes_of_this_exam, field='page')
            for page in pages:

                # Read PNG image of the page
                if page != 0:
                    orig = cv2.imread(pool_dir + os.sep + "page-{}-{}-{:03d}.png".format(self.date, self.ex, page))
                    # print(pool_dir + os.sep + "page-{}-{}-{:03d}.png".format(self.date, self.ex, page))
                else:
                    page0 = codes_filter_by(codes_of_this_exam, date=self.date, exam=self.ex, page=0)
                    orig = cv2.imread(pool_dir + os.sep + "page-{}-{}-{:03d}-{:d}.png".format(self.date, self.ex, page,
                                                                                              page0[0].pdf_page))

                # Get page Codes
                codes = codes_filter_by(allcodes, date=self.date, exam=self.ex, page=page)

                # Get page number codes (either type 1 or 5) (needed to rotate image)
                pnc_up = codes_filter_by(codes, type=1, elem=0)
                pnc_dw = codes_filter_by(codes, type=5, elem=0)
                pnc = pnc_up if pnc_up is not None else pnc_dw

                # Rotate image AND codes according to pnc
                orig = rotate(pnc, orig, codes)

                # Finally resize page
                if resize != 1.0:
                    orig = cv2.resize(orig, (int(orig.shape[1] * resize), int(orig.shape[0] * resize)),
                                      interpolation=cv2.INTER_AREA)

                # And write the JPG images
                jpg_file = "page-{}-{}-{:03d}.jpg".format(self.date, self.ex, page)
                cv2.imwrite(jpg_dir + os.sep + jpg_file, orig)
                jpg_files.append(jpg_file)

            try:
                # Join these pages
                join_pages(jpg_files, self.date, self.ex)
            finally:
                threadLimiter.release()


    def n2a(n, b=string.ascii_uppercase):
        d, m = divmod(n, len(b))
        return n2a(d - 1, b) + b[m] if d else b[m]


    if update_raw is not None:
        print("Downloading updated '{}_raw' table from workbook {}".format(date, update_raw))
        gc = gspread.service_account()
        sh = gc.open(update_raw)
        try:
            ws = sh.worksheet("{}_raw".format(date))
        except:
            print("Table do not exist, exiting")
            sys.exit(0)

        f = open(dir_xls + os.sep + "{}_raw.fix".format(date), "w")
        writer = csv.writer(f)
        # print("G8:{}{}".format(n2a(nquest * 4 + 7), 7 + len(exams)))
        writer.writerows(ws.get_values("G8:{}{}".format(n2a(int(nquest * 4) + 7), 8 + len(exams))))
        f.close()
        print("Done.")
        sys.exit(0)

    if reconstruct_exams:

        # Extract all the QRs seen during the scan, generate files
        if not direxist(pool_dir):
            print("Can't find " + strip(pool_dir, base) + " directory. Have you processed the input files (option -p)?")
            sys.exit()

        if allnative is None:
            allnative = read_native(base + os.sep + "generated/qr/generated.txt", shrink)

        print("STEP: Joining exams pages")

        # Create needed JPG directory
        makedir(jpg_dir)

        threadLimiter = multiprocessing.BoundedSemaphore(use_parallel)

        cnt = 1
        proc = []

        for ex in exams:
            # Any free slot for another process?
            threadLimiter.acquire()

            # Yes, so some process must be finished, clear it to avoit "too many files open" error
            clear_finished_processes(proc)

            # Launch another Thread
            p = Reconstructor(date, ex)
            proc.append(p)
            p.start()

            # Update Info
            print("INFO: Reconstructing exam {} ({} of {})".format(ex, cnt, len(exams)), end='\r')
            cnt = cnt + 1

        # All thread launched, wait for those not cleared (the last ones to terminate)
        wait_lagging_processes(proc)

        # rewrite the code in case they have been rotated during reconstruction
        codes_write(base + os.sep + "scanned/detected/detected.txt".format(date), allcodes, "w")

        if listdir(pool_dir + os.sep + "unrecognized"):
            print("WARNING: Folder 'unrecognized' is not empty.")

        print("Done.")

    if annotations is not None:
        if allnative is None:
            allnative = read_native(base + os.sep + "generated/qr/generated.txt", shrink)

        print("STEP: Annotating exams")

        cnt = 1
        proc = []

        user_answers = read_user_answers(dir_xls, "{}_raw.fix".format(date))
        if user_answers is not None:
            print("Read user answers from '{}_raw.fix' ({} answers)".format(date, len(user_answers)))
        else:
            user_answers = read_user_answers(dir_xls, "{}_raw.csv".format(date))
            if user_answers is not None:
                print("Read user answers from '{}_raw.csv' ({} answers)".format(date, len(user_answers)))
            else:
                print("User answers not available, skipping annotations.")
                reconstruct_exams = 0

        page_ratio = shrink

        fixes = {}
        for elem in fix.split(",") if fix is not None else []:
            qn, a = elem.split("=")
            qn = int(qn)
            if fixes.get(qn, None) is None:
                fixes[qn] = []
            fixes[qn].append(ord(a.lower()) - 96)

        for ex in exams:

            print("INFO: Annotating exam {} ({} of {})".format(ex, cnt, len(exams)), end='\r')

            codes_of_this_exam = codes_filter_by(allcodes, date=date, exam=ex)
            pages = codes_to_list(codes_of_this_exam, field='page')
            doc = fitz.open("results/publish/" + date + ex + ".pdf")

            xml_data = {}

            # for each page we have
            for i in pages:
                page = doc[i - 1]

                xml_data[i-1] = []
                xml_list = xml_data[i-1]
                # Remove annotations
                doc.xref_set_key(page.xref, "Annots", "[]")

                # annots = page.
                # for annot in annots:

                codes_this_page = codes_filter_by(allcodes, date=date, exam=ex, page=i)
                native_this_page = codes_filter_by(allnative, date=date, exam=ex, page=i)

                # Extract Page QR (scanned)
                pnc_up = codes_filter_by(codes_this_page, type=1, elem=0)
                pnc_dw = codes_filter_by(codes_this_page, type=5, elem=0)

                # codes_print([pnc_up, pnc_dw])

                # Extract Page QR (native)
                pnc_native_up = codes_filter_by(native_this_page, type=1, elem=0)
                pnc_native_dw = codes_filter_by(native_this_page, type=5, elem=0)

                if pnc_up is not None and pnc_dw is not None and pnc_native_up is not None and pnc_native_dw is not None:
                    page_native_height = abs(pnc_native_up.y - pnc_native_dw.y)
                    page_height = abs(pnc_up.y - pnc_dw.y)
                    page_ratio = page_height/page_native_height

                if page_ratio != 1.0:
                    for c in native_this_page:
                        c.x = c.x * page_ratio
                        c.y = c.y * page_ratio
                        c.w = c.w * page_ratio
                        c.h = c.h * page_ratio

                    # Recompute after shrinking
                    pnc_native_up = codes_filter_by(native_this_page, type=1, elem=0)
                    pnc_native_dw = codes_filter_by(native_this_page, type=5, elem=0)


                # codes_print([pnc_native_up, pnc_native_dw])
                # sys.exit()

                for c in native_this_page:

                     #c = Code(cc.type, cc.data, cc.x * page_ratio, cc.y * page_ratio, cc.w * page_ratio, cc.h * page_ratio, cc.page, cc.pdf_page)

                     if annotations is not None and c.type == 0:
                        aa = ppm * 210 / 595  # the page 595 points wide
                        bb = 0
                        dx, dy = get_delta(c, pnc_up, pnc_dw, pnc_native_up, pnc_native_dw)
                        # dx, dy = 0,0
                        r = fitz.Rect((c.x + dx) / aa+bb, (c.y + dy) / aa+bb, (c.x + dx) / aa + c.w / aa -bb, (c.y + dy) / aa + c.h / aa - bb)

                        annot = page.add_rect_annot(r)  # 'Square'
                        annot.set_border(width=3)
                        annot.set_name(c.data)

                        opacity = 0.999
                        if annotations.lower() == "transparent":
                            color = (0, 0, 0)
                            opacity = 0

                        elif annotations.lower() == "all":
                            color = (0, 0, 1)

                        elif annotations.lower() == "answers":
                            color = (1, 0, 0)
                            if c.answer in fixes.get(c.question, []):
                                color = (0, 1, 0)
                            elif len(correct_answer) == 1 and c.answer == ord(correct_answer.lower()) - 96:
                                color = (0, 1, 0)
                            elif len(correct_answer) > 1:
                                if int(c.question) > len(correct_answer):
                                    print("*** ERROR: Not enough data for option -C, exiting.")
                                    sys.exit(2)
                                if ord(correct_answer[c.question - 1].lower()) - 96 == c.answer:
                                    color = (0, 1, 0)
                            if c.data not in user_answers:
                                color = (1, 1, 1)
                                #opacity = 0

                        elif annotations.lower() == "detected":
                            color = (0, 1, 1)
                            if c.data in user_answers:
                                opacity = 0

                        elif annotations.lower() == "correct":
                            color = (0, 1, 0)
                            if c.answer != ord(correct_answer[c.question-1].lower()) - 96:
                                opacity = 0

                        else:
                            print("*** ERROR: Incorrect parameter for option -a (options: 'all' or 'answers'). Exiting.")
                            sys.exit(3)

                        annot.set_colors(stroke=color)

                        flags = annot.flags
                        flags |= fitz.PDF_ANNOT_IS_LOCKED
                        flags |= fitz.PDF_ANNOT_IS_READ_ONLY
                        annot.set_flags(flags)
                        annot.update(opacity=opacity)

                        xml_list.append({"name": c.data, "x": c.x, "y": c.y, "w": c.w, "h": c.h})

                doc[i - 1].apply_redactions()

            doc.set_xml_metadata(jjson.dumps(xml_data))

            if flatten:
                pdfbytes = doc.convert_to_pdf()
                doc = fitz.open("pdf", pdfbytes)

            doc.save("results/publish/" + date + ex + ".pdf", incremental=not flatten, encryption=fitz.PDF_ENCRYPT_KEEP)
            cnt = cnt + 1
        print()

    if zip_encode:
        print("STEP: Compressing and encoding files")
        pwd_csv = open(dir_xls + os.sep + "{}_pwd.csv".format(date), 'w+')
        zip_encoded = {}

        # Compress files
        for ex in exams:
            examid = date + ex
            pwd = secrets.token_urlsafe(10)
            zip_encoded[examid] = pwd
            pwd_csv.write(examid + "," + pwd + "\n")

        enc_dir = makedir(dir_publish + os.sep + "encrypted")
        pdf_files = [f.__str__().replace(".pdf", "") for f in listdir(dir_publish) if f.endswith('.pdf')]
        for f in pdf_files:
            print("INFO: Compressing and encoding exam", f, "with password", zip_encoded[f])
            pyminizip.compress(dir_publish + os.sep + f + ".pdf", None, enc_dir + os.sep + f + ".zip", zip_encoded[f],
                               int(1))
        print("Done.")

    # Upload data
    if upload is not None or get_files_gid is not None:

        gauth = GoogleAuth()
        # gauth.flow.params.update({'approval_prompt': 'force'})
        gauth.LoadCredentialsFile(credentials_path)

        if gauth.credentials is None:
            gauth.GetFlow()
            # gauth.flow.params.update({'access_type': 'offline'})
            gauth.flow.params.update({'approval_prompt': 'force'})
            gauth.LocalWebserverAuth()
        elif gauth.access_token_expired:
            gauth.Refresh()
        else:
            gauth.Authorize()

        gauth.SaveCredentialsFile(credentials_path)
        drive = GoogleDrive(gauth)

        # NOTE: get_files_gid is not none if -l OR -u switches are used

        if upload:
            fileList = drive.ListFile({'q': "'" + upload + "' in parents and trashed=false"}).GetList()
            existent = [f['title'] for f in fileList]
            pdf_files = [f.__str__() for f in listdir(dir_publish) if f.endswith('.pdf')]

            for f in pdf_files:
                if f in existent:
                    print("File", f, "already present")
                else:
                    print("Uploading file", f)
                    file = drive.CreateFile({"mimeType": "application/pdf", "title": f,
                                             "parents": [{"kind": "drive#fileLink", "id": upload}]})
                    file.SetContentFile(dir_publish + os.sep + f)
                    file.Upload()

        if get_files_gid is not None:
            fileList = drive.ListFile({'q': "'" + get_files_gid + "' in parents and trashed=false"}).GetList()
            if date is not None:
                pdf_csv = open(dir_xls + os.sep + "{}_pdf.csv".format(date), 'w+')
            else:
                pdf_csv = open("date_pdf.csv", 'w+')

            print("Writing file", pdf_csv.name)
            cnt = 0
            for f in fileList:
                if f['title'].endswith(".pdf"):
                    examid = f['title'].replace(".pdf", "")
                    fgid = f['id']
                    pdf_csv.write(examid + "," + fgid + "\n")
                    cnt = cnt + 1
            pdf_csv.close()
            print("Written {} rows. Done.".format(cnt))

    if workbook is not None:

        def upload_table(table_name, sep=","):

            try:
                df = pd.read_csv(dir_xls + os.sep + table_name + ".csv", sep=sep, header=None, dtype=object)
            except FileNotFoundError:
                print("Skipping table '{}' (does not exist)".format(table_name))
                return
            except pd.errors.EmptyDataError:
                print("Skipping table '{}' (no data)".format(table_name))
                return
            except pd.errors.ParserError:
                print("Skipping table '{}' (parse error)".format(table_name))
                return
            except Exception:
                print("Skipping table '{}' (unknown error)".format(table_name))
                return

            try:
                newsheet = sh.worksheet(table_name)
                ok = yes or ask_user("INFO: Table '{}' exists. Overwrite (y/n)?".format(table_name))
            except:
                newsheet = sh.add_worksheet(title=table_name, rows=df.shape[0], cols=df.shape[1])
                ok = True

            if ok:
                print("STEP: Uploading table '{}'".format(table_name))
                pandas_to_sheets(df, newsheet)


        print("STEP: Uploading results to workbook {}".format(workbook))

        gc = gspread.service_account()
        #print(gc)
        sh = gc.open(workbook)
        print("STEP: Opened workbook {}".format(workbook))

        tables = [f.replace(".csv", "") for f in listdir(dir_xls) if f.endswith('.csv')]
        if table_to_upload is not None:
            tables = [f for f in tables if table_to_upload in f]

        for table in tables:
            if "_questions" in table:
                upload_table(table, sep="\t")
            else:
                upload_table(table)
        print("Done.")



    print("All Done :)")


if __name__ == "__main__":
    main()
