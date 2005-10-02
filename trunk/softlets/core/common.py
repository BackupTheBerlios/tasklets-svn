"""
Common base stuff.
"""

import threading

__all__ = [
    '_singleton', '_lock', '_protect', '_unprotect',
    ]


def _singleton(cls):
    instance = []
    def wrapper(*args, **kargs):
        if not instance:
            instance.append(cls(*args, **kargs))
        return instance[0]
    return wrapper

# def _local_singleton(cls):
#     instances = {}
#     def wrapper(*args, **kargs):
#         switcher = current_switcher()
#         try:
#             instance = instances[switcher]
#         except KeyError:
#             instance = cls(*args, **kargs)
#             instances[switcher] = instance
#         return instance
#     return wrapper

#
# To be used when other threads have to interact with
# a switcher thread.
#
_lock = threading.Lock()

def _protect(func, lock=None):
    lock = lock or _lock
    try:
        func.__unprotected
    except AttributeError:
        def wrapper(*args, **kargs):
            lock.acquire()
            try:
                return func(*args, **kargs)
            finally:
                lock.release()
        wrapper.__unprotected = func
        return wrapper
    else:
        return func

def _unprotect(func):
    try:
        return func.__unprotected
    except AttributeError:
        return func
