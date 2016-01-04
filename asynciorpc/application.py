import argparse
import asyncio
from aiohttp import web
from asynciorpc.handler import Handler
from asynciorpc.config import CONFIG, INTERFACES


async def rpc_handler(request):
    handler_obj = Handler()
    return await handler_obj.post(request)


def get_application():
    app = web.Application()
    app.router.add_route('POST', '/', rpc_handler)
    return app
