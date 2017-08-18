import asyncio
import random
import time

import youtube_dl
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
        self.bot.queue.pop(0)
        if self.bot.queue:
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            await self.start_playing(ctx, self.bot.queue[0])
        else:
            print('Queue empty. Using auto-playlist.')

            found = False
            while not found:
                url = random.choice(self.bot.autoplaylist)
                
                try:
                    player = await YTDLSource.from_url(url, ctx.author, loop=self.bot.loop)
                    found = True
                except youtube_dl.utils.DownloadError:
                    print('Download error. Skipping.')
            
            self.bot.queue.append(player)
            
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            
            await self.start_playing(ctx, player, announce=False)
                    
    async def start_playing(self, ctx, player, announce=True):
        player.start_time = time.time()
        ctx.voice_client.play(player, after=lambda e: self.music_finished(e, ctx))
        if announce:
            await ctx.send('Now playing: **{}**'.format(player.title))
        game = discord.Game(name=player.title)
        await self.bot.change_presence(game=game)

    @commands.command()
    async def play(self, ctx, *, url):
        """Streams from a url (almost anything youtube_dl supports)"""
        
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
               return await ctx.send("Not connected to a voice channel.")

        try:
            with ctx.typing():
                player = await YTDLSource.from_url(url, ctx.author, loop=self.bot.loop)
        except youtube_dl.utils.DownloadError:
            await ctx.send('No song found.')
            return
        print(player)
        
        if not self.bot.queue:
            self.bot.queue.append(player)
            
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            
            await self.start_playing(ctx, player)
        else:
            self.bot.queue.append(player)
            await ctx.send('**{}** has been added to the queue. Position: {}'.format(player.title, len(self.bot.queue) - 1))

    @commands.command()
    async def queue(self, ctx):
        if self.bot.queue:
            playing = self.bot.queue[0]
            playing_time = int(time.time()-playing.start_time)
            if ctx.voice_client.is_paused(): 
                playing_time -= time.time() - ctx.voice_client.source.pause_start
                
            message = 'Now playing: **{}** `[{}/{}]`\n\n'.format(
                playing.title, 
                time.strftime("%M:%S", time.gmtime(playing_time)),  # here's a hack for now
                time.strftime("%M:%S", time.gmtime(playing.duration))
                )
            message += '\n'.join([
                '`{}.` **{}** added by **{}**'.format(n + 1, i.title, i.user.name) for n, i in enumerate(self.bot.queue[1:])
            ])
        else:
            message = 'Not playing anything.'    
        await ctx.send(message)
    
    @commands.command()
    async def np(self, ctx):
        if self.bot.queue:
            playing = self.bot.queue[0]
            playing_time = int(time.time()-playing.start_time)
            if ctx.voice_client.is_paused(): 
                playing_time -= time.time() - ctx.voice_client.source.pause_start
                
            message = 'Now playing: **{}** `[{}/{}]`\n\n'.format(
                playing.title, 
                time.strftime("%M:%S", time.gmtime(playing_time)),  # here's a hack for now
                time.strftime("%M:%S", time.gmtime(playing.duration))
                )
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
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            ctx.voice_client.source.start_time += time.time() - ctx.voice_client.source.pause_start

    @commands.command()
    @checks.manage_channels()
    async def pause(self, ctx):
        """Stops player"""
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            ctx.voice_client.source.pause_start = time.time()

    @commands.command()
    @checks.manage_channels()
    async def forceskip(self, ctx):
        """Skips a song"""

        ctx.voice_client.stop()
        
    @commands.command()
    @checks.manage_channels()
    async def stop(self, ctx):
        """Stops player and clears queue"""
        self.bot.queue = []
        ctx.voice_client.stop()
        
    @commands.command()
    @checks.manage_channels()
    async def die(self, ctx):
        """Shuts down the bot"""

        await ctx.send(':wave:')
        await ctx.bot.logout()
        
def setup(bot):
    bot.add_cog(Music(bot))
