from PyQt5.QtWidgets import QWidget


class Copyable:

    def duplicate(self):
        pass


class Undoable:

    def notify_creation(self):
        if self.scene():
            self.scene().item_added(self)

    def notify_deletion(self):
        if self.scene():
            self.scene().item_removed(self)

    def notify_change(self, kind, old, new):
        if self.scene():
            self.scene().notify_change(self, kind, old, new)

    def undo(self, kind, info):
        pass

    def redo(self, kind, info):
        self.undo(kind, info)

    def notify_not_undoable(self):
        if self.scene():
            self.scene().notify_not_undoable()


class Shell(QWidget):
    def get_renderer(self):
        pass

    def get_view(self):
        pass

    def get_manager(self):
        pass

    def get_config(self):
        pass

    def get_font_manager(self):
        pass

    def get_other_views(self):
        pass

    def set_app_widget(self, widget, width=500, title=""):
        pass

    def remove_app_widget(self):
        pass

    def set_protected_interaction(self, value):
        pass
