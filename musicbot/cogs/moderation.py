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
    @commands.guild_only()
    @commands.command()
    async def default_channel(self, ctx):
        """Instruct the bot to auto-join the current channel."""
        voice = ctx.author.voice
        if voice is None:
            return await ctx.send('You are not in a voice channel!')

        for i in list(self.bot.default_channels):
            if i[0] == ctx.guild.id:
                self.bot.default_channels.remove(i)
        self.bot.default_channels.append((ctx.guild.id,
                                          voice.channel.id,
                                          ' ' + ctx.guild.name))
        self.bot.save_default_channels()
        if self.bot.voice.get(ctx.guild.id) is not None:
            await self.bot.voice[ctx.guild.id].disconnect()
            del self.bot.voice[ctx.guild.id]

        self.bot.voice[ctx.guild.id] = await voice.channel.connect()
        await self.bot.cogs['Music'].auto_playlist(ctx)

        return await ctx.send(f'{voice.channel.name} has been set as the default channel.')

    @category('moderation')
    @commands.guild_only()
    @commands.command()
    async def allow_commands(self, ctx):
        """Add the current channel to the whitelist of bot channels."""
        if ctx.guild.id not in self.bot.bot_channels:
            self.bot.bot_channels[ctx.guild.id] = []

        if ctx.channel.id in self.bot.bot_channels[ctx.guild.id]:
            return await ctx.send(f'{ctx.channel.name} is already in the whilelist.')

        self.bot.bot_channels[ctx.guild.id].append(ctx.channel.id)
        self.bot.save_bot_channels()
        return await ctx.send(f'{ctx.channel.name} has been whitelisted.')

    @category('moderation')
    @commands.guild_only()
    @commands.command()
    async def disallow_commands(self, ctx):
        """Add the current channel to the whitelist of bot channels."""
        if ctx.guild.id not in self.bot.bot_channels:
            return await ctx.send(f'{ctx.channel.name} is not in the whilelist.')

        if ctx.channel.id not in self.bot.bot_channels[ctx.guild.id]:
            return await ctx.send(f'{ctx.channel.name} is not in the whilelist.')

        self.bot.bot_channels[ctx.guild.id].remove(ctx.channel.id)
        if not self.bot.bot_channels[ctx.guild.id]:
            del self.bot.bot_channels[ctx.guild.id]
        self.bot.save_bot_channels()
        return await ctx.send(f'{ctx.channel.name} has been removed from the whitelist.')

    @category('moderation')
    @commands.guild_only()
    @commands.command()
    async def command_channels(self, ctx):
        """Gets the whitelist of bot channels."""
        if ctx.guild.id not in self.bot.bot_channels:
            return await ctx.send(f'{ctx.guild.name} has no channels setup.')

        names = []
        for i in self.bot.bot_channels[ctx.guild.id]:
            c = ctx.guild.get_channel(i)
            if c is not None:
                names.append(c.name)
        return await ctx.send(f'The channels are: {", ".join(names)}.')

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
