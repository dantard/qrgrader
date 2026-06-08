import argparse
import os
from datetime import date

import yaml

from qrgrader.common import get_workspace_paths, get_workspace_paths_with_config

import importlib.resources

import os
import shutil
import sys
import argparse
from datetime import date
import yaml
from qrgrader.gdrive import GDrive, Sheets
from qrgrader.common import check_workspace, get_workspace_paths, get_date, get_workspace_paths_with_config
from qrgrader.utils import makedir
from qrgrader.secret import get_secret
from qrgrader.encrypt import decrypt

def get_resource(name):
    with importlib.resources.files("qrgrader").joinpath("latex" + os.sep + name).open("r", encoding='utf-8') as f:
        return f.read()


def get_gdrive(verbose=False, dry_run=False):
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

    return GDrive(config_dir="config", verbose=verbose, dry_run=dry_run)

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
    parser.add_argument('-c', '--create', help='Create workspace', action='store_true')
    parser.add_argument('-d', '--date', type=int, help='Date', default=None)
    parser.add_argument("-i", "--folder-id", default=None, help="Drive folder ID to upload/download from")
    parser.add_argument("--upload", action="store_true", help="Create workspace online")
    parser.add_argument("--clone", action="store_true", help="Clone workspace")
    parser.add_argument("--minimal", action="store_true", help="Download minimum needed files")
    parser.add_argument("--commit", default=None, nargs="+",help="Upload specific files")
    parser.add_argument("--push", action="store_true", help="Update workspace")
    parser.add_argument("--pull", action="store_true", help="Update workspace")
    parser.add_argument("--force", action="store_true", help="Force action for super user")
    parser.add_argument("-s", "--silent", action="store_true", help="Update workspace")
    parser.add_argument("--dry", action="store_true", help="Execute a dry run without uploading or downloading files")
    args = parser.parse_args()

    if args.date is not None:
        args.create = True

    if args.create:
        args.date = args.date or int(date.today().strftime("%y%m%d"))

        if args.date < 100000 or args.date > 999999:
            print("Invalid date value, exiting.")
            exit(1)

        directories = get_workspace_paths_with_config(os.getcwd() + os.sep + "qrgrading-" + str(args.date))

        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)

        dir_workspace, dir_data, dir_scanned, dir_generated, dir_xls, dir_publish, dir_source, dir_config = directories

        with open(dir_source + "main.tex", "w", encoding='utf-8') as f:
            f.write(get_resource("main.tex"))

        with open(dir_source + "qrgrader.sty", "w", encoding='utf-8') as f:
            f.write(get_resource("qrgrader.sty"))

        config={"workbook": "none", "folder_id": "none", "su": "*", "owners": {}}
        with open(dir_config + "config.yaml", "w", encoding='utf-8') as f:
            yaml.dump(config, f)

        print(f"Workspace qrgrader-{args.date} created successfully.")
        return

    excluded = {"files":["client_secret.json", "credentials.json"], "folders": []}

    if args.minimal:
        excluded["folders"].extend(["generated", "scanned", "source", "encrypted"])
        excluded["files"].extend(["~"])

    if args.clone:
        drive = get_gdrive(not args.silent)
        print("User: {}".format(drive.get_current_user()))
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

    drive = get_gdrive(not args.silent, args.dry)
    if os.path.exists(dir_config + "config.yaml"):
        with open(dir_config + "config.yaml", "r", encoding='utf-8') as f:
            config = yaml.safe_load(f)
    else:
        config = {"workbook": "none", "folder_id": "none", "owners": {}}

    name, email = drive.get_current_user()
    owners = config.get("owners", {})
    is_superuser = (email == config.get("su") and args.force) or config.get("su") == "*"
    has_wildcard = "*" in owners.get(email, [])

    if args.folder_id:
        config["folder_id"] = args.folder_id

    if args.upload:
        # if the user is not in owners or does not have "*" permission,
        # and is not the superuser with force flag, deny upload

        if not (is_superuser or has_wildcard):
            print(f"ERROR: User {email} does not have permission to upload this workspace.")
            sys.exit(1)

        folder_id = drive.upload_directory(dir_workspace, parent_id=args.folder_id, exclude=excluded)
        config["folder_id"] = folder_id
        upload_summary(drive)

    elif args.push:
        if is_superuser or has_wildcard:
            included = None
        elif email in owners:
            included, excluded = [os.getcwd() + os.sep + path for path in owners.get(email, [])], None
        else:
            print(f"ERROR: User {email} does not have permission to upload this workspace.")
            sys.exit(1)

        folder_id = args.folder_id or config.get("folder_id", None)
        drive.update_upload(folder_id, dir_workspace, exclude=excluded, include=included)
        upload_summary(drive)


    elif args.pull:
        if is_superuser or has_wildcard:
            excluded = None
        elif email in owners:
            excluded = {"files":[os.getcwd() + os.sep + path for path in owners.get(email, [])]}

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