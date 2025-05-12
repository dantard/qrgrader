import argparse
import os
import sys
import time
from multiprocessing import Manager, Pool, Process
from random import randint

import cv2
import pymupdf
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QGraphicsRectItem
from pymupdf.mupdf import PDF_ENCRYPT_KEEP

from qrgrader.code import Code
from qrgrader.code_set import CodeSet, PageCodeSet
from qrgrader.common import check_workspace, get_workspace_paths, get_temp_paths, Generated, Questions, get_date
from qrgrader.page_processor import PageProcessor
from qrgrader.utils import makedir


def main():
    parser = argparse.ArgumentParser(description='Patching and detection')

    parser.add_argument('-B', '--begin', type=int, help='First page to process', default=0)
    parser.add_argument('-E', '--end', type=int, help='Last page to process', default=None)
    parser.add_argument('-R', '--ratio', type=int, help='Resize image to save space', default=0.25)
    parser.add_argument('-s', '--scan', help='Process pages in scanned folder', action="store_true")
    parser.add_argument('-d', '--dpi', help='Dot per inch', type=int, default=400)
    parser.add_argument('-a', '--annotate', help='Annotate files', action="store_true")
    parser.add_argument('-n', '--nia', help='Create NIA file', action="store_true")
    parser.add_argument('-r', '--raw', help='Create RAW file', action="store_true")
    parser.add_argument('-c', '--correct', help='Correct QRs position (according to -x -y and -z)', action="store_true")
    parser.add_argument('-S', '--simulate', help='Create random marked files', type=int, default=0)
    parser.add_argument('-e', '--reconstruct', help='Reconstruct exams', action="store_true")
    parser.add_argument('-p', '--process', help='Options -snre', action="store_true")
    parser.add_argument('-T', '--temp', help='Specify temp directory', type=str, default="/tmp")
    parser.add_argument('-z', '--zoom', help='Specify printer zoom', type=float, default=1.0)
    parser.add_argument('-x', '--xdisp', help='Specify printer X displacement', type=float, default=0.0)
    parser.add_argument('-y', '--ydisp', help='Specify printer Y displacement', type=float, default=0.0)

    args = vars(parser.parse_args())

    if not check_workspace():
        print("ERROR: qrscanner must be run from a workspace directory")
        sys.exit(1)

    dir_workspace, dir_data, dir_scanned, dir_generated, dir_xls, dir_publish, dir_source = get_workspace_paths(os.getcwd())
    dir_temp_scanner, _ = get_temp_paths(get_date(), os.getcwd() if args.get("temp") is None else args.get("temp"))

    prefix = str(get_date()) + "_"



    ppm = args.get("dpi") / 25.4
    if args.get("process"):
        args["scan"] = True
        args["nia"] = True
        args["raw"] = True
        args["reconstruct"] = True

    zoom = args.get("zoom", 1.0)
    xdisp = args.get("xdisp", 0.0)
    ydisp = args.get("ydisp", 0.0)

    if args.get("correct") > 0:
        codes = CodeSet()
        if not codes.load(dir_data + prefix + "detected.csv"):
            print("ERROR: detected.csv not found")
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
            print("ERROR: generated.csv not found")
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

        generated = Generated(ppm)
        if not generated.load(dir_data + prefix + "generated.csv"):
            print("ERROR: generated.csv not found")
            sys.exit(1)

        with Manager() as manager:

            processes = []
            detected = manager.list()

            files = [x for x in os.listdir(dir_scanned) if x.endswith(".pdf")]
            for filename in files:
                #print("Processing file {}".format(filename))
                document = pymupdf.open(dir_scanned + filename)
                last_page = args.get("end") if args.get("end") is not None else len(document)
                document.close()

                for i in range(args.get("begin"), last_page):

                    # We send the filename and open the document in the process for three reasons:
                    # 1. Sending the page object is not possible because it is not pickable
                    # 2. Rendering the page image in parallel make the whole process much faster
                    # 3. For some reason sending the image to the process creates memory overflow

                    procs = [p for p in processes if not p.is_alive()].copy()
                    for process in procs:
                        process.join()
                        processes.remove(process)

                    process = PageProcessor(dir_scanned + filename, i, generated, detected, dir_images=dir_temp_scanner, resize=args.get("ratio"))
                    processes.append(process)
                    process.start()

                    while len([p for p in processes if p.is_alive()]) >= 4:
                        time.sleep(0.25)


            for process in processes:
                process.join()

            codes = CodeSet()
            codes.extend(detected)
            codes.save(dir_data + prefix + "detected.csv")

    if args.get("reconstruct") or args.get("nia") or args.get("raw") or args.get("annotate"):
        codes = CodeSet()
        if not codes.load(dir_data + prefix + "detected.csv"):
            print("ERROR: detected.csv not found")
            sys.exit(1)

        exams = codes.get_exams()
        date = codes.get_date()

    if args.get("reconstruct"):
        print("Reconstructing exams")
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
        print("Creating NIA xls file")
        with open(dir_xls + prefix + "nia.csv", "w", encoding='utf-8') as f:
            f.write("EXAM\tNIA\n")
            for exam in exams:
                nia = {0: 'Y', 1: 'Y', 2: 'Y', 3: 'Y', 4: 'Y', 5: 'Y'}
                for row in range(6):
                    for number in range(10):
                        result = codes.first(exam=exam, type=Code.TYPE_N, number=row * 10 + number)
                        if result is None or result.marked:
                            nia[row] = number if nia[row] == 'Y' else 'X'
                nia = "".join([str(x) for x in nia.values()])

                f.write("{}\t{}\n".format(date * 1000 + exam, nia))

    if args.get("raw"):
        print("Creating RAW xls file")
        with open(dir_xls + prefix + "raw.csv", "w", encoding='utf-8') as f:
            # # Header
            # line = "DATE\tEXAM"
            # for qn in codes.get_questions():
            #     for an in codes.get_answers():
            #         line += "\tQ{:d}{}".format(qn, chr(64 + an))
            # for on in codes.get_open():
            #     line += "\tO{:d}".format(on)
            # f.write(line + "\n")

            # Exams
            for exam in exams:
                line = f"{date}\t{exam}"
                for question in codes.get_questions():
                    for answer in codes.get_answers():
                        result = codes.first(exam=exam, type=Code.TYPE_A, question=question, answer=answer)
                        line += "\t1" if result is None or result.marked else "\t0"

                for open_questions in codes.get_open():
                    line += "\t0"
                f.write(line + "\n")

    if args.get("annotate"):
        questions = Questions(dir_xls + prefix + "questions.csv")
        if not questions.load():
            print("ERROR: questions.csv not found")
            sys.exit(1)

        for exam in exams:
            print("Annotating exam {}".format(exam), end="\r")
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

    print("All done :)")


if __name__ == '__main__':
    main()
