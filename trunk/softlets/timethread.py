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
from operator import itemgetter

from softlets.core.common import _singleton

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

def NamedTuple(*names):
    d = dict([(name, index) for index, name in enumerate(names)])
    n = len(names)
    class T(tuple):
        def __new__(cls, *args, **kargs):
            p = len(args)
            assert p + len(kargs) == n
            l = list(args) + [None] * (n - p)
            for k, v in kargs.items():
                i = d[k]
                assert i >= p
                l[i] = v
            return tuple.__new__(cls, l)
    for k, v in d.items():
        setattr(T, k, property(itemgetter(v)))
    return T

_Callback = NamedTuple("timestamp", "func")


class _TimeThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.callbacks = []
        self.interrupt = threading.Condition()
        self.started = False
        self.running = False
        self.setDaemon(True)

    def start(self):
        if not self.started:
            threading.Thread.start(self)
            self.started = True
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
        self.running = False
        self.interrupt.acquire()
        self.callbacks = []
        self.interrupt.notify()
        self.interrupt.release()
        self.join()

    def run(self):
        self.running = True
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

