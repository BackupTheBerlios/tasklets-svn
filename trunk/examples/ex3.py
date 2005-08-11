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
    print "end subthread %s" % name

def main_thread():
    print "begin main thread"
    ta = softlets.Softlet(subthread('A'))
    tb = softlets.Softlet(subthread('B'))
    yield ta
    print "A finished"
    yield tb
    print "B finished"
    print "end main thread"

softlets.Softlet(main_thread())
softlets.main_loop()

