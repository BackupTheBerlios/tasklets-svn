
from operator import itemgetter

def NamedTuple(*names):
    """
    Create a named tuple class from a list of property names.
    """
    d = dict([(name, index) for index, name in enumerate(names)])
    n = len(names)
    tdoc = "Automatically generated named tuple.\n"
    tdoc += "Properties are (in slot order):\n"
    for name in d:
        tdoc += "- '%s'\n" % name
    tdoc += "This class has the natural characteristics of a tuple:\n"
    tdoc += "light memory usage, builtin comparison, builtin hashing...\n"

    class T(tuple):
        __doc__ = tdoc
        def __new__(cls, *args, **kargs):
            p = len(args)
            assert p + len(kargs) == n
            l = list(args) + [None] * (n - p)
            for k, v in kargs.items():
                i = d[k]
                assert i >= p
                l[i] = v
            return tuple.__new__(cls, l)
    for name, index in d.items():
        setattr(T, name, property(
            fget=itemgetter(index),
            doc="Property '%s' (slot #%d of named tuple)" % (name, index),
            ))
    return T
