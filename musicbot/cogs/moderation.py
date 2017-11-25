from discord.ext import commands

from .util.categories import category


class Moderation:
    def __init__(self, bot):
        self.bot = bot

    @category('moderation')
    @commands.command()
    async def bldump(self, ctx):
        '''Gets a list of every blacklisted user.'''

        m = '**Blacklisted users:\n**'
        m += '\n'.join(str(i[1]) for i in self.bot.blacklist if i[0] == ctx.guild.id)
        await ctx.author.send(m)
        await ctx.send(':mailbox_with_mail:')

    @category('moderation')
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
                    self.bot.blacklist.append((ctx.guild.id, id))
                    self.bot.save_bl()
                    await ctx.send('The user with the id `{}` has been blacklisted.'.format(id))
                else:
                    await ctx.send('The user with the id `{}` has already been blacklisted.'.format(id))
            else:
                await ctx.send('You can\'t blacklist someone with `Manage Channels`. Please ask a developer if you *must* blacklist them.')
        else:
            if (ctx.guild.id, id) not in self.bot.blacklist:
                await ctx.send('`{}` isn\'t in the blacklist.'.format(id))
            else:
                while (ctx.guild.id, id) in self.bot.blacklist:
                    self.bot.blacklist.remove((ctx.guild.id, id))
                self.bot.save_bl()
                await ctx.send('The user with the id `{}` has been removed from the blacklist.'.format(id))


def setup(bot):
    bot.add_cog(Moderation(bot))
