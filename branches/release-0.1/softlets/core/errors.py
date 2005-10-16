"""
Various exception classes used in Softlets.
"""

class Error(StandardError):
    """
    An error in Softlets-related stuff.
    """
    def __str__(self):
        try:
            s = self.msg
        except AttributeError:
            s = self.__doc__
        except AttributeError:
            s = StandardError.__str__(self)
        # Undo formatting in docstrings
        lines = s.splitlines()
        lines = [l.strip() for l in lines]
        s = '\n'.join([l for l in lines if l])
        return s

class Starvation(Error):
    """
    Softlets are starved.
    This means all softlets are waiting but none can be woken up,
    and there are no async objects.
    """
