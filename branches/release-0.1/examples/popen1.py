#!/usr/bin/env python

import sys
import itertools
import threading
try:
    import softlets
except ImportError:
    import _autopath, softlets

from softlets.timer import Timer
from softlets.popen import Popen, PIPE

tick = 0.3
command = ["sleep", "3"]
clock_symbols = "-/|\\"
if len(sys.argv) > 1:
    command = sys.argv[1:]

print "Execute a command in a subprocess and wait for completion"

def main_thread():
    print "Executing \"%s\" ..." % ' '.join(command)
    popen = Popen(command, stdout=PIPE, stderr=PIPE)
    clock = itertools.cycle(clock_symbols)
    while not popen.finished:
        print "\r" + clock.next(),
        sys.stdout.flush()
        yield popen | Timer(tick)
    print "\rResult code =", popen.retcode
    print "Output:"
    print popen.popen.communicate()[0]

softlets.Softlet(main_thread())
softlets.main_loop()
