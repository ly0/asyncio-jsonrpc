Asyncio-JSONRPC
======

based on https://github.com/joshmarshall/tornadorpc

**This is a experimental project, which tends to change frequently. Caveat Emptor!**


## Signatures of `register`
```python
register(func, name:str=None, timeout:(int, float)=None)
```

Try to use `python3 server.py -h` to see what optional arguments you can offer.

## Config

```yaml
# Server settings
rpc_port: 10080

# RPC settings
company: github
service: user
```

## Handler

A simple example:

```python
def add_user(username: str, password: str):
    if username == 'test':
        return True
    else:
        raise Exception('test exception: Username invalid')
```

Type hints are optional, if you specify them, parameter types will be checked in runtime.
Asyncio-JSONRPC can detect your handler's type, if handler

1. Type is `asyncio.coroutine`, `await handler(*args, **kwargs)` will be invoked
2. Type isn't `asyncio.coroutine`
    * if handler has attribute `_new_process`, it will be executed in a ProcessExecutorPool
    * else handler will be executed in a ThreadExecutorPool.


### HTTP Basic Authentication
Add attribute `_need_authenticated` with value is `auth_handler`, `auth_handler` is a function which has two keyword
parameters `username, password`, it should return `True` or `False` to check if user should be granted.

Create a file (`server.py` or something else)

```python
from asynciorpc.interface.register import register
from asynciorpc.runner import run

# put your implement codes to implements package
# import here and register as an asynciorpc

class TestClass:

    def test(self, a, b):
        import time
        time.sleep(10)
        return (1, a, b)

    def test2(self, a, b):
        return (1, a, b)

a = TestClass()
register(a.test, 'TestApi') # http://127.0.0.1:10080/github.user.TestApi
register(a.test2, 'TestApi2') # http://127.0.0.1:10080/github.user.TestApi2

run()
```

## Attention
`handler` must return python builtin types, such as `int`, `float`, `str`, `dict`, `list`, others like `datetime.datetime`
are not supported, JSON serialization exceptions will be raised.
