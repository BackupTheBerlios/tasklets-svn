
from softlets.core import WaitObject

class Queue(WaitObject):
    """
    A general message queue (FIFO) to communicate between threads.
    Can contain any kind of objects.
    """
    def __init__(self):
        WaitObject.__init__(self)
        self.data = []

    def put(self, value):
        """
        Put a value in the queue.
        """
#         _lock.acquire()
        if not self.data:
            self.set_ready(True)
        self.data.append(value)
#         _lock.release()

    def get(self):
        """
        Get and remove a value from the queue.
        """
#         _lock.acquire()
        if len(self.data) == 1:
            self.set_ready(False)
        value = self.data.pop(0)
#         _lock.release()
        return value

