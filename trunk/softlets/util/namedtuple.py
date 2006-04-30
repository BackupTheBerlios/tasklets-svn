
from operator import itemgetter

def NamedTuple(*names):
    """
    Create a named tuple class from a list of property names.
    """
    name_to_index = dict([(name, index) for index, name in enumerate(names)])
    n = len(names)
    tdoc = "Automatically generated named tuple.\n"
    tdoc += "Properties are (in slot order):\n"
    for name in names:
        tdoc += "- '%s'\n" % name
    tdoc += "This class has the natural characteristics of a tuple:\n"
    tdoc += "light memory usage, builtin comparison, builtin hashing...\n"

    class T(tuple):
        __doc__ = tdoc
        def __new__(cls, *args, **kargs):
            nk = len(kargs)
            np = len(args)
            if np + nk != n:
                raise TypeError("%d elements expected, got %d" % (n, np + nk))
            if not nk:
                t = args
            else:
                try:
                    t = args + tuple(kargs[names[i]] for i in xrange(np, n))
                except KeyError:
                    for i in xrange(np, n):
                        if names[i] not in kargs:
                            raise TypeError("Missing parameter '%s'" % names[i])
                    assert False # should not happen
            return tuple.__new__(cls, t)
    for name, index in name_to_index.items():
        setattr(T, name, property(
            fget=itemgetter(index),
            doc="Property '%s' (slot #%d of named tuple)" % (name, index),
            ))
    return T


def __test():
    Point = NamedTuple('x', 'y')
    print Point.__doc__
    a = Point(1, 2)
    b = Point(y=2, x=1)
    print a
    print b
    print a[0], a[1]
    print b[0], b[1]


if __name__ == "__main__":
    __test()

