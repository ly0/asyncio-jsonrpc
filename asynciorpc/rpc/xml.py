"""
===========================
XML-RPC Handler for Tornado
===========================
This is a XML-RPC server implementation, designed for use within the
Tornado framework. Usage is pretty simple:

>>> from tornadorpc.xml import XMLRPCHandler
>>> from tornadorpc import start_server
>>>
>>> class handler(XMLRPCHandler):
>>> ... def add(self, x, y):
>>> ....... return x+y
>>>
>>> start_server(handler, port=8484)

It requires the xmlrpclib, which is built-in to Python distributions
from version 2.3 on.

"""

from asynciorpc.rpc.base import BaseRPCParser, BaseRPCHandler
import xmlrpc.client as xmlrpclib


class XMLRPCSystem(object):
    # Multicall functions and, eventually, introspection

    def __init__(self, handler):
        self._dispatch = handler._RPC_.dispatch

    def multicall(self, calls):
        for call in calls:
            method_name = call['methodName']
            params = call['params']
            self._dispatch(method_name, params)


class XMLRPCParser(BaseRPCParser):

    content_type = 'text/xml'

    def parse_request(self, request_body):
        try:
            params, method_name = xmlrpclib.loads(request_body)
        except:
            # Bad request formatting, bad.
            return self.faults.parse_error()
        return ((method_name, params),)

    def parse_responses(self, responses):
        try:
            if isinstance(responses[0], xmlrpclib.Fault):
                return xmlrpclib.dumps(responses[0])
        except IndexError:
            pass
        try:
            response_xml = xmlrpclib.dumps(responses, methodresponse=True)
        except TypeError:
            return self.faults.internal_error()
        return response_xml


class XMLRPCHandler(BaseRPCHandler):
    """
    Subclass this to add methods -- you can treat them
    just like normal methods, this handles the XML formatting.
    """
    _RPC_ = XMLRPCParser(xmlrpclib)

    @property
    def system(self):
        return XMLRPCSystem(self)
