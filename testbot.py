import asyncio

from ruamel import yaml
from aiohttp import web

from discord.ext import commands

with open('./config/config.yml', 'r') as config_file:
    config = yaml.safe_load(config_file)

TOKEN = config['token']

bot = commands.Bot('!')

async def authorize(request):
    id = int(request.match_info.get('id', '0'))
    member = bot.get_guild(297811083308171264).get_member(id)
    print(id)
    if member is None:
        return web.Response(text='false')
    else:
        for role in member.roles:
            if role.id == 303278074672185346:
                return web.Response(text='true')
        else:
            return web.Response(text='false')


@bot.event
async def on_ready():
    print(f'Connected to Discord')
    print(f'Guilds  : {len(bot.guilds)}')
    print(f'Users   : {len(set(bot.get_all_members()))}')
    print(f'Channels: {len(list(bot.get_all_channels()))}')
    app = web.Application()
    app.router.add_get('/authorize/{id}', authorize)
    handler = app.make_handler()
    f = bot.loop.create_server(handler, '127.0.0.1', '8088')
    await f


@bot.command()
async def ping(ctx):
    await ctx.send('Birb')

bot.run(TOKEN)