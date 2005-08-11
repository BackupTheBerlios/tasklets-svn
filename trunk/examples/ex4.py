#!/usr/bin/env python

import sys
try:
    import softlets
except ImportError:
    import _autopath, softlets

def sub_thread(queue, name, count):
    print "begin subthread %s" % name
    for i in range(count):
        queue.put("%s_%d" % (name, i))
        yield softlets.Ready()
    print "end subthread %s" % name

def or_thread(queues, count):
    print "begin main thread"
    n = 3
    cond = None
    for q in queues:
        cond = cond | q
    for i in range(count * len(queues)):
        yield cond
        print "got %s" % cond.pop().get()
    print "end main thread"

nb_queues = 3
iterations = 3
queues = []
for i in range(nb_queues):
    q = softlets.Queue()
    softlets.Softlet(sub_thread(q, chr(ord('A') + i), iterations))
    queues.append(q)
softlets.Softlet(or_thread(queues, iterations))
softlets.main_loop()

