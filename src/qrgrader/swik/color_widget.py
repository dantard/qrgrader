from PyQt5 import QtGui
from PyQt5.QtCore import QRectF, Qt, pyqtSignal, QItemSelectionModel
from PyQt5.QtGui import QPainter, QPixmap, QColor
from PyQt5.QtWidgets import QPushButton, QColorDialog, QWidget, QSlider, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QLabel, \
    QGroupBox, QTreeWidget, QTreeWidgetItem


class ColorWidget(QPushButton):
    enable = pyqtSignal(bool)

    def __init__(self, color, text=True):
        super().__init__()
        self.color = QColor(color)
        self.has_text = text
        self.opacity = 255
        self.order = 0
        self.clicked.connect(self.choose_color)

    def set_color(self, color):
        self.color = color
        self.update()

    def set_opacity(self, opacity):
        self.opacity = opacity
        self.update()

    def get_color(self):
        return self.color

    def get_color_with_alpha(self):
        # print(self.color.red(), self.color.green(), self.color.blue(), self.opacity)
        return QColor(self.color.red(), self.color.green(), self.color.blue(), self.opacity)

    def set_order(self, order):
        self.order = order

    def choose_color(self):
        color = QColorDialog.getColor(self.color)
        # color.setAlpha(self.opacity_slider.value())
        if color.isValid():
            self.set_color(color)

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        painter = QPainter(self)
        qr = QRectF(self.rect().x(), self.rect().y(), self.rect().width(), self.rect().height())

        def draw_text():
            if self.has_text:
                painter.drawText(qr, Qt.AlignCenter, "Example Text")

        def draw_color():
            pixmap = QPixmap(self.rect().width(), self.rect().height())
            # print(self.color.red(), self.color.green(), self.color.blue(), int(self.opacity * 255))
            if self.color != Qt.transparent:
                color = QColor(self.color.red(), self.color.green(), self.color.blue(), int(self.opacity))
                pixmap.fill(color)
                painter.drawPixmap(0, 0, pixmap)

        if self.order == 1:
            draw_color()
            draw_text()
        else:
            draw_text()
            draw_color()


class Color(QWidget):
    enable = pyqtSignal(bool)

    def __init__(self, color):
        super().__init__()
        r, g, b, a = QColor(color).getRgb()
        # print(r, g, b, a, "color")
        self.color_widget = ColorWidget(color)
        self.color_widget.set_order(2)
        self.layout = QFormLayout()
        self.layout.addRow("Color", self.color_widget)
        self.setLayout(self.layout)

    def get_color(self):
        return self.color_widget.get_color()


class ColorAndAlpha(Color):
    def __init__(self, color):
        super().__init__(color)
        r, g, b, a = color.getRgb()
        self.slider = QSlider(Qt.Horizontal)
        self.layout.addRow("Opacity", self.slider)
        self.slider.setRange(0, 255)
        self.slider.valueChanged.connect(self.color_widget.set_opacity)
        self.slider.setValue(a)

    def get_color(self):
        return self.color_widget.get_color_with_alpha()

    def get_opacity(self):
        return self.slider.value() / 100


class ColorAlphaAndWidth(ColorAndAlpha):
    def __init__(self, pen, width=1):
        super().__init__(pen.color())
        self.slider2 = QSlider(Qt.Horizontal)
        self.slider2.setRange(0, 10)
        self.slider2.setValue(pen.width())
        self.layout.addRow("Width", self.slider2)

    def get_width(self):
        return self.slider2.value()


class TextLineEdit(QLineEdit):
    enable = pyqtSignal(bool)

    def __init__(self, text, editable=True):
        super().__init__()
        self.setText(text)
        self.setReadOnly(not editable)

    def set_text(self, text):
        self.setText(text)

    def get_text(self):
        return self.text()


class FontPicker(QWidget):
    enable = pyqtSignal(bool)

    class TreeWidgetItem(QTreeWidgetItem):
        def __init__(self, font_info=None):
            super().__init__()
            self.font_info = font_info

    class TreeWidget(QTreeWidget):

        def selectionCommand(self, index, event=None):
            item: FontPicker.TreeWidgetItem = self.itemFromIndex(index)
            if not isinstance(item, FontPicker.TreeWidgetItem):
                return QItemSelectionModel.NoUpdate

            return super().selectionCommand(index, event)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.list_widget = self.TreeWidget()
        self.list_widget.header().hide()
        self.list_widget.setStyleSheet("QListWidget::item { height: 40px; }")
        layout.addWidget(self.list_widget)
        size_layout = QHBoxLayout()
        # pb = QPushButton("Show System Fonts")
        # pb.clicked.connect(self.show_system_fonts)
        # layout.addWidget(pb)
        layout.addLayout(size_layout)
        self.size = QSlider(Qt.Horizontal)
        self.size.setRange(4, 72)
        self.size.valueChanged.connect(self.set_font_size)
        self.size_label = QLabel("")
        self.size_label.setMinimumWidth(30)
        self.size_label.setAlignment(Qt.AlignRight)
        size_layout.addWidget(QLabel("Size"))
        size_layout.addWidget(self.size)
        size_layout.addWidget(self.size_label)
        self.example_label = QLabel()
        self.example_label.setMaximumWidth(300)
        self.example_label.setText("The red fox snuggled up to the lazy dog.")
        gb = QGroupBox("Example")
        gb.setLayout(QVBoxLayout())
        gb.layout().addWidget(self.example_label)
        layout.addWidget(gb)
        self.items = []
        self.list_widget.itemSelectionChanged.connect(self.change_font)
        self.list_widget.setStyleSheet("QTreeView::background-color{background-color:rgb(255,255,255);}")

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        super().resizeEvent(a0)
        self.example_label.setMaximumWidth(self.width() - 45)

    def add_section(self, name, parent=None):
        header = QTreeWidgetItem()
        header.setText(0, name)
        if parent is None:
            self.list_widget.addTopLevelItem(header)
        else:
            parent.addChild(header)

        return header

    def add_elements(self, parent, fonts, use_own_font=True):

        for font_info in fonts:
            item = FontPicker.TreeWidgetItem(font_info)
            label = QLabel(font_info.full_name)
            if use_own_font:
                qfont = font_info.get_qfont(12)
                if not qfont:
                    continue
                # print()
                if qfont:
                    label.setFont(qfont)
            parent.addChild(item)
            self.list_widget.setItemWidget(item, 0, label)
            self.items.append(item)

    def find(self, name):
        for item in self.items:
            if item.font_info.nickname == name:
                return item
        return None

    def set_default(self, nickname, size):
        self.size.setValue(int(size))
        current = self.find(nickname)
        if current:
            self.list_widget.setCurrentItem(current)
            while current.parent():
                current.parent().setExpanded(True)
                current = current.parent()

    def change_font(self):
        ok = False
        item: FontPicker.TreeWidgetItem = self.get_selected()
        if item is not None:
            if item.font_info is not None and item.font_info.supported:
                font = item.font_info.get_qfont(self.size.value())
                self.example_label.setFont(font)
                self.example_label.update()
                ok = True

        self.enable.emit(ok)

    def set_font_size(self, size):
        self.size_label.setText(str(size))
        font = self.example_label.font()
        font.setPointSize(size)
        self.example_label.setFont(font)

    def get_selected(self):
        selected = self.list_widget.selectedItems()
        return selected[0] if len(selected) > 0 else None

    def get_font_size(self):
        return self.size.value()

    def get_font(self):
        return self.get_selected().font_info
