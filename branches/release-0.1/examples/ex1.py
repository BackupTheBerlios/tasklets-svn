#!/usr/bin/env python

try:
    import softlets
except ImportError:
    import _autopath, softlets

from softlets.queue import Queue


q1 = Queue()
q2 = Queue()
iterations = 3

def thread_a(n, qin, qout):
    for i in range(n):
        qout.put(i)
#         print "Thread A put '%s'" % i
        yield qin
        print "Thread A got '%s'" % qin.get()

def thread_b(n, qin, qout):
    for i in reversed(range(n)):
        qout.put(i)
#         print "Thread B put '%s'" % i
        yield qin
        print "Thread B got '%s'" % qin.get()

def thread_c(n):
    for i in range(n):
        yield softlets.Ready()
        print "Thread C running"

def thread_d(n):
    for i in range(n):
        yield softlets.Ready()
        print "Thread D running"

softlets.Softlet(thread_a(iterations, q1, q2))
softlets.Softlet(thread_b(iterations, q2, q1))
softlets.Softlet(thread_c(iterations))
softlets.Softlet(thread_d(iterations))
softlets.main_loop()
