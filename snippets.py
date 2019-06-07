"""
Some useful snippets of code that may come into use
at some point.
"""

__author__ = 'Ali Scott'

def get_class(name):
    """Retreives a class from a class name."""

    # loop through modules in name
    parts = name.split('.')
    try:
        module = __import__('.'.join(parts[0:-1]))
        for m in parts[1:-1]:
            module = getattr(module, m)
        return getattr(module, parts[-1])
    except ValueError:
        return None
