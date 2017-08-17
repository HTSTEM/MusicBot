import asyncio

import discord
import youtube_dl

from discord.ext import commands

# Suppress noise about console usage from errors
token = open('token.txt','r').read().split('\n')[0]


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'before_options': '-nostdin',
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, ytdl.extract_info, url)
        
        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class Music:
    def __init__(self, bot):
        self.bot = bot
        self.queue = []

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Joins a voice channel"""

        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)
        
        await channel.connect()

    @commands.command()
    async def play(self, ctx, *, query):
        """Plays a file from the local filesystem"""
        return await ctx.send("We need to make this not local. `return`ed.")

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

    def song_finished(self, e, ctx):
        coro = self.read_queue(ctx)
        fut = asyncio.run_coroutine_threadsafe(coro, ctx.bot.loop)
        try:
            fut.result()
        except:
            print("Fork")
    
    async def read_queue(self, ctx):
        print('rq')
        if self.queue:
            print(self.queue)
            player = self.queue.pop()
            print(player)
            
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            
            ctx.voice_client.play(player, after=lambda: self.song_finished(ctx))
            await ctx.send('Now playing: **{}**'.format(player.title))
        
    @commands.command()
    async def yt(self, ctx, *, url):
        """Streams from a url (almost anything youtube_dl supports)"""

        if ctx.voice_client is None:
            if ctx.author.voice.channel:
                await ctx.author.voice.channel.connect()
            else:
                return await ctx.send("Not connected to a voice channel.")

        player = await YTDLSource.from_url(url, loop=self.bot.loop)
        
        if not self.queue:
            self.queue.append(player)
            
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            
            ctx.voice_client.play(player, after=lambda e: self.song_finished(e, ctx))
            await ctx.send('Now playing: **{}**'.format(player.title))
        else:
            self.queue.append(player)
            await ctx.send('**{}** has been added to the queue. Position: {}'.format(player.title, len(self.queue) - 1))

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""

        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume/100
        await ctx.send("Changed volume to {}%".format(volume))


    @commands.command()
    async def stop(self, ctx):
        """Stops and disconnects the bot from voice"""

        await ctx.voice_client.disconnect()


bot = commands.Bot('!')

@bot.event
async def on_ready():
    print('Logged in as {0.id}/{0}'.format(bot.user))
    print('------')

bot.add_cog(Music(bot))

bot.run(token)
