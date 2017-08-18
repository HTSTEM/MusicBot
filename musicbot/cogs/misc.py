import base64
import re
import os

import discord

from discord.ext import commands

from cogs.util import checks
from cogs.util.categories import category


class Misc:
    def __init__(self, bot):
        self.bot = bot

    @category('misc')
    @commands.command()
    async def id(self, ctx):
        await ctx.send('<@{0}>, your ID is `{0}`'.format(ctx.author.id))

    @category('bot')
    @commands.command()
    async def joinserver(self, ctx):
        await ctx.send('Sorry. This bot has been designed to only work on HTC.')

    @category('bot')
    @commands.command(aliases=['shutdown'])
    @checks.manage_channels()
    async def die(self, ctx):
        """Shuts down the bot"""
        ctx.bot.dying = True
        await ctx.send(':wave:')
        await ctx.bot.logout()

    @category('bot')
    @commands.command()
    async def restart(self, ctx):
        await ctx.send('Please use `{}die` and run the bot in a restart loop.'.format(ctx.prefix))

    @category('misc')
    @commands.command()
    @checks.manage_channels()
    async def start_comp(self, ctx):
        if self.bot.like_comp_active:
            return await ctx.send('There is already a competition going on.')
        self.bot.like_comp_active = True
        self.bot.like_comp = {}
        await ctx.send('A like competition has been started! Woot?')
    
    @category('misc')
    @commands.command()
    @checks.manage_channels()
    async def cancel_comp(self, ctx):
        if not self.bot.like_comp_active:
            return await ctx.send('There isn\'t a competition going on..')
        self.bot.like_comp_active = False
        self.bot.like_comp = {}
        await ctx.send('The like competition has been canceled.')
    
    @category('misc')
    @commands.command()
    @checks.manage_channels()
    async def end_comp(self, ctx):
        if not self.bot.like_comp_active:
            return await ctx.send('There isn\'t a competition going on..')
        self.bot.like_comp_active = False
        print(self.bot.like_comp)
        
        m = 'The like competition has ended.\n**Results:**\n'
        likes = []
        for user in self.bot.like_comp:
            for song in self.bot.like_comp[user]:
                likes.append((user, song, len(self.bot.like_comp[user][song])))
        likes.sort(key=lambda x:x[2], reverse=True)
        
        m += '\n'.join('`{}`: **{}** with the song **{}** and **{} like{}**'.format(n + 1, i[0], i[1], i[2], 's' if i[2] != 1 else '') for n, i in enumerate(likes[:10]))
        
        self.bot.like_comp = {}
        await ctx.send(m)
        
    @category('misc')
    @commands.command(aliases=['mostliked', 'most_likes', 'mostlikes'])
    async def most_liked(self, ctx):
        likes = {}
        for i in self.bot.likes:
            for j in self.bot.likes[i]:
                j = base64.b64decode(j.encode('ascii')).decode('utf-8')
                if j not in likes:
                    likes[j] = 0
                likes[j] += 1
        likes = list(likes.items())
        likes.sort(key=lambda x:x[1], reverse=True)
        likes
        m = '**The top 10 most liked songs of all time are:**\n'
        m += '\n'.join('{} ({} like{})'.format(i[0], i[1], 's' if i[1] != 1 else '') for i in likes[:10])
        await ctx.send(m)
        
    @category('misc')
    @commands.command()
    async def listids(self, ctx):
        data = 'Your ID: {}\n\n'.format(ctx.author.id)

        data += 'Text Channel IDs:\n'
        for c in ctx.guild.channels:
            if isinstance(c, discord.TextChannel):
                data += '{}: {}\n'.format(c.name, c.id)

        data += '\nVoice Channel IDs:\n'
        for c in ctx.guild.channels:
            if isinstance(c, discord.VoiceChannel):
                data += '{}: {}\n'.format(c.name, c.id)

        data += '\nRole IDs:\n'
        for r in ctx.guild.roles:
            data += '{}: {}\n'.format(r.name, r.id)

        data += '\nUser IDs:\n'
        if ctx.guild.large:
            await self.bot.request_offline_member(ctx.guild)
        for m in ctx.guild.members:
            data += '{}: {}\n'.format(m.name, m.id)
        
        filename = '{}-ids-all.txt'.format("".join([x if x.isalnum() else "_" for x in ctx.guild.name]))
        
        with open(filename, 'wb') as ids_file:
            ids_file.write(data.encode('utf-8'))
        
        await ctx.send(':mailbox_with_mail:')
        with open(filename, 'rb') as ids_file:
            await ctx.author.send(file=discord.File(ids_file))
        
        os.remove(filename)    

    @category('misc')
    @commands.command()
    @checks.manage_channels()
    async def bldump(self, ctx):
        m = '**Blacklisted users:\n**'
        m += '\n'.join(str(i) for i in self.bot.blacklist)
        await ctx.author.send(m)
        await ctx.send(':mailbox_with_mail:')
        
    @category('misc')
    @commands.command()
    @checks.manage_channels()
    async def blacklist(self, ctx, mode, id):
        """Blacklist a user from using commands"""
        mode = mode.lower()
        if mode not in ['+', '-', 'add', 'remove']:
            await ctx.send('Usage: `{}blacklist [+|-|add|remove] <user id>`'.format(ctx.prefix))
            return
        
        try:
            id = int(id)
        except ValueError:
            await ctx.send('Usage: `{}blacklist [+|-|add|remove] <user id>`'.format(ctx.prefix))
            return
        
        if mode in ['+', 'add']:
            user = ctx.guild.get_member(id)
            if user is None or not user.permissions_in(ctx.channel).manage_channels:
                if id not in self.bot.blacklist:
                    self.bot.blacklist.append(id)
                    self.bot.save_bl()
                    await ctx.send('The user with the id `{}` has been blacklisted.'.format(id))
                else:
                    await ctx.send('The user with the id `{}` has already been blacklisted.'.format(id))
            else:
                await ctx.send('You can\'t blacklist someone with `Manage Channels`. Please ask a developer if you *must* blacklist them.')
        else:
            if id not in self.bot.blacklist:
                await ctx.send('`{}` isn\'t in the blacklist.'.format(id))
            else:
                while id in self.bot.blacklist:
                    self.bot.blacklist.remove(id)
                self.bot.save_bl()
                await ctx.send('The user with the id `{}` has been removed from the blacklist.'.format(id))
        
    @category('misc')
    @commands.command()
    async def help(self, ctx, *args):
        '''This help message'''
        cmds = {i for i in ctx.bot.all_commands.values()}

        if len(args) == 0:
            d = ''#'**TWOWBot help:**'

            cats = {'All': []}
            for cmd in cmds:
                if not hasattr(cmd, 'category'):
                    cmd.category = 'Misc'
                if cmd.category not in cats:
                    cats[cmd.category] = []
                cats[cmd.category].append(cmd)
                cats['All'].append(cmd)

            d += '\n**Categories:**\n'
            for cat in cats:
                d += '**`{}`**\n'.format(cat)
            d += '\nUse `{}help <category>` to list commands in a category'.format(ctx.prefix)
            d += '\nUse `{}help <command>` to get indepth help for a command\n'.format(ctx.prefix)
        elif len(args) == 1:
            cats = {'All': []}
            for cmd in cmds:
                if not hasattr(cmd, 'category'):
                    cmd.category = 'Misc'
                if cmd.category not in cats:
                    cats[cmd.category] = []
                cats[cmd.category].append(cmd)
                cats['All'].append(cmd)
            if args[0].title() in cats:
                d = 'Commands in caterogy **`{}`**:\n'.format(args[0])
                for cmd in sorted(cats[args[0].title()], key=lambda x:x.name):
                    d += '\n  `{}{}`'.format(ctx.prefix, cmd.name)

                    brief = cmd.brief
                    if brief is None and cmd.help is not None:
                        brief = cmd.help.split('\n')[0]

                    if brief is not None:
                        d += ' - {}'.format(brief)
                d += '\n'
            else:
                if args[0] not in ctx.bot.all_commands:
                    d = 'Command not found.'
                else:
                    cmd = ctx.bot.all_commands[args[0]]
                    d = 'Help for command `{}`:\n'.format(cmd.name)
                    d += '\n**Usage:**\n'

                    if type(cmd) != commands.core.Group:
                        params = list(cmd.clean_params.items())
                        p_str = ''
                        for p in params:
                            if p[1].default == p[1].empty:
                                p_str += ' [{}]'.format(p[0])
                            else:
                                p_str += ' <{}>'.format(p[0])
                        d += '`{}{}{}`\n'.format(ctx.prefix, cmd.name, p_str)
                    else:
                        d += '`{}{} '.format(ctx.prefix, cmd.name)
                        if cmd.invoke_without_command:
                            d += '['
                        else:
                            d += '<'
                        d += '|'.join(cmd.all_commands.keys())
                        if cmd.invoke_without_command:
                            d += ']`\n'
                        else:
                            d += '>`\n'

                    d += '\n**Description:**\n'
                    d += '{}\n'.format('None' if cmd.help is None else cmd.help.strip())

                    if cmd.checks:
                        d += '\n**Checks:**'
                        for check in cmd.checks:
                            d += '\n{}'.format(check.__qualname__.split('.')[0])
                        d += '\n'

                    if cmd.aliases:
                        d += '\n**Aliases:**'
                        for alias in cmd.aliases:
                            d += '\n`{}{}`'.format(ctx.prefix, alias)

                        d += '\n'
        else:
            d = ''
            cmd = ctx.bot
            cmd_name = ''
            for i in args:
                i = i.replace('@', '@\u200b')
                if hasattr(cmd, 'all_commands') and i in cmd.all_commands:
                    cmd = cmd.all_commands[i]
                    cmd_name += cmd.name + ' '
                else:
                    if cmd == ctx.bot:
                        d += 'Command not found.'
                    else:
                        d += '`{}` has no sub-command `{}`.'.format(cmd.name, i)
                    break
            if cmd != ctx.bot:
                d = 'Help for command `{}`:\n'.format(cmd_name)
                d += '\n**Usage:**\n'

                if type(cmd) != commands.core.Group:
                    params = list(cmd.clean_params.items())
                    p_str = ''
                    for p in params:
                        if p[1].default == p[1].empty:
                            p_str += ' [{}]'.format(p[0])
                        else:
                            p_str += ' <{}>'.format(p[0])
                    d += '`{}{}{}`\n'.format(ctx.prefix, cmd_name, p_str)
                else:
                    d += '`{}{} '.format(ctx.prefix, cmd.name)
                    if cmd.invoke_without_command:
                        d += '['
                    else:
                        d += '<'
                    d += '|'.join(cmd.all_commands.keys())
                    if cmd.invoke_without_command:
                        d += ']`\n'
                    else:
                        d += '>`\n'

                d += '\n**Description:**\n'
                d += '{}\n'.format('None' if cmd.help is None else cmd.help.strip())

                if cmd.checks:
                    d += '\n**Checks:**'
                    for check in cmd.checks:
                        d += '\n{}'.format(check.__qualname__.split('.')[0])
                    d += '\n'

                if cmd.aliases:
                    d += '\n**Aliases:**'
                    for alias in cmd.aliases:
                        d += '\n`{}{}`'.format(ctx.prefix, alias)

                    d += '\n'

        d += '\n*Made by Bottersnike#3605 and hanss314#0128*'
        await ctx.send(d)


def setup(bot):
    bot.add_cog(Misc(bot))
