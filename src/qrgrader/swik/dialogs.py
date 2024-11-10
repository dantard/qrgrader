from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialogButtonBox, QDialog, QLabel, QVBoxLayout, QGroupBox, QLineEdit, QCheckBox, \
    QTreeWidget, QTreeWidgetItem, \
    QComboBox, QPushButton, QFileDialog, QHBoxLayout, QInputDialog, QMessageBox, QFormLayout, QTextEdit
from cryptography.hazmat._oid import NameOID
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12

import qrgrader.swik.utils as utils
from qrgrader.swik.color_widget import FontPicker, Color
from qrgrader.swik.font_manager import FontManager, Arial
from qrgrader.swik.progressing import Progressing
from OpenSSL import crypto


class ComposableDialog(QDialog):
    def __init__(self, start_enabled=True, title="Edit"):
        super().__init__()
        self.rows = {}
        self.initUI(title)
        if not start_enabled:
            self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)

    def set_ok_enabled(self, enabled):
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(enabled)

    def initUI(self, title):
        self.setWindowTitle(title)

        layout = QVBoxLayout()

        self.setLayout(layout)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

    def exec(self):
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout().addWidget(self.button_box)
        return super().exec()

    def add_row(self, label, widget):
        layout = QVBoxLayout()
        widget.enable.connect(lambda x: self.button_box.button(QDialogButtonBox.Ok).setEnabled(x))

        gb = QGroupBox(label)
        gb.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)

        self.rows[label] = widget
        layout.addWidget(widget)
        self.layout().addWidget(gb)
        return widget

    def get(self, label):
        return self.rows[label]


class PasswordDialog(QDialog):
    def __init__(self, checkbox=True, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Password")
        layout = QVBoxLayout(self)
        self.lb = QLabel("Password")
        self.le = QLineEdit()
        self.le.setEchoMode(QLineEdit.Password)
        self.cb = QCheckBox("Save Password")
        layout.addWidget(self.lb)
        layout.addWidget(self.le)
        if checkbox:
            layout.addWidget(self.cb)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(bb)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)

    def getText(self):
        return self.le.text()

    def getCheckBox(self):
        return self.cb.isChecked()

    def closeEvent(self, a0):
        pass


class FontAndColorDialog(ComposableDialog):
    def __init__(self, font_manager, font_name, font_size, text_color):
        super().__init__()
        self.font_manager: FontManager = font_manager
        self.font_picker = self.add_row("Font", FontPicker())
        self.color_picker = self.add_row("Text Color", Color(text_color))
        self.set_ok_enabled(False)
        self.progressing = None
        utils.delayed(100, self.update_fonts, font_name, font_size)

    def update_fonts(self, default, font_size):
        def process():
            self.font_manager.update_fonts()

            parent = self.font_picker.add_section("Base14 Fonts")
            self.font_picker.add_elements(parent, self.font_manager.get_base14_fonts())

            parent = self.font_picker.add_section("Swik Fonts")
            self.font_picker.add_elements(parent, self.font_manager.get_swik_fonts())

            parent = self.font_picker.add_section("System Fonts")
            self.font_picker.add_elements(parent, self.font_manager.get_system_fonts())

            parent = self.font_picker.add_section("Document Fonts")
            sec1 = self.font_picker.add_section("Fully embedded", parent)
            sec2 = self.font_picker.add_section("Subset", parent)
            sec3 = self.font_picker.add_section("Unsupported", parent)
            self.font_picker.add_elements(sec1, self.font_manager.filter('document', subset=False, supported=True))
            self.font_picker.add_elements(sec2, self.font_manager.filter('document', subset=True, supported=True))
            self.font_picker.add_elements(sec3, self.font_manager.filter('document', supported=False), use_own_font=False)

            # Set the default font and highlight it
            self.font_picker.set_default(default, font_size)

        self.progressing = Progressing(self, 0, "Updating Fonts")
        self.progressing.start(process)

    def get_font(self):
        return self.font_picker.get_font()

    def get_font_size(self):
        return self.font_picker.get_font_size()

    def get_text_color(self):
        return self.color_picker.get_color()


