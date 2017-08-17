import asyncio

import discord

from discord.ext import commands

from cogs.util import checks
from cogs.util.ytdl import YTDLSource

class Music:
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @checks.manage_channels()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Joins a voice channel"""

        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)
        
        await channel.connect()
        
    @commands.command()
    @checks.manage_channels()
    async def summon(self, ctx):
        """Join the voice channel you're in."""
        voice = ctx.author.voice
        if voice is None:
            return await ctx.send('You are not in a voice channel!')
        
        await voice.channel.connect()
    '''
    @commands.command()
    async def playLocal(self, ctx, *, query):
        """Plays a file from the local filesystem"""

        if ctx.voice_client is None:
            if ctx.author.voice.channel:
                await ctx.author.voice.channel.connect()
            else:
                return await ctx.send("Not connected to a voice channel.")

        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()

        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(query))
        ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else None)
        
        await ctx.send('Now playing: {}'.format(query))
    '''
    def music_finished(self, e, ctx):
        coro = self.read_queue(ctx)
        fut = asyncio.run_coroutine_threadsafe(coro, ctx.bot.loop)
        try:
            fut.result()
        except:
            import traceback
            traceback.print_exc()
            print("Fork")
    
    async def read_queue(self, ctx):
        if self.bot.queue:
            player = self.bot.queue.pop()
            
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()

            ctx.voice_client.play(player, after=lambda e: self.music_finished(e, ctx))
            await ctx.send('Now playing: **{}**'.format(player.title))
            game = discord.Game(name=player.title)
            await self.bot.change_presence(game=game)
        else:    
            await ctx.send('Out of songs :\'(')

    @commands.command()
    async def play(self, ctx, *, url):
        """Streams from a url (almost anything youtube_dl supports)"""
        
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
               return await ctx.send("Not connected to a voice channel.")

        player = await YTDLSource.from_url(url, loop=self.bot.loop)
        
        if not self.bot.queue:
            self.bot.queue.append(player)
            
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            
            ctx.voice_client.play(player, after=lambda e: self.music_finished(e, ctx))
            await ctx.send('Now playing: **{}**'.format(player.title))
            game = discord.Game(name=player.title)
            await self.bot.change_presence(game=game)
        else:
            self.bot.queue.append(player)
            await ctx.send('**{}** has been added to the queue. Position: {}'.format(player.title, len(self.bot.queue) - 1))

        '''
        if ctx.voice_client is None:
            if ctx.author.voice.channel:
                await ctx.author.voice.channel.connect()
            else:
                return await ctx.send("Not connected to a voice channel.")

        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()

        player = await YTDLSource.from_url(url, loop=self.bot.loop)
        ctx.voice_client.play(player, after=lambda e:self.music_finished(e, ctx))
        
        await ctx.send('Now playing: {}'.format(player.title))'''

    @commands.command()
    async def queue(self, ctx):
        print(self.bot.queue)
        if self.bot.queue:
            message = 'Now playing: **{}** `[00:00/00:00]`\n\n'.format(self.bot.queue[0].title)
            message += '\n'.join([
                '`{}.` **{}** added by **?**'.format(n + 1, i.title) for n, i in enumerate(self.bot.queue[1:])
            ])
        else:
            message = 'Not playing anything.'    
        await ctx.send(message)

    @commands.command()
    @checks.manage_channels()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""

        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume/100
        await ctx.send("Changed volume to {}%".format(volume))
        
    @commands.command()
    @checks.manage_channels()
    async def resume(self, ctx):
        """Resumes player"""

        ctx.voice_client.resume()

    @commands.command()
    @checks.manage_channels()
    async def pause(self, ctx):
        """Stops player"""

        ctx.voice_client.pause()

    @commands.command()
    @checks.manage_channels()
    async def stop(self, ctx):
        """Stops player"""

        ctx.voice_client.stop()
        
    @commands.command()
    @checks.manage_channels()
    async def die(self, ctx):
        """Stops player"""

        await ctx.send(':wave:')
        await ctx.bot.logout()
        
def setup(bot):
    bot.add_cog(Music(bot))
