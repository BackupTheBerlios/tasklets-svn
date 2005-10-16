#!/usr/bin/env python

import sys
try:
    import softlets
except ImportError:
    import _autopath, softlets

from softlets.queue import Queue


def sub_thread(queue, name, count):
    print "begin subthread %s" % name
    for i in range(count):
        queue.put("%s_%d" % (name, i))
        yield softlets.Ready()

def or_thread(queues, count):
    print "begin main thread"
    n = 3
    cond = None
    for q in queues:
        cond = cond | q
    for i in range(count * len(queues)):
        print "waiting"
        yield cond
        obj = cond.get()
        print "got %s from %r" % (obj.get(), obj)

nb_queues = 3
iterations = 3
queues = []
for i in range(nb_queues):
    q = Queue()
    softlets.Softlet(sub_thread(q, chr(ord('A') + i), iterations))
    queues.append(q)
softlets.Softlet(or_thread(queues, iterations))
softlets.main_loop()

