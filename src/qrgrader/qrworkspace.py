#!/usr/bin/env python

from __future__ import print_function

import argparse
from datetime import date as thedate

from qrgrader.python.support import *

def main():

    parser = argparse.ArgumentParser(description='Patching and detection')
    parser.add_argument('-d', '--date', help='Examen id code (usually da date, 6 figures)', default=None)

    args = vars(parser.parse_args())

    date = args["date"]

    if date is None:
        date = thedate.today().strftime("%y%m%d")

    base = "qrgrading-{}".format(date)
    pool = base + "/generated/pdf"
    qrs = base + "/generated/qr"
    xls = base + "/results/xls"
    publish = base + "/results/publish"
    scanned = base + "/scanned"
    source = base + "/source"

    makedir(base, False)
    makedir(pool, False)
    makedir(qrs, False)
    makedir(xls, False)
    makedir(publish, False)
    makedir(scanned, False)
    makedir(source, False)

    with open(base + os.sep + ".date", "w") as f:
        f.write("{}".format(date))

    print("Workspace '{}' has been created correctly.".format(base))


if __name__ == "__main__":
    main()