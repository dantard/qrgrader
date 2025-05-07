#!/usr/bin/env python

from __future__ import print_function

import argparse
import os.path
import re
import sys
from multiprocessing import Manager
from os import listdir

from qrgrader.common import get_workspace_paths, get_temp_paths, check_workspace, get_date, get_prefix
from qrgrader.generator import Generator
from qrgrader.utils import makedir


def main():
    parser = argparse.ArgumentParser(description='Patching and detection')
    parser.add_argument('-b', '--begin', help='First exam number', default=1, type=int)
    parser.add_argument('-c', '--cleanup', help='Clear pool files', action='store_true')
    parser.add_argument('-f', '--filename', help='Specify .tex filename', default=None)
    parser.add_argument('-j', '--threads', help='Maximum number of threads to use (4)', default=4, type=int)
    parser.add_argument('-n', '--number', help='Number or exams to be generated', default=0, type=int)
    parser.add_argument('-P', '--pages', help='Acceptable number of pages of output PDF', default=-1, type=int)
    parser.add_argument('-T', '--temp', help='Specify temp directory', type=str, default="/tmp")
    parser.add_argument('-q', '--questions', help='Generate questions csv', action='store_true')
    parser.add_argument('-g', '--generated', help='Generate questions csv', action='store_true')
    parser.add_argument('-v', '--verbose', help='Extra verbosity', action='store_true')
    args = vars(parser.parse_args())

    if not check_workspace():
        print("ERROR: qrscanner must be run from a workspace directory")
        sys.exit(1)

    date = get_date()
    prefix = get_prefix()

    (file, number, begin,
     threads, verbose, desired_pages,
     create_generated, create_questions, cleanup, temporary, filename) = (args["filename"], args["number"],
                                                                          args["begin"], args["threads"],
                                                                          args["verbose"], args["pages"],
                                                                          args["generated"], args["questions"],
                                                                          args["cleanup"], args["temp"], args["filename"])
    if number > 0:
        create_generated = True
        create_questions = True

    dir_workspace, dir_data, _, dir_generated, dir_xls, _, dir_source = get_workspace_paths(os.getcwd())
    _, dir_temp_generator = get_temp_paths(date, os.getcwd() if temporary is None else temporary)

    print("Workspace: {}".format(dir_temp_generator))

    if desired_pages != -1:
        print("WARNING: With -P option qrgenerator will generate a maximum of {} exams to get {} with {} pages".format(4 * number, number, desired_pages))
        print("WARNING: With -P option qrgenerator may generate up to {} more exams than needed.".format(threads))

    if number > 0:

        makedir(dir_generated, clear=True)
        makedir(dir_temp_generator, clear=True)

        if filename is None:
            source = dir_source
            filename = dir_source + "main.tex"
        else:
            source = os.path.dirname(os.path.abspath(filename))
            filename = os.path.basename(filename)

        if not os.path.exists(filename):
            print("ERROR: Source file {} does not exist".format(source + os.sep + filename))
            sys.exit(1)

        print("** Starting parallelized generation (using {} threads)".format(threads))

        end = begin + (number if desired_pages == -1 else 4 * number)

        processes = []

        with Manager() as manager:
            queue = manager.BoundedSemaphore(threads)

            i = begin

            while i < end and len(os.listdir(dir_generated)) < number:
                queue.acquire()

                print("Creating exam {}{:03d} ({:d} ready)".format(date, i, len(os.listdir(dir_generated))))
                p = Generator(queue, filename, "{}{:03d}".format(date, i),
                              dir_temp_generator=dir_temp_generator,
                              dir_generated=dir_generated,
                              dir_source=source,
                              desired_pages=desired_pages,
                              verbose=verbose)

                processes.append(p)
                p.start()
                i += 1

            for p in processes:
                p.join()

            print("Done ({:d} exams generated).".format(len(os.listdir(dir_generated))))

    if create_generated:
        print("Creating generated.csv file...", end="")
        logs = sorted([x for x in listdir(dir_temp_generator) if x.endswith(".aux")])

        w = open(dir_data + prefix + "generated.csv", "w", encoding='utf-8')
        for f in logs:
            pdf_page = 0
            f = open(dir_temp_generator + os.sep + f, "r", encoding='utf-8')

            for line in f:
                if line.startswith("\\zref@newlabel{QRPOSE"):
                    words_with_numbers = re.findall(r'\b\w*\d\w*\b', line)
                    if len(words_with_numbers) != 5:
                        print("ERROR: QRPOSE line does not have 5 values: {}".format(line))
                        sys.exit(0)
                    else:
                        qr_data, posx, posy, abs_page, page_value = words_with_numbers

                        if qr_data.startswith("P"):
                            pdf_page += 1

                        line = "{},{},{},{},{},{},{}\n".format(qr_data, posx, posy, 0, 0, abs_page, pdf_page)
                        w.write(line)
            f.close()
        w.close()
        print("Done.")

    if create_questions:
        logs = [x for x in listdir(dir_temp_generator) if x.endswith(".log")]

        if len(logs) > 0:
            print("Creating questions csv file...", end="")

            any_log_will_do = dir_temp_generator + os.sep + logs[0]

            with open(any_log_will_do, "r", encoding='utf-8') as file:
                log = file.read()
                log = log.split(";;;")
                questions_number = []
                with open(dir_xls + prefix + "questions.csv".format(date), "w", encoding='utf-8') as filew:
                    data = "ID\tTYPE\tA\tB\tC\tD\tBRIEF\n"

                    for i in range(1, len(log) - 1):
                        line = log[i].replace("\n", "").replace("\t", "")
                        fields = line.split(";;")
                        fields = [f for f in fields if f != ""]
                        if len(fields) == 6:

                            if fields[0] in questions_number:
                                print("\n****************************************************")
                                print("*** WARNING: Multiple questions with same id: {:2s} ***".format(fields[0]))
                                print("****************************************************")
                            else:
                                questions_number.append(fields[0])

                            line = fields[0] + "\t" + fields[1] + \
                                   "\t" + (fields[3] if fields[2] == "a" else fields[4].replace(" ", "")) + \
                                   "\t" + (fields[3] if fields[2] == "b" else fields[4].replace(" ", "")) + \
                                   "\t" + (fields[3] if fields[2] == "c" else fields[4].replace(" ", "")) + \
                                   "\t" + (fields[3] if fields[2] == "d" else fields[4].replace(" ", "")) + \
                                   "\t" + fields[5]
                            data += line + "\n"
                    filew.write(data)

    print("Done.")


if __name__ == "__main__":
    main()
