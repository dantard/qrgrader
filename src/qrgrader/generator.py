import shutil
import subprocess
import sys
import threading
from multiprocessing import Process

from pymupdf import pymupdf


class Done:
    def __init__(self):
        self.done = 0
        self.mutex = threading.Lock()

    def inc_done(self):
        self.mutex.acquire()
        self.done = self.done + 1
        self.mutex.release()

    def get_done(self):
        return self.done


class Generator(Process):
    def __init__(self, semaphore, filename, uniqueid, **kwargs):
        super().__init__()
        self.uniqueid = uniqueid
        self.dir_generated = kwargs.get("dir_generated", "../..")
        self.source_filename = filename
        self.dir_temp_generator = kwargs.get("dir_temp_generator", "../..")
        self.desired_pages = kwargs.get("desired_pages", -1)
        self.verbose = kwargs.get("verbose", False)
        self.dir_source = kwargs.get("dir_source", "../..")
        self.semaphore = semaphore

    def run(self):
        process = subprocess.Popen(['xelatex',
                                    '-interaction', 'nonstopmode',
                                    '-halt-on-error',
                                    '-output-directory', '{}'.format(self.dir_temp_generator),
                                    '-jobname', '{}'.format(self.uniqueid),
                                    '\\newcommand{{\\uniqueid}}{{{:s}}}\\input{{{:s}}}"'.format(self.uniqueid,
                                                                                                self.source_filename.replace("\\", "/"))],
                                   stdout=subprocess.PIPE,
                                   universal_newlines=True,
                                   cwd=self.dir_source)

        while True:
            output = process.stdout.readline()
            self.verbose and print(output.strip())
            if "MATCODE" in output.strip():
                print(output)

            # Do something else
            return_code = process.poll()
            if return_code is not None:
                if return_code == 0:
                    this_one_done = True
                    if self.desired_pages != -1:
                        the_pdf = pymupdf.open(self.dir_temp_generator + str(self.uniqueid) + ".pdf")
                        if the_pdf.page_count != self.desired_pages:
                            this_one_done = False
                            print("Discarding exam {} ({} pages)".format(self.uniqueid, the_pdf.page_count))

                    if this_one_done:
                        shutil.move(self.dir_temp_generator + str(self.uniqueid) + ".pdf", self.dir_generated + str(self.uniqueid) + ".pdf")

                else:
                    print(" * ERROR: Exam {} generation has finished with return code: {}".format(self.uniqueid, return_code))
                # Process has finished, read rest of the output
                for output in process.stdout.readlines():
                    (self.verbose or return_code != 0) and print(output.strip())

                break
        self.semaphore.release()
