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
        if self.bot.like_comp_active:
            return await ctx.send('There is already a competition going on.')
        self.bot.like_comp_active = True
        self.bot.like_comp = {}
        await ctx.send('A like competition has been started! Woot?')

    @category('comp')
    @commands.command(aliases=['cancelcomp'])
    @commands.guild_only()
    async def cancel_comp(self, ctx):
        '''Cancel any current competitions'''
        if not self.bot.like_comp_active:
            return await ctx.send('There isn\'t a competition going on..')
        self.bot.like_comp_active = False
        self.bot.like_comp = {}
        await ctx.send('The like competition has been canceled.')

    @category('comp')
    @commands.command(aliases=['endcomp'])
    @commands.guild_only()
    async def end_comp(self, ctx):
        '''End the current competition'''
        if not self.bot.like_comp_active:
            return await ctx.send('There isn\'t a competition going on..')
        self.bot.like_comp_active = False

        m = 'The like competition has ended.\n**Results:**\n'
        likes = []
        for user in self.bot.like_comp:
            for song in self.bot.like_comp[user]:
                likes.append((user, song, len(self.bot.like_comp[user][song])))
        likes.sort(key=lambda x:x[2], reverse=True)

        for n, i in enumerate(likes):
            ta = '`{}`: **{}** with the song **{}** and **{} like{}**\n'.format(n + 1, i[0], i[1], i[2], 's' if i[2] != 1 else '')
            if len(m + ta) > 1500:
                await ctx.send(m)
                m = ''
            m += ta
        if m:
            await ctx.send(m)
        await ctx.send(m)
        
        self.bot.like_comp = {}


def setup(bot):
    bot.add_cog(Comp(bot))
