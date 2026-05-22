import os
from datetime import datetime, timezone

import gspread
from gspread.utils import a1_to_rowcol, ValueInputOption
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from pathlib import Path

from qrgrader import utils
from qrgrader.common import get_narrowest_type

FOLDER_MIME = "application/vnd.google-apps.folder"


class GDrive:

    def __init__(self, config_dir=".", **kwargs):
        self.stats = {"downloaded": [], "uploaded": [], "conflict": [],
                      "skipped_files": [], "skipped_dir": [], "excluded": []}
        self.gdrive = None
        self.config_dir = config_dir

        if kwargs.get("authorize", True):
            self.authorize()

    def reset_stats(self):
        self.stats = {"downloaded": [], "uploaded": [], "skipped_files": [], "skipped_dir": [], "excluded": []}


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

        if online_files:
            file_info = online_files[0]
            file_id = file_info.get('id')
            drive_md5 = file_info.get('md5Checksum')
            online_mtime = file_info.get("modifiedDate")
            online_mtime = datetime.fromisoformat(online_mtime.replace('Z', '+00:00'))

            if drive_md5 == local_md5:
                self.stats["skipped_files"].append(name)
                os.utime(filename, (online_mtime.timestamp(), online_mtime.timestamp()))
            elif local_mtime > online_mtime :
                file = self.gdrive.CreateFile({'id': online_files[0]['id']})
                file.SetContentFile(filename)
                file.Upload()
                self.stats["uploaded"].append(name)
            else:
                self.stats["conflict"].append(name)
        else:
            file = self.gdrive.CreateFile({'title': name, 'parents': [{'id': folder_id}]})
            file.SetContentFile(filename)
            file.Upload()
            self.stats["uploaded"].append(name)
            file_id = file.get('id')

        return file_id

    def create_folder(self, name, parent_id="root"):
        folder = self.gdrive.CreateFile({
            "title": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [{"id": parent_id}],
        })
        folder.Upload()
        return folder["id"]

    def delete_folder(self, folder_id):
        file = self.gdrive.CreateFile({'id': folder_id})
        file.Delete()

    def upload_directory(self, local_dir: str, parent_id="root", exclude=None, overwrite=False, is_root=True):
        local_dir = Path(local_dir)
        if is_root:
            if overwrite:
                query = f"title = '{local_dir.name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false and '{parent_id}' in parents"
                existing = self.gdrive.ListFile({'q': query}).GetList()
                if existing:
                    #print(f"Deleting existing '{local_dir.name}/'...")
                    self.delete_folder(existing[0]['id'])
                folder_id = self.create_folder(local_dir.name, parent_id)
            else:
                query = f"title = '{local_dir.name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false and '{parent_id}' in parents"
                existing = self.gdrive.ListFile({'q': query}).GetList()
                if existing:
                    folder_id = existing[0]['id']
                    #print(f"Entering {local_dir.name}/ (existing)")
                else:
                    folder_id = self.create_folder(local_dir.name, parent_id)
                    #print(f"Entering {local_dir.name}/")
        else:
            folder_id = parent_id

        exclude = exclude or []
        #print(f"Entering {local_dir.name}/")

        for entry in sorted(local_dir.iterdir()):
            if entry.is_dir():
                if entry.name in exclude:
                    #print(f"Skipping directory {entry.name}/")
                    self.stats["skipped_dir"].append(entry.name)
                    continue
                self.upload_directory(entry, parent_id=folder_id, exclude=exclude)
            elif entry.is_file():
                if entry.name in exclude:
                    self.stats["excluded"].append(entry.name)
                    continue
                self.upload_file(str(entry), folder_id)
                print(f"Uploaded {len(self.stats['uploaded'])}, Skipped {len(self.stats['skipped_files'])}, "
                      f"Conflict {len(self.stats['conflict'])} Processing: {str(entry)}                                        ", end="\r")

        return folder_id
    def update_download(self, folder_id: str, dest: str):
        self.download_directory(folder_id, dest, is_root=False)

    def update_upload(self, folder_id: str, local_dir: str):
        self.upload_directory(local_dir, parent_id=folder_id, is_root=False)

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
                self.stats["skipped_files"].append(local_path.name)
                os.utime(local_path, (online_mtime.timestamp(), online_mtime.timestamp()))
            elif online_mtime > local_mtime:
                f.GetContentFile(str(local_path))
                os.utime(local_path, (online_mtime.timestamp(), online_mtime.timestamp()))
                self.stats["downloaded"].append(local_path.name)
            else:
                self.stats["conflict"].append(local_path.name)
        else:
            f.GetContentFile(str(local_path))
            os.utime(local_path, (online_mtime.timestamp(), online_mtime.timestamp()))
            self.stats["downloaded"].append(local_path.name)

        return file_id





    def download_directory(self, folder_id: str, dest: str, is_root=True):
        dest = Path(dest)

        if is_root:
            meta = self.gdrive.CreateFile({'id': folder_id})
            meta.FetchMetadata(fields="title")
            dest = dest / meta['title']

        dest.mkdir(parents=True, exist_ok=True)

        entries = self.gdrive.ListFile(
            {'q': f"'{folder_id}' in parents and trashed=false"}
        ).GetList()

        for entry in sorted(entries, key=lambda e: e['title']):
            local_path = dest / entry['title']

            if entry['mimeType'] == FOLDER_MIME:
                # print(f"Entering {local_path}")
                self.download_directory(entry['id'], local_path, is_root=False)
            else:
                # print(f"Downloading {entry['title']}")
                self.download_file(entry['id'], local_path)
                print(f"Downloaded {len(self.stats['downloaded'])}, Skipped {len(self.stats['skipped_files'])}, "
                      f"Conflict {len(self.stats['conflict'])}, Processing {local_path}                          ", end="\r")


