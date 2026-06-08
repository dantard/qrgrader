import argparse
import os
import re
import sys

import pandas
import yaml

from qrgrader.code import Code
from qrgrader.code_set import CodeSet
from qrgrader.common import check_workspace, get_workspace_paths, get_date, Password, Nia, get_prefix, \
    get_workspace_paths_with_config
from qrgrader.encrypt import decrypt
from qrgrader.secret import get_secret
from qrgrader.utils import makedir

# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qrgrader.gdrive import GDrive, Sheets

def main(params=None):


    parser = argparse.ArgumentParser(description='Upload and download sheets from Google Sheets')
    parser.add_argument('-d', '--download', help='Download sheet', action="append", default=[])
    parser.add_argument('-u', '--upload', help='Upload sheet', nargs="+", default=[])
    parser.add_argument('-w', '--workbook', help='Workbook name')
    parser.add_argument('-y', '--yeah', help="Answer 'yes' to all questions", action="store_true")
    args = parser.parse_args()

    if not check_workspace():
        print("ERROR: qrsheets must be run from a workspace directory")
        sys.exit(1)

    dir_workspace, dir_data, _, dir_generated, dir_xls, _, dir_source, dir_config = get_workspace_paths_with_config(os.getcwd())
    date = get_date()

    # Create json file with client secrets
    makedir("config")
    if not os.path.exists("config" + os.sep + "client_secret.json"):
        secret = get_secret()
        passwd = input("Enter password for QRGrader secret: ")
        try:
            client_secrets_json = decrypt(secret, passwd)
            with open("config" + os.sep + "client_secret.json", "w", encoding='utf-8') as f:
                f.write(client_secrets_json)
        except Exception as e:
            print("Password incorrect. You may request a password to dantard@unizar.es", e)
            sys.exit(1)

    # Load config file if provided


    if args.workbook is not None:
        sh = Sheets(config_dir=dir_config)
        sh.open(args.workbook)

        if args.upload is not None:
            for sheet in args.upload:
                sh.upload(sheet)

    print("All Done :)")


if __name__ == "__main__":
    main()
