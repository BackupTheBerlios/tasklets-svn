#!/usr/bin/env python

import sys
import time
try:
    import softlets
except ImportError:
    import _autopath, softlets

def subthread(name, delay):
    print "begin subthread %s" % name
    yield softlets.Timer(delay)
    print "end subthread %s" % name

def main_thread():
    print "waiting on two threads"
    ta = softlets.Softlet(subthread('A', 1))
    tb = softlets.Softlet(subthread('B', 2))
    yield ta | tb
    if ta.finished:
        print "A finished"
        yield tb
    elif tb.finished:
        print "B finished"
        yield ta
    print "A & B finished"

softlets.Softlet(main_thread())
softlets.main_loop()

