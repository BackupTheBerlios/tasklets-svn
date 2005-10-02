
from collections import deque

from common import *


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
    Logical AND between several WaitObjects.
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

