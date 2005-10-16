

# Try to autodetect where in the hierarchy a package is.
# Useful when running examples in subdirectories without
# wanting to install the package in the system dirs.
def _autopath(package_name='softlets', path=None):
    import os, sys
    if path is None:
        path = os.path.abspath(__file__)
    subdir = os.path.join(path, package_name)
    exc = None
    if os.path.isdir(subdir):
        sys.path.append(path)
        try:
            __import__(package_name)
            return
        except ImportError, exc:
            sys.path.remove(path)
    # Get parent
    parent = os.path.split(path)[0]
    if parent == path:
        raise ImportError("Could not find package '%s':\n%s" % (package_name, exc))
    _autopath(package_name, parent)

_autopath()
