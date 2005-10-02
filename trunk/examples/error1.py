#!/usr/bin/env python

import sys
try:
    import softlets
except ImportError:
    import _autopath, softlets

from softlets.queue import Queue

print "A consumer without producer..."

def main_thread():
    q = Queue()
    print "... trying to fetch from queue\n"
    yield q

softlets.Softlet(main_thread())
softlets.main_loop()
