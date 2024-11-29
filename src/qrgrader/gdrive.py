import os

import gspread
from gspread.utils import a1_to_rowcol, ValueInputOption
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

from qrgrader.common import get_narrowest_type


class GDrive:

    def __init__(self, config_dir=".", **kwargs):
        self.gdrive = None
        self.config_dir = config_dir
        if kwargs.get("authorize", True):
            self.authorize()

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
        file = self.gdrive.CreateFile({'title': os.path.basename(filename), 'parents': [{'id': folder_id}]})
        file.SetContentFile(filename)
        file.Upload()
        return file['id']


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
