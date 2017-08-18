import re

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
