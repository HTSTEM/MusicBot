import sys

import discord

from discord.ext import commands

from .util.categories import category


class Core:
    def __init__(self, bot):
        self.bot = bot

    @category('developer')
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

    @category('developer')
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

    @category('developer')
    @reload.command(name='config')
    async def reload_config(self, ctx):
        '''Reload the config files'''
        with open('config/autoplaylist.txt') as ap_file:
            ctx.bot.autoplaylist = ap_file.read().split('\n')

        with open('config/jingles.txt') as jingle_file:
            ctx.bot.jingles = jingle_file.read().split('\n')

        with open('config/blacklist.txt') as bl_file:
            ctx.bot.blacklist = [(int(i.split(',')[0]), int(i.split(',')[1])) for i in bl_file.read().split('\n') if i]

        with open('config/config.yml') as conf_file:
            ctx.bot.config = ctx.bot.yaml.load(conf_file)

        with open('config/permissions.yml') as perm_file:
            ctx.bot.permissions = ctx.bot.yaml.load(perm_file)

        await ctx.send('Reloaded config files.')

    @category('developer')
    @commands.command(aliases=['exception'])
    async def error(self, ctx, *, text: str = None):
        '''Raises an error. Testing purposes only, please don't use.'''
        raise Exception(text or 'Woo! Errors!')

    @category('misc')
    @commands.command(aliases=['invite'])
    async def joinserver(self, ctx):
        '''Invite the bot to your server'''
        await ctx.send('If you want to invite me to your server, DM one of the developers and we might be able to add it for you.')

    @category('developer')
    @commands.command()
    async def setname(self, ctx, *, name):
        '''Change the bot's username'''
        try:
            await self.bot.user.edit(username=name)
        except discord.HTTPException:
            await ctx.send('Changing the name failed.')

    @category('developer')
    @commands.command()
    async def setnick(self, ctx, *, name):
        '''Change the bot's nickname'''
        try:
            await ctx.guild.get_member(self.bot.user.id).edit(nick=name)
        except discord.HTTPException:
            await ctx.send('Changing the name failed.')

    @category('developer')
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

    @category('developer')
    @commands.command(aliases=['shutdown'])
    async def die(self, ctx):
        """Shuts down the bot"""
        ctx.bot.dying = True
        await ctx.send(':wave:')
        await ctx.bot.logout()
    
    @category('developer')
    @commands.command(aliases=['diesoon'])
    async def die_soon(self, ctx):
        """Shuts down the bot at the end of the current song"""
        if ctx.bot.dying:
            return await ctx.send('Already doing that..')
            
        ctx.bot.dying = True
        ctx.bot.die_soon = ctx
        await ctx.send('Shutting down after this song.')

    @category('developer')
    @commands.command()
    async def restart(self, ctx):
        '''Restart the bot'''
        ctx.bot.dying = True
        await ctx.send('Shutting down the bot. If the bot is in a restart loop, it will start back up.\nPlease use `{}die` in future as it is a more accurate command.'.format(ctx.prefix))
        await ctx.bot.logout()

    @category('bot')
    @commands.command()
    @commands.guild_only()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        '''Joins a voice channel'''

        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        self.bot.voice[ctx.guild.id] = await channel.connect()

    @category('bot')
    @commands.command()
    @commands.guild_only()
    async def summon(self, ctx):
        '''Join the voice channel you're in.'''
        voice = ctx.author.voice
        if voice is None:
            return await ctx.send('You are not in a voice channel!')

        self.bot.voice[ctx.guild.id] = await voice.channel.connect()


def setup(bot):
    bot.add_cog(Core(bot))
