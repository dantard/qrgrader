import os
import qrgrader.swik.fonts
import shutil
from pathlib import Path
from subprocess import Popen

import psutil
from PyQt5.QtCore import QObject, pyqtSignal, QRectF, QRect, Qt, QTimer
from PyQt5.QtGui import QImage, QColor
from PyQt5.QtWidgets import QGraphicsRectItem, QGraphicsItem, QHBoxLayout, QLabel, QSizePolicy, QFrame, QGroupBox, QVBoxLayout, QWidget, QMessageBox, QCheckBox
from pymupdf import pymupdf


class Signals(QObject):
    done = pyqtSignal(QGraphicsRectItem)
    moving = pyqtSignal(QGraphicsRectItem)
    resizing = pyqtSignal(QGraphicsRectItem)
    creating = pyqtSignal(QGraphicsRectItem)
    action = pyqtSignal(int, object)
    item_added = pyqtSignal(QGraphicsItem)
    item_removed = pyqtSignal(QGraphicsItem)
    item_changed = pyqtSignal(QGraphicsItem)
    discarded = pyqtSignal()


def check_parent_limits(parent: QGraphicsRectItem, scene_x, scene_y):
    if parent is not None:
        pos_on_item = parent.mapFromScene(scene_x, scene_y)
        x, y = pos_on_item.x(), pos_on_item.y()
        x = parent.rect().x() if x < parent.rect().x() else x
        x = parent.rect().x() + parent.rect().width() if x > parent.rect().x() + parent.rect().width() else x
        y = parent.rect().y() if y < parent.rect().y() else y
        y = parent.rect().y() + parent.rect().height() if y > parent.rect().y() + parent.rect().height() else y
        point_on_scene = parent.mapToScene(x, y)
        x, y = point_on_scene.x(), point_on_scene.y()
    else:
        x, y = scene_x, scene_y

    return x, y


def fitz_rect_to_qrectf(rect):
    return QRectF(rect.x0, rect.y0, rect.x1 - rect.x0, rect.y1 - rect.y0)


def qrectf_to_fitz_rect(rect):
    return pymupdf.Rect(rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height())


def qrectf_and_pos_to_fitz_rect(rect, pos):
    return pymupdf.Rect(pos.x(), pos.y(), pos.x() + rect.width(), pos.y() + rect.height())


def qcolor_to_fitz_color(color: QColor):
    if color == Qt.transparent:
        return None
    return color.red() / 255, color.green() / 255, color.blue() / 255


def fitz_color_to_qcolor(color, opacity=1):
    color = QColor(int(color[0] * 255), int(color[1] * 255), int(color[2] * 255),
                   int(opacity * 255)) if color else Qt.transparent
    return color


def adjust_crop2(image: QImage, ratio=1.0) -> QRectF:
    w = image.width()
    h = image.height()
    f = h / w

    for i in range(100, w):
        white = QColor(Qt.white)
        h1 = f * i
        w1 = i
        x1, y1 = int(w / 2 - w1 / 2), int(h / 2 - h1 / 2)
        x2, y2 = int(x1 + w1), int(y1 + h1)

        ok = True
        for x in range(x1, x2):
            color_up = QColor(image.pixel(x, y1))
            color_down = QColor(image.pixel(x, y2))
            if color_up != white or color_down != white:
                ok = False
                break

        for y in range(y1, y2):
            color_left = QColor(image.pixel(x1, y))
            color_right = QColor(image.pixel(x2, y))
            if color_left != white or color_right != white:
                ok = False
                break

        if ok:
            return QRectF(x1 / ratio, y1 / ratio, (x2 - x1) / ratio, (y2 - y1) / ratio)

    return None


def adjust_crop(image: QImage, ratio=1.0, level=255) -> QRectF:
    # Create a QColor object to represent white

    # Initialize variables for the dimensions of the smallest rectangle
    # that contains non-white pixels
    left = image.width()
    top = image.height()
    right = 0
    bottom = 0

    # Iterate over all pixels in the image
    for x in range(image.width()):
        for y in range(image.height()):
            # Get the color of the current pixel
            color = QColor(image.pixel(x, y))
            r, g, b = color.red(), color.green(), color.blue()
            # If the color is not white, update the dimensions of the
            # smallest rectangle that contains non-white pixels
            if r < level or g < level or b < level:
                left = min(left, x)
                top = min(top, y)
                right = max(right, x)
                bottom = max(bottom, y)

    # Return the smallest rectangle that contains non-white pixels
    return QRectF(left / ratio, top / ratio, (right - left) / ratio + 2, (bottom - top) / ratio + 2)
    # return QRect(left, top, right - left + 1, bottom - top + 1)/ratio


def are_other_instances_running():
    swiks = [p for p in psutil.process_iter() if len(p.cmdline()) > 1 and "swik" in p.cmdline()[1]]
    # And their PID
    pids = [p.pid for p in swiks]
    # Remove my PID
    pids.remove(os.getpid())
    # Remove all the swiks that are children (worker for the real swik)
    for swik in swiks:
        for p in swik.children():
            if p.pid in pids:
                pids.remove(p.pid)

    if len(pids) == 0:
        return -1
    else:
        swik = psutil.Process(pids[-1])
        # Get other instance port
        return swik.connections()[0][3][1]


