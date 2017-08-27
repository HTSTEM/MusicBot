import subprocess
import asyncio
import inspect
import base64
import sys
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
        '''Get your user id'''
        await ctx.send('<@{0}>, your ID is `{0}`'.format(ctx.author.id))

    @category('bot')
    @commands.command()
    async def joinserver(self, ctx):
        '''Invite the bot to your server'''
        await ctx.send('Sorry. This bot has been designed to only work on HTC.')

    @category('bot')
    @commands.command()
    async def setname(self, ctx, *, name):
        '''Change the bot's username'''
        try:
            await self.bot.user.edit(username=name)
        except discord.HTTPException:
            await ctx.send('Changing the name failed.')

    @category('bot')
    @commands.command()
    async def setnick(self, ctx, *, name):
        '''Change the bot's nickname'''
        try:
            await ctx.guild.get_member(self.bot.user.id).edit(nick=name)
        except discord.HTTPException:
            await ctx.send('Changing the name failed.')

    @category('bot')
    @commands.command()
    async def setavatar(self, ctx):
        '''Change the bot's profile picture'''
        attachment = ctx.message.attachments[0]
        await attachment.save(attachment.filename)
        try:
            with open(attachment.filename, 'rb') as avatar:
                await self.bot.user.edit(avatar=avatar.read())
        except discord.HTTPException:
            await ctx.send('Changing the avatar failed.')
        except discord.InvalidArgument:
            await ctx.send('You did not upload an image.')

    @category('bot')
    @commands.command(aliases=['shutdown'])
    async def die(self, ctx):
        """Shuts down the bot"""
        ctx.bot.dying = True
        await ctx.send(':wave:')
        await ctx.bot.logout()

    @category('bot')
    @commands.command()
    async def restart(self, ctx):
        '''Restart the bot'''
        ctx.bot.dying = True
        await ctx.send('Shutting down the bot. If the bot is in a restart loop, it will start back up.\nPlease use `{}die` in future as it is a more accurate command.'.format(ctx.prefix))
        await ctx.bot.logout()

    @category('comp')
    @commands.command(aliases=['startcomp'])
    @checks.not_dm()
    async def start_comp(self, ctx):
        '''Start a competition'''
        if self.bot.like_comp_active:
            return await ctx.send('There is already a competition going on.')
        self.bot.like_comp_active = True
        self.bot.like_comp = {}
        await ctx.send('A like competition has been started! Woot?')

    @category('comp')
    @commands.command(aliases=['cancelcomp'])
    @checks.not_dm()
    async def cancel_comp(self, ctx):
        '''Cancel any current competitions'''
        if not self.bot.like_comp_active:
            return await ctx.send('There isn\'t a competition going on..')
        self.bot.like_comp_active = False
        self.bot.like_comp = {}
        await ctx.send('The like competition has been canceled.')

    @category('comp')
    @commands.command(aliases=['endcomp'])
    @checks.not_dm()
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

        m += '\n'.join('`{}`: **{}** with the song **{}** and **{} like{}**'.format(n + 1, i[0], i[1], i[2], 's' if i[2] != 1 else '') for n, i in enumerate(likes[:10]))

        self.bot.like_comp = {}
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
    @checks.not_dm()
    async def perms(self, ctx):
        '''View your permissions'''
        perms = ctx.channel.permissions_for(ctx.author)
        whitelist = []
        vc_only = []
        for command in ctx.bot.commands:
            for check in command.checks:
                try:
                    if not await check(ctx):
                        break
                except Exception as e:
                    if 'user_in_vc' in e.args:
                        vc_only.append(command.name)
                    break
            else:
                whitelist.append(command.name)
        m = '```yaml\n'
        m += 'Command_Whitelist: {}\n'.format(', '.join(whitelist))
        if len(vc_only)>0: m += 'VC_only: {}\n'.format(', '.join(vc_only))
        m += 'Max_Song_Length: {}\n'.format(self.bot.config['max_song_length'])
        m += 'Max_Songs: {}\n'.format(self.bot.config['max_songs_queued'])
        m += '```'
        await ctx.author.send(m)

    @category('misc')
    @commands.command()
    @checks.not_dm()
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

    @category('modding')
    @commands.command()
    async def bldump(self, ctx):
        '''Gets a list of every blacklisted user.'''

        m = '**Blacklisted users:\n**'
        m += '\n'.join(str(i) for i in self.bot.blacklist)
        await ctx.author.send(m)
        await ctx.send(':mailbox_with_mail:')

    @category('modding')
    @commands.command()
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

    @category('bot')
    @commands.command(aliases=['git_pull'])
    async def update(self, ctx):
        '''Updates the bot from git'''

        await ctx.send(':warning: Warning! Pulling from git!')

        if sys.platform == 'win32':
            process = subprocess.run('git pull', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.stdout, process.stderr
        else:
            process = await asyncio.create_subprocess_exec('git', 'pull', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = await process.communicate()
        stdout = stdout.decode().splitlines()
        stdout = '\n'.join('+ ' + i for i in stdout)
        stderr = stderr.decode().splitlines()
        stderr = '\n'.join('- ' + i for i in stderr)

        await ctx.send('`Git` response: ```diff\n{}\n{}```'.format(stdout, stderr))
        await ctx.send('These changes will only come into effect next time you restart the bot. Use `{0}die` or `{0}restart` now (or later) to do that.'.format(ctx.prefix))

    @category('misc')
    @commands.command()
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

            d += '\n**Categories:**\n'
            for cat in cats:
                d += '**`{}`**\n'.format(cat)
            d += '\nUse `{}help <category>` to list commands in a category'.format(ctx.prefix)
            d += '\nUse `{}help <command>` to get indepth help for a command\n'.format(ctx.prefix)
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
        return await ctx.send(d)
    
def setup(bot):
    bot.add_cog(Misc(bot))
