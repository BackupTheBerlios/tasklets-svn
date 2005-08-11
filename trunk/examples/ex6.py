#!/usr/bin/env python

import sys
import time
try:
    import softlets
except ImportError:
    import _autopath, softlets

def subthread(name):
    print "begin subthread %s" % name
    time.sleep(1)
    yield softlets.Ready()
    time.sleep(1)
    print "** error: we should never get here"

def main_thread():
    print "begin main thread"
    ta = softlets.Softlet(subthread('A'))
    tb = softlets.Softlet(subthread('B'))
    yield softlets.Ready()
    print "end main thread, killing subthreads"

softlets.Softlet(main_thread())
softlets.main_loop()

