import argparse
import os
from datetime import date

from qrgrader.common import get_workspace_paths

import importlib.resources


def get_resource(name):
    with importlib.resources.files("qrgrader").joinpath("latex" + os.sep + name).open("r", encoding='utf-8') as f:
        return f.read()


def main():
    parser = argparse.ArgumentParser()
    today = date.today().strftime("%y%m%d")
    parser.add_argument('-d', '--date', type=int, help='Date', default=today)
    args = vars(parser.parse_args())

    if args["date"] < 100000 or args["date"] > 999999:
        print("Invalid date value, exiting.")
        exit(1)

    directories = get_workspace_paths(os.getcwd() + os.sep + "qrgrading-" + str(args["date"]))

    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    dir_workspace, dir_data, dir_scanned, dir_generated, dir_xls, dir_publish, dir_source = directories

    with open(dir_source + "main.tex", "w", encoding='utf-8') as f:
        f.write(get_resource("main.tex"))

    with open(dir_source + "qrgrader.sty", "w", encoding='utf-8') as f:
        f.write(get_resource("qrgrader.sty"))

    print(f"Workspace qrgrader-{args['date']} created successfully.")


if __name__ == '__main__':
    main()
