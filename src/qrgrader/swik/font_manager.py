import os
import re
import shutil
import sys
import tempfile

from PyQt5.QtCore import QObject, QStandardPaths
from PyQt5.QtGui import QFont, QFontDatabase
from fontTools import ttLib
from qrgrader.swik import utils


class SwikFont:
    def __init__(self, filename):
        self.path = filename
        self.nickname = None
        self.family_name = None
        self.full_name = None
        self.weight = 400
        self.italic = False
        self.subset = False
        self.supported = True


class Base14Font(SwikFont):
    def __init__(self, info):
        super().__init__(None)
        self.nickname = info.get('nickname')
        self.family = info.get('family')
        self.full_name = info.get('full_name')
        self.weight = info.get('weight')
        self.italic = self.nickname.endswith('Oblique') or self.nickname.endswith('Italic')
        self.subset = False
        self.supported = True

    def get_qfont(self, size=11):
        weight = FontManager.map_weigth_to_qfont(self.weight)
        font = QFont(self.family)
        font.setWeight(weight)
        font.setItalic(self.italic)
        font.setPointSizeF(size)
        return font


class Font(SwikFont):

    def __init__(self, path):
        super().__init__(path)
        self.nickname = path
        self.full_name = path
        self.get_font_info(path)

    def get_font_info(self, path):
        self.subset = '+' in path

        try:
            font = ttLib.TTFont(path)
            if font.has_key('name'):
                self.family_name = font['name'].getDebugName(1)
                self.full_name = font['name'].getDebugName(4) if font['name'].getDebugName(4) else self.full_name
                self.nickname = font['name'].getDebugName(6)
                self.nickname = self.nickname if not '+' in self.nickname else self.nickname.split('+')[1]
                modifiers = str(font['name'].getDebugName(2))
                modifiers = modifiers.lower()
                if font.has_key('OS/2'):
                    os2_table = font['OS/2']
                    weight_class = os2_table.usWeightClass
                    if type(weight_class) is not int:
                        sys.exit(1)
                else:
                    weight_class = 400

                self.weight = weight_class
                self.italic = 'italic' in modifiers or 'oblique' in modifiers
        except:
            font_name_match = re.search(r'\+(.+?)-\d+\.cff', os.path.basename(self.path))
            if font_name_match:
                self.nickname = font_name_match.group(1)
                self.full_name = self.nickname
            self.supported = False
            return None

    def get_qfont(self, size=11):
        idx = QFontDatabase.addApplicationFont(self.path)
        families = QFontDatabase.applicationFontFamilies(idx)
        if len(families) > 0:
            family = families[0]
        else:
            family = self.family_name

        if self.supported:
            weight = FontManager.map_weigth_to_qfont(self.weight)
            font = QFont(family)
            font.setWeight(weight)
            font.setItalic(self.italic)
            font.setPointSizeF(size)
            return font
        else:
            return None


class Arial(Font):
    def __init__(self):
        super().__init__(utils.get_font_path("Arial.ttf"))


