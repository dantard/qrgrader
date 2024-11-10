import queue
import threading
import time

from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QGraphicsRectItem


class Finder(QObject):
    MODE_NORMAL = 0
    MODE_Cc = 1
    MODE_W = 2
    MODE_Cc_W = 3

    found = pyqtSignal(int, list)
    words_needed = pyqtSignal(QGraphicsRectItem)
    progress = pyqtSignal(float)

    def __init__(self, view, renderer):
        super(Finder, self).__init__()
        self.renderer = renderer
        self.view = view
        self.confirmed = []
        self.confirmed_index = 0
        self.mode = Finder.MODE_NORMAL
        self.words_needed.connect(self.page_gather_words)
        self.queue = queue.Queue()
        self.worker = None
        self.keep_running = True

    def finish(self):
        pass
        #        self.keep_running = False
        #        if self.thread is not None:
        #            self.thread.join()

    def set_mode(self, mode):
        self.set_mode(mode)

    def get_mode(self):
        return self.mode

    def find(self, text, mode, first_page=0):
        self.mode = mode
        if self.worker is None:
            self.worker = threading.Thread(target=self.find_thread)
            self.worker.start()

        self.queue.put((text, first_page))

    def check_words_case(self, w1, w2):
        if self.mode == Finder.MODE_NORMAL:
            return w1.lower() in w2.lower()
        elif self.mode == Finder.MODE_Cc:
            return w1 in w2
        elif self.mode == Finder.MODE_W:
            return w1.lower() == w2.lower()
        elif self.mode == Finder.MODE_Cc_W:
            return w1 == w2

    def find_thread(self):
        while True:

            text, first_page = self.queue.get()

            self.clear()

            if first_page == -1:
                break
            elif first_page == -2:
                continue

            needles = text.split()
            text = needles[0]
            candidates, words = [], []
            self.keep_running = True

            for jk in range(self.view.get_num_of_pages()):

                if not self.queue.empty():
                    break

                i = (first_page + jk) % self.view.get_num_of_pages()

                page = self.view.get_page_item(i)
                self.progress.emit((jk + 1) / (self.view.get_num_of_pages()))

                # This must be done with a signal
                # because the words must be created
                # in the main thread
                if not page.has_words():
                    self.words_needed.emit(page)

                # Wait until the page is ready
                while not page.has_words():
                    time.sleep(0.1)

                # Check if the word is in the page
                for word in page.get_words():
                    words.append(word)
                    if self.check_words_case(text, word.get_text()):
                        candidates.append((word, len(words) - 1))

                # After processing every page we must check the candidates
                # because the sentence can be split between pages
                # WARNING: We are copying the list because we are going to remove elements
                copy = candidates.copy()
                for word, index in copy:
                    sentence = [word]
                    for j, needle in enumerate(needles[1:]):
                        if index + j + 1 >= len(words) or not self.check_words_case(needle,
                                                                                    words[index + j + 1].get_text()):
                            break
                        sentence.append(words[index + j + 1])
                    else:
                        candidates.remove((word, index))
                        self.confirmed.append(sentence)
                        self.found.emit(len(self.confirmed), sentence)
            self.progress.emit(1)

    def page_gather_words(self, page):
        page.gather_words()

    def next(self, direction):
        if len(self.confirmed) > 0:
            sentence = self.confirmed[self.confirmed_index]
            self.confirmed_index = self.confirmed_index + direction
            self.confirmed_index = self.confirmed_index if self.confirmed_index < len(self.confirmed) else 0
            self.confirmed_index = self.confirmed_index if self.confirmed_index >= 0 else len(self.confirmed) - 1
            return sentence
        return []

    def get_count(self):
        return len(self.confirmed)

    def get_index(self):
        return self.confirmed_index

    def clear(self):
        for sentence in self.confirmed:
            for word in sentence:
                word.set_highlighted(False)

        self.confirmed.clear()
        self.confirmed_index = 0
        self.progress.emit(-1)

    def discard(self):
        if self.worker is not None:
            self.queue.put((None, -2))
            while not self.queue.empty():
                time.sleep(0.1)

    def die(self):
        self.queue.put((None, -1))
        if self.worker is not None:
            self.worker.join()
