
import subprocess
from threading import Thread

from softlets.core import WaitObject


# For convenience
from subprocess import *
__all__ = list(subprocess.__all__)


class Popen(WaitObject):
    def __init__(self, *args, **kargs):
        WaitObject.__init__(self)
        self.is_async = True
        self.protect()
        self.popen = subprocess.Popen(*args, **kargs)
        self.finished = False
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