class FontManager(QObject):
    base14_fonts_def = [
        {'full_name': 'Helvetica', 'path': None, 'family': 'Helvetica', 'weight': 400, 'nickname': 'helv', },
        {'full_name': 'Helvetica-Bold', 'path': None, 'family': 'Helvetica', 'weight': 700,
         'nickname': 'Helvetica-Bold', },
        {'full_name': 'Helvetica-Oblique', 'path': None, 'family': 'Helvetica', 'weight': 400,
         'nickname': 'Helvetica-Oblique', },
        {'full_name': 'Helvetica-BoldOblique', 'path': None, 'family': 'Helvetica', 'weight': 700,
         'nickname': 'Helvetica-BoldOblique', },
        {'full_name': 'Courier', 'path': None, 'family': 'Courier', 'weight': 400, 'nickname': 'Courier', },
        {'full_name': 'Courier-Bold', 'path': None, 'family': 'Courier', 'weight': 700, 'nickname': 'Courier-Bold', },
        {'full_name': 'Courier-Oblique', 'path': None, 'family': 'Courier', 'weight': 400,
         'nickname': 'Courier-Oblique', },
        {'full_name': 'Courier-BoldOblique', 'path': None, 'family': 'Courier', 'weight': 700,
         'nickname': 'Courier-BoldOblique', },
        {'full_name': 'Times-Roman', 'path': None, 'family': 'Times', 'weight': 400, 'nickname': 'Times-Roman', },
        {'full_name': 'Times-Bold', 'path': None, 'family': 'Times', 'weight': 700, 'nickname': 'Times-Bold', },
        {'full_name': 'Times-Italic', 'path': None, 'family': 'Times', 'weight': 400, 'nickname': 'Times-Italic', },
        {'full_name': 'Times-BoldItalic', 'path': None, 'family': 'Times', 'weight': 700,
         'nickname': 'Times-BoldItalic', },
        {'full_name': 'Symbol', 'path': None, 'family': 'Symbol', 'weight': 400, 'nickname': 'Symbol', },
        {'full_name': 'ZapfDingbats', 'path': None, 'family': 'ZapfDingbats', 'weight': 400,
         'nickname': 'ZapfDingbats', }
    ]

    base14_fonts = []
    system_fonts = []
    swik_fonts = []

    def __init__(self, renderer):
        super().__init__()
        self.renderer = renderer
        self.document_fonts = []
        self.font_dir = None

    def clear_document_fonts(self):
        self.document_fonts.clear()
        if self.font_dir is not None:
            shutil.rmtree(self.font_dir, ignore_errors=True)
        self.font_dir = None

    def update_document_fonts(self):
        if len(self.document_fonts) == 0:
            self.font_dir = tempfile.mkdtemp()
            self.renderer.save_fonts(self.font_dir)
            fonts = self.get_fonts([self.font_dir])
            self.document_fonts.extend(fonts)

    @staticmethod
    def get_system_fonts():
        FontManager.update_system_fonts()
        return FontManager.system_fonts

    def get_document_fonts(self):
        self.update_document_fonts()
        return self.document_fonts

    def filter(self, section=None, **kwargs):
        self.update_fonts()
        if section is not None:
            if section == 'document':
                fonts = self.document_fonts
            elif section == 'swik':
                fonts = self.swik_fonts
            elif section == 'base14':
                fonts = self.base14_fonts
            elif section == 'system':
                fonts = self.system_fonts
            else:
                raise ValueError("Invalid section")
        else:
            fonts = self.swik_fonts + self.base14_fonts + self.system_fonts + self.document_fonts

        pos = kwargs.pop('pos', None)
        fallback = kwargs.pop('fallback', None)

        for key, value in kwargs.items():
            fonts = [f for f in fonts if getattr(f, key) == value]
        fonts.sort(key=lambda x: x.full_name.lower())

        if pos is not None:
            if len(fonts) > pos:
                fonts = fonts[pos]
            else:
                fonts = None

        return fonts if fonts is not None else fallback

    @staticmethod
    def update_swik_fonts():
        if len(FontManager.swik_fonts) == 0:
            FontManager.swik_fonts = FontManager.get_fonts("fonts")

    @staticmethod
    def get_swik_fonts():
        FontManager.update_swik_fonts()
        return FontManager.swik_fonts

    @staticmethod
    def get_base14_fonts():
        FontManager.update_base_14_fonts()
        return FontManager.base14_fonts

    @staticmethod
    def update_base_14_fonts():
        if len(FontManager.base14_fonts) == 0:
            for base14 in FontManager.base14_fonts_def:
                font = Base14Font(base14)
                FontManager.base14_fonts.append(font)

    @staticmethod
    def update_system_fonts(force=False):
        if len(FontManager.system_fonts) == 0:
            FontManager.system_fonts = FontManager.gather_system_fonts()

    def update_fonts(self):
        self.update_system_fonts()
        self.update_swik_fonts()
        self.update_base_14_fonts()
        self.update_document_fonts()

    @staticmethod
    def map_weigth_to_qfont(weight):
        weight_class_mapping = {
            100: QFont.Thin,
            200: QFont.ExtraLight,
            300: QFont.Light,
            400: QFont.Normal,
            500: QFont.Medium,
            600: QFont.DemiBold,
            700: QFont.Bold,
            800: QFont.ExtraBold,
            900: QFont.Black
        }
        return weight_class_mapping.get(weight, QFont.Normal)

    @staticmethod
    def get_fonts(font_paths):
        fonts = []
        if type(font_paths) is not list:
            font_paths = [font_paths]
        for fpath in font_paths:  # go through all font paths
            if os.path.isdir(fpath):
                walk = os.walk(fpath)
                for root, dirs, files in walk:
                    for filename in files:
                        if filename[-4:].lower() in ['.ttf', '.otf', '.ttc', '.cff', '.pfa',
                                                     '.pfb', '.pfm', '.woff', '.woff2', '.eot',
                                                     '.svg', '.bmp', '.cff']:
                            path = os.path.join(root, filename)
                            # print("Path: ", path)
                            font = Font(path)
                            fonts.append(font)

        fonts.sort(key=lambda x: x.full_name)
        return fonts

    @staticmethod
    def gather_system_fonts():
        font_paths = QStandardPaths.standardLocations(QStandardPaths.FontsLocation)
        return FontManager.get_fonts(font_paths)
