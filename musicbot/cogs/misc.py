import subprocess
import asyncio
import base64
import sys
import os


import discord

from discord.ext import commands

from .util import checks
from .util.categories import category


class Misc:
    def __init__(self, bot):
        self.bot = bot

    def format_args(self, cmd):
        params = list(cmd.clean_params.items())
        p_str = ''
        for p in params:
            print(p[1], p[1].default, p[1].empty)
            if p[1].default == p[1].empty:
                p_str += f' <{p[0]}>'
            else:
                p_str += f' [{p[0]}]'

        return p_str

    def format_commands(self, prefix, cmd, name=None):
        cmd_args = self.format_args(cmd)
        if not name: name = cmd.name
        name = name.replace('  ',' ')
        d = f'`{prefix}{name}{cmd_args}`\n'

        if type(cmd) == commands.core.Group:
            cmds = sorted(list(cmd.commands), key=lambda x: x.name)
            for subcmd in cmds:
                d += self.format_commands(prefix, subcmd, name=f'{name} {subcmd.name}')

        return d

    def get_help(self, ctx, cmd, name=None):
        d = f'Help for command `{cmd.name}`:\n'
        d += '\n**Usage:**\n'

        d += self.format_commands(ctx.prefix, cmd, name=name)

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
                d += f'\n`{ctx.prefix}{alias}`'

            d += '\n'

        return d

    # Comp. category
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

        msg = 'The like competition has ended.\n**Results:**\n'
        likes = []
        for user in self.bot.like_comp:
            for song in self.bot.like_comp[user]:
                likes.append((user, song, len(self.bot.like_comp[user][song])))
        likes.sort(key=lambda x:x[2], reverse=True)

        msg += '\n'.join('`{}`: **{}** with the song **{}** and **{} like{}**'.format(n + 1, i[0], i[1], i[2], 's' if i[2] != 1 else '') for n, i in enumerate(likes[:10]))

        self.bot.like_comp = {}
        await ctx.send(msg)

    # Moderation category
    @category('modding')
    @commands.command()
    async def bldump(self, ctx):
        '''Gets a list of every blacklisted user.'''

        msg = '**Blacklisted users:\n**'
        msg += '\n'.join(str(i) for i in self.bot.blacklist)
        await ctx.author.send(msg)
        await ctx.send(':mailbox_with_mail:')

    @category('modding')
    @commands.group(invoke_without_command=True)
    async def blacklist(self, ctx):
        """Show the blacklist"""
        blacklist = [ctx.bot.get_user(id) for id in self.bot.blacklist]
        blacklist = [str(x) for x in blacklist if x is not None]
        if blacklist:
            await ctx.author.send('\n'.join(blacklist))
        else:
            await ctx.author.send('No one is blacklisted')


    @category('modding')
    @blacklist.command(name='add', aliases=['+'])
    async def blacklist_add(self, ctx, user: discord.Member):
        '''Add a user to the blacklist'''
        if user is None or not user.permissions_in(ctx.channel).manage_channels:
            if user.id not in self.bot.blacklist:
                self.bot.blacklist.append(user.id)
                self.bot.save_bl()
                await ctx.send(f'**{user.name}** has been blacklisted.')
            else:
                await ctx.send(f'**{user.name}** has already been blacklisted.')
        else:
            await ctx.send('You can\'t blacklist someone with `Manage Channels`. Please ask a developer if you *must* blacklist them.')

    @category('modding')
    @blacklist.command(name='remove', aliases=['-'])
    async def blacklist_remove(self, ctx, user: discord.Member):
        '''Remove a user from the blacklist'''
        if user.id not in self.bot.blacklist:
            await ctx.send(f'**{user.name}** isn\'t in the blacklist.')
        else:
            while user.id in self.bot.blacklist:
                self.bot.blacklist.remove(user.id)
            self.bot.save_bl()
            await ctx.send(f'**{user.name}** has been removed from the blacklist.')

    # Git category
    @category('git')
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

    @category('git')
    @commands.command()
    async def revert(self, ctx, commit):
        '''Revert local copy to specified commit'''

        await ctx.send(':warning: Warning! Reverting!')

        if sys.platform == 'win32':
            process = subprocess.run('git reset --hard {}'.format(commit), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.stdout, process.stderr
        else:
            process = await asyncio.create_subprocess_exec('git', 'reset', '--hard', commit, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = await process.communicate()
        stdout = stdout.decode().splitlines()
        stdout = '\n'.join('+ ' + i for i in stdout)
        stderr = stderr.decode().splitlines()
        stderr = '\n'.join('- ' + i for i in stderr)

        await ctx.send('`Git` response: ```diff\n{}\n{}```'.format(stdout, stderr))
        await ctx.send('These changes will only come into effect next time you restart the bot. Use `{0}die` or `{0}restart` now (or later) to do that.'.format(ctx.prefix))

    @category('git')
    @commands.command(aliases=['gitlog'])
    async def git_log(self, ctx, commits:int = 20):
        '''Shows the latest commits. Defaults to 20 commits.'''

        if sys.platform == 'win32':
            process = subprocess.run('git log --pretty=oneline --abbrev-commit', shell=True,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.stdout, process.stderr
        else:
            process = await asyncio.create_subprocess_exec('git', 'log', '--pretty=oneline', '--abbrev-commit',
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = await process.communicate()
        stdout = stdout.decode().splitlines()
        stdout = '\n'.join('+ ' + i[:90] for i in stdout[:commits])
        stderr = stderr.decode().splitlines()
        stderr = '\n'.join('- ' + i for i in stderr)

        if commits > 10:
            try:
                await ctx.author.send('`Git` response: ```diff\n{}\n{}```'.format(stdout, stderr))
            except discord.errors.HTTPException:
                import os
                with open('gitlog.txt', 'w') as log_file:
                    log_file.write('{}\n{}'.format(stdout,stderr))
                with open('gitlog.txt', 'r') as log_file:
                    await ctx.author.send(file=discord.File(log_file))
                os.remove('gitlog.txt')
        else:
            await ctx.send('`Git` response: ```diff\n{}\n{}```'.format(stdout, stderr))

    # Bot category
    @category('bot')
    @commands.group(invoke_without_command=True)
    async def reload(self, ctx, *, cog=''):
        '''Reloads an extension'''
        try:
            ctx.bot.unload_extension(cog)
            ctx.bot.load_extension(cog)
        except Exception as e:
            await ctx.send('Failed to load: `{}`\n```py\n{}\n```'.format(cog, e))
        else:
            await ctx.send('\N{OK HAND SIGN} Reloaded cog {} successfully'.format(cog))

    @category('bot')
    @reload.command(name='all')
    async def reload_all(self, ctx):
        '''Reloads all extensions'''
        import importlib
        importlib.reload(sys.modules['cogs.util'])
        for extension in ctx.bot.extensions.copy():
            ctx.bot.unload_extension(extension)
            try:
                ctx.bot.load_extension(extension)
            except Exception as e:
                await ctx.send('Failed to load `{}`:\n```py\n{}\n```'.format(extension, e))

        await ctx.send('\N{OK HAND SIGN} Reloaded {} cogs successfully'.format(len(ctx.bot.extensions)))

    @category('bot')
    @reload.command(name='perms')
    async def reload_perms(self, ctx):
        '''Reload the permissions'''
        with open('config/permissions.yml') as conf_file:
            ctx.bot.permissions = ctx.bot.yaml.load(conf_file)

        await ctx.send('Reloaded perms.')

    @category('bot')
    @commands.command(aliases=['exception'])
    async def error(self, ctx, *, text: str = None):
        '''Raises an error. Testing purposes only, please don't use.'''
        raise Exception(text or 'Woo! Errors!')

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

    # Misc. category
    @category('misc')
    @commands.command()
    async def id(self, ctx):
        '''Get your user id'''
        await ctx.send('<@{0}>, your ID is `{0}`'.format(ctx.author.id))

    @category('misc')
    @commands.command()
    async def patreon(self, ctx):
        '''Posts info about patreon & the patrons'''
        msg = 'The following is a list of users who are contributing to <https://patreon.com/HTSTEM>, which helps fund the bot hosting.'
        msg += ' You can get added to this list to if you pledge any amount of money. You will also get extra songs in the music queue,'
        msg += ' a colored flair, and other rewards depending on your pledge amount.'
        msg += '\n**Space Witch ($3/mo)**'
        msg += '\nSatomi ($1/mo)'
        msg += '\nsills ($1/mo)'
        await ctx.send(msg)

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
        msg = '**The top 10 most liked songs of all time are:**\n'
        msg += '\n'.join('{} ({} like{})'.format(i[0], i[1], 's' if i[1] != 1 else '') for i in likes[:10])
        await ctx.send(msg)

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
        msg = '```yaml\n'
        msg += 'Command_Whitelist: {}\n'.format(', '.join(whitelist))
        if len(vc_only)>0: msg += 'VC_only: {}\n'.format(', '.join(vc_only))
        msg += 'Max_Song_Length: {}\n'.format(perms['max_song_length'])
        msg += 'Max_Songs: {}\n'.format(perms['max_songs_queued'])
        msg += '```'
        await ctx.author.send(msg)

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
        for msg in ctx.guild.members:
            data += '{}: {}\n'.format(msg.name, msg.id)

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
            cats = {}
            for cmd in cmds:
                if not hasattr(cmd, 'category'):
                    cmd.category = 'misc'
                if cmd.category not in cats:
                    cats[cmd.category] = []
                cats[cmd.category].append(cmd)
            cats = list(cats.keys())
            cats.sort()
            width = max([len(cat) for cat in cats]) + 2
            d = '**Categories:**\n'
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
                if cmd.category.lower() not in cats:
                    cats[cmd.category.lower()] = []
                cats[cmd.category.lower()].append(cmd)
            if args[0].lower() in cats:
                cog_name = args[0].title()
                d = 'Commands in category **`{}`**:\n'.format(cog_name)
                cmds = cats[args[0].lower()]
                for cmd in sorted(list(cmds), key=lambda x:x.name):
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
                    d = self.get_help(ctx, cmd)
        else:
            d = ''
            cmd = ctx.bot
            cmd_name = ''
            for i in args:
                i = i.replace('@', '@\u200b')
                if cmd == ctx.bot and i in cmd.all_commands:
                    cmd = cmd.all_commands[i]
                    cmd_name += cmd.name + ' '
                elif type(cmd) == commands.Group and i in cmd.all_commands:
                    cmd = cmd.all_commands[i]
                    cmd_name += cmd.name + ' '
                else:
                    if cmd == ctx.bot:
                        d += 'Command not found.'
                    else:
                        d += 'No sub-command found.'.format(cmd.name, i)
                    break

            else:
                d = self.get_help(ctx, cmd, name=cmd_name)

        # d += '\n*Made by Bottersnike#3605 and hanss314#0128*'
        return await ctx.send(d)

def setup(bot):
    bot.add_cog(Misc(bot))
