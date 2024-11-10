from PyQt5.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox


class Dialog(QDialog):

    def __init__(self, widget):
        super().__init__()
        vbox = QVBoxLayout()
        self.setLayout(vbox)
        vbox.addWidget(widget)

        self.bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.bb.accepted.connect(self.accept)
        self.bb.rejected.connect(self.reject)

        vbox.addWidget(self.bb)