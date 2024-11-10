from PyQt5 import QtCore
from PyQt5.QtWidgets import QGraphicsScene
from qrgrader.swik import utils

from qrgrader.swik.action import Action
from qrgrader.swik.changes_tracker import ChangesTracker
from qrgrader.swik.resizeable import HandleItem
from qrgrader.swik.utils import Signals


class Scene(QGraphicsScene):

    def __init__(self, changes_tracker: ChangesTracker):
        super().__init__()
        self.signals = Signals()
        self.changes_tracker = changes_tracker
        self.bunches = []
        self.selectionChanged.connect(self.selection_changed)
        self.group = None
        self.poses = {}

    def selection_changed(self):
        # Necessary because if I move multiple
        # items at the same time the "dragged"
        # items position is not stored anywhere
        self.poses.clear()
        for elem in self.selectedItems():
            self.poses[elem] = elem.pos()

    def action_added(self, action):
        self.tracker().add_action(action)

    def notify_not_undoable(self):
        self.tracker().add_not_undoable()

    def notify_change(self, item, kind, old, new):
        action = Action(item, kind, old, new)

        item_state = utils.get_different_keys(old, new, ["pos", "text", "rect", "content"])

        for elem in self.selectedItems():
            if elem is not item and type(elem) != HandleItem:
                cur_state = elem.get_full_state().copy()
                cur_state["pos"] = self.poses[elem]
                elem.set_full_state(item_state)
                action.push(elem, kind, cur_state, elem.get_full_state())

        self.tracker().item_changed(action)

    def item_added(self, item):
        self.tracker().item_added(item)

    def items_removed(self, items):
        self.tracker().item_removed(items)

    def tracker(self) -> ChangesTracker:
        return self.changes_tracker

    def remove_bunches(self, kind):
        bunches = [b for b in self.bunches if type(b) == kind]
        for bunch in bunches:
            self.bunches.remove(bunch)

    def get_bunches(self, kind):
        return [b for b in self.bunches if type(b) == kind]

    def get_bunches_count(self):
        return len(self.bunches)

    def delete_objects(self):
        items = self.selectedItems()
        self.tracker().items_removed(items)
        for item in items:
            if hasattr(item, "deleted"):
                item.deleted()
            self.removeItem(item)

    def addItem(self, item) -> None:
        super().addItem(item)
        self.signals.item_added.emit(item)

    def removeItem(self, item) -> None:
        super().removeItem(item)
        if item is not None:
            self.signals.item_removed.emit(item)

    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        # print("mouse press on scene", event.scenePos())
        super(Scene, self).mousePressEvent(event)

    def keyPressEvent(self, event) -> None:
        items = self.selectedItems()
        if len(items) == 0:
            super().keyPressEvent(event)
            if event.key() in [QtCore.Qt.Key_Up, QtCore.Qt.Key_Down, QtCore.Qt.Key_Left, QtCore.Qt.Key_Right]:
                if event.key() in [QtCore.Qt.Key_Right, QtCore.Qt.Key_Up]:
                    view = self.views()[0]
                    view.move_to_page(view.page + 1)
                elif event.key() in [QtCore.Qt.Key_Down, QtCore.Qt.Key_Left]:
                    view = self.views()[0]
                    view.move_to_page(view.page - 1)

        elif event.key() in [QtCore.Qt.Key_Up, QtCore.Qt.Key_Down, QtCore.Qt.Key_Left, QtCore.Qt.Key_Right]:
            val = 1 if event.modifiers() == QtCore.Qt.ControlModifier else 10
            if event.key() == QtCore.Qt.Key_Up:
                x, y = 0, -1
            elif event.key() == QtCore.Qt.Key_Down:
                x, y = 0, 1
            elif event.key() == QtCore.Qt.Key_Left:
                x, y = -1, 0
            elif event.key() == QtCore.Qt.Key_Right:
                x, y = 1, 0
            else:
                x, y = 0, 0

            for item in items:
                current_state = item.get_full_state()
                item.setPos(item.pos().x() + x * val, item.pos().y() + y * val)
                self.notify_change(item, Action.FULL_STATE, current_state, item.get_full_state())
        elif event.key() == QtCore.Qt.Key_Delete:
            self.delete_objects()
        elif event.key() == QtCore.Qt.Key_Backspace:
            self.delete_objects()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:
        super(Scene, self).keyReleaseEvent(event)

    # TODO: to be completed
    '''
    def context_menu(self, event):
        items = self.selectedItems()
        if len(items) == 1:
            intersection = items[0].get_full_state().keys()
        else:
            intersection = None
            for item in self.selectedItems():
                state = item.get_common_state().keys()
                intersection = list(set(state) & set(intersection)) if intersection is not None else state

        print("intersection", intersection)
        menu = QMenu()
        edit = menu.addAction("Edit", self.delete_objects)
        delete = menu.addAction("Delete", self.delete_objects)
        res = menu.exec(event.screenPos())
        if res == edit:
            dialog = ComposableDialog()
            for row in intersection:
                if row == "brush":
                    dialog.add_row("Brush", Color(self.brush().color()))
    '''
