import time
import json
import hashlib

from aiohttp import web
from .util.checks import permissions_for
from .util.categories import category

from discord.ext import commands

cog = None


class Website:

    def __init__(self, bot):
        self.bot = bot
        self.app = web.Application()
        self.app.router.add_get('/authorize/{guild_id}/{user_id}', self.authorize)
        self.app.router.add_get('/{guild_id}/playlist', self.get_queue)
        self.app.router.add_delete('/{guild_id}', self.skip)
        self.handler = self.app.make_handler()
        self.server = self.bot.loop.create_server(self.handler, '127.0.0.1', '8088')

    async def get_queue(self, request):
        gid = int(request.match_info.get('guild_id', '0'))
        queue = [{
            'title': player.title,
            'duration': player.duration,
            'user': player.user.name if player.user else 'Autoplaylist',
            'id': hashlib.sha1((player.title+str(player.user or '')).encode('utf-8')).hexdigest(),
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
        self.server = await self.server

    @commands.command()
    @category('developer')
    async def start(self, ctx):
        """Manually start the server after reload"""
        if hasattr(self.server, 'sockets'):
            return await ctx.send('Server already started.')
        else:
            self.server = await self.server
            return await ctx.send('Server started.')

    @commands.command()
    async def website(self, ctx):
        """Get a link to the queue website for this guild."""
        await ctx.send(f'<https://htcraft.ml/queue?g={ctx.guild.id}>')


def setup(bot):
    global cog
    bot.add_cog(Website(bot))
    cog = bot.cogs['Website']


def teardown(_):
    global cog
    cog.server.close()
