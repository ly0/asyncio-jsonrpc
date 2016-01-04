import argparse
import asyncio
from aiohttp import web
from asynciorpc.handler import Handler
from asynciorpc.config import CONFIG, INTERFACES
from asynciorpc.application import get_application

async def rpc_handler(request):
    handler_obj = Handler()
    return await handler_obj.post(request)

def run(*, wsgi=False):
    app = get_application()

    if wsgi:
        return app

    service_name = '%s.%s' % (CONFIG['company'], CONFIG['service'])
    current_interfaces = ['    %s.%s' % (service_name, x) for x in INTERFACES.keys()]
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='''Run rpc service {company}.{service}

Current registered interfaces
{current_interfaces}
        '''.format(company=CONFIG['company'],
                   service=CONFIG['service'],
                   current_interfaces='\n'.join(current_interfaces))
    )

    parser.add_argument('--port', metavar='port',
                        type=int,
                        default=CONFIG['rpc_port'],
                        help='service runs on this port')

    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    handler = app.make_handler()
    f = loop.create_server(handler, '0.0.0.0', args.port)
    srv = loop.run_until_complete(f)

    print('Server listening on port', args.port)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(handler.finish_connections(1.0))
        srv.close()
        loop.run_until_complete(srv.wait_closed())
        loop.run_until_complete(app.finish())
    loop.close()
