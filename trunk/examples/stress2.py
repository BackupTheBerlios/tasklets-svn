#!/usr/bin/env python

import sys
import time
try:
    import softlets
except ImportError:
    import _autopath, softlets

from softlets.timer import Timer


nb_threads = len(sys.argv) > 1 and int(sys.argv[1]) or 2000
nb_sleeps = 0
nb_simult = 0
max_simult = 0
abs_delay = 1.0
target = time.time() + abs_delay

def sleeping_thread():
    global nb_simult, nb_sleeps, max_simult
    nb_simult += 1
    yield Timer(max(0.0, target - time.time()))
    max_simult = max(max_simult, nb_simult)
    nb_simult -= 1
    nb_sleeps += 1

def setup_threads():
    for i in xrange(1, nb_threads + 1):
        softlets.Softlet(sleeping_thread())

def run_threads():
    softlets.main_loop()

def duration(fun):
    _t = time.time
    _f = fun
    t1 = _t()
    _f()
    t2 = _t()
    return t2 - t1

dt = duration(lambda: setup_threads())
print "Setup %d threads in %f seconds" % (nb_threads, dt)
dt = duration(lambda: run_threads())
print "Ran up to %d simultaneous timers in %f seconds" % (max_simult, dt)

