"""
Various utilities for the TornadoRPC library.
"""

import inspect
from .. config import CONFIG


def getcallargs(func, *positional, **named):
    """
    Simple implementation of inspect.getcallargs function in
    the Python 2.7 standard library.

    Takes a function and the position and keyword arguments and
    returns a dictionary with the appropriate named arguments.
    Raises an exception if invalid arguments are passed.
    """
    signature = inspect.getfullargspec(func)
    args = signature.args
    varargs = signature.varargs
    varkw = signature.varkw
    defaults = signature.defaults

    final_kwargs = {}
    extra_args = []
    # has_self = inspect.ismethod(func) and func.im_self is not None
    # Note: statement after or is a bullshit way to determine a function-like
    #       object is a bound method
    has_self = inspect.ismethod(func) and hasattr(func, '__self__') \
               or (not hasattr(func, '__self__') and 'self' in func.__code__.co_varnames)




    if has_self and len(args) > 0:
        args.pop(0)

    # (Since our RPC supports only positional OR named.)
    if named:
        for key, value in named.items():
            arg_key = None
            try:
                arg_key = args[args.index(key)]
            except ValueError:
                if not varkw:
                    raise TypeError("Keyword argument '%s' not valid" % key)
            if key in final_kwargs.keys():
                message = "Keyword argument '%s' used more than once" % key
                raise TypeError(message)
            final_kwargs[key] = value
    else:
        for i in range(len(positional)):
            value = positional[i]
            arg_key = None
            try:
                arg_key = args[i]
            except IndexError:
                if not varargs:
                    raise TypeError("Too many positional arguments")
            if arg_key:
                final_kwargs[arg_key] = value
            else:
                extra_args.append(value)
    if defaults:
        for kwarg, default in zip(args[-len(defaults):], defaults):
            final_kwargs.setdefault(kwarg, default)
    for arg in args:
        if arg not in final_kwargs:
            raise TypeError("Not all arguments supplied. (%s)", arg)
    return final_kwargs, extra_args

def getfullmethod(method_name):
    return '%s.%s.%s' % (CONFIG['company'], CONFIG['service'], method_name)