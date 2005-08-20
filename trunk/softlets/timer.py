
from softlets.core import WaitObject
from softlets.timethread import TimeThread

__all__ = ['Timer']

class Timer(WaitObject):
    """
    This object becomes ready when a certain delay has expired.
    """
    timethread = TimeThread()
    timethread_started = False
    lock = timethread.get_lock()

    def __init__(self, delay):
        WaitObject.__init__(self)
        self.delay = delay
        self.callback = None
        self.is_async = True
        self.protect()
        if not self.timethread_started:
            self.timethread.start()
            self.timethread_started = True
        self.reschedule()

    def reschedule(self):
        # take the lock to ensure the callback doesn't
        # expire in the meantime
        self.lock.acquire()
        try:
            if self.callback:
                self.timethread.remove_timer(self.callback)
            self.set_ready(False)
            self.callback = self.timethread.add_timer(self.delay, self.on_delay_expired, keep_lock=True)
        finally:
            self.lock.release()

    def on_delay_expired(self):
        # the timethread has already taken the lock for us
        self.set_ready(True)
        self.callback = None

