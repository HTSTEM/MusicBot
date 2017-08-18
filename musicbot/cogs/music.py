import asyncio
import random
import time

import youtube_dl
import discord

from discord.ext import commands

from cogs.util import checks
from cogs.util.ytdl import YTDLSource
from cogs.util.categories import category


class Music:
    def __init__(self, bot):
        self.bot = bot
        self.jingle_last = False

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

    # Callbacks:
    def music_finished(self, e, ctx):
        if not ctx.bot.dying:
            coro = self.read_queue(ctx)
            fut = asyncio.run_coroutine_threadsafe(coro, ctx.bot.loop)
            try:
                fut.result()
            except:
                import traceback
                traceback.print_exc()

    # Utilities:
    async def read_queue(self, ctx):
        if self.bot.queue:
            just_played = self.bot.queue.pop(0)
            if just_played.likes and just_played.channel is not None:
                await just_played.channel.send('The song **{}** recieved **{}** likes.'.format(just_played.title, len(just_played.likes)))

        if self.bot.queue:
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            await self.start_playing(ctx, self.bot.queue[0])
        else:
            self.bot.logger.info('Queue empty. Using auto-playlist.')
            await self.auto_playlist(ctx)

    async def auto_playlist(self, ctx):
        found = False
        while not found and not self.bot.queue:
            if (not self.jingle_last) and (not bool(random.randint(0, self.bot.config['jingle_chance'] - 1))):
                url = random.choice(self.bot.jingles)
                self.jingle_last = True
            else:
                url = random.choice(self.bot.autoplaylist)
                self.jingle_last = False

            player = None
            try:
                player = await YTDLSource.from_url(url, None, loop=self.bot.loop)
                found = True
            except youtube_dl.utils.DownloadError:
                self.bot.logger.warn('Download error. Skipping.')
            
            if player is None:
                found = False
        
        if not self.bot.queue:
            self.bot.queue.append(player)

            if ctx.voice_client.is_playing():
                return

            await self.start_playing(ctx, player, announce=False)

    async def start_playing(self, ctx, player, announce=True):
        player.start_time = time.time()
        ctx.voice_client.play(player, after=lambda e: self.music_finished(e, ctx))
        if announce:
            if player.user is None:
                c = player.channel if player.channel is not None else ctx.channel
                await c.send('Now playing: **{}**'.format(player.title))
            else:
                c = player.channel if player.channel is not None else ctx.channel
                await c.send('<@{}>, your song **{}** is now playing in {}!'.format(player.user.id, player.title, ctx.voice_client.channel.name))
        game = discord.Game(name=player.title)
        await self.bot.change_presence(game=game)

    # User commands:
    @category('music')
    @commands.command()
    async def play(self, ctx, *, url):
        """Streams from a url (almost anything youtube_dl supports)"""

        if ctx.voice_client is None:
            if ctx.author.voice:
                self.bot.voice[ctx.guild.id] = await ctx.author.voice.channel.connect()
            else:
               return await ctx.send("Not connected to a voice channel.")

        mod_perms = ctx.channel.permissions_for(ctx.author).manage_channels

        if not mod_perms:
            # Check the queue limit before bothering to download the song
            queued = 0
            for i in self.bot.queue[1:]:
                if i.user is not None:
                    if i.user.id == ctx.author.id:
                        queued += 1
            if queued >= self.bot.config['max_songs_queued']:
                await ctx.send('You can only have {} song{} in the queue at once.'.format(self.bot.config['max_songs_queued'], '' if self.bot.config['max_songs_queued'] == 1 else 's'))
                return

        try:
            with ctx.typing():
                player = await YTDLSource.from_url(url, ctx.author, loop=self.bot.loop)
                player.channel = ctx.channel
        except youtube_dl.utils.DownloadError:
            await ctx.send('No song found.')
            return

        if not mod_perms:
            # Length checking
            if player.duration > self.bot.config['max_song_length']:
                await ctx.send('You don\'t have permission to queue songs longer than {}s. ({}s)'.format(self.bot.config['max_song_length'], player.duration))
                return

        player.channel = ctx.channel

        if not self.bot.queue:
            self.bot.queue.append(player)

            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()

            await self.start_playing(ctx, player)
        else:
            ttp = 0
            for i in self.bot.queue:
                ttp += i.duration
            playing = self.bot.queue[0]
            playing_time = int(time.time()-playing.start_time)
            if ctx.voice_client.is_paused():
                playing_time -= time.time() - ctx.voice_client.source.pause_start
            ttp -= playing_time

            self.bot.queue.append(player)

            await ctx.send('Enqueued **{}** to be played. Position in queue: {} - estimated time until playing: {}'.format(player.title, len(self.bot.queue) - 1, time.strftime("%H:%M:%S", time.gmtime(ttp))))

    @category('music')
    @commands.command()
    async def skip(self, ctx):
        """Registers that you want to skip the current song."""

        # Register skips
        if not self.bot.queue:
            await ctx.send('There\'s nothing playing.')
            return
        elif ctx.author.id in self.bot.queue[0].skips:
            pass
        else:
            self.bot.queue[0].skips.append(ctx.author.id)

        # Skip the song
        num_needed = min(8, int(len(ctx.voice_client.channel.members) / 2))
        if len(self.bot.queue[0].skips) >= num_needed or (self.bot.queue[0].user is not None and ctx.author.id == self.bot.queue[0].user.id):
            await ctx.send('The skip ratio has been reached, skipping song...'.format(ctx.author.id))
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            return

        left = num_needed - len(self.bot.queue[0].skips)
        await ctx.send('<@{}>, your skip for **{}** was acknowledged.\n**{}** more {} is required to vote to skip this song.'.format(ctx.author.id, self.bot.queue[0].title, left, 'person' if left == 1 else 'people'))

    @category('music')
    @commands.command()
    async def like(self, ctx):
        """'Like' the currently playing song"""
        if not self.bot.queue:
            await ctx.send('There\'s nothing playing.')
            return
        elif ctx.author.id in self.bot.queue[0].likes:
            pass
        else:
            self.bot.queue[0].likes.append(ctx.author.id)

        if self.bot.queue[0].channel is None:
            self.bot.queue[0].channel = ctx.channel

        await ctx.send('<@{}>,your \'like\' for **{}** was acknowledged.'.format(ctx.author.id, self.bot.queue[0].title))

    @category('music')
    @commands.command()
    async def queue(self, ctx):
        """Shows the current queue."""
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

    @category('music')
    @commands.command()
    async def np(self, ctx):
        """Gets the currently playing song"""
        if self.bot.queue:
            playing = self.bot.queue[0]
            playing_time = int(time.time()-playing.start_time)
            if ctx.voice_client.is_paused():
                playing_time -= time.time() - ctx.voice_client.source.pause_start

            if ctx.voice_client.is_paused():
                message = 'Now playing: **{}** `[{}/{}]` (**PAUSED**)\n\n'.format(
                    playing.title,
                    time.strftime("%M:%S", time.gmtime(playing_time)),  # here's a hack for now
                    time.strftime("%M:%S", time.gmtime(playing.duration))
                    )
            else:
                message = 'Now playing: **{}** `[{}/{}]`\n\n'.format(
                    playing.title,
                    time.strftime("%M:%S", time.gmtime(playing_time)),  # here's a hack for now
                    time.strftime("%M:%S", time.gmtime(playing.duration))
                    )
        else:
            message = 'Not playing anything.'
        await ctx.send(message)

    @category('music')
    @commands.command()
    async def dequeue(self, ctx):
        for i in self.bot.queue:
            if i.user is not None:
                if i.user.id == ctx.author.id:
                    self.bot.queue.remove(i)
                    await ctx.send('<@{}>, your song **{}** has been removed from the queue.'.format(ctx.author.id, i.title))
                    return
        await ctx.send('<@{}>, you don\'t appear to have any songs in the queue.'.format(ctx.author.id))            

    # Mod commands:
    @category('music')
    @commands.command()
    @checks.manage_channels()
    async def remsong(self, ctx, *, song):
        try:
            song = int(song)
            is_int = True
        except ValueError:
            is_int = False
        
        if is_int:
            if song < 1 or song >= len(self.bot.queue):
                await ctx.send('<@{}>, song must be in range 1-{} or the title.'.format(ctx.author.id, len(self.bot.queue) - 1))
                return
            else:
                player = self.bot.queue.pop(song)
                await ctx.send('<@{}>, the song **{}** has been removed from the queue.'.format(ctx.author.id, player.title))   
        else:
            for i in self.bot.queue:
                if song in i.title:
                    player = i
                    break
            else:
                await ctx.send('<@{}>, no song found matching `{}` in the queue.'.format(ctx.author.id, song))
                return
            self.bot.queue.remove(player)
            await ctx.send('<@{}>, the song **{}** has been removed from the queue.'.format(ctx.author.id, player.title))
    
    @category('bot')
    @commands.command()
    @checks.manage_channels()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Joins a voice channel"""

        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        self.bot.voice[ctx.guild.id] = await channel.connect()

    @category('bot')
    @commands.command()
    @checks.manage_channels()
    async def summon(self, ctx):
        """Join the voice channel you're in."""
        voice = ctx.author.voice
        if voice is None:
            return await ctx.send('You are not in a voice channel!')

        self.bot.voice[ctx.guild.id] = await voice.channel.connect()

    @category('player')
    @commands.command()
    @checks.manage_channels()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""

        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume/100
        await ctx.send("Changed volume to {}%".format(volume))

    @category('player')
    @commands.command()
    @checks.manage_channels()
    async def resume(self, ctx):
        """Resumes player"""
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            ctx.voice_client.source.start_time += time.time() - ctx.voice_client.source.pause_start

    @category('player')
    @commands.command()
    @checks.manage_channels()
    async def pause(self, ctx):
        """Pause the player"""
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            ctx.voice_client.source.pause_start = time.time()

    @category('player')
    @commands.command()
    @checks.manage_channels()
    async def forceskip(self, ctx):
        """Forcefully skips a song"""

        ctx.voice_client.stop()

    @category('player')
    @commands.command()
    @checks.manage_channels()
    async def clear(self, ctx):
        """Stops player and clears queue"""
        self.bot.queue = []
        ctx.voice_client.stop()

def setup(bot):
    bot.add_cog(Music(bot))
