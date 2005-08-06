
from collections import deque

#
# A very simple cooperative threads package using generators,
#

def _singleton(cls):
    instance = []
    def wrapper(*args, **kargs):
        if not instance:
            instance.append(cls(*args, **kargs))
        return instance[0]
    return wrapper

class WaitObject(object):
    def __init__(self):
        self.switcher = current_switcher()
#         self.waiters = []
        self.waiters = deque()

    def get_waiter(self):
        try:
#             return self.waiters.pop()
            return self.waiters.popleft()
        except IndexError:
            return None

    def add_waiter(self, waiter):
        self.waiters.append(waiter)

    def set_ready(self, ready):
        self.switcher.set_ready(self, ready)

class Queue(WaitObject):
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

class _Ready(WaitObject):
    def __init__(self):
        WaitObject.__init__(self)
        self.set_ready(True)

# Special-casing Ready as a singleton is important for scalability
Ready = _singleton(_Ready)


class Softlet(object):
    def __init__(self, func=None, switcher=None):
        self.switcher = switcher or current_switcher()
        self.runner = func or self.run()
        self.switcher.add_thread(self)

class Switcher(object):
    def __init__(self):
        self.threads = set()
        self.ready_objects = set()
        self.nb_switches = 0

    def add_thread(self, thread):
        Ready().add_waiter(thread)
        self.threads.add(thread)

    def set_ready(self, wait_object, ready):
        if ready:
            self.ready_objects.add(wait_object)
        else:
            self.ready_objects.discard(wait_object)

    def run(self):
        while self.threads:
            for r in self.ready_objects:
                thread = r.get_waiter()
                if thread is None or thread.runner is None:
                    continue
                try:
                    self.nb_switches += 1
                    wait_object = thread.runner.next()
                except StopIteration:
                    thread.runner = None
                    self.threads.remove(thread)
                else:
                    wait_object.add_waiter(thread)
                break

current_switcher = _singleton(Switcher)

def main_loop(switcher=None):
    switcher = switcher or current_switcher()
    switcher.run()
