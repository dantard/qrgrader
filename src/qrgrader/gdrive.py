import os
import sys
from datetime import datetime, timezone

import gspread
import pandas
from colorama import Fore, Style
from gspread.utils import a1_to_rowcol, ValueInputOption
from gspread_dataframe import set_with_dataframe, get_as_dataframe
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from pathlib import Path

from qrgrader import utils
from qrgrader.common import get_narrowest_type

FOLDER_MIME = "application/vnd.google-apps.folder"


class GDrive:

    def __init__(self, config_dir=".", **kwargs):
        self.reset_stats()
        self.gdrive = None
        self.config_dir = config_dir
        self.verbose = kwargs.get("verbose", False)
        self.dry_run = kwargs.get("dry_run", False)

        if kwargs.get("authorize", True):
            self.authorize()

    def print(self, message):
        if self.verbose:
            print(message + Style.RESET_ALL)

    def reset_stats(self):
        self.stats = {"downloaded": [],
                      "uploaded": [],
                      "skipped": [],
                      "excluded": [],
                      "conflict": [],
                      "up_to_date": []}


    def authorize(self):

        GoogleAuth.DEFAULT_SETTINGS['client_config_file'] = self.config_dir + os.sep + "client_secret.json"
        credentials_path = self.config_dir + os.sep + "credentials.json"

        gauth = GoogleAuth()
        gauth.LoadCredentialsFile(credentials_path)

        if gauth.credentials is None:
            gauth.GetFlow()
            gauth.flow.params.update({'approval_prompt': 'force'})
            gauth.LocalWebserverAuth()
        elif gauth.access_token_expired:
            gauth.GetFlow()
            gauth.flow.params.update({'approval_prompt': 'force'})
            gauth.LocalWebserverAuth()
        else:
            gauth.Authorize()

        gauth.SaveCredentialsFile(credentials_path)
        self.gdrive = GoogleDrive(gauth)

    def ls(self, folder_id):
        try:
            file_list = self.gdrive.ListFile({'q': f"'{folder_id}' in parents and trashed=false"}).GetList()
            result = []
            for file in file_list:
                result.append((file['title'], file['id']))
        except:
            result = None
        return result

    def get_folder_id_by_path(self, path):
        folder_names = path.strip("/").split("/")  # Split the path into folder names
        parent_id = "root"  # Start from the root directory

        for folder_name in folder_names:
            query = f"title = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false and '{parent_id}' in parents"
            folder_list = self.gdrive.ListFile({'q': query}).GetList()

            if not folder_list:
                return None  # Folder not found

            parent_id = folder_list[0]['id']  # Move to the next folder in the path

        return parent_id  # Return the final folder ID

    def get_shared_folder_id(self, folder_name):
        query = "title = '" + folder_name + "' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        shared_folders = self.gdrive.ListFile(
            {'q': query, 'spaces': 'drive', 'corpora': 'allDrives', 'supportsAllDrives': True}).GetList()
        if shared_folders:
            folder_id = shared_folders[0]['id']
            return folder_id
        else:
            return None



    def upload_file(self, filename, folder_id):
        name = os.path.basename(filename)
        query = f"title = '{name}' and '{folder_id}' in parents and trashed = false"
        online_files = self.gdrive.ListFile({'q': query}).GetList()

        local_md5 = utils.md5(filename)
        local_mtime = Path(filename).stat().st_mtime
        local_mtime = datetime.fromtimestamp(local_mtime, tz=timezone.utc)

        file_id = None
        if online_files:
            file_info = online_files[0]
            file_id = file_info.get('id')
            drive_md5 = file_info.get('md5Checksum')
            online_mtime = file_info.get("modifiedDate")
            online_mtime = datetime.fromisoformat(online_mtime.replace('Z', '+00:00'))

            if drive_md5 == local_md5:
                if not self.dry_run:
                    os.utime(filename, (online_mtime.timestamp(), online_mtime.timestamp()))
                self.stats["up_to_date"].append(name)
                self.print(" - Skipping file {} (already up to date)".format(name))
            elif local_mtime > online_mtime :
                if not self.dry_run:
                    file = self.gdrive.CreateFile({'id': online_files[0]['id']})
                    file.SetContentFile(filename)
                    file.Upload()
                self.stats["uploaded"].append(name)
                self.print(Fore.GREEN + " - Updating file {} (local version is newer)".format(name))
            else:
                self.stats["conflict"].append(name)
                self.print(Fore.RED + " - Conflict for file {} (remote version is newer)".format(name))
        else:
            if not self.dry_run:
                file = self.gdrive.CreateFile({'title': name, 'parents': [{'id': folder_id}]})
                file.SetContentFile(filename)
                file.Upload()
                file_id = file.get('id')
            self.stats["uploaded"].append(name)
            self.print(Fore.GREEN + " - Uploading file {} (new file)".format(name))


        return file_id

    def create_folder(self, name, parent_id="root"):
        if self.dry_run:
            return None
        folder = self.gdrive.CreateFile({
            "title": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [{"id": parent_id}],
        })
        folder.Upload()
        return folder["id"]

    def delete_folder(self, folder_id):
        if not self.dry_run:
            file = self.gdrive.CreateFile({'id': folder_id})
            file.Delete()

    def upload_directory(self, local_dir: str, parent_id="root", exclude=None, overwrite=False, is_root=True, include=None):
        local_dir = Path(local_dir)
        if is_root:
            if overwrite:
                query = f"title = '{local_dir.name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false and '{parent_id}' in parents"
                existing = self.gdrive.ListFile({'q': query}).GetList()
                if existing:
                    self.delete_folder(existing[0]['id'])
                folder_id = self.create_folder(local_dir.name, parent_id)
            else:
                query = f"title = '{local_dir.name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false and '{parent_id}' in parents"
                existing = self.gdrive.ListFile({'q': query}).GetList()
                if existing:
                    folder_id = existing[0]['id']
                else:
                    folder_id = self.create_folder(local_dir.name, parent_id)
        else:
            folder_id = parent_id

        if include is None:
            self.print("Entering directory {}".format(local_dir))

        exclude = exclude or {}

        for entry in sorted(local_dir.iterdir()):
            if entry.is_dir():
                if entry.name in exclude.get("folders", []):
                    self.stats["skipped"].append(str(entry))
                    self.print(Fore.YELLOW + f" - Skipping directory {entry} (excluded)")
                    continue
                self.upload_directory(entry, parent_id=folder_id, exclude=exclude, include=include)
            elif entry.is_file():
                if entry.name in exclude.get("files", []):
                    self.stats["skipped"].append(str(entry))
                    self.print(f" - Skipping file {entry} (excluded)")
                    continue
                if include is not None and str(entry) not in include:
                    continue
                self.upload_file(str(entry), folder_id)

        return folder_id
    def update_download(self, folder_id: str, dest: str, excluded=None):
        self.download_directory(folder_id, dest, is_root=False, excluded=excluded)

    def update_upload(self, folder_id: str, local_dir: str, exclude=None, overwrite=False, include=None):
        self.upload_directory(local_dir, parent_id=folder_id, is_root=False, exclude=exclude, overwrite=overwrite, include=include)

    def download_file(self, file_id, local_path: Path):
        f = self.gdrive.CreateFile({'id': file_id})
        f.FetchMetadata(fields="title,md5Checksum,modifiedDate")
        drive_md5 = f.get('md5Checksum')
        online_mtime = f.get("modifiedDate")
        online_mtime = datetime.fromisoformat(online_mtime.replace('Z', '+00:00'))

        if local_path.exists():
            local_mtime = Path(local_path).stat().st_mtime
            local_mtime = datetime.fromtimestamp(local_mtime, tz=timezone.utc)
            local_md5 = utils.md5(local_path)
            if local_md5 == drive_md5:
                if not self.dry_run:
                    os.utime(local_path, (online_mtime.timestamp(), online_mtime.timestamp()))
                self.stats["up_to_date"].append(local_path.name)
                self.print(" - Skipping file {} (already up to date)".format(local_path.name))
            elif online_mtime > local_mtime:
                if not self.dry_run:
                    f.GetContentFile(str(local_path))
                    os.utime(local_path, (online_mtime.timestamp(), online_mtime.timestamp()))
                self.stats["downloaded"].append(local_path.name)
                self.print(Fore.GREEN + " - Updating file {} (remote version is newer)".format(local_path.name))
            else:
                self.stats["conflict"].append(local_path.name)
                self.print(Fore.RED + " - Conflict for file {} (local version is newer)".format(local_path.name))
        else:
            if not self.dry_run:
                f.GetContentFile(str(local_path))
                os.utime(local_path, (online_mtime.timestamp(), online_mtime.timestamp()))
            self.stats["downloaded"].append(local_path.name)
            self.print(Fore.GREEN + " - Downloading file {} (new file)".format(local_path.name))

        return file_id

    def download_directory(self, folder_id: str, dest: str, is_root=True, excluded=None):
        excluded = excluded or {}
        for value in excluded.get("folders", []):
            if value in str(dest):
                print(f"Skipping directory {dest} (excluded)")
                return

        dest = Path(dest)

        if is_root:
            meta = self.gdrive.CreateFile({'id': folder_id})
            meta.FetchMetadata(fields="title")
            dest = dest / meta['title']

        self.print("Entering directory {}".format(dest))

        dest.mkdir(parents=True, exist_ok=True)


        entries = self.gdrive.ListFile(
            {'q': f"'{folder_id}' in parents and trashed=false"}
        ).GetList()

        for entry in sorted(entries, key=lambda e: e['title']):
            local_path = dest / entry['title']

            if entry['mimeType'] == FOLDER_MIME:
                self.download_directory(entry['id'], local_path, is_root=False, excluded=excluded)
            else:
                skipped = False
                for file in excluded.get("files", []):
                    if file in str(local_path):
                        skipped = True
                        break

                if skipped:
                    self.stats["skipped"].append(str(local_path))
                    self.print(Fore.YELLOW + f" - Skipping file {entry['title']} (excluded)")
                else:
                    self.download_file(entry['id'], local_path)


        return dest

    def get_current_user(self):
        """
        Retrieves the name and email address of the currently authenticated user.
        """
        if not self.gdrive:
            self.print("Drive instance not initialized or authenticated.")
            return None

        try:
            # Query Google Drive API for account metadata
            about = self.gdrive.GetAbout()
            user_info = about.get('user', {})
            return user_info.get("displayName"), user_info.get("emailAddress")

        except Exception as e:
            self.print(f"Error retrieving user info: {e}")
            return None, None

