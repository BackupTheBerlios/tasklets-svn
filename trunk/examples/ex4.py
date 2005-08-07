#!/usr/bin/env python

import sys
try:
    import softlets
except ImportError:
    import _autopath, softlets

class Subthread(softlets.Softlet):
    def __init__(self, name, count):
        softlets.Softlet.__init__(self)
        self.name = name
        self.count = count

    def run(self):
        print "begin subthread %s" % self.name
        for i in range(self.count):
            yield softlets.Ready()
        print "end subthread %s" % self.name

def or_thread():
    print "begin main thread"
    n = 3
    cond = None
    for i in range(3):
        cond = cond | Subthread(name=chr(ord('A') + i), count=n)
    for i in range(3 * n):
        yield cond
        print cond.pop().name
    print "end main thread"

softlets.Softlet(or_thread())
softlets.main_loop()

