from PyQt5.QtCore import QObject
from qrgrader.swik.action import Action

from qrgrader.swik.interfaces import Undoable

from qrgrader.swik.swik_text import SwikTextNumerate


class Bunch(QObject):

    def __init__(self, scene):
        super(Bunch, self).__init__()
        self.my_scene = scene
        self.numbers = []

    def add(self, element):
        self.numbers.append(element)

    def scene(self):
        return self.my_scene

    def notify_creation(self):
        action = Action()
        for number in self.numbers:
            action.push(number, Action.ACTION_CREATE, number.parentItem())
        self.my_scene.tracker().add_action(action)

    def clear(self):
        action = Action()
        for number in self.numbers:
            # self.my_scene.removeItem(number)
            action.push(number, Action.ACTION_REMOVE, number.parentItem())
            self.my_scene.removeItem(number)

        self.my_scene.tracker().add_action(action)

        # self.numbers.clear()


class AnchoredBunch(Bunch):

    def __init__(self, scene):
        super(AnchoredBunch, self).__init__(scene)
        self.my_scene.bunches.append(self)
        self.current_state = None

    def add(self, element):
        super(AnchoredBunch, self).add(element)
        element.signals.moved.connect(self.moved)
        element.signals.move_started.connect(self.move_started)
        element.signals.move_finished.connect(self.move_finished)

    def move_started(self, obj):
        self.current_state = obj.get_full_state()

    def move_finished(self, obj):
        if self.current_state != obj.get_full_state():
            action = Action()
            for number in self.numbers:
                action.push(number, Action.FULL_STATE, self.current_state, obj.get_full_state())
            self.my_scene.tracker().add_action(action)

    def moved(self, obj, pos):
        for number in self.numbers:
            if number != obj:
                if number.anchor == SwikTextNumerate.ANCHOR_TOP_LEFT:
                    number.setPos(pos)
                elif number.anchor == SwikTextNumerate.ANCHOR_TOP_RIGHT:
                    obj_x_pos = obj.parentItem().boundingRect().width() - obj.pos().x()
                    number.setPos(number.parentItem().boundingRect().width() - obj_x_pos, obj.pos().y())
                elif number.anchor == SwikTextNumerate.ANCHOR_BOTTOM_LEFT:
                    obj_y_pos = obj.parentItem().boundingRect().height() - obj.pos().y()
                    number.setPos(obj.pos().x(), number.parentItem().boundingRect().height() - obj_y_pos)
                elif number.anchor == SwikTextNumerate.ANCHOR_BOTTOM_RIGHT:
                    obj_x_pos = obj.parentItem().boundingRect().width() - obj.pos().x()
                    obj_y_pos = obj.parentItem().boundingRect().height() - obj.pos().y()
                    number.setPos(number.parentItem().boundingRect().width() - obj_x_pos, number.parentItem().boundingRect().height() - obj_y_pos)
                elif number.anchor == SwikTextNumerate.ANCHOR_TOP_CENTER:
                    delta_x = obj.pos().x() - obj.parentItem().boundingRect().width() / 2
                    number.setPos(number.parentItem().boundingRect().width() / 2 + delta_x, obj.pos().y())
                elif number.anchor == SwikTextNumerate.ANCHOR_BOTTOM_CENTER:
                    obj_y_pos = obj.parentItem().boundingRect().height() - obj.pos().y()
                    number.setPos(obj.parentItem().boundingRect().width() / 2, number.parentItem().boundingRect().height() - obj_y_pos)


class NumerateBunch(AnchoredBunch):

    def add(self, element):
        super(NumerateBunch, self).add(element)
        element.signals.state_changed.connect(self.state_changed)
        element.signals.action.connect(self.action)

    def state_changed(self, item, old_state, new_state):
        old_state.pop('text')
        new_state.pop('text')
        action = Action()
        for number in self.numbers:
            if number != item:
                number.set_full_state(new_state)
            action.push(number, Action.FULL_STATE, old_state, new_state)
        self.my_scene.tracker().add_action(action)

    def action(self, obj, action):
        if action == 'remove':
            self.my_scene.tracker().add_action(Action(obj, Action.ACTION_REMOVE, obj.parentItem()))
            self.my_scene.removeItem(obj)
            # self.numbers.remove(obj)
        elif action == 'start_here':
            index = self.numbers.index(obj)
            for number in self.numbers[:index]:
                self.my_scene.removeItem(number)
            self.numbers = self.numbers[index:]
            for i, number in enumerate(self.numbers):
                number.set_text(str(i + 1))
        elif action == 'remove_all':
            self.clear()
        elif action == 'anchor_changed':
            anchor = obj.anchor
            for number in self.numbers:
                if number != obj:
                    number.anchor = anchor
                    self.moved(obj, obj.pos())
        elif action == 'center':
            for number in self.numbers:
                number.setPos(number.parentItem().boundingRect().width() / 2 - number.boundingRect().width() / 2, number.pos().y())
