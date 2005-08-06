#!/usr/bin/env python

import sys
try:
    import softlets
except ImportError:
    import _autopath, softlets

def looping_thread(count):
    cond = softlets.Ready()
    for i in xrange(count):
        yield cond

nb_threads = len(sys.argv) > 1 and int(sys.argv[1]) or 1000
iterations = 100

def setup_threads():
    for i in xrange(nb_threads):
        softlets.Softlet(looping_thread(iterations))

def run_threads():
    softlets.main_loop()

def duration(fun):
    import time
    _t = time.time
    _f = fun
    t1 = _t()
    _f()
    t2 = _t()
    return t2 - t1

dt = duration(lambda: setup_threads())
print "Setup %d threads in %f seconds" % (nb_threads, dt)
dt = duration(lambda: run_threads())
print "Switched %d times between %d threads in %f seconds" % \
    (softlets.current_switcher().nb_switches, nb_threads, dt)