def update_value(method, dictionary, key):
    method(dictionary[key] if key in dictionary else None)


def delayed(delay, func, *args):
    QTimer.singleShot(delay, lambda: func(*args))


def int_to_roman(number):
    num = [1, 4, 5, 9, 10, 40, 50, 90,
           100, 400, 500, 900, 1000]
    sym = ["I", "IV", "V", "IX", "X", "XL",
           "L", "XC", "C", "CD", "D", "CM", "M"]
    i = 12
    res = str()
    while number:
        div = number // num[i]
        number %= num[i]

        while div:
            res += sym[i]
            div -= 1
        i -= 1
    return res


colors = [Qt.black, Qt.red, Qt.green, Qt.blue, Qt.magenta, Qt.cyan, Qt.darkRed, Qt.darkGreen, Qt.darkBlue, Qt.white]


def get_color(index, alpha=1):
    color = QColor(colors[index % len(colors)])
    color.setAlpha(int(alpha * 255))
    return color


def row(w1, w2, all=True):
    h_layout = QHBoxLayout()
    if isinstance(w1, str):
        w1 = QLabel(w1)
        w1.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    h_layout.addWidget(w1)
    h_layout.addWidget(w2)
    if all:
        return h_layout, w1, w2

    return h_layout


def col(*args):
    v_layout = QVBoxLayout()

    for w in args:
        if type(w) == str:
            w1 = QLabel(w)
            v_layout.addWidget(w1)
            w1.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        elif isinstance(w, QWidget):
            v_layout.addWidget(w)
        else:
            v_layout.addLayout(w)

    return v_layout


def separator():
    hLine = QFrame()
    hLine.setFrameShape(QFrame.HLine)
    hLine.setFrameShadow(QFrame.Sunken)
    return hLine


def framed(widget, title=None):
    frame = QGroupBox()
    frame.setStyleSheet(
        "QGroupBox {border: 1px solid silver; border-radius: 2px; margin-top: 10px;}"
        "QGroupBox::title { subcontrol-origin: margin;    left: 7px;  padding: 0px 5px 0px 5px;}")

    frame.setTitle(title if title else "")
    frame.setLayout(QVBoxLayout())

    if isinstance(widget, QWidget):
        frame.layout().addWidget(widget)
    else:
        frame.layout().addLayout(widget)

    return frame


def get_font_path(name):
    return swik.fonts.__path__[0] + os.sep + name


def get_warning_messagebox(text, icon=QMessageBox.Warning, title=None, parent=None):
    msg = QMessageBox()
    msg.setWindowTitle(title if title else "Warning")
    msg.setParent(parent)
    msg.setIcon(icon)
    msg.setText(text)
    msg.setStandardButtons(QMessageBox.Yes)
    msg.addButton(QMessageBox.Cancel)
    # msg.setDefaultButton(QMessageBox.Cancel)

    check_box = QCheckBox("Don't show this again")
    msg.setCheckBox(check_box)
    return msg.exec() == QMessageBox.Yes, check_box.isChecked()


def add_mimeapps_entry(section, name):
    # Path to the mimeapps.list file
    mimeapps_list_path = os.path.expanduser("~/.config/mimeapps.list")

    # The entry to be added or modified
    default_app_entry = "application/pdf=" + name + "\n"

    # Read the current content of mimeapps.list
    if os.path.exists(mimeapps_list_path):
        with open(mimeapps_list_path, "r") as file:
            lines = file.readlines()
    else:
        lines = []

    # Check if the [Default Applications] section exists
    section_found = False
    for i, line in enumerate(lines):
        if line.strip() == section:
            section_found = True
            # Check if there's already an entry for application/pdf
            for j in range(i + 1, len(lines)):
                if lines[j].startswith("application/pdf=swik"):
                    lines[j] = default_app_entry
                    break
            else:
                # Add the entry if it doesn't exist
                lines.insert(i + 1, default_app_entry)
            break

    # If the section doesn't exist, add it
    if not section_found:
        lines.append(section + "\n")
        lines.append(default_app_entry)

    # Write the updated content back to mimeapps.list
    with open(mimeapps_list_path, "w") as file:
        file.writelines(lines)


def filter_out_dict(d, keys):
    return {k: v for k, v in d.items() if k not in keys}


def get_different_keys(old: dict, new: dict, ignore_keys=None):
    return {k: v for k, v in new.items() if new[k] != old[k] and k not in (ignore_keys if ignore_keys else [])}


def word_to_pdf(doc):
    office = shutil.which("soffice")
    if not office:
        return -4
    real_path = os.path.realpath(office)
    office_dir = os.path.dirname(real_path)

    _, ext = os.path.splitext(doc)
    if ext in ['.docx', '.doc'] and not os.path.exists(office_dir + os.sep + "swriter"):
        return -1
    if ext in ['.pptx', '.ppt'] and not os.path.exists(office_dir + os.sep + "sdraw"):
        return -2
    if ext in ['.xlsx', '.xls'] and not os.path.exists(office_dir + os.sep + "scalc"):
        return -3

    out_dir = os.path.dirname(doc)
    p = Popen([office, '--headless', '--convert-to', 'pdf', '--outdir', out_dir, doc])
    p.communicate()

    return p.returncode
