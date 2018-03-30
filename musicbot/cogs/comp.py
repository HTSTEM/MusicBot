import discord

from discord.ext import commands

from .util import checks
from .util.categories import category


class Comp:
    def __init__(self, bot):
        self.bot = bot

    @category('comp')
    @commands.command(aliases=['startcomp'])
    @commands.guild_only()
    async def start_comp(self, ctx):
        '''Start a competition'''
        await ctx.send('OCTAGON?')

    @category('comp')
    @commands.command(aliases=['cancelcomp'])
    @commands.guild_only()
    async def cancel_comp(self, ctx):
        '''Cancel any current competitions'''
        await ctx.send('OCTAGON :(')

    @category('comp')
    @commands.command(aliases=['endcomp'])
    @commands.guild_only()
    async def end_comp(self, ctx):
        '''End the current competition'''
        return await ctx.send('OCTAGON!')


def setup(bot):
    bot.add_cog(Comp(bot))
