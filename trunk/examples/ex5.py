#!/usr/bin/env python

import sys
try:
    import softlets
except ImportError:
    import _autopath, softlets

def sub_thread(queue, name, count):
    print "begin subthread %s" % name
    for i in range(count):
        queue.put("%s_%d_first" % (name, i))
        queue.put("%s_%d_second" % (name, i))
        yield softlets.Ready()

def and_thread(queues, count):
    print "begin main thread"
    n = 3
    cond = None
    for q in queues:
        cond = cond & q
    for i in range(count):
        print "waiting"
        yield cond
        for obj in cond.objects():
            print "got %s from %r" % (obj.get(), obj)

nb_queues = 3
iterations = 2
queues = []
for i in range(nb_queues):
    q = softlets.Queue()
    softlets.Softlet(sub_thread(q, chr(ord('A') + i), iterations))
    queues.append(q)
softlets.Softlet(and_thread(queues, iterations))
softlets.main_loop()

