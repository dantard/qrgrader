from threading import Lock


class SyncDict(dict):
    def __init__(self):
        super().__init__()
        self.lock = Lock()

    def values(self):
        self.lock.acquire()
        res = [p for p in super().values()]
        self.lock.release()
        return res

    def items(self):
        self.lock.acquire()
        res = [p for p in super().items()]
        self.lock.release()
        return res

    def __setitem__(self, key, value):
        self.lock.acquire()
        super().__setitem__(key, value)
        self.lock.release()

    def update(self, __m, **kwargs) -> None:
        self.lock.acquire()
        super().update(__m, **kwargs)
        self.lock.release()
