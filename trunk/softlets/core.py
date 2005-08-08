
from collections import deque
import threading

def _singleton(cls):
    instance = []
    def wrapper(*args, **kargs):
        if not instance:
            instance.append(cls(*args, **kargs))
        return instance[0]
    return wrapper

_lock = threading.Lock()

def _protected(func, lock=_lock):
    def f(*args, **kargs):
        lock.acquire()
        func(*args, **kargs)
        lock.release()
    return f

def _unprotected(func):
    return func


#
# Different kinds of objects providing a simple synchronization scheme
#

class WaitObject(object):
    """
    A WaitObject is an object a softlet can wait on by yield'ing it.
    """

    def __init__(self):
        self.waiters = {}
        self.ready = False
        self.event_sinks = []

    def get_waiter(self, switcher):
        try:
            q = self.waiters[switcher]
        except KeyError:
            return None
        waiter = q.popleft()
        if not q:
            del self.waiters[switcher]
            switcher.remove_ready_object(self)
        return waiter

        waiter = self.waiters.popleft()
        switcher = waiter.switcher
        if self.switchers_ref_cnt[switcher] == 1:
            del self.switchers_ref_cnt[switcher]
            switcher.remove_ready_object(self)
        else:
            self.switchers_ref_cnt[switcher] -= 1
        return waiter

    def add_waiter(self, waiter):
        switcher = waiter.switcher
        try:
            self.waiters[switcher].append(waiter)
        except KeyError:
            self.waiters[switcher] = deque([waiter])
            if self.ready:
                switcher.add_ready_object(self)
        return

    def set_ready(self, ready):
        if ready != self.ready:
            self.ready = ready
            for func in self.event_sinks:
                func(ready)
            for switcher in self.waiters:
                switcher.set_ready(self, ready)

    def ask_notifications(self, func):
        self.event_sinks.append(func)

    def __or__(self, b):
        if b is None:
            return self
        assert isinstance(b, WaitObject)
        return LogicalOr([self, b])

    def __ror__(self, b):
        return self.__or__(b)


class _Ready(WaitObject):
    def __init__(self):
        WaitObject.__init__(self)
        self.set_ready(True)

# Special-casing Ready improves scalability with many threads
Ready = _singleton(_Ready)


class Softlet(WaitObject):
    def __init__(self, func=None):
        WaitObject.__init__(self)
        self.switcher = current_switcher()
        self.restart(func)

    def restart(self, func=None):
        self.runner = func or self.run()
        self.finished = False
        self.set_ready(False)
        self.switcher.add_thread(self)

    def terminate(self):
        self.finished = True
        self.set_ready(True)
        self.switcher.remove_thread(self)

class Queue(WaitObject):
    """
    A general message queue to communicate between threads.
    Can contain any kind of objects.
    """
    def __init__(self):
        WaitObject.__init__(self)
        self.data = []

    def put(self, value):
        if not self.data:
            self.set_ready(True)
        self.data.append(value)

    def get(self):
        if len(self.data) == 1:
            self.set_ready(False)
        return self.data.pop(0)

class LogicalOr(WaitObject):
    """
    Logical OR between several WaitObjects.
    The natural way to construct it is to use the "|" operator
    between those objects.
    """
    def __init__(self, objs):
        WaitObject.__init__(self)
        def _wait(o):
#             while o in self.objs:
                yield o
                self.ready_objs.append(o)
                self.set_ready(True)

        self.objs = list(objs)
        self.ready_objs = []
        for obj in objs:
            thread = Softlet(_wait(obj))

    def discard(self, obj):
        self.objs(remove(obj))

    def pop(self):
        if len(self.ready_objs) == 1:
            self.set_ready(False)
        try:
            return self.ready_objs.pop()
        except IndexError:
            return None

    def __or__(self, b):
        if b is None:
            return self
        assert isinstance(b, WaitObject)
        if isinstance(b, LogicalOr):
            return LogicalOr(self.objs + b.objs)
        else:
            return LogicalOr(self.objs + [b])

    def __ror__(self, b):
        return self.__or__(b)


#
# Main loop
#

# Wicked idea: rewrite the switcher as a generator that yields
# the next thread to be scheduled.
# Then, write a metaswitcher that will iterate through the switcher.

class Switcher(object):
    """
    The main switching loop. Handles WaitObjects and Softlets.
    """

    def __init__(self):
        self.threads = set()
        self.ready_objects = set()
        self.nb_switches = 0
        self.current_thread = None

    def add_thread(self, thread):
        Ready().add_waiter(thread)
        self.threads.add(thread)
        thread.parent = self.current_thread

    def remove_thread(self, thread):
        self.threads.remove(thread)

    def set_ready(self, wait_object, ready):
        if ready:
            self.ready_objects.add(wait_object)
        else:
            self.ready_objects.discard(wait_object)

    def add_ready_object(self, wait_object):
        self.ready_objects.add(wait_object)

    def remove_ready_object(self, wait_object):
        self.ready_objects.remove(wait_object)

    def run(self):
#         _lock.acquire()
        while self.threads:
            if not self.ready_objects:
                raise Exception("softlets starved")
            for r in self.ready_objects:
                thread = r.get_waiter(self)
                if thread.finished:
                    continue
                self.nb_switches += 1
                try:
                    self.current_thread = thread
#                     _lock.release()
                    wait_object = thread.runner.next()
                except StopIteration:
#                     _lock.acquire()
                    self.current_thread = None
                    thread.terminate()
                except:
#                     _lock.acquire()
                    raise
                else:
#                     _lock.acquire()
                    self.current_thread = None
                    wait_object.add_waiter(thread)
                break
#         _lock.release()

#
# Functions
#

current_switcher = _singleton(Switcher)

def main_loop(switcher=None):
    switcher = switcher or current_switcher()
    switcher.run()
