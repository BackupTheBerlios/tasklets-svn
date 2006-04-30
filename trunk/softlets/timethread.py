"""
TimeThread is a helper thread to handle lots of timers
without any scalability problem.
(in contrast, the Timer class in the builtin threading package
allocates a separate thread for each timer)
"""

import time
import threading
import atexit
from heapq import heappush, heappop, heapify

from softlets.core.common import _singleton
from softlets.util.namedtuple import NamedTuple

__all__ = ['TimeThread']


def _p(s):
    def p():
        print s
    return p

def _q(s):
    def q():
        if not s % 100:
            print s
    return q

_Callback = NamedTuple("timestamp", "func")


class _TimeThread(object):
    def __init__(self):
        self.callbacks = []
        self.interrupt = threading.Condition()
        self.running = False

    def start(self):
        assert not self.running, "TimeThread already started"
        self.thread = threading.Thread(
            target=self.run,
            name="TimeThread polling thread")
        self.thread.setDaemon(True)
        self.thread.start()
        self.running = True
        atexit.register(self.finish)

    def get_lock(self):
        return self.interrupt

    def add_timer(self, delay, func, keep_lock=False):
        timestamp = time.time() + delay
        if not keep_lock:
            # If not asked otherwise, release the lock
            # in case the func() wants to add/remove other callbacks
            def f(func=func):
                self.interrupt.release()
                try:
                    func()
                finally:
                    self.interrupt.acquire()
            func = f
        callback = _Callback(timestamp, func)
        try:
            self.interrupt.acquire()
            heappush(self.callbacks, callback)
            if self.callbacks[0] is callback:
                self.interrupt.notify()
        finally:
            self.interrupt.release()
        return callback

    def remove_timer(self, callback):
        try:
            self.interrupt.acquire()
            try:
                if self.callbacks[0] is callback:
                    self.interrupt.notify()
                self.callbacks.remove(callback)
            except (ValueError, IndexError):
                raise ValueError("cannot remove unknown timer '%s'" % str(callback))
            heapify(self.callbacks)
        finally:
            self.interrupt.release()

    def finish(self):
        self.interrupt.acquire()
        self.running = False
        self.callbacks = []
        self.interrupt.notify()
        self.interrupt.release()
        self.thread.join()

    def run(self):
        try:
            self.interrupt.acquire()
            while self.running:
                if not self.callbacks:
                    self.interrupt.wait()
                    continue
                cb = self.callbacks[0]
                timeout = cb.timestamp - time.time()
                if timeout > 0:
                    r = self.interrupt.wait(timeout)
                    # If the next callback has changed at return, it means we
                    # have been interrupted by the main thread
                    if not self.callbacks or cb is not self.callbacks[0]:
                        continue
                heappop(self.callbacks)
                cb.func()
        finally:
            self.interrupt.release()


TimeThread = _singleton(_TimeThread)

