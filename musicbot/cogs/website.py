from aiohttp import web

class Website:

    def __init__(self, bot):
        self.bot = bot

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
        handler = app.make_handler()
        f = self.bot.loop.create_server(handler, '127.0.0.1', '8088')
        await f


def setup(bot):
    bot.add_cog(Website(bot))