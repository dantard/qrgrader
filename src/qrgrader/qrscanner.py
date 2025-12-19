import argparse
import os
import shutil
import sys
import time
from itertools import accumulate
from multiprocessing import Manager, Pool, Process
from random import randint

import cv2
import pandas as pd
import pymupdf
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QGraphicsRectItem
from pymupdf.mupdf import PDF_ENCRYPT_KEEP

from qrgrader.code import Code
from qrgrader.code_set import CodeSet, PageCodeSet
from qrgrader.common import check_workspace, get_workspace_paths, get_temp_paths, Generated, Questions, get_date, Nia, \
    StudentsData
from qrgrader.page_processor import PageProcessor
from qrgrader.utils import makedir


def main():
    parser = argparse.ArgumentParser(description='Patching and detection')

    parser.add_argument('-a', '--annotate', help='Annotate files', action="store_true")
    parser.add_argument('-B', '--begin', type=int, help='First page to process', default=0)
    parser.add_argument('-c', '--correct', help='Correct QRs position (according to -x -y and -z)', action="store_true")
    parser.add_argument('-d', '--dpi', help='Dot per inch', type=int, default=400)
    parser.add_argument('-e', '--reconstruct', help='Reconstruct exams', action="store_true")
    parser.add_argument('-E', '--end', type=int, help='Last page to process', default=None)
    parser.add_argument('-g', '--export', type=str, help='Export project for storage', default=None)
    parser.add_argument('-j', '--threads', help='Number of threads to be used for processing', type=int, default=4)
    parser.add_argument('-n', '--nia', help='Create NIA file', action="store_true")
    parser.add_argument('-p', '--process', help='Options -sne', action="store_true")
    parser.add_argument('-q', '--postprocess', help='Options -nrta', action="store_true")
    parser.add_argument('-R', '--ratio', type=int, help='Resize image to save space', default=0.25)
    parser.add_argument('-r', '--raw', help='Create RAW file', action="store_true")
    parser.add_argument('-s', '--scan', help='Process pages in scanned folder', action="store_true")
    parser.add_argument('-S', '--simulate', help='Create random marked files', type=int, default=0)
    parser.add_argument('-t', '--table', help='Generate table',action="store_true")
    parser.add_argument('-T', '--temp', help='Specify temp directory', type=str, default="/tmp")
    parser.add_argument('-x', '--xdisp', help='Specify printer X displacement', type=float, default=0.0)
    parser.add_argument('-y', '--ydisp', help='Specify printer Y displacement', type=float, default=0.0)
    parser.add_argument('-z', '--zoom', help='Specify printer zoom', type=float, default=1.0)


    args = vars(parser.parse_args())

    if not check_workspace():
        print("ERROR: qrscanner must be run from a workspace directory")
        sys.exit(1)

    dir_workspace, dir_data, dir_scanned, dir_generated, dir_xls, dir_publish, dir_source = get_workspace_paths(os.getcwd())
    dir_temp_scanner, _ = get_temp_paths(get_date(), os.getcwd() if args.get("temp") is None else args.get("temp"))

    prefix = str(get_date()) + "_"
    ppm = args.get("dpi") / 25.4
    ws_date = get_date()

    if args.get("export") is not None:
        path = args.get("export")
        if not os.path.exists(path):
            print("ERROR: Export path {} does not exist".format(path))
            sys.exit(1)

        base_dir = path + os.sep + "qrgrading-" + get_date()

        print("Exporting to {}".format(base_dir))

        makedir(base_dir, clear=True)
        makedir(base_dir + os.sep + "scanned", clear=True)
        makedir(base_dir + os.sep + "generated", clear=True)
        #shutil.copytree("generated", base_dir + os.sep + "generated")
        shutil.copytree("data", base_dir + os.sep + "data")
        shutil.copytree("results", base_dir + os.sep + "results")
        shutil.copytree("source", base_dir + os.sep + "source")

        for item in os.listdir("."):
            s = os.path.join(".", item)
            if os.path.isfile(s):
                shutil.copy2(s, base_dir)
        sys.exit(0)

    if args.get("process"):
        args["scan"] = True
        args["nia"] = True
        args["reconstruct"] = True

    if args.get("postprocess"):
        args["nia"] = True
        args["raw"] = True
        args["table"] = True
        args["annotate"] = True

    zoom = args.get("zoom", 1.0)
    xdisp = args.get("xdisp", 0.0)
    ydisp = args.get("ydisp", 0.0)

    if args.get("correct") > 0:
        codes = CodeSet()
        if not codes.load(dir_data + prefix + "detected.csv"):
            print(f"ERROR: file {os.path.basename(dir_data + prefix + 'detected.csv')} not found")
            sys.exit(1)

        for code in codes:
            code: Code
            code.x = code.x * zoom + xdisp
            code.y = code.y * zoom + ydisp
            code.w = code.w * zoom
            code.h = code.h * zoom

        codes.save(dir_data + prefix + "detected.csv")


    if (simulate := args.get("simulate")) > 0:
        print("Simulation in progress ({} files)".format(simulate))
        makedir(dir_scanned, clear=True)

        generated = Generated(72 / 25.4)

        if not generated.load(dir_data + prefix + "generated.csv"):
            print(f"ERROR: file {os.path.basename(dir_data + prefix + 'generated.csv')} not found")
            sys.exit(1)

        pdf_filenames = [f for f in os.listdir(dir_generated) if f.endswith(".pdf")]
        pdf_filenames.sort()

        for pdf_filename in pdf_filenames[0:simulate]:
            print("Marking random answers in {}".format(pdf_filename), end="\r")

            new_pdf = pymupdf.open()
            doc = pymupdf.open(dir_generated + pdf_filename)

            exam = pdf_filename[6:9]

            for page in doc:

                filtered = generated.select(type=Code.TYPE_A, exam=int(exam), page=page.number + 1)
                for question in filtered.get_questions():
                    qrs = filtered.select(type=Code.TYPE_A, question=question)
                    for qr in qrs:
                        if qr.answer == randint(1, 4):
                            x = qr.x + 5
                            y = qr.y - 7
                            w = 10
                            h = 10
                            annot = page.add_redact_annot(pymupdf.Rect(x, y, x + w, y + h), fill=(0.5, 0.5, 0.5), cross_out=False)
                            break

                nias = generated.select(type=Code.TYPE_N, exam=int(exam), page=page.number + 1)
                for i in range(6):
                    r = randint(0, 9)
                    qr = nias.first(number=i * 10 + r)
                    if qr is not None:
                        x = qr.x + 5
                        y = qr.y - 7
                        w = 10
                        h = 10
                        annot = page.add_redact_annot(pymupdf.Rect(x, y, x + w, y + h), fill=(0.5, 0.5, 0.5), cross_out=False)

                # Apply the redactions
                page.apply_redactions()
                # Get the images with the marked codes
                pix = page.get_pixmap(matrix=pymupdf.Matrix(args.get("dpi") / 72, args.get("dpi") / 72))
                # Insert the new page and the image inside it
                new_page = new_pdf.new_page()
                new_page.insert_image(new_page.rect, stream=pix.tobytes("jpg"), width=pix.width, height=pix.height)
                # To be sure avoiding memory leaks
                del pix

            new_pdf.save(dir_scanned + pdf_filename)
            new_pdf.close()
            doc.close()

        print("\nSimulation done.")

    if args.get("scan", False):
        os.makedirs(dir_temp_scanner, exist_ok=True)

        first_page = args.get("begin")
        last_page = args.get("end")

        generated = Generated(ppm)
        if not generated.load(dir_data + prefix + "generated.csv"):
            print(f"ERROR: file {os.path.basename(dir_data + prefix + 'generated.csv')} not found")
            sys.exit(1)

        files = []
        for i, filename in enumerate(sorted([x for x in os.listdir(dir_scanned) if x.endswith(".pdf")])):
            document = pymupdf.open(dir_scanned + filename)
            files.append((i, filename, first_page, len(document) if last_page is None else last_page))
            document.close()

        total_length = sum(length-first for _, _, first, length in files)
        if total_length <= 0:
            print("No pages to process. Exiting.")
            sys.exit(0)

        with Manager() as manager:

            done = 0
            processes = []
            detected = manager.list()
            semaphore = manager.BoundedSemaphore(args.get("threads"))

            for index, filename, first, length in files:

                index > 0 and print() # for the \r at the end of the last line
                print(f">> Processing file {filename} ({index+1}/{len(files)})")

                for i in range(first, length):

                    semaphore.acquire()
                    done += 1

                    procs = [p for p in processes if not p.is_alive()].copy()
                    for process in procs:
                        process.join()
                        processes.remove(process)

                    # We send the filename and open the document in the process for three reasons:
                    # 1. Sending the page object is not possible because it is not pickable
                    # 2. Rendering the page image in parallel make the whole process much faster
                    # 3. For some reason sending the image to the process creates memory overflow

                    process = PageProcessor(semaphore, dir_scanned + filename, i, generated, detected, dir_images=dir_temp_scanner, resize=args.get("ratio"))
                    processes.append(process)
                    process.start()

                    #while len([p for p in processes if p.is_alive()]) >= 4:
                    #    time.sleep(0.25)
                    print(f"   Processed {done}/{total_length} ({100*done/total_length:.2f}%) ({len(detected)} codes found)", end="\r")

            print() # for the \r at the end of the last line

            for process in processes:
                process.join()

            codes = CodeSet()
            codes.extend(detected)
            codes.save(dir_data + prefix + "detected.csv")

    if args.get("reconstruct") or args.get("nia") or args.get("raw") or args.get("annotate"):
        codes = CodeSet()
        if not codes.load(dir_data + prefix + "detected.csv"):
            print(f"ERROR: file {os.path.basename(dir_data + prefix + 'detected.csv')} not found")
            sys.exit(1)

        exams = codes.get_exams()
        date = codes.get_date()

    if args.get("reconstruct"):
        print(">> Reconstructing exams")
        images = os.listdir(dir_temp_scanner)
        for exam in exams:
            filename = dir_publish + "{}{:03d}.pdf".format(date, exam)
            pdf_file = pymupdf.open()
            exam_images = sorted([x for x in images if x.startswith("page-{}-{}-".format(date, exam))])
            for image in exam_images:
                page = pdf_file.new_page()  # noqa
                page.insert_image(pymupdf.Rect(0, 0, 595.28, 842), filename=dir_temp_scanner + os.sep + image)

            pdf_file.save(filename)

    if args.get("nia"):
        nia_filename = dir_xls + prefix + "nia.csv"
        print(f">> Creating {os.path.basename(nia_filename)} file")
        type_n = codes.select(type=Code.TYPE_N)
        with open(nia_filename, "w", encoding='utf-8') as f:
            f.write("EXAM\tNIA\n")
            for exam in exams:
                nia = {0: 'Y', 1: 'Y', 2: 'Y', 3: 'Y', 4: 'Y', 5: 'Y'}
                exam_codes = type_n.select(exam=exam)
                for row in range(6):
                    for number in range(10):
                        result = exam_codes.first(number=row * 10 + number)
                        if result is None or result.marked:
                            nia[row] = number if nia[row] == 'Y' else 'X'
                nia = "".join([str(x) for x in nia.values()])

                f.write("{}\t{}\n".format(date * 1000 + exam, nia))

    if args.get("raw"):
        raw_filename = dir_xls + prefix + "raw.csv"
        print(f">> Creating {os.path.basename(raw_filename)} file")
        with open(raw_filename, "w", encoding='utf-8') as f:
            # # Header
            # line = "DATE\tEXAM"
            # for qn in codes.get_questions():
            #     for an in codes.get_answers():
            #         line += "\tQ{:d}{}".format(qn, chr(64 + an))
            # for on in codes.get_open():
            #     line += "\tO{:d}".format(on)
            # f.write(line + "\n")

            # Exams
            type_a = codes.select(type=Code.TYPE_A)
            type_o = codes.select(type=Code.TYPE_O)
            questions = type_a.get_questions()
            answers = type_a.get_answers()
            openq = type_o.get_open()

            # print("questions: {}".format(questions))
            # print("answers: {}".format(answers))
            # print("openq: {}".format(openq))

            for exam in exams:
                exam_codes = type_a.select(exam=exam)
                line = f"{date}\t{exam}"
                for question in questions:
                    for answer in answers:
                        result = exam_codes.first(question=question, answer=answer)
                        line += "\t1" if result is None or result.marked else "\t0"

                for _ in openq:
                    line += "\t0"
                f.write(line + "\n")
    if args.get("table"):
        table_filename = dir_xls + prefix + "table.csv"
        print(f">> Creating {os.path.basename(table_filename)} file")

        nia = Nia(dir_xls + prefix + "nia.csv")
        nia.load()

        students_data = StudentsData(dir_xls + os.sep + "data.csv")
        students_data.load()

        questions = Questions(dir_xls + os.sep + str(ws_date) + "_questions.csv")
        questions.load()

        raw = pd.read_csv(dir_xls + os.sep + str(ws_date) + "_raw.csv", sep='\t', header=None)
        raw.iloc[:, 0] = raw.iloc[:, 0] * 1000 + raw.iloc[:, 1]
        raw.set_index(raw.iloc[:, 0], inplace=True)

        hdr = 4  # Number of header rows
        inserted = 0

        # Insert the NIA column
        raw.insert(inserted + 2, "NIA", "")
        for exam_id in raw.iloc[:, 0].tolist():
            raw.loc[exam_id, "NIA"] = nia.get_nia(exam_id)
        inserted += 1

        # Insert the GRADE columns
        raw.insert(inserted + 2, "T", '=INDIRECT(ADDRESS(ROW(), COLUMN() -2)) + INDIRECT(ADDRESS(ROW(), COLUMN() -1))')
        raw.insert(inserted + 2, "O", '=SUMPRODUCT(($G$3:$3="O") * INDIRECT(ADDRESS(ROW(), COLUMN() + 2) & ":" '
                                      '& ADDRESS(ROW(), COLUMNS($A$1:$1)))* INDIRECT(ADDRESS(4, COLUMN() + 2) & ":" '
                                      '& ADDRESS(4, COLUMNS($A$1:$1))))')
        raw.insert(inserted + 2, "Q", '=max(0,SUMPRODUCT(($G$3:$3<>"O") *INDIRECT(ADDRESS(ROW(), COLUMN() + 3) & ":" '
                                      '& ADDRESS(ROW(), COLUMNS($A$1:$1)))* INDIRECT(ADDRESS(4, COLUMN() + 3) & ":" '
                                      '& ADDRESS(4, COLUMNS($A$1:$1)))))')

        inserted += 3

        # Fill the header
        percent_answ = '=SUM(OFFSET(INDIRECT("RC", FALSE), 1, 0, ROWS(A:A)-ROW(), 1))/COUNT(OFFSET(INDIRECT("RC", FALSE), 1, 0, ROWS(A:A)-ROW(), 1))'
        percent_ques = ('=SUM(OFFSET(INDIRECT("RC", FALSE), ' + str(
            hdr) + ', -3, ROWS(A:A) - ROW()-4, 4))/COUNT(OFFSET(INDIRECT("RC", FALSE), '
                        + str(hdr) + ', 0, ROWS(A:A)-ROW(), 1))')

        names, qn, ans_letter, ans_value = [""] * (inserted + 2), [""] * (inserted + 2), [""] * (inserted + 2), [
            ""] * (inserted + 2)
        ans_perc = ["Exam ID", "#", "NIA", "Q", "O", "T"]

        num_open = 0
        for question in questions.get_questions():
            if questions.get_type(question) == "Q":
                names.extend([questions.get_text(question), "", "", percent_ques])
                qn.extend([question, question, question, question])
                ans_value.extend([questions.get_value(question, i + 1) for i in range(4)])
                ans_letter.extend([chr(65 + i) for i in range(4)])
                ans_perc.extend([percent_answ] * 4)
            else:
                names.append(questions.get_text(question))
                qn.append(question)
                ans_letter.append("O")
                ans_value.append(questions.get_value(question, 1))
                ans_perc.append('=countif((INDIRECT(ADDRESS(6, COLUMN()) & ":" & ADDRESS(ROWS(6:1000), COLUMN()))),">0")/count((INDIRECT(ADDRESS(6, COLUMN()) & ":" & ADDRESS(ROWS(6:1000), COLUMN()))))')
                num_open += 1

        # print(raw.shape, len(names), len(qn), len(ans_letter), len(ans_value), len(ans_perc))

        raw.loc[-5] = names
        raw.loc[-4] = qn
        raw.loc[-3] = ans_letter
        raw.loc[-2] = ans_value
        raw.loc[-1] = ans_perc
        df = raw.sort_index().reset_index(drop=True)

        df.iloc[5:,-num_open:] = '=IFERROR(VLOOKUP(INDIRECT("A" & ROW()), INDIRECT("'+get_date()+'_" & INDIRECT(ADDRESS(1, COLUMN(), 4)) & "!A:D"), 2, FALSE),0)'

        df.to_csv(table_filename, sep='\t', index=False, header=False)


    if args.get("annotate"):
        print(">> Annotating exams")
        questions = Questions(dir_xls + prefix + "questions.csv")
        if not questions.load():
            print(f"ERROR: file {os.path.basename(dir_xls + prefix + 'questions.csv')} not found")
            sys.exit(1)

        for exam in exams:
            print("   Annotating exam {}".format(exam), end="\r")
            filename = dir_publish + "{}{:03d}.pdf".format(date, exam)
            pdf_file = pymupdf.open(filename)
            for page in pdf_file:

                for annot in page.annots():
                    page.delete_annot(annot)

                this_page = codes.select(type=Code.TYPE_A, exam=exam, page=page.number + 1)
                for code in this_page:
                    if code.marked:
                        x, y = code.get_pos()
                        w, h = code.get_size()
                        r = pymupdf.Rect(xdisp + x*zoom, ydisp + y*zoom, xdisp + x*zoom + w*zoom, ydisp + y*zoom + h*zoom)
                        annot = page.add_rect_annot(r)
                        annot.set_border(width=2)
                        if questions.get_value(code.question, code.answer) > 0:
                            annot.set_colors(stroke=(0, 1, 0))
                        else:
                            annot.set_colors(stroke=(1, 0, 0))
                        annot.update()
            pdf_file.save(filename, incremental=True, encryption=PDF_ENCRYPT_KEEP)
        print()

    print("All done :)")


if __name__ == '__main__':
    main()
