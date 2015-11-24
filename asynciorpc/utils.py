import asyncio
import socket


@asyncio.coroutine
def future_to_coroutine(future):
    """
    In Mac OS asyncio.coroutine may be turned to generator,
    that can't be used after `await`
    """
    foo = yield from future
    return foo
