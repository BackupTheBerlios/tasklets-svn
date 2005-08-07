#!/usr/bin/env python

import sys
try:
    import softlets
except ImportError:
    import _autopath, softlets

def subthread(name):
    print "begin subthread %s" % name
    yield softlets.Ready()
    print "end subthread %s" % name

def main_thread():
    print "begin main thread"
    ta = softlets.Softlet(subthread('A'))
    tb = softlets.Softlet(subthread('B'))
    yield tb
    print "B finished"
    yield ta
    print "A finished"
    print "end main thread"

softlets.Softlet(main_thread())
softlets.main_loop()

