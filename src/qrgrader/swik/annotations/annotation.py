from PyQt5.QtWidgets import QDialog

from qrgrader.swik.action import Action
from qrgrader.swik.color_widget import ColorAlphaAndWidth, ColorAndAlpha, TextLineEdit
from qrgrader.swik.dialogs import ComposableDialog
from qrgrader.swik.resizeable import ResizableRectItem


class Annotation(ResizableRectItem):

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.content = str()
        self.name = str()

    def set_content(self, text):
        self.content = text

    def set_name(self, name):
        self.name = name

    def get_content(self):
        return self.content

    def mouseDoubleClickEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mouseDoubleClickEvent(event)
        self.change_color()

    def change_color(self):
        before = self.get_full_state()

        color = ComposableDialog()
        color.add_row("Content", TextLineEdit(self.content))
        color.add_row("Border", ColorAlphaAndWidth(self.pen()))
        color.add_row("Fill", ColorAndAlpha(self.brush().color()))

        if color.exec() == QDialog.Accepted:
            self.set_border_color(color.get("Border").get_color())
            self.set_border_width(color.get("Border").get_width())
            c1 = color.get("Fill").get_color()
            self.set_fill_color(color.get("Fill").get_color())
            self.set_content(color.get("Content").get_text())
            self.setToolTip(self.get_content())

        if self.get_full_state() != before:
            self.notify_change(Action.ACTION_ANNOT_CHANGED, before, self.get_full_state())

    def undo(self, kind, info):
        super().undo(kind, info)
        self.set_full_state(info)

# Compare this snippet from annotations/annotation.py: