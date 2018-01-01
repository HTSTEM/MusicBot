import time
import json
import hashlib

from aiohttp import web
from .util.checks import permissions_for


class Website:

    def __init__(self, bot):
        self.bot = bot

    async def get_queue(self, request):
        gid = int(request.match_info.get('id', '0'))
        queue = [{
            'title': player.title,
            'duration': player.duration,
            'user': player.user.name if player.user else None,
            'id': hashlib.sha1((player.title+(player.user or '')).encode('utf-8')).hexdigest(),
        } for player in self.bot.queues[gid]]
        if queue:
            queue[0]['time'] = int(time.time()-self.bot.queues[gid][0].start_time)
        return web.Response(text=json.dumps(queue))

    async def skip(self, request):
        data = await request.post()
        pid = data['position']
        guild = int(request.match_info.get('guild_id', '0'))
        try:
            vc = self.bot.voice[guild]
            queue = self.bot.queues[guild]
        except KeyError:
            return web.Response(status=404)

        for n, player in enumerate(queue):
            if hashlib.sha1((player.title+(player.user or '')).encode('utf-8')).hexdigest() == pid:
                if n == 0:
                    vc.stop()
                    return web.Response(status=200)

                else:
                    try:
                        music_cog = self.bot.cogs['Music']
                        music_cog.remove_from_queue(player, guild)
                        return web.Response(status=200)
                    except (AttributeError, KeyError):
                        return web.Response(status=500)

        return web.Response(status=404)

    async def authorize(self, request):
        guild = self.bot.get_guild(int(request.match_info.get('guild_id', '0')))
        if guild is None:
            return web.Response(text='false')
        user = guild.get_member(int(request.match_info.get('user_id', '0')))
        if user is None:
            return web.Response(text='false')
        ctx = lambda: None  # lol ikr
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
        app.router.add_delete('/{guild_id}', self.skip)
        handler = app.make_handler()
        f = self.bot.loop.create_server(handler, '127.0.0.1', '8088')
        await f


def setup(bot):
    bot.add_cog(Website(bot))
