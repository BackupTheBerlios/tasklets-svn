
from collections import deque
import threading
from thread import get_ident

def _singleton(cls):
    instance = []
    def wrapper(*args, **kargs):
        if not instance:
            instance.append(cls(*args, **kargs))
        return instance[0]
    return wrapper

def _local_singleton(cls):
    instances = {}
    def wrapper(*args, **kargs):
        switcher = current_switcher()
        try:
            instance = instances[switcher]
        except KeyError:
            instance = cls(*args, **kargs)
            instances[switcher] = instance
        return instance
    return wrapper

#
# To be used when other threads have to interact with
# a switcher thread.
#
_lock = threading.Lock()

def _protect(func, lock=None):
    lock = lock or _lock
    try:
        func.__unprotected
    except AttributeError:
        def wrapper(*args, **kargs):
            lock.acquire()
            try:
                return func(*args, **kargs)
            finally:
                lock.release()
        wrapper.__unprotected = func
        return wrapper
    else:
        return func

def _unprotect(func):
    try:
        return func.__unprotected
    except AttributeError:
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
        self.is_async = False

    def protect(self, lock=None):
        lock = lock or _lock
        self.get_waiter = _protect(self.get_waiter, lock)
        self.add_waiter = _protect(self.add_waiter, lock)
        self.set_ready = _protect(self.set_ready, lock)
        self.notify_readiness = _protect(self.notify_readiness, lock)

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
            if self.is_async:
                switcher.remove_async_wait(self)
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
            if self.is_async:
                switcher.add_async_wait(self)

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

    def __invert__(self):
        return LogicalNot(self)


class _Ready(WaitObject):
    def __init__(self):
        WaitObject.__init__(self)
        self.set_ready(True)

# Special-casing Ready improves scalability with many threads
Ready = _singleton(_Ready)


class LogicalNot(WaitObject):
    """
    Logical negation of a WaitObject.
    This class is invoked with the "~" operator.
    """
    def __init__(self, obj):
        WaitObject.__init__(self)
        self.obj = obj
        self.is_async = obj.is_async
        self.set_ready(not obj.ready)

    def arm(self):
        self.obj.notify_readiness(self.on_object_ready)

    def on_object_ready(self, obj, ready):
        self.set_ready(not ready)

    def __invert__(self):
        return self.obj


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
            self.is_async |= obj.is_async
            obj.notify_readiness(self.on_object_ready)

    def on_object_ready(self, obj, ready):
        if ready:
            self.ready_objs.add(obj)
        else:
            self.ready_objs.discard(obj)
        self.update_readiness()

    def get(self):
        try:
            return iter(self.ready_objs).next()
        except StopIteration:
            return None

    def objects(self):
        while True:
            try:
                obj = iter(self.ready_objs).next()
            except StopIteration:
                break
            else:
                yield obj


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
# Softlet object
#

class Softlet(WaitObject):
    """
    A Softlet is an object that represents a cooperative thread.
    A Softlet is automatically registered to a specific switcher
    which handles the scheduling of all softlets attached to it.
    (for now and by default, there is only one switcher)
    """

    def __init__(self, func=None, standalone=False, daemon=False):
        """
        Create Softlet from given generator, or from
        the overriden run() method if "func" is not specified.
        If "standalone" is True, Softlet won't be killed
        when parent terminates.
        If "daemon" is True, Softlet is automatically killed
        when no non-daemon Softlets are left.
        """
        WaitObject.__init__(self)
        self.standalone = standalone
        self.switcher = current_switcher()
        self.children = set()
        self.daemon = daemon
        if not standalone:
            self.parent = self.switcher.current_thread
            if self.parent:
                self.parent.children.add(self)
        else:
            self.parent = None
        self.waiting_on = None
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
        while True:
            try:
                child = iter(self.children).next()
            except StopIteration:
                break
            else:
                child.terminate()


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
        self.nb_daemons = 0
        self.current_thread = None
        # Async signalling (objects waken out of the switcher thread)
        self.tid = get_ident()
        self.nb_async_waits = 0
        self.async_cond = threading.Condition()

    def add_thread(self, thread):
        wait_object = Ready()
        wait_object.add_waiter(thread)
        thread.waiting_on = wait_object
        self.threads.add(thread)
        if thread.daemon:
            self.nb_daemons += 1

    def remove_thread(self, thread):
        self.threads.remove(thread)
        if thread.daemon:
            self.nb_daemons -= 1

    def add_async_wait(self, wait_object):
        # Called in-thread
        self.nb_async_waits += 1

    def remove_async_wait(self, wait_object):
        # Called in-thread
        self.nb_async_waits -= 1

    def set_ready(self, wait_object, ready):
        # May be called async (out-of-thread)
        async = (get_ident() != self.tid)
        if ready:
            if async:
                self.async_cond.acquire()
                self.ready_objects.add(wait_object)
                self.async_cond.notify()
                self.async_cond.release()
            else:
                self.ready_objects.add(wait_object)
        else:
            self.ready_objects.discard(wait_object)

    def add_ready_object(self, wait_object):
        # Called in-thread
        self.ready_objects.add(wait_object)

    def remove_ready_object(self, wait_object):
        # Called in-thread
        self.ready_objects.remove(wait_object)

    def run(self):
        _ar_null = (lambda: 0, lambda: 0)
        _ar_async = (self.async_cond.acquire, self.async_cond.release)
        while len(self.threads) > self.nb_daemons:
            async = self.nb_async_waits > 0
            A, R = async and _ar_async or _ar_null
            A()
            if not self.ready_objects:
                if not async:
                    raise Exception("softlets starved")
                self.async_cond.wait()
            for r in self.ready_objects:
                R()
                thread = r.get_waiter(self)
                if thread is None or thread.finished:
                    break
                self.nb_switches += 1
                try:
                    self.current_thread = thread
                    wait_object = thread.runner.next()
                except Exception, e:
                    self.current_thread = None
                    thread.terminate()
                    if not isinstance(e, StopIteration):
                        raise
                else:
                    self.current_thread = None
                    wait_object.add_waiter(thread)
                    thread.waiting_on = wait_object
                break
            else:
                R()

#
# Functions
#

current_switcher = _singleton(Switcher)
current_switcher.__doc__ = """
Returns the switcher currently in use.
"""

def current_softlet():
    """
    Returns the currently running softlet,
    or None if not called from a softlet.
    """
    return current_switcher().current_thread

def main_loop(switcher=None):
    """
    Runs the softlets main loop.
    """
    switcher = switcher or current_switcher()
    switcher.run()
