import asyncio
import base64
import os

import discord

from discord.ext import commands

from .util import checks
from .util.categories import category


class Misc:
    def __init__(self, bot):
        self.bot = bot

    @category('misc')
    @commands.command()
    async def id(self, ctx):
        '''Get your user id'''
        await ctx.send('<@{0}>, your ID is `{0}`'.format(ctx.author.id))

    @category('misc')
    @commands.command()
    async def patreon(self, ctx):
        '''Posts info about patreon & the patrons'''
        m = 'The following is a list of users who are contributing to <https://patreon.com/HTSTEM>, which helps fund the bot hosting.'
        m += '\nSatomi ($1/mo, total $1)'
        m += '\nsills ($1/mo, total $1)'
        await ctx.send(m)

    @category('misc')
    @commands.command(aliases=['mostliked', 'most_likes', 'mostlikes'])
    async def most_liked(self, ctx):
        '''Get the top 10 most liked songs of all time'''
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
    @commands.command(aliases=['permissions'])
    @commands.guild_only()
    async def perms(self, ctx):
        '''View your permissions'''
        perms = await checks.permissions_for(ctx)
        whitelist = []
        vc_only = []
        perms = await checks.permissions_for(ctx)
        cats = {}
        for cmd in ctx.bot.commands:
            if not hasattr(cmd, 'category'):
                cmd.category = 'Misc'
            if cmd.category.lower() not in cats:
                cats[cmd.category.lower()] = []
            cats[cmd.category.lower()].append(cmd)

        print(cats)
        for cat in perms['categories']:
            if cat in cats:
                for cmd in cats[cat]:
                    for check in cmd.checks:
                        try:
                            if not await check(ctx):
                                break
                        except Exception as e:
                            if 'user_in_vc' in e.args:
                                vc_only.append(cmd.name)
                            break
                    else:
                        whitelist.append(cmd.name)
        m = '```yaml\n'
        m += 'Command_Whitelist: {}\n'.format(', '.join(whitelist))
        if len(vc_only)>0: m += 'VC_only: {}\n'.format(', '.join(vc_only))
        m += 'Max_Song_Length: {}\n'.format(perms['max_song_length'])
        m += 'Max_Songs: {}\n'.format(perms['max_songs_queued'])
        m += '```'
        await ctx.author.send(m)

    @category('misc')
    @commands.command()
    @commands.guild_only()
    async def listids(self, ctx):
        '''Get all of the IDs for the current server'''
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
            await self.bot.request_offline_members(ctx.guild)
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
    @commands.guild_only()
    async def help(self, ctx, *args):
        '''This help message'''
        cmds = {i for i in ctx.bot.all_commands.values()}

        if len(args) == 0:
            d = ''#'**TWOWBot help:**'

            cats = {}
            for cmd in cmds:
                if not hasattr(cmd, 'category'):
                    cmd.category = 'Misc'
                if cmd.category not in cats:
                    cats[cmd.category] = []
                cats[cmd.category].append(cmd)
            cats = list(cats.keys())
            cats.sort()

            width = max([len(cat) for cat in cats]) + 2
            d += '**Categories:**\n'
            for cat in zip(cats[0::2], cats[1::2]):
                d += '**`{}`**{}**`{}`**\n'.format(cat[0],' ' * int(2.3 * (width-len(cat[0]))), cat[1])
            if len(cats)%2 == 1:
                d += '**`{}`**\n'.format(cats[-1])

            d += '\nUse `{0}help <category>` to list commands in a category.\n'.format(ctx.prefix)
            d += 'Use `{0}help <command>` to get in depth help for a command.\n'.format(ctx.prefix)

        elif len(args) == 1:
            cats = {}
            for cmd in cmds:
                if not hasattr(cmd, 'category'):
                    cmd.category = 'Misc'
                if cmd.category not in cats:
                    cats[cmd.category] = []
                cats[cmd.category].append(cmd)
            if args[0].title() in cats:
                d = 'Commands in category **`{}`**:\n'.format(args[0])
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

                    if type(cmd) != commands.core.Group or cmd.invoke_without_command:
                        params = list(cmd.clean_params.items())
                        p_str = ''
                        for p in params:
                            print(p[1], p[1].default, p[1].empty)
                            if p[1].default == p[1].empty:
                                p_str += ' <{}>'.format(p[0])
                            else:
                                p_str += ' [{}]'.format(p[0])
                        d += '`{}{}{}`\n'.format(ctx.prefix, cmd.name, p_str)

                    if type(cmd) == commands.core.Group:
                        d += '`{}{} '.format(ctx.prefix, cmd.name)
                        #if cmd.invoke_without_command:
                        #    d += '['
                        #else:
                        #    d += '<'
                        d += '|'.join(cmd.all_commands.keys())
                        #if cmd.invoke_without_command:
                        #    d += ']`\n'
                        #else:
                        #    d += '>`\n'
                        d += '`\n'

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
        return await ctx.send(d)


def setup(bot):
    bot.add_cog(Misc(bot))
