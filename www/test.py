# encoding=utf-8
import orm
from models import User, Blog, Comment
import asyncio

@asyncio.coroutine
def test(loop):
    yield from  orm.create_pool(loop=loop,user = 'www-data', password = 'www-data', db = 'awesome')

    user = User(name = 'Test', email='test@example1.com', passwd = '123456', image = 'blank:link')

    yield from user.save()

loop = asyncio.get_event_loop()
loop.run_until_complete(test(loop))
loop.close()