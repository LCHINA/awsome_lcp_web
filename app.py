# encoding:utf-8

import logging; logging.baseConfig(level=Logging.INFO)

import asyncio,os,json,time

from datetime import datetime

from aiohttp import web

def index(request):
    return web.Response(body=b'<h1>Awesome</h1>')

@asyncio.cotoutine
def init(loop1):
    app=web.Application(loop=loop1)
    app.route.add_route('GET','/',index)
    srv = await loop1.create_server(app.make_handler(),'127.0.0.1',9000)
    logging.info('server started at http://127.0.0.1:9000')
    return srv


loop=asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()