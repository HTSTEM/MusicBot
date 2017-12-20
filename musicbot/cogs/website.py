import time
import json

from aiohttp import web

class Website:

    def __init__(self, bot):
        self.bot = bot

    async def get_queue(self, request):
        queue = [{
            'title': player.title,
            'duration': player.duration,
            'user': player.user.name if player.user else None,
        } for player in self.bot.queue]
        queue[0]['time'] = int(time.time()-self.bot.queue[0].start_time)
        web.Response(text=json.dumps(queue))

    async def authorize(self, request):
        id = int(request.match_info.get('id', '0'))
        member = self.bot.get_guild(297811083308171264).get_member(id)
        print(id)
        if member is None:
            return web.Response(text='false')
        else:
            for role in member.roles:
                if role.id == 303278074672185346:
                    return web.Response(text='true')
            else:
                return web.Response(text='false')

    async def on_ready(self):
        app = web.Application()
        app.router.add_get('/authorize/{id}', self.authorize)
        app.router.add_get('/playlist', self.get_queue)
        handler = app.make_handler()
        f = self.bot.loop.create_server(handler, '127.0.0.1', '8088')
        await f


def setup(bot):
    bot.add_cog(Website(bot))