
import threading
from thread import get_ident

from softlets.core.common import *
from softlets.core.errors import *
from softlets.core.waitobject import WaitObject

#
# Ready object
#
class _Ready(WaitObject):
    """
    The Ready object is always ready.
    It is used implicitly when a thread is launched,
    or explicitly when a thread wants to temporarily
    yield control without actually waiting on anything.
    """
    def __init__(self):
        WaitObject.__init__(self)
        self.set_ready(True)

# Special-casing Ready improves scalability with many threads
Ready = _singleton(_Ready)


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
        self.async_cond = threading.Condition(threading.Lock())
        self.async_calls = []

    def add_thread(self, thread):
        # Called in-thread
        wait_object = Ready()
        wait_object.add_waiter(thread)
        thread.waiting_on = wait_object
        self.threads.add(thread)
        if thread.daemon:
            self.nb_daemons += 1

    def remove_thread(self, thread):
        # Called in-thread
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
        if async:
            def f():
                self.set_ready(wait_object, ready)
            self.push_async_call(f)
            return
        else:
            # In-thread
            if ready:
                self.ready_objects.add(wait_object)
            else:
                self.ready_objects.discard(wait_object)

    def add_ready_object(self, wait_object):
        # Called in-thread
        self.ready_objects.add(wait_object)

    def remove_ready_object(self, wait_object):
        # Called in-thread
        self.ready_objects.remove(wait_object)

    def push_async_call(self, func):
        # Called out-of-thread
        self.async_cond.acquire()
        self.async_calls.append(func)
        self.async_cond.notify()
        self.async_cond.release()

    def run_async_calls(self):
        # Called in-thread while locked
        for fun in self.async_calls:
            fun()
        del self.async_calls[:]

    def run(self):
        A, R = (self.async_cond.acquire, self.async_cond.release)
        while len(self.threads) > self.nb_daemons:
            # Process pending async calls
            if self.async_calls:
                A()
                self.run_async_calls()
                R()
            # This loop is a fake: we always break because
            # thread calls inside the loop can change the set size
            for r in self.ready_objects:
                # Give control to a thread
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
                # self.ready_objects is empty
                async = self.nb_async_waits > 0
                if not async:
                    raise Starvation()
                A()
                self.async_cond.wait()
                self.run_async_calls()
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
