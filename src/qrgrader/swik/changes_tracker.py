from PyQt5.QtCore import QObject, pyqtSignal

from qrgrader.swik.action import Action


# This is just an undo/redo class; the philosophy is the following:
# It manages directly undo/redo of creation and removal of items, and it is the only one that can do it.
# Instead, the items are responsible for their own changes, and they notify the changes to the tracker
# through the notify_change method. They send an Action object, that contains the item, the kind of change,
# and the old and new state of the item. These states can be anything but must mean something to the item since
# they will be sent back by the tracker by calling undo() and redo() and the item must restore its state accordingly.
# The actions are stored to implement the undone or redone. The states are vectors of atoms because they can store
# multiple changes at once, for example when a word is replaced, it is covered by a redaction and a new word is added
# which are 2 atoms to undo/redo. The items that want to be undoable must implement the Undoable interface.

class ChangesTracker(QObject):
    dirty = pyqtSignal(bool)

    class Stack(list):

        class Signals(QObject):
            dirty = pyqtSignal(bool)

        def __init__(self):
            super(ChangesTracker.Stack, self).__init__()
            self.signals = self.Signals()

        def append(self, __object) -> None:
            super(ChangesTracker.Stack, self).append(__object)
            self.signals.dirty.emit(len(self) > 0)

        def pop(self, index=-1) -> Action:
            action = super(ChangesTracker.Stack, self).pop(index)
            self.signals.dirty.emit(len(self) > 0)
            return action

        def clear(self) -> None:
            super(ChangesTracker.Stack, self).clear()
            self.signals.dirty.emit(False)

    def __init__(self):
        super(ChangesTracker, self).__init__()
        self.undo_stack = self.Stack()
        self.redo_stack = self.Stack()
        self.undo_stack.signals.dirty.connect(self.dirty.emit)
        self.not_undoable = 0

    def add_not_undoable(self):
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.not_undoable += 1
        self.dirty.emit(True)

    def is_dirty(self):
        return len(self.undo_stack) > 0 or self.not_undoable > 0

    def clear(self):
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.not_undoable = 0
        self.dirty.emit(False)

    def undo(self):
        print("undo", len(self.undo_stack), len(self.redo_stack))
        if len(self.undo_stack) > 0:
            action = self.undo_stack.pop()
            self.redo_stack.append(action)
            for atom in action:
                if atom.kind == Action.ACTION_CREATE:
                    atom.item.scene().removeItem(atom.item)
                elif atom.kind == Action.ACTION_REMOVE:
                    atom.item.setParentItem(atom.parent)
                else:
                    atom.item.undo(atom.kind, atom.old)

    def redo(self):
        print("redo", len(self.undo_stack), len(self.redo_stack))
        if len(self.redo_stack) > 0:
            action = self.redo_stack.pop()
            for atom in action:
                if atom.kind == Action.ACTION_CREATE:
                    print("reattaching", atom.item, atom.item.parentItem())
                    atom.item.setParentItem(atom.parent)
                elif atom.kind == Action.ACTION_REMOVE:
                    atom.item.scene().removeItem(atom.item)
                else:
                    atom.item.redo(atom.kind, atom.new)
            self.undo_stack.append(action)

    def item_added(self, item):
        self.undo_stack.append(Action(item, Action.ACTION_CREATE, item.parentItem()))
        # print("item added", item)

    def item_removed(self, item):
        self.undo_stack.append(Action(item, Action.ACTION_REMOVE, item.parentItem()))
        # print("item removed", item, item.parentItem())

    def items_removed(self, items):
        action = Action()
        for item in items:
            action.push(item, Action.ACTION_REMOVE, item.parentItem())
        self.undo_stack.append(action)

    def add_action(self, action):
        self.undo_stack.append(action)

    def item_changed(self, action):
        self.undo_stack.append(action)

    def saved(self):
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.not_undoable = 0
