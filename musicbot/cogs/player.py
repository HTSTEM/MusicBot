import discord

from discord.ext import commands

from .util import checks
from .util.categories import category


class Player:
    def __init__(self, bot):
        self.bot = bot

    @category('player')
    @commands.command()
    @commands.guild_only()
    async def resume(self, ctx):
        '''Resumes player'''
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            ctx.voice_client.source.start_time += time.time() - ctx.voice_client.source.pause_start

    @category('player')
    @commands.command()
    @commands.guild_only()
    async def pause(self, ctx):
        '''Pause the player'''
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            ctx.voice_client.source.pause_start = time.time()

    @category('player')
    @commands.command()
    @commands.guild_only()
    async def forceskip(self, ctx):
        '''Forcefully skips a song'''
        ctx.voice_client.stop()
        await ctx.send('Song forceskipped.')

    @category('player')
    @commands.command()
    @commands.guild_only()
    async def clear(self, ctx):
        '''Stops player and clears queue'''
        while self.bot.queue:
            self.bot.queue.pop()

        ctx.voice_client.stop()


def setup(bot):
    bot.add_cog(Player(bot))
