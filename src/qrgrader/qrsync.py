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

def get_gdrive(verbose=False):
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

    return GDrive(config_dir="config", verbose=verbose)

def upload_summary(drive):
    print(
        f"Uploaded {len(drive.stats["uploaded"])} files, up-to-date {len(drive.stats["up_to_date"])} files, skipped {len(drive.stats["skipped"])} files.")
    if len(drive.stats["conflict"]) > 0:
        print("There are conflicts:")
        for path in drive.stats["conflict"]:
            print(f" - {path}")

def download_summary(drive):
    print(
        f"Downloaded {len(drive.stats['downloaded'])} files, up-to-date {len(drive.stats['up_to_date'])} files, skipped {len(drive.stats['skipped'])} files.")
    if len(drive.stats["conflict"]) > 0:
        print("There are conflicts:")
        for path in drive.stats["conflict"]:
            print(f" - {path}")

def main():
    parser = argparse.ArgumentParser(description="Upload a directory to Google Drive.")
    parser.add_argument("-i", "--folder-id", default=None, help="Drive folder ID to upload into")
    parser.add_argument("--upload", action="store_true", help="Create workspace online")
    parser.add_argument("--clone", action="store_true", help="Clone workspace")
    parser.add_argument("--minimal", action="store_true", help="Download minimum needed files")
    parser.add_argument("--commit", default=None, nargs="+",help="Upload specific files")
    parser.add_argument("--push", action="store_true", help="Update workspace")
    parser.add_argument("--pull", action="store_true", help="Update workspace")
    parser.add_argument("-s", "--silent", action="store_true", help="Update workspace")
    args = parser.parse_args()

    excluded = {"files":["client_secret.json", "credentials.json"], "folders": []}

    if args.minimal:
        excluded["folders"].extend(["generated", "scanned", "source", "encrypted"])
        excluded["files"].extend(["~"])

    if args.clone:
        drive = get_gdrive(not args.silent)
        created = drive.download_directory(args.folder_id, ".", excluded=excluded)
        dest_config_dir = str(created) + os.sep + "config" + os.sep
        os.makedirs(dest_config_dir, exist_ok=True)
        shutil.move("config" + os.sep + "client_secret.json", dest_config_dir +  "client_secret.json")
        shutil.move("config" + os.sep + "credentials.json", dest_config_dir + "credentials.json")
        shutil.rmtree("config")
        download_summary(drive)
        print(f"Workspace {created} cloned successfully.")
        return

    if not check_workspace():
       print("ERROR: qrsync must be run from a workspace directory unless cloning a workspace")
       sys.exit(1)



    dir_workspace, dir_data, _, dir_generated, dir_xls, _, dir_source, dir_config = get_workspace_paths_with_config(os.getcwd())

    drive = get_gdrive(not args.silent)
    if os.path.exists(dir_config + "config.yaml"):
        with open(dir_config + "config.yaml", "r", encoding='utf-8') as f:
            config = yaml.safe_load(f)
    else:
        config = {"workbook": "none", "folder_id": "none"}

    if args.folder_id:
        config["folder_id"] = args.folder_id

    if args.upload:
        folder_id = drive.upload_directory(dir_workspace, parent_id=args.folder_id, exclude=excluded)
        config["folder_id"] = folder_id
        upload_summary(drive)

    elif args.push:
        folder_id = args.folder_id or config.get("folder_id", None)
        drive.update_upload(folder_id, dir_workspace, exclude=excluded)
        upload_summary(drive)


    elif args.pull:
        folder_id = args.folder_id or config.get("folder_id", None)
        drive.update_download(folder_id, dir_workspace, excluded=excluded)
        download_summary(drive)

    elif args.commit:
        folder_id = args.folder_id or config.get("folder_id", None)
        include = [os.getcwd() + os.sep + path for path in args.commit]
        drive.update_upload(folder_id, dir_workspace, include=include)
        upload_summary(drive)

    with open(dir_config + "config.yaml", "w", encoding='utf-8') as f:
        yaml.dump(config, f)

    print("Done :)")

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