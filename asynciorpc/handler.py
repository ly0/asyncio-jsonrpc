from .bases import Interface
from asynciorpc.rpc.json import JSONRPCHandler
from .config import CONFIG


class HandlerMeta(type):
    def __new__(cls, name, bases, attrs):
        service = type(CONFIG['service'], (Interface,), {})()
        company = type(CONFIG['company'], (Interface,), {CONFIG['service']: service})()
        attrs[CONFIG['company']] = company
        attrs['_service'] = service
        return super().__new__(cls, name, bases, attrs)


class Handler(JSONRPCHandler, metaclass=HandlerMeta):
    pass