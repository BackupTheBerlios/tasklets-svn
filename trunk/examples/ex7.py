#!/usr/bin/env python

import sys
try:
    import softlets
except ImportError:
    import _autopath, softlets

from softlets.timer import Timer


nb_threads = len(sys.argv) > 1 and int(sys.argv[1]) or 10
step = 0.1

def thread(name, delay):
    print "Thread %s: waiting for %s s." % (name, str(delay))
    yield Timer(delay)
    print "Thread %s: finished" % name

for i in range(nb_threads):
    name = chr(ord('A') + (i&15)) + str(i>>4)
    softlets.Softlet(thread(name, (nb_threads - i) * step))

softlets.main_loop()
