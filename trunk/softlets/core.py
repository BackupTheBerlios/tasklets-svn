
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
        # Waiters are keyed by their respective switcher
        self.waiters = {}
        self.ready = False
        self.readiness_callbacks = []
        self.armed = False

    def arm(self):
        """
        Can be overriden if some specific actions need to
        be taken the first time the WaitObject is armed
        (i.e. waited upon).
        """
        pass

    def get_waiter(self, switcher):
        """
        Get one of the softlets waiting upon this WaitObject,
        depending on the switcher.
        """
        try:
            q = self.waiters[switcher]
        except KeyError:
            return None
        waiter = q.popleft()
        if not q:
            del self.waiters[switcher]
            switcher.remove_ready_object(self)
        return waiter

    def add_waiter(self, waiter):
        """
        Add a softlet waiting upon this WaitObject.
        """
        if not self.armed:
            self.arm()
            self.armed = True
        switcher = waiter.switcher
        try:
            self.waiters[switcher].append(waiter)
        except KeyError:
            self.waiters[switcher] = deque([waiter])
            if self.ready:
                switcher.add_ready_object(self)

    def set_ready(self, ready):
        """
        Sets whether the WaitObject is ready or not.
        (i.e. whether a softlet can be waken)
        """
        if ready != self.ready:
            self.ready = ready
            for callback in self.readiness_callbacks:
                callback(self, ready)
            for switcher in self.waiters:
                switcher.set_ready(self, ready)

    def notify_readiness(self, callback):
        """
        Ask to be notified when the WaitObject's readiness changes.
        The function will be called back with two arguments:
        the WaitObject, and its ready state (True or False).
        """
        self.readiness_callbacks.append(callback)
        if self.ready:
            callback(self, True)

    def __or__(self, b):
        if b is None:
            return self
        assert isinstance(b, WaitObject)
        return LogicalOr([self, b])

    def __ror__(self, b):
        return self.__or__(b)

    def __and__(self, b):
        if b is None:
            return self
        assert isinstance(b, WaitObject)
        return LogicalAnd([self, b])

    def __rand__(self, b):
        return self.__and__(b)


class _Ready(WaitObject):
    def __init__(self):
        WaitObject.__init__(self)
        self.set_ready(True)

# Special-casing Ready improves scalability with many threads
Ready = _singleton(_Ready)


class Softlet(WaitObject):
    def __init__(self, func=None, standalone=False):
        """
        Create Softlet from given generator, or from
        the overriden run() method if "func" is not specified.
        If "standalone" is True, Softlet won't be killed
        when parent terminates.
        """
        WaitObject.__init__(self)
        self.standalone = standalone
        self.switcher = current_switcher()
        self.children = set()
        if not standalone:
            self.parent = self.switcher.current_thread
            if self.parent:
                self.parent.children.add(self)
        else:
            self.parent = None
        self.start(func)

    def start(self, func=None):
        self.runner = func or self.run()
        self.finished = False
        self.set_ready(False)
        self.switcher.add_thread(self)

    def terminate(self):
        self.finished = True
        self.set_ready(True)
        self.switcher.remove_thread(self)
        if self.parent:
            self.parent.children.remove(self)
        for child in self.children:
            print "killing child %r" % child
            child.terminate()

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

class MultipleWaitObject(WaitObject):
    """
    Base class for combinations of several WaitObjects.
    """
    def __init__(self, objs):
        WaitObject.__init__(self)
        self.objs = list(objs)
        self.ready_objs = set()

    def arm(self):
        for obj in self.objs:
            obj.notify_readiness(self.on_object_ready)

    def on_object_ready(self, obj, ready):
        if ready:
            self.ready_objs.add(obj)
        else:
            self.ready_objs.discard(obj)
        self.update_readiness()

    def pop(self):
        try:
            obj = self.ready_objs.pop()
        except IndexError:
            obj = None
        self.update_readiness()
        return obj


class LogicalOr(MultipleWaitObject):
    """
    Logical OR between several WaitObjects.
    The natural way to construct it is to use the "|" operator
    between those objects.
    """
    def update_readiness(self):
        self.set_ready(len(self.ready_objs) > 0)

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

class LogicalAnd(MultipleWaitObject):
    """
    Logical OR between several WaitObjects.
    The natural way to construct it is to use the "&" operator
    between those objects.
    """
    def update_readiness(self):
        self.set_ready(len(self.ready_objs) == len(self.objs))

    def __and__(self, b):
        if b is None:
            return self
        assert isinstance(b, WaitObject)
        if isinstance(b, LogicalAnd):
            return LogicalAnd(self.objs + b.objs)
        else:
            return LogicalAnd(self.objs + [b])

    def __rand__(self, b):
        return self.__and__(b)


#
# Main loop
#

# Wicked idea: rewrite the switcher as a generator that yields
# the next thread to be scheduled.
# Then, write a metaswitcher that will iterate on the switcher.

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
