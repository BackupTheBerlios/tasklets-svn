#!/usr/bin/env python

try:
    import softlets
except ImportError:
    import _autopath, softlets

from softlets.queue import Queue
from softlets.timer import Timer

q = Queue()
iterations = 4

print "Producer/consumer running in lock step"

def producer(n, qout):
    for i in range(n):
        yield ~qout
        print "Thread A put '%s'" % (n-i)
        qout.put(n-i)

def consumer(n, qin):
    for i in range(n):
        yield Timer(0.1)
        yield qin
        print "Thread B got '%s'" % qin.get()

softlets.Softlet(producer(iterations, q))
softlets.Softlet(consumer(iterations, q))
softlets.main_loop()