class Sheets:

    def __init__(self, **kwargs):
        self.base_folder = kwargs.get("base_folder", "../..")
        self.config_dir = kwargs.get("config_dir", "../..")
        self.gc = None
        self.wb = None
        self.woksheets = None
        self.woksheets_names = None
        if kwargs.get("authorize", True):
            self.authorize()

    def authorize(self):
        self.gc = gspread.oauth(credentials_filename=self.config_dir + os.sep + "client_secret.json",
                                authorized_user_filename=self.config_dir + os.sep + "token.json")

    def open(self, args_workbook):
        self.wb = self.gc.open(args_workbook)
        self.woksheets = self.wb.worksheets()
        self.woksheets_names = [sheet.title for sheet in self.woksheets]

    def set_base_folder(self, folder):
        self.base_folder = folder

    def upload_all(self, args_filter=None, args_yes=False):
        csv_files = [self.base_folder + os.sep + f for f in os.listdir(self.base_folder) if f.endswith(".csv")]

        if args_filter is not None:
            csv_files = [f for f in csv_files if args_filter in f]

        self._upload(csv_files, args_yes=args_yes)

    def upload(self, filename, args_yes=False):
        self._upload([self.base_folder + os.sep + f for f in filename], args_yes)

    def _upload(self, csv_files, args_yes=True, sep="\t"):

        for csv_file in csv_files:

            info = csv_file.split(":")
            if len(info) == 2:
                csv_file, corner = info
            else:
                csv_file, corner = info[0], "A1"

            print("Uploading file {} at corner: {}".format(csv_file, corner))

            title = str(os.path.basename(csv_file).replace(".csv", ""))

            row, col = a1_to_rowcol(corner)

            if title in self.woksheets_names:
                if not args_yes:
                    ok = input("Sheet {} already exists. Continue (Y/n)? ".format(title))
                    if ok.lower() != "y":
                        continue
                new_ws = self.wb.worksheet(title)
                rows = max(new_ws.row_count, row)
                cols = max(new_ws.col_count, col)
                new_ws.resize(rows, cols)
            else:
                new_ws = self.wb.add_worksheet(title, row, col)

            if len(csv_file.split(".")) == 1:
                csv_file += ".csv"

            with open(csv_file, "r", encoding='utf-8') as f:
                data = f.readlines()
                data = [line.strip().split(sep) for line in data]

                for row in data:
                    for i in range(len(row)):
                        row[i] = get_narrowest_type(row[i])

            # print("Uploading sheet {}".format(title))
            new_ws.update(data, corner, value_input_option=ValueInputOption.user_entered)

    def download(self, args_sheet, args_yes=False):
        self._download(args_sheet, self.base_folder, args_yes)

    def download_all(self, args_filter=None, args_yes=False):
        # Download files
        sheets_to_download = self.woksheets_names
        if args_filter is not None:
            sheets_to_download = [sheet for sheet in sheets_to_download if args_filter in sheet]
        self._download(sheets_to_download, self.base_folder, args_yes)

    def _download(self, sheets_to_download, args_folder, args_yes=False):
        for sheet in sheets_to_download:
            ws = self.wb.worksheet(sheet)
            filename = args_folder + os.sep + str(sheet + ".csv")

            if os.path.exists(filename) and not args_yes:
                ok = input("File {} already exists. Overwrite (Y/n)? ".format(filename))
                if ok.lower() != "y":
                    continue
            with open(filename, "w", encoding='utf-8') as f:
                print("Downloading sheet {}".format(sheet))
                data = ws.get_all_values()
                for line in data:
                    f.write(",".join(line) + "\n")

    def diff(self, args_diff):
        self._diff(args_diff, self.base_folder)

    def _diff(self, args_diff, args_folder, sep="\t"):
        if args_diff:
            ws = self.wb.worksheet(args_diff)
            ws_data = ws.get_all_values()

            filename = args_folder + os.sep + str(args_diff + ".csv")
            with open(filename, "r", encoding='utf-8') as f:
                data = f.readlines()
                data = [line.strip().split(sep) for line in data]

            data_len = len(data)
            ws_len = len(ws_data)

            if data_len != ws_len:
                print("Data have different number of rows")
                print("Local:  ", data_len)
                print("Remote: ", ws_len)

            min_length = min(data_len, ws_len)

            for i in range(min_length):
                if data[i] != ws_data[i]:
                    print("Row {}:".format(i))
                    print("Local:  ", str(data[i]).replace("'", ""))
                    print("Remote: ", str(ws_data[i]).replace("'", ""))
                    print("")
