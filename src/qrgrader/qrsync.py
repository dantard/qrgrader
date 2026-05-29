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
import sys
import argparse

from attr.filters import exclude

from qrgrader.gdrive import GDrive, Sheets
from qrgrader.common import check_workspace, get_workspace_paths, get_date
from qrgrader.utils import makedir
from qrgrader.secret import get_secret
from qrgrader.encrypt import decrypt

def main():
    parser = argparse.ArgumentParser(description="Upload a directory to Google Drive.")
    parser.add_argument("-i", "--folder-id", default="root", help="Drive folder ID to upload into")
    parser.add_argument("-U", "--upload-workspace", action="store_true", help="Upload workspace")
    parser.add_argument("-D", "--download-workspace", action="store_true", help="Download workspace")
    parser.add_argument("-u", "--upload-updates", action="store_true", help="Update workspace")
    parser.add_argument("-d", "--download-updates", action="store_true", help="Update workspace")
    parser.add_argument("-g", "--generated", action="store_true", help="Include generated")
    parser.add_argument("-x", "--exclude-pdf", action="store_true", help="Exclude result PDF files")
    args = parser.parse_args()

    dir_workspace, dir_data, _, dir_generated, dir_xls, _, dir_source, date = [None] * 8

    if args.upload_updates or args.download_updates or args.upload_workspace:
        if not check_workspace():
           print("ERROR: qrupload must be run from a workspace directory")
           sys.exit(1)

        dir_workspace, dir_data, _, dir_generated, dir_xls, _, dir_source = get_workspace_paths(os.getcwd())

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

    drive = GDrive(config_dir="config")

    if args.download_workspace:
        drive.download_directory(args.folder_id, ".")
    elif args.upload_workspace:
        excluded = ["client_secrets.json", "credentials.json"]
        if not args.generated:
            excluded.append("generated")
        if args.exclude_pdf:
            excluded.append("pdf")

        drive.upload_directory(dir_workspace, parent_id=args.folder_id,
                               exclude=excluded)

    elif args.upload_updates:
        drive.update_upload(args.folder_id, dir_workspace)
        print("\n")
        if len(drive.stats.get("uploaded", 0)) > 0:
            print("Uploaded:")
            for x in drive.stats["uploaded"]:
                print(" - " + x)

        if len(drive.stats.get("conflict", 0)) > 0:
            print("Conflict (not uploaded):")
            for x in drive.stats["conflict"]:
                print(" - " + x)

    elif args.download_updates:
        drive.update_download(args.folder_id, dir_workspace, dry=True)
        if len(drive.stats.get("downloaded", 0)) > 0:
            print("Downloaded:")
            for x in drive.stats["downloaded"]:
                print(" - " + x)

        if len(drive.stats.get("conflict", 0)) > 0:
            print("Conflict (not downloaded):")
            for x in drive.stats["conflict"]:
                print(" - " + x)


if __name__ == "__main__":
    main()