class Sheets:

    def __init__(self, **kwargs):
        self.gc = None
        self.wb = None
        self.worksheets = None
        self.worksheets_names = None
        self.arg_yes = kwargs.get("yes", False)
        self.config_dir = kwargs.get("config_dir", ".")
        if kwargs.get("authorize", True):
            self.authorize()

    def authorize(self):
        self.gc = gspread.oauth(credentials_filename=self.config_dir + os.sep + "client_secret.json",
                                authorized_user_filename=self.config_dir + os.sep + "token.json")

    def open(self, workbook):
        self.wb = self.gc.open(workbook)
        self.worksheets = self.wb.worksheets()
        self.worksheets_names = [sheet.title for sheet in self.worksheets]

    def worksheet_exists(self, sheet_name):
        return sheet_name in self.worksheets_names

    def upload(self, csv_file, title, sep="\t"):

            if title in self.worksheets_names:
                if not self.arg_yes:
                    ok = input("Sheet {} already exists. Continue (y/N)? ".format(title))
                    if ok.lower() != "y":
                        return
                worksheet = self.wb.worksheet(title)
            else:
                worksheet = self.wb.add_worksheet(title, 0, 0)

            df = pandas.read_csv(csv_file, sep=sep, header=None)
            set_with_dataframe(worksheet, df, include_index=False, include_column_header=False, resize=True, allow_formulas=True)
            self.worksheets_names = [sheet.title for sheet in self.wb.worksheets()]



def download(self, sheet_name, dest_folder):
        ws = self.wb.worksheet(sheet_name)
        filename = dest_folder + os.sep + str(sheet_name + ".csv")

        if os.path.exists(filename) and not self.arg_yes:
            ok = input("File {} already exists. Overwrite (y/N)? ".format(filename))
            if ok.lower() != "y":
                return
            get_as_dataframe(ws, evaluate_formulas=True).to_csv(filename, index=False, header=False)



