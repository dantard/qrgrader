"""
upload_to_gdrive.py
--------------------
Upload a local directory to Google Drive using the GDrive class.

Requirements:
    pip install pydrive2

Setup (one-time):
    Place client_secret.json in your config directory (default: current folder).

Usage:
    python upload_to_gdrive.py /path/to/local/folder
    python upload_to_gdrive.py /path/to/local/folder --parent-id <DRIVE_FOLDER_ID>
    python upload_to_gdrive.py /path/to/local/folder --config-dir /path/to/config
"""

import os
import shutil
import sys
import argparse

import yaml
from attr.filters import exclude

from qrgrader.gdrive import GDrive, Sheets
from qrgrader.common import check_workspace, get_workspace_paths, get_date, get_workspace_paths_with_config
from qrgrader.utils import makedir
from qrgrader.secret import get_secret
from qrgrader.encrypt import decrypt

def get_gdrive(delete=False):
    if not os.path.exists("config" + os.sep + "client_secret.json"):
        makedir("config")
        secret = get_secret()
        passwd = input("Enter password for QRGrader secret: ")
        try:
            client_secrets_json = decrypt(secret, passwd)
            with open("config" + os.sep + "client_secret.json", "w", encoding='utf-8') as f:
                f.write(client_secrets_json)
        except Exception as e:
            print("Password incorrect. You may request a password to dantard@unizar.es", e)
            sys.exit(1)

    gdrive = GDrive(config_dir="config")
    if delete:
        shutil.rmtree("config")
    return gdrive

def main():
    parser = argparse.ArgumentParser(description="Upload a directory to Google Drive.")
    parser.add_argument("-i", "--folder-id", default=None, help="Drive folder ID to upload into")
    parser.add_argument("--upload", action="store_true", help="Create workspace online")
    parser.add_argument("--clone", action="store_true", help="Clone workspace")

    parser.add_argument("--push", action="store_true", help="Update workspace")
    parser.add_argument("--pull", action="store_true", help="Update workspace")
    args = parser.parse_args()

    if args.clone:
        drive = get_gdrive(delete=True)
        drive.download_directory(args.folder_id, ".")
        print("Workspace cloned successfully.")
        return

    if not check_workspace():
       print("ERROR: qrsync must be run from a workspace directory unless cloning a workspace")
       sys.exit(1)

    excluded = ["client_secret.json", "credentials.json"]

    dir_workspace, dir_data, _, dir_generated, dir_xls, _, dir_source, dir_config = get_workspace_paths_with_config(os.getcwd())

    drive = get_gdrive()
    with open(dir_config + "config.yaml", "r", encoding='utf-8') as f:
        config = yaml.safe_load(f)

    if args.upload:
        folder_id = drive.upload_directory(dir_workspace, parent_id=args.folder_id, exclude=excluded)
        config["folder_id"] = folder_id

    elif args.push:
        folder_id = args.folder_id or config.get("folder_id", None)

        drive.update_upload(folder_id, dir_workspace, exclude=excluded)
        print("\n")
        if len(drive.stats.get("uploaded", 0)) > 0:
            print("Uploaded:")
            for x in drive.stats["uploaded"]:
                print(" - " + x)

        if len(drive.stats.get("conflict", 0)) > 0:
            print("Conflict (not uploaded):")
            for x in drive.stats["conflict"]:
                print(" - " + x)

    elif args.pull:
        folder_id = args.folder_id or config.get("folder_id", None)
        drive.update_download(folder_id, dir_workspace)
        if len(drive.stats.get("downloaded", 0)) > 0:
            print("Downloaded:")
            for x in drive.stats["downloaded"]:
                print(" - " + x)

        if len(drive.stats.get("conflict", 0)) > 0:
            print("Conflict (not downloaded):")
            for x in drive.stats["conflict"]:
                print(" - " + x)
        print("\n")


if __name__ == "__main__":
    main()


    # elif args.create:
    #     excluded = ["client_secret.json", "credentials.json"]
    #     folder_id = drive.upload_directory(dir_workspace, parent_id=args.folder_id, exclude=excluded)
    #
    #     config["folder_id"] = folder_id
    #
    #     with open(dir_config + "config.yaml", "w", encoding='utf-8') as f:
    #         yaml.dump(config, f)