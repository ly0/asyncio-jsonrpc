from asynciorpc import config as rpc_config
from asynciorpc.handler import Handler


def register(func, name: str=None, timeout: (int, float)=None):
    """
    Register a handler as RPC interface
    :param func: handler function
    :type func: coroutine function or normal function
    :param name: interface name (rpc name will be COMPANY.SERVICE.name)
    :param timeout: set maximum timeout to run the handler function
    """
    if not name:
        name = func.__name__

    if timeout:
        rpc_config.TIMEOUTS[func] = timeout

    rpc_config.INTERFACES[name] = func

    setattr(Handler._service, name, func)
