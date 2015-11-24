"""
============================
Base RPC Handler for Tornado
============================
This is a basic server implementation, designed for use within the
Tornado framework. The classes in this library should not be used
directly, but rather though the XML or JSON RPC implementations.
You can use the utility functions like 'private' and 'start_server'.
"""
import asyncio
import base64
import concurrent
import inspect
import traceback
from .. bases import Interface
from .. pool import tpool
from .utils import getcallargs
from asynciorpc import config as rpc_config
from aiohttp import web

# Configuration element
class Config(object):
    verbose = True
    short_errors = True

config = Config()

class BaseRPCParser(object):
    """
    This class is responsible for managing the request, dispatch,
    and response formatting of the system. It is tied into the
    _RPC_ attribute of the BaseRPCHandler (or subclasses) and
    populated as necessary throughout the request. Use the
    .faults attribute to take advantage of the built-in error
    codes.
    """
    content_type = 'text/plain'

    def __init__(self, library, encode=None, decode=None):
        # Attaches the RPC library and encode / decode functions.
        self.library = library
        if not encode:
            encode = getattr(library, 'dumps')
        if not decode:
            decode = getattr(library, 'loads')
        self.encode = encode
        self.decode = decode
        self.requests_in_progress = 0
        self.responses = []

    @property
    def faults(self):
        # Grabs the fault tree on request
        return Faults(self)

    async def run(self, handler, request_body):
        """
        This is the main loop -- it passes the request body to
        the parse_request method, and then takes the resulting
        method(s) and parameters and passes them to the appropriate
        method on the parent Handler class, then parses the response
        into text and returns it to the parent Handler to send back
        to the client.
        """
        self.handler = handler
        try:
            request_body = request_body.decode()
            requests = self.parse_request(request_body)
        except:
            #self.traceback()
            return [self.faults.parse_error()]

        if not isinstance(requests, tuple):
            # SHOULD be the result of a fault call,
            # according tothe parse_request spec below.
            if isinstance(requests, str):
                # Should be the response text of a fault
                # This will break in Python 3.x
                return requests
            elif hasattr(requests, 'response'):
                # Fault types should have a 'response' method
                return requests.response()
            elif hasattr(requests, 'faultCode'):
                # XML-RPC fault types need to be properly dispatched. This
                # should only happen if there was an error parsing the
                # request above.
                #return self.handler.result(requests)
                return requests.response()
            else:
                # No idea, hopefully the handler knows what it
                # is doing.
                return requests
        self.handler._requests = len(requests)
        responses = []
        for request in requests:
            responses.append(await self.dispatch(request[0], request[1]))
        return responses

    async def dispatch(self, method_name, params):
        """
        This method walks the attribute tree in the method
        and passes the parameters, either in positional or
        keyword form, into the appropriate method on the
        Handler class. Currently supports only positional
        or keyword arguments, not mixed.
        """

        INNER_METHOD = []
        INNER_CLASS = []

        # list all methods
        if method_name == '__dir__':
            return [i for i in dir(self.handler)
                                 if not inspect.isroutine(getattr(self.handler, i))
                                 and not i.startswith('_')
                                 and isinstance(getattr(self.handler, i), Interface)
                                 and i not in INNER_METHOD
                                 ]

        # if hasattr(RequestHandler, method_name):
        #     # Pre-existing, not an implemented attribute
        #     return self.faults.method_not_found()

        method = self.handler
        method_list = dir(method)
        method_list.sort()
        attr_tree = method_name.split('.')

        # check list method
        if '__dir__' not in method_name:
            try:
                for attr_name in attr_tree:
                    method = self.check_method(attr_name, method)
            except AttributeError:
                return self.faults.method_not_found()
        else:
            for attr_name in attr_tree[:-1]:
                if attr_name != '__dir__':
                    method = self.check_method(attr_name, method)
                else:
                    break
            return [i for i in dir(method) if not i.startswith('_')
                                 and not getattr(getattr(method, i), 'private', False)
                                 and not inspect.isroutine(method)
                                 and i not in INNER_METHOD
                                 and not any([isinstance(getattr(method, i), cls) for cls in INNER_CLASS])]

        if not callable(method):
            # Not callable, so not a method
            return self.faults.method_not_found()

        if (method_name.startswith('_')) or \
                getattr(method, 'private', False) is True:
            # No, no. That's private.
            return self.faults.method_not_found()

        def _request_auth(handler):
            handler.set_header('WWW-Authenticate', 'Basic realm=tmr')
            handler.set_status(401)
            return self.faults.not_authorized()

        # HTTP Basic Authentication
        if hasattr(method, '_need_authenticated'):
            auth_func = getattr(method, '_need_authenticated')
            auth_header = self.handler.request.headers.get('Authorization')
            if auth_header is None:
                return _request_auth(self.handler)
            if not auth_header.startswith('Basic '):
                return _request_auth(self.handler)

            auth_decoded = base64.decodebytes(auth_header[6:])
            username, password = auth_decoded.split(':', 2)

            if not auth_func(username, password):
                return _request_auth(self.handler)

        args = []
        kwargs = {}
        if isinstance(params, dict):
            # The parameters are keyword-based
            kwargs = params
        elif type(params) in (list, tuple):
            # The parameters are positional
            args = params
        else:
            # Bad argument formatting?
            return self.faults.invalid_params()
        # Validating call arguments

        try:
            final_kwargs, extra_args = getcallargs(method, *args, **kwargs)
            # check type hints
            type_hints = method.__annotations__
            for k, v in final_kwargs.items():
                if k in type_hints:
                    assert isinstance(v, type_hints[k])
        except (TypeError, AssertionError):
            return self.faults.invalid_params()

        try:
            # Call method
            # modified: pass self.handler to class of method
            #method.__self__.rpc_handler = self.handler
            timeout = rpc_config.TIMEOUTS.get(method)
            if not inspect.iscoroutinefunction(method):
                future = asyncio.wrap_future(tpool.submit(method, *extra_args, **final_kwargs))
            else:
                future = method(*extra_args, **final_kwargs)

            if not timeout:
                response = await future
            else:
                response = await asyncio.wait_for(future, timeout=timeout)
        except (asyncio.TimeoutError, concurrent.futures.TimeoutError):
            return self.faults.service_timeout()
        except ValueError:
            return self.faults.invalid_params()
        except Exception:
            self.traceback(method_name, params)
            return self.faults.internal_error()

        if getattr(method, 'async', False):
            # Asynchronous response -- the method should have called
            # self.result(RESULT_VALUE)
            if response is not None:
                # This should be deprecated to use self.result
                return self.faults.internal_error()
        else:
            # Synchronous result -- we call result manually.
            return response

    def response(self, handler, results):
        """
        This is the callback for a single finished dispatch.
        Once all the dispatches have been run, it calls the
        parser library to parse responses and then calls the
        handler's async method.
        """
        #handler._requests -= 1
        #if handler._requests > 0:
        #    return
        # We are finished with requests, send response
        # if handler._RPC_finished:
        #     # We've already sent the response
        #     raise Exception("Error trying to send response twice.")
        #handler._RPC_finished = True

        responses = tuple(results)
        response_text = self.parse_responses(responses)
        if type(response_text) not in [str, bytes]:
            # Likely a fault, or something messed up
            response_text = self.encode(response_text)
        # Calling the async callback
        #handler.on_result(response_text)
        return response_text

    def traceback(self, method_name='REQUEST', params=[]):
        err_lines = traceback.format_exc().splitlines()
        err_title = "ERROR IN %s" % method_name
        if len(params) > 0:
            err_title = '%s - (PARAMS: %s)' % (err_title, repr(params))
        err_sep = ('-'*len(err_title))[:79]
        err_lines = [err_sep, err_title, err_sep]+err_lines
        if config.verbose:
            if len(err_lines) >= 7 and config.short_errors:
                # Minimum number of lines to see what happened
                # Plus title and separators
                print('\n'.join(err_lines[0:4]+err_lines[-3:]))
            else:
                print('\n'.join(err_lines))
        # Log here
        return

    def parse_request(self, request_body):
        """
        Extend this on the implementing protocol. If it
        should error out, return the output of the
        'self.faults.fault_name' response. Otherwise,
        it MUST return a TUPLE of TUPLE. Each entry
        tuple must have the following structure:
        ('method_name', params)
        ...where params is a list or dictionary of
        arguments (positional or keyword, respectively.)
        So, the result should look something like
        the following:
        ( ('add', [5,4]), ('add', {'x':5, 'y':4}) )
        """
        return ([], [])

    def parse_responses(self, responses):
        """
        Extend this on the implementing protocol. It must
        return a response that can be returned as output to
        the client.
        """
        return self.encode(responses, methodresponse=True)

    def check_method(self, attr_name, obj):
        """
        Just checks to see whether an attribute is private
        (by the decorator or by a leading underscore) and
        returns boolean result.
        """
        if attr_name.startswith('_'):
            raise AttributeError('Private object or method.')
        attr = getattr(obj, attr_name)

        if getattr(attr, 'private', False):
            raise AttributeError('Private object or method.')
        return attr

