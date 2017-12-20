import time
import json

from aiohttp import web
from .util.checks import permissions_for

class Website:

    def __init__(self, bot):
        self.bot = bot

    async def get_queue(self, request):
        id = int(request.match_info.get('id', '0'))
        queue = [{
            'title': player.title,
            'duration': player.duration,
            'user': player.user.name if player.user else None,
        } for player in self.bot.queue[id]]
        queue[0]['time'] = int(time.time()-self.bot.queue[0].start_time)
        web.Response(text=json.dumps(queue))

    async def authorize(self, request):
        guild = self.bot.get_guild(int(request.match_info.get('guild_id', '0')))
        if guild is None: return web.Response(text='false')
        user = guild.get_member(int(request.match_info.get('user_id', '0')))
        if user is None: return False
        ctx = lambda: None # lol ikr
        ctx.author = user
        ctx.bot = self.bot
        perms = await permissions_for(ctx)
        if 'moderation' in perms['categories']:
            return web.Response(text='true')
        else:
            return web.Response(text='false')


    async def on_ready(self):
        app = web.Application()
        app.router.add_get('/authorize/{guild_id}/{user_id}', self.authorize)
        app.router.add_get('/{id}/playlist', self.get_queue)
        handler = app.make_handler()
        f = self.bot.loop.create_server(handler, '127.0.0.1', '8088')
        await f


def setup(bot):
    bot.add_cog(Website(bot))