
import time
import threading
from heapq import heappush, heappop, heapify
from operator import itemgetter

from softlets.core import WaitObject, _singleton

def _p(s):
    def p():
        print s
    return p

def _q(s):
    def q():
        if not s % 100:
            print s
    return q

class _Callback(tuple):
    def __new__(cls, timestamp, func):
        self = tuple.__new__(cls, (timestamp, func))
        return self
    timestamp = property(itemgetter(0))
    func = property(itemgetter(1))

class TimeThread1(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.callbacks = set()
        self.interrupt = threading.Condition()
        self.next_callback = None
        self.running = False
        self.setDaemon(True)

    def _get_next_callback(self):
        return self.callbacks and min(self.callbacks) or None

    def add_callback(self, delay, func):
        timestamp = time.time() + delay
        callback = _Callback(timestamp, func)
        try:
            self.interrupt.acquire()
            self.callbacks.add(callback)
            if not self.next_callback or timestamp < self.next_callback.timestamp:
                self.next_callback = callback
                self.interrupt.notify()
        finally:
            self.interrupt.release()
        return callback

    def remove_callback(self, callback):
        try:
            self.interrupt.acquire()
            self.callbacks.discard(callback)
            if self.next_callback == callback:
                self.next_callback = self._get_next_callback()
                self.interrupt.notify()
        finally:
            self.interrupt.release()

    def finish(self):
        self.running = False
        self.interrupt.acquire()
        self.interrupt.notify()
        self.interrupt.release()

    def run(self):
        self.running = True
        try:
            self.interrupt.acquire()
            while self.running:
                cb = self.next_callback
                timeout = cb and (cb.timestamp - time.time()) or None
                if timeout is None or timeout > 0:
                    # We wait until the end of the next_callback timeout
                    # If the next_callback has changed at return, it means we
                    # have been interrupted by the main thread
                    r = self.interrupt.wait(timeout)
                    if self.next_callback is not cb:
                        continue
                self.callbacks.remove(cb)
                self.next_callback = self._get_next_callback()
                # Release the lock in case the func() wants to
                # add/remove other callbacks
                self.interrupt.release()
                cb.func()
                self.interrupt.acquire()
        finally:
            self.interrupt.release()


class TimeThread2(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.callbacks = []
        self.interrupt = threading.Condition()
        self.running = False
        self.setDaemon(True)

    def add_callback(self, delay, func):
        timestamp = time.time() + delay
        callback = _Callback(timestamp, func)
        try:
            self.interrupt.acquire()
            heappush(self.callbacks, callback)
            if self.callbacks[0] is callback:
                self.interrupt.notify()
        finally:
            self.interrupt.release()
        return callback

    def remove_callback(self, callback):
        try:
            self.interrupt.acquire()
            if self.callbacks[0] is callback:
                self.interrupt.notify()
            self.callbacks.remove(callback)
            heapify(self.callbacks)
        finally:
            self.interrupt.release()

    def finish(self):
        self.running = False
        self.interrupt.acquire()
        self.interrupt.notify()
        self.interrupt.release()

    def run(self):
        self.running = True
        try:
            self.interrupt.acquire()
            while self.running:
                if not self.callbacks:
                    self.interrupt.wait()
                    continue
                cb = self.callbacks[0]
                timeout = cb and (cb.timestamp - time.time())
                if timeout is None or timeout > 0:
                    r = self.interrupt.wait(timeout)
                    # If the next callback has changed at return, it means we
                    # have been interrupted by the main thread
                    if not self.callbacks or cb != self.callbacks[0]:
                        continue
                heappop(self.callbacks)
                # Release the lock in case the func() wants to
                # add/remove other callbacks
                self.interrupt.release()
                cb.func()
                self.interrupt.acquire()
        finally:
            self.interrupt.release()


# TimeThread = _singleton(_TimeThread)
