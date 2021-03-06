
import subprocess
from threading import Thread

from softlets.core import WaitObject


# For convenience
from subprocess import *
__all__ = list(subprocess.__all__)


class Popen(WaitObject):
    """
    Executes a command in a subprocess (with the same args as
    subprocess.Popen), and becomes ready when the subprocess ends.
    The following properties are defined:
    - popen: the underlying subprocess.Popen object
    - retcode: the return code of the subprocess (if finished)

    The implementation is not optimal, as a helper thread is created
    for each subprocess.
    """
    def __init__(self, *args, **kargs):
        """
        Launch a command in a subprocess.
        Arguments are passed to subprocess.Popen.
        """
        WaitObject.__init__(self)
        self.is_async = True
        self.protect()
        self.popen = subprocess.Popen(*args, **kargs)
        self.finished = False
        self._thread = None

    def arm(self):
        r = self.popen.poll()
        if r is not None:
            # Avoid launching a thread if already finished
            self.retcode = r
            self._on_subprocess_exited()
        else:
            self._start_polling()

    def _start_polling(self):
        # We create a thread for each subprocess, because Python
        # has no portable primitive to wait asynchronously for
        # multiple processes.
        # XXX: try a poll/sleep loop instead
        self._thread = Thread(target=self._blocking_wait,
            name="softlets.popen helper thread")
        self._thread.setDaemon(True)
        self._thread.start()

    def _blocking_wait(self):
        self.retcode = self.popen.wait()
        self._on_subprocess_exited()

    def _on_subprocess_exited(self):
        self.finished = True
        self.set_ready(True)
