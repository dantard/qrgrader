#!/usr/bin/env python

from __future__ import print_function

import argparse
import multiprocessing
import os.path
import re
import shutil
import subprocess
import threading
from os import listdir
from pylatexenc.latex2text import LatexNodes2Text

import pymupdf as fitz

########################### float(re.sub("[^\d\.]", "", "(2.4 puntos)"))


from qrgrader.python.support import *

def main():
    parser = argparse.ArgumentParser(description='Patching and detection')
    parser.add_argument('-b', '--begin', help='First exam number', default=1, type=int)
    parser.add_argument('-c', '--cleanup', help='Clear pool files', action='store_true')
    parser.add_argument('-D', '--draft', help='Force draft generation', action='store_true')
    parser.add_argument('-f', '--filename', help='Specify .tex filename', default=None)
    parser.add_argument('-j', '--threads', help='Maximum number of threads to use (4)', default=4, type=int)
    parser.add_argument('-k', '--feedback', help='Generate feedback csv file', action='store_true')
    parser.add_argument('-n', '--number', help='Number or exams to be generated (1)', default=0, type=int)
    parser.add_argument('-p', '--process', help='Process source folder (main.tex)', action='store_true')
    parser.add_argument('-P', '--pages', help='Acceptable number of pages of output PDF', default=-1, type=int)
    parser.add_argument('-Q', '--questions', help='Generate questions csv', action='store_true')
    parser.add_argument('-v', '--verbose', help='Extra verbosity', action='store_true')

    if len(sys.argv) == 1:
        parser.print_usage()
        sys.exit()

    args = vars(parser.parse_args())
    exe_name = os.path.basename(sys.argv[0])
    dir_name = os.path.basename(os.getcwd())

    if re.match("qrgrading-[0-9][0-9][0-9][0-9][0-9][0-9]", dir_name) == None:
        print("ERROR: {} must be run in the root of the workspace".format(exe_name))
        sys.exit(0)

    filename = args["filename"]
    number = int(args["number"])
    # date = args["date"]
    begin = args["begin"]
    threads = args["threads"]
    verbose = args["verbose"]
    generate_feedback = args["feedback"]
    generate_questions = args["questions"]
    per_pages = args["pages"]
    do_process = args["process"]
    desired_pages = args["pages"]
    cleanup = args["cleanup"]

    isdraft = "draft" if args["draft"] else ""

    if number > 0:
        do_process = True

    if do_process:
        generate_feedback = True
        generate_questions = True

    # if date is None:
    #    date = thedate.today().strftime("%y%m%d")

    date = int(''.join(filter(str.isdigit, dir_name)))

    if desired_pages != -1:
        print("WARNING: With -P option {} will try to generate a maximum of {} exams to get {} with {} pages".format(exe_name, 4 * number, number, desired_pages))
        print("WARNING: With -P option {} may generate up to {} more exams than needed.".format(exe_name, threads))

    base = os.getcwd() + os.sep
    pool = base + "generated" + os.sep + "pdf"
    qrs = base + "generated" + os.sep + "qr"
    xls = base + "results" + os.sep + "xls"
    publish = base + "results" + os.sep + "publish"
    scanned = base + "scanned"
    source_pool = base + "source" + os.sep + "pool"

    makedir(source_pool, True)

    threadLimiter = multiprocessing.BoundedSemaphore(threads)
    mutex = threading.Lock()


    class Done:
        def __init__(self):
            self.done = 0

        def inc_done(self):
            global done
            mutex.acquire()
            self.done = self.done + 1
            mutex.release()

        def get_done(self):
            return self.done


    done = Done()


    class Latexer(threading.Thread):
        def __init__(self, filename, pool, uniqueid, working_dir, draft=""):
            self.uniqueid = uniqueid
            self.pool = pool
            self.filename = filename
            self.working_dir = working_dir
            self.draft = draft
            threading.Thread.__init__(self)

        def run(self):

            process = subprocess.Popen(['xelatex',
                                        '-interaction', 'nonstopmode',
                                        '-halt-on-error',
                                        '-output-directory', '{}'.format(source_pool),
                                        '-jobname', '{}'.format(self.uniqueid),
                                        '\\newcommand{{\\draftoverride}}{{{:s}}}'
                                        '\\newcommand{{\\uniqueid}}{{{:s}}}\\input{{{:s}}}"'.format(self.draft, self.uniqueid,
                                                                                                    self.filename)],
                                       stdout=subprocess.PIPE,
                                       universal_newlines=True,
                                       cwd=self.working_dir)

            while True:
                output = process.stdout.readline()
                verbose and print(output.strip())
                if "MATCODE" in output.strip():
                    print(output)

                # Do something else
                return_code = process.poll()
                if return_code is not None:
                    if return_code == 0:
                        this_one_done = True
                        if desired_pages != -1:
                            the_pdf = fitz.open(source_pool + os.sep + str(self.uniqueid) + ".pdf")
                            if the_pdf.page_count != desired_pages:
                                this_one_done = False
                                print("Discarding exam {} ({} pages)".format(self.uniqueid, the_pdf.page_count))

                        if this_one_done:
                            done.inc_done()
                            shutil.move(source_pool + os.sep + str(self.uniqueid) + ".pdf", pool + os.sep + str(self.uniqueid) + ".pdf")
                            print("Done exam {} ({}/{})".format(self.uniqueid, done.get_done(), number))
                    else:
                        print(" * ERROR: Exam {} generation has finished with return code: {}".format(self.uniqueid, return_code))
                    # Process has finished, read rest of the output
                    for output in process.stdout.readlines():
                        (verbose or return_code != 0) and print(output.strip())

                    break

            threadLimiter.release()


    if do_process:

        processes = []

        if filename is None:
            source = base + "source"
            filename = "main.tex"
        else:
            source = os.path.dirname(os.path.abspath(filename))
            filename = os.path.basename(filename)

        if not os.path.exists(source + os.sep + filename):
            print("ERROR: Source file {} does not exist".format(source + os.sep + filename))
            sys.exit(0)

        print("** Starting parallelized generation (using {} threads)".format(threads))

        end = begin + (number if desired_pages == -1 else 4 * number)

        for i in range(begin, end):

            threadLimiter.acquire()

            uniqueid = "{}{:03d}".format(date, i)
            p = Latexer(filename, pool, uniqueid, source, isdraft)
            p.start()
            processes.append(p)

            if desired_pages != -1 and done.get_done() >= number:
                break

        for p in processes:
            p.join()

        if desired_pages != -1:
            print("Total exams generated: {}".format(done.get_done()))

        # pdfs = [x for x in listdir(source_pool) if x.endswith(".pdf")]

        # for pdf in pdfs:
        #    shutil.move(source_pool + os.sep + pdf, pool + os.sep + pdf)

        codes = []
        logs = [x for x in listdir(source_pool) if x.endswith(".aux")]
        logs.sort()

        w = open(qrs + os.sep + "generated.txt", "w")
        for f in logs:
            pdf_page = 0  # was 1 before merging (commented lines below)
            f = open(source_pool + os.sep + f, "r")
            for line in f:
                if "QRPOSE" in line:
                    line = line.replace("\zref@newlabel{QRPOSE,", "") \
                        .replace("}{\posx{", ",") \
                        .replace("}\posy{", ",") \
                        .replace("}\\abspage{", ",").replace("}}", "").strip()

                    if line.startswith("P"):
                        pdf_page += 1

                    params = line.split(sep=",")
                    line = "{},{},{},{},{},{},{}\n".format(params[0], params[1], params[2], 0, 0, params[3], pdf_page)

                    # if line.startswith("P"):
                    #    pdf_page += 1
                    w.write(line)
            f.close()
        w.close()

    if generate_feedback:
        codes = []

        w = open(qrs + os.sep + "generated.txt", "r")

        for line in w:
            params = line.split()
            codes.append(Code(0, params[0], 0, 0, 0, 0))

        w.close()

        if len(codes) > 0:
            exams = set()
            date = codes[0].date
            for c in codes:
                if c.type == 0:
                    exams.add(c.exam)

            exams = list(exams)
            exams.sort()
            print("Creating feedback file...", end="")
            w = open(xls + os.sep + "{}_feedback.csv".format(date), "w")

            for e in exams:
                w.write("{}{}".format(date, e))
                for c in codes:
                    if c.exam == e and c.type == 0:
                        id = (c.question - 1) * 4 + c.answer
                        w.write(",{}".format(id))
                w.write("\n")

            w.close()
            print("Done.")
        else:
            print("No QR data found, exiting.")

        # Generate xxxxxx_questions.csv

        if generate_questions:
            logs = [x for x in listdir(source_pool) if x.endswith(".log")]
            if len(logs) > 0:
                print("Creating questions csv file...", end="")
                any_log_will_do = source_pool + os.sep + logs[0]

                with open(any_log_will_do, 'r') as file:
                    log = file.read()
                    log = log.split(";;;")
                    questions_number = []
                    with open(xls + os.sep + "{}_questions.csv".format(date), 'w') as filew:
                        data = str()
                        for i in range(1, len(log) - 1):
                            line = log[i].replace("\n", "").replace("\t", "")
                            fields = line.split(";;")
                            fields = [f for f in fields if f != ""]
                            if len(fields) > 9:

                                if fields[0] in questions_number:
                                    print("\n****************************************************")
                                    print("*** WARNING: Multiple questions with same id: {:2s} ***".format(fields[0]))
                                    print("****************************************************")
                                else:
                                    questions_number.append(fields[0])

                                line = fields[0] + "\t" + fields[1] + \
                                       "\t" + (fields[3] if fields[2] == "a" else "0") + \
                                       "\t" + (fields[3] if fields[2] == "b" else "0") + \
                                       "\t" + (fields[3] if fields[2] == "c" else "0") + \
                                       "\t" + (fields[3] if fields[2] == "d" else "0") + \
                                       "\t" + fields[4] + \
                                       "\t" + LatexNodes2Text().latex_to_text(fields[5]).replace("\t", "").replace("\n", " ") + \
                                       "\t" + LatexNodes2Text().latex_to_text(fields[6]).replace("\t", "").replace("\n", " ") + \
                                       "\t" + LatexNodes2Text().latex_to_text(fields[7]).replace("\t", "").replace("\n", " ") + \
                                       "\t" + LatexNodes2Text().latex_to_text(fields[8]).replace("\t", "").replace("\n", " ") + \
                                       "\t" + LatexNodes2Text().latex_to_text(fields[9]).replace("\t", "").replace("\n", " ")
                                data += line + "\n"
                        filew.write(data)


    if cleanup:
        print("Cleaning pool directory")
        shutil.rmtree(source_pool, ignore_errors=True)

    print("Done.")

if __name__ == "__main__":
    main()