def FontTextAndColor(FontAndColorDialog):
    pass


class ImportDialog(QDialog):

    def __init__(self, text, filter, path=None, nickname=None, parent=None):
        super().__init__()
        self.setWindowTitle(text)
        # self.setWindowIcon(QIcon(ICON_PATH))
        self.setMinimumWidth(400)
        self.filter = filter
        self.setWindowFlags(Qt.Window)
        self.setWindowModality(Qt.ApplicationModal)
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.path = path

        self.lb = QLabel("Select the file to import")
        layout.addWidget(self.lb)
        h_layout = QHBoxLayout()

        self.le = QLineEdit(path)
        self.le.setReadOnly(True)
        self.pb = QPushButton("...")
        self.pb.clicked.connect(self.browse)
        self.pb.setFixedSize(25, 25)
        self.clear_btn = QPushButton("✕")
        self.clear_btn.setFixedSize(25, 25)
        self.clear_btn.clicked.connect(self.cleared)
        h_layout.addWidget(self.le)
        h_layout.addWidget(self.pb)
        h_layout.addWidget(self.clear_btn)
        layout.addLayout(h_layout)
        layout.addWidget(QLabel("Nickname"))
        self.nickname = QLineEdit(nickname)
        layout.addWidget(self.nickname)
        self.nickname.textChanged.connect(self.check_interaction)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(bb)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        self.ok_btn = bb.button(QDialogButtonBox.Ok)
        self.check_interaction()

    def cleared(self):
        self.le.clear()
        self.check_interaction()

    def check_interaction(self):
        ok = self.nickname.text() != "" and self.le.text() != ""
        self.ok_btn.setEnabled(ok)

    def browse(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select File", self.path, self.filter)
        if file:
            self.le.setText(file)
            self.nickname.setText(Path(file).stem)
            self.check_interaction()

    def get_file(self):
        return self.le.text()

    def get_nickname(self):
        return self.nickname.text()


class ImportP12(ImportDialog):

    def read_p12_file(self, file_path, password):
        with open(file_path, 'rb') as file:
            p12_data = file.read()

        p12 = pkcs12.load_key_and_certificates(p12_data, password.encode(), backend=default_backend())
        certificates = p12[1]
        subject = certificates.subject
        common_name = subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        return common_name

    def browse(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select File", "", self.filter)
        if file:
            password, ok = QInputDialog.getText(self, "Password", "Enter the password (it will NOT be stored)",
                                                QLineEdit.Password)
            if ok:
                try:
                    common_name = self.read_p12_file(file, password)
                    self.nickname.setText(common_name)
                except Exception as e:
                    QMessageBox.critical(self, "Error", str(e))
                    return
                self.le.setText(file)
            self.check_interaction()


class DictDialog(QDialog):

    def __init__(self, input_dict, ignore=None, parent=None):
        super(DictDialog, self).__init__(parent)

        ignore = [] if ignore is None else ignore

        self.setWindowTitle("Input Dialog")
        self.input_dict = input_dict  # Store the input dictionary

        # Create the form layout
        self.form_layout = QFormLayout()

        # Iterate over the dictionary and add labels and line edits to the form layout
        for key, value in input_dict.items():
            label = key
            line_edit = QLineEdit()
            line_edit.setText(value)
            if key in ignore:
                line_edit.setEnabled(False)
            self.form_layout.addRow(label, line_edit)
            line_edit.home(True)

        # Create the button box with OK and Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # Create the main layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(self.form_layout)
        main_layout.addWidget(button_box)

        self.setLayout(main_layout)
        self.setMinimumWidth(400)

    def get_dict(self):
        # Update the values in the input dictionary with the new values from the line edits
        for i in range(self.form_layout.rowCount()):
            label_widget = self.form_layout.itemAt(i, QFormLayout.LabelRole).widget()
            line_edit_widget = self.form_layout.itemAt(i, QFormLayout.FieldRole).widget()
            label = label_widget.text()
            value = line_edit_widget.text()
            self.input_dict[label] = value
        return self.input_dict


class TextBoxDialog(QDialog):

    def __init__(self, text, title="", parent=None):
        super(TextBoxDialog, self).__init__(parent)

        self.setWindowTitle(title)

        # Create the form layout
        self.form_layout = QVBoxLayout()

        # Create the text box
        self.text_box = QTextEdit()
        self.text_box.setPlainText(text)

        # Create the button box with OK and Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # Create the main layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.text_box)
        main_layout.addWidget(button_box)

        self.setLayout(main_layout)
        self.setMinimumWidth(400)

    def get_text(self):
        return self.text_box.toPlainText()


class EnumerateDialog(QDialog):

    def __init__(self, view, font_manager):
        super().__init__()

        self.view = view
        self.font_manager = font_manager
        self.layout = QVBoxLayout()
        f_layout = QFormLayout()
        self.layout.addLayout(f_layout)
        self.from_cb = QComboBox()
        self.from_cb.addItems(str(i) for i in range(1, len(self.view.pages) + 1))
        self.from_cb.currentIndexChanged.connect(self.from_changed)

        self.to_cb = QComboBox()
        self.from_changed(0)

        self.first_page = QComboBox()
        self.first_page.addItems(str(i) for i in range(1, len(self.view.pages) + 1))

        self.text_te = QLineEdit("$i")
        self.text_te.setAlignment(Qt.AlignCenter)
        self.text_te.setPlaceholderText("Use $i for the number")

        self.style_cb = QComboBox()
        self.style_cb.addItems(["Arabic (1, 2, ...)", "Roman (lvxi, ...)", "Roman (LVI, ...)"])

        self.oddeven_db = QComboBox()
        self.oddeven_db.addItems(["Both", "Odd", "Even"])

        f_layout.addRow("Style", self.style_cb)
        f_layout.addRow("From", self.from_cb)
        f_layout.addRow("To", self.to_cb)
        f_layout.addRow("Start with", self.first_page)
        f_layout.addRow("Text", self.text_te)
        f_layout.addRow("Pages", self.oddeven_db)

        font = Arial()
        self.font_btn = QPushButton(font.full_name)
        self.font_btn.setFont(font.get_qfont())
        self.font_btn.clicked.connect(self.font_clicked)
        f_layout.addRow("Font", self.font_btn)

        anchor_cb = QComboBox()
        anchor_cb.addItems(["Top Left", "Top Right", "Bottom Left", "Bottom Right"])
        f_layout.addRow("Anchor", anchor_cb)

        # self.layout.addStretch(1)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)
        self.setLayout(self.layout)

    def font_clicked(self):
        font_dialog = FontAndColorDialog(self.font_manager, Arial(), 11, Qt.black)
        if font_dialog.exec() == FontAndColorDialog.Accepted:
            font, color = font_dialog.get("Font"), font_dialog.get("Text Color")
            self.font_btn.setFont(font.get_font().get_qfont())
            self.font_btn.setText(font.get_font().full_name)

    def from_changed(self, index):
        self.to_cb.clear()
        self.to_cb.addItems(str(i) for i in range(index + 1, len(self.view.pages) + 1))
        self.to_cb.setCurrentIndex(self.to_cb.count() - 1)


class DeveloperInfoDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("About Swik")
        self.setFixedSize(400, 220)

        layout = QVBoxLayout()

        # Program name and description
        program_name_label = QLabel("<h2>Swik - PDF Swiss Knife</h2>")
        version_label = QLabel("<h4>v0.31 Alpha</h4>")
        description_label = QLabel("Swik is a user-friendly PDF reader designed to provide\na seamless reading experience with advanced features.")

        # Developer information
        developer_info_label = QLabel("<b>Developed by</b>")
        developer_name_label = QLabel("Danilo Tardioli")
        contact_label = QLabel("Contact: dantard@unizar.es")

        # Adding widgets to layout
        layout.addWidget(program_name_label)
        layout.addWidget(version_label)
        layout.addWidget(description_label)
        layout.addSpacing(10)
        layout.addWidget(developer_info_label)
        layout.addWidget(developer_name_label)
        layout.addWidget(contact_label)
        layout.addStretch()

        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)
