import base64
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

    @category('misc')
    @commands.command()
    @commands.cooldown(1, 15, type=commands.BucketType.user)
    async def id(self, ctx):
        '''Get your user id'''
        await ctx.send('<@{0}>, your ID is `{0}`'.format(ctx.author.id))

    @category('misc')
    @commands.command()
    @commands.cooldown(1, 10, type=commands.BucketType.guild)
    async def patreon(self, ctx):
        '''Posts info about patreon & the patrons'''
        s = self.bot.patrons
        msg = 'All of the bots on this server (such as the Musicbot, Flairbot, and Joinbot) were all made by our wonderful developers over countless hours. '
        msg += 'As much as we would love to provide these bots for free, they need a place to be hosted, which costs money. '
        msg += 'That\'s where you come in. If you donate at <https://patreon.com/HTSTEM>, you can support our developers by allowing them to host the bots, pay for websites, domains, '
        msg += 'and possibly other fun things along the way. '
        msg += 'Supporting us gives you access to some really cool rewards, like being added to this list (comes with any donation amount); being able to queue a bunch more songs in the music channel; '
        msg += 'recieving a special, patreon-only flair; and other special things depending on your pledge amount.\n'
        msg += '--Our wonderful Patrons:--\n'
        for uid in s["patrons"]:
            amnt = s["patrons"].get(uid).get('pledge')
            try:
                name = self.bot.get_user(uid).name
            except Exception as e:
                name = uid + " (name not available)"
            if amnt >= 3:
                msg += '**{0} (${1}/mo)**\n'.format(name, amnt)
            else:
                msg += '{0} (${1}/mo)\n'.format(name, amnt)
        await ctx.send(msg)

    @category('misc')
    @commands.command(aliases=['mostliked', 'most_likes', 'mostlikes'])
    @commands.cooldown(4, 60, type=commands.BucketType.guild)
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
        msg = '**The top 10 most liked songs of all time are:**\n'
        msg += '\n'.join('{} ({} like{})'.format(i[0], i[1], 's' if i[1] != 1 else '') for i in likes[:10])
        await ctx.send(msg)

    @category('misc')
    @commands.command()
    @commands.cooldown(1, 60, type=commands.BucketType.guild)
    async def dump_likes(self, ctx):
        '''Get a dump of every like (all time)'''
        likes = {}
        for i in self.bot.likes:
            for j in self.bot.likes[i]:
                j = base64.b64decode(j.encode('ascii')).decode('utf-8')
                if j not in likes:
                    likes[j] = 0
                likes[j] += 1
        likes = list(likes.items())
        likes.sort(key=lambda x:x[1], reverse=True)
        msg = '\n'.join(f'{i[1]},{i[0]}' for i in likes)

        with open('likesdump.txt', 'w') as f:
            f.write(msg)

        await ctx.send(':mailbox_with_mail:')
        with open('likesdump.txt', 'rb') as ids_file:
            await ctx.author.send(file=discord.File(ids_file))

        os.remove('likesdump.txt')

    @category('misc')
    @commands.command(aliases=['permissions'])
    @commands.guild_only()
    @commands.cooldown(1, 120, type=commands.BucketType.user)
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
        msg += 'Max_Playlist_Length: {}\n'.format(perms['max_playlist_length'])
        msg += '```'
        await ctx.author.send(msg)

    @category('misc')
    @commands.command()
    @commands.guild_only()
    @commands.cooldown(1, 120, type=commands.BucketType.user)
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
    @commands.cooldown(10, 15, type=commands.BucketType.user)
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
                        d += 'No sub-command found.'
                    break

            else:
                d = self.get_help(ctx, cmd, name=cmd_name)

        d += '\n*Made by Bottersnike#3605 and hanss314#0128*\n*Made possible thanks to our patrons.*'
        d += '\n*$5 patrons: Satomi, sin*'
        return await ctx.send(d)


def setup(bot):
    bot.add_cog(Misc(bot))
