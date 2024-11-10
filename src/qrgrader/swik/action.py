class Atom:
    def __init__(self, item, kind, old=None, new=None):
        self.kind = kind
        self.item = item
        self.old = old
        self.new = new
        self.parent = old


class Action(list):
    ACTION_CREATE = 0
    ACTION_REMOVE = 1
    ACTION_CHANGED = 2
    ACTION_COLOR_CHANGED = 3
    ACTION_ANNOT_CHANGED = 4
    POSE_SHAPE_CHANGED = 5
    TEXT_CHANGED = 7
    PAGE_ORDER_CHANGED = 8
    FULL_STATE = 9
    PAGES_ADDED = 10
    PAGES_ROTATED = 11
    PAGES_DUPLICATED = 12

    def __init__(self, item=None, kind=None, old=None, new=None):
        super().__init__()
        if item is not None:
            self.push(item, kind, old, new)

    def push(self, item, kind, old=None, new=None):
        super().append(Atom(item, kind, old, new))


class CreateAction(Action):
    def __init__(self, item):
        super().__init__(item, Action.ACTION_CREATE, item.parentItem())

    def item(self):
        return self[0].item
