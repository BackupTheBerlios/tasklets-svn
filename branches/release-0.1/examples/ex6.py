#!/usr/bin/env python

import sys
import time
try:
    import softlets
except ImportError:
    import _autopath, softlets

from softlets.timer import Timer


def subthread(name):
    print "begin subthread %s" % name
    yield Timer(2)
    print "** error: we should never get here"

def main_thread():
    print "main thread will kill subthreads on ending"
    ta = softlets.Softlet(subthread('A'))
    tb = softlets.Softlet(subthread('B'))
    yield Timer(1)
    print "end main thread"

softlets.Softlet(main_thread())
softlets.main_loop()