class BaseRPCHandler:
    """
    This is the base handler to be subclassed by the actual
    implementations and by the end user.
    """
    _RPC_finished = False

    def __init__(self, *args, **kwargs):
        self._RPC_ = None
        self._requests = 0
        self._results = None
        self.status = 200
        self.request = None
        self.response = web.Response(text='', content_type='application/json')
        super().__init__(*args, **kwargs)

    def set_header(self, key, value):
        self.response._headers[key] = value

    def set_status(self, status: int):
        self.response._status = status

    async def post(self, request):
        self._results = []
        self.request = request
        request_body = await request.payload.read()

        responses = await self._RPC_.run(self, request_body)

        response_text = self._RPC_.parse_responses(responses)
        # response_text = self.parse_responses(responses)
        # if type(response_text) not in [str, bytes]:
        #     # Likely a fault, or something messed up
        #     response_text = self.encode(response_text)
        #
        # import ipdb; ipdb.set_trace()
        self.response._status = self.status
        self.response.text = response_text
        return self.response

        #self.finish(response_text)


    def result(self, result, *results):
        """ Use this to return a result. """
        if results:
            results = [result] + results
        else:
            results = result
        self._results.append(results)
        self._RPC_.response(self)

    def on_result(self, response_text):
        """ Asynchronous callback. """
        self.set_header('Content-Type', self._RPC_.content_type)
        self.finish(response_text)




class FaultMethod(object):
    """
    This is the 'dynamic' fault method so that the message can
    be changed on request from the parser.faults call.
    """
    def __init__(self, fault, code, message):
        self.fault = fault
        self.code = code
        self.message = message

    def __call__(self, message=None):
        if message:
            self.message = message
        return self.fault(self.code, self.message)


class Faults(object):
    """
    This holds the codes and messages for the RPC implementation.
    It is attached (dynamically) to the Parser when called via the
    parser.faults query, and returns a FaultMethod to be called so
    that the message can be changed. If the 'dynamic' attribute is
    not a key in the codes list, then it will error.

    USAGE:
        parser.fault.parse_error('Error parsing content.')

    If no message is passed in, it will check the messages dictionary
    for the same key as the codes dict. Otherwise, it just prettifies
    the code 'key' from the codes dict.

    """
    codes = {
        'parse_error': -32700,
        'method_not_found': -32601,
        'invalid_request': -32600,
        'invalid_params': -32602,
        'internal_error': -32603,
        'not_authorized': -32602,
        'service_timeout': -32090
    }

    messages = {}

    def __init__(self, parser, fault=None):
        self.library = parser.library
        self.fault = fault
        if not self.fault:
            self.fault = getattr(self.library, 'Fault')

    def __getattr__(self, attr):
        message = 'Error'
        if attr in self.messages.keys():
            message = self.messages[attr]
        else:
            message = ' '.join(map(str.capitalize, attr.split('_')))
        fault = FaultMethod(self.fault, self.codes[attr], message)
        return fault


"""
Utility Functions
"""


def private(func):
    """
    Use this to make a method private.
    It is intended to be used as a decorator.
    If you wish to make a method tree private, just
    create and set the 'private' variable to True
    on the tree object itself.
    """
    func.private = True
    return func


def async(func):
    """
    Use this to make a method asynchronous
    It is intended to be used as a decorator.
    Make sure you call "self.result" on any
    async method. Also, trees do not currently
    support async methods.
    """
    func.async = True
    return func
