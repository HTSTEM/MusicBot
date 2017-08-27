import asyncio
import base64
import random
import time
import os

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
                if just_played.user is not None:
                    await just_played.channel.send('<@{}>, your song **{}** recieved **{}** like{}.'.format(
                        just_played.user.id, just_played.title, len(just_played.likes), '' if len(just_played.likes) == 1 else 's'))
                else:
                    await just_played.channel.send('The song **{}** recieved **{}** like{}.'.format(
                        just_played.title, len(just_played.likes), '' if len(just_played.likes) == 1 else 's'))

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
    @checks.in_vc()
    @checks.not_dm()
    async def play(self, ctx, *, url):
        """Streams from a url (almost anything youtube_dl supports)"""

        url = url.strip('<>')

        if ctx.voice_client is None:
            if ctx.author.voice:
                self.bot.voice[ctx.guild.id] = await ctx.author.voice.channel.connect()
            else:
               return await ctx.send("Not connected to a voice channel.")

        perms = await checks.permissions_for(ctx)

        # Check the queue limit before bothering to download the song
        queued = 0
        for i in self.bot.queue[1:]:
            if i.user is not None:
                if i.user.id == ctx.author.id:
                    queued += 1
        if queued >= perms['max_songs_queued']:
            await ctx.send('You can only have {} song{} in the queue at once.'.format(perms['max_songs_queued'], '' if perms['max_songs_queued'] == 1 else 's'))
            return

        try:
            with ctx.typing():
                duration = await YTDLSource.get_duration(url, ctx.author, loop=self.bot.loop)
                if duration > perms['max_song_length']:
                    await ctx.send('You don\'t have permission to queue songs longer than {}s. ({}s)'.format(perms['max_song_length'], duration))
                    return

                player = await YTDLSource.from_url(url, ctx.author, loop=self.bot.loop)
                player.channel = ctx.channel
        except youtube_dl.utils.DownloadError:
            await ctx.send('No song found.')
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
    @checks.in_vc()
    @checks.not_dm()
    async def search(self, ctx, *, query):
        '''Search for a song'''

        perms = checks.permissions_for(ctx)
        # Check the queue limit before bothering to download the song
        queued = 0
        for i in self.bot.queue[1:]:
            if i.user is not None:
                if i.user.id == ctx.author.id:
                    queued += 1
        if queued >= perms['max_songs_queued']:
            await ctx.send('You can only have {} song{} in the queue at once.'.format(perms['max_songs_queued'], '' if perms['max_songs_queued'] == 1 else 's'))
            return


        if not query:
            return await ctx.send('Please specify a search query.')

        search_query = 'ytsearch{}:{}'.format(self.bot.config['search_limit'], query)

        search_msg = await ctx.send("Searching for videos...")
        await ctx.channel.trigger_typing()
        try:
            info = await YTDLSource.search(search_query, download=False, process=True)
        except Exception as e:
            await search_msg.edit(content=str(e))
            raise e
        else:
            await search_msg.delete()

        if not info:
            await ctx.send("No videos found.")

        def check(m):
            valid_message = (
                m.content.lower()[0] in 'yn' or
                # hardcoded function name weeee
                m.content.lower().startswith('{}{}'.format(ctx.prefix, 'search')) or
                m.content.lower().startswith('exit'))
            is_author = m.author == ctx.author
            is_channel = m.channel == ctx.channel
            return valid_message and is_author and is_channel

        for e in info['entries']:
            result_message = await ctx.send( "Result {}/{}: {}".format(
                info['entries'].index(e) + 1, len(info['entries']), e['webpage_url']))

            confirm_message = await ctx.send("Is this ok? Type `y`, `n` or `exit`")
            response_message = await ctx.bot.wait_for('message', check=check)

            if not response_message:
                await result_message.delete()
                await confirm_message.delete()
                return await ctx.send("Ok nevermind.")

            # They started a new search query so lets clean up and bugger off
            elif response_message.content.startswith(ctx.prefix) or \
                    response_message.content.lower().startswith('exit'):

                await result_message.delete()
                await confirm_message.delete()
                return

            if response_message.content.lower().startswith('y'):
                await result_message.delete()
                await confirm_message.delete()
                try:
                    await response_message.delete()
                except discord.errors.Forbidden:
                    pass
                await ctx.send("Alright, coming right up!")
                await ctx.invoke(self.play, url=e['webpage_url'])
                return
            else:
                await result_message.delete()
                await confirm_message.delete()
                try:
                    await response_message.delete()
                except discord.errors.Forbidden:
                    pass

        await ctx.send("Oh well :frowning:")

    @category('music')
    @commands.command()
    @checks.in_vc()
    @checks.not_dm()
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
        if self.bot.queue[0].user is not None and ctx.author.id == self.bot.queue[0].user.id:
            await ctx.send('The current song was force-skipped by the queuer.')
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            return
        if len(self.bot.queue[0].skips) >= num_needed:
            await ctx.send('The skip ratio has been reached, skipping song...'.format(ctx.author.id))
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            return

        left = num_needed - len(self.bot.queue[0].skips)
        await ctx.send('<@{}>, your skip for **{}** was acknowledged.\n**{}** more {} is required to vote to skip this song.'.format(ctx.author.id, self.bot.queue[0].title, left, 'person' if left == 1 else 'people'))


    @category('music')
    @commands.command()
    async def mylikes(self, ctx):
        '''Get a list of every song you've ever liked.'''
        if ctx.author.id in self.bot.likes and self.bot.likes[ctx.author.id]:
            m = '**Your liked songs:**\n'
            m += '\n'.join(base64.b64decode(i.encode('ascii')).decode('utf-8') for i in self.bot.likes[ctx.author.id])
        else:
            m = 'You haven\'t liked any songs.'

        if len(m) < 2000:
            await ctx.author.send(m)
        else:
            with open('{}-likes.txt'.format(ctx.author.id), 'wb') as f:
                f.write(m.encode('utf-8'))
            with open('{}-likes.txt'.format(ctx.author.id), 'rb') as f:
                await ctx.author.send(file=discord.File(f))
            os.remove('{}-likes.txt'.format(ctx.author.id))
        await ctx.send(':mailbox_with_mail:')

    @category('music')
    @commands.command()
    @checks.in_vc()
    @checks.not_dm()
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

        if ctx.author.id not in self.bot.likes:
            self.bot.likes[ctx.author.id] = []
        if base64.b64encode(self.bot.queue[0].title.encode('utf-8')).decode('ascii') not in self.bot.likes[ctx.author.id]:
            self.bot.likes[ctx.author.id].append(base64.b64encode(self.bot.queue[0].title.encode('utf-8')).decode('ascii'))
            self.bot.save_likes()

        if self.bot.like_comp_active:
            if self.bot.queue[0].user is not None:
                if self.bot.queue[0].user not in self.bot.like_comp:
                    self.bot.like_comp[self.bot.queue[0].user] = {}
                if self.bot.queue[0].title not in self.bot.like_comp[self.bot.queue[0].user]:
                    self.bot.like_comp[self.bot.queue[0].user][self.bot.queue[0].title] = []
                if ctx.author.id != self.bot.queue[0].user.id:
                    if ctx.author.id not in self.bot.like_comp[self.bot.queue[0].user][self.bot.queue[0].title]:
                        self.bot.like_comp[self.bot.queue[0].user][self.bot.queue[0].title].append(ctx.author.id)

        await ctx.send('<@{}>, your \'like\' for **{}** was acknowledged.'.format(ctx.author.id, self.bot.queue[0].title))

    @category('music')
    @commands.command()
    async def remlike(self, ctx, song):
        '''Remove your 'like' from a song.
        This does not affect like competitions.'''
        # Notes for any other developers:
        # I was originally using levenshtein, however there is one
        # problem I have found with it in the past:
        # If the search string is short, then levenshtein will weight
        # other short strings higher, even if they have nothing to do
        # with your target. For example, if I searched 'abcd' looking
        # for 'abcdefghijklmnop', 'jlki' would have a higher priority
        # than what you really want. For this reason, I'm just using
        # `in`.
        #
        # TL;DR:
        # Levenshtein sucks as a general search algorithm.
        #
        # P.S.
        #  I might write my own algorithm one day to use that handles
        #  this better. :P
        
        if ctx.author.id not in self.bot.likes:
            return await ctx.send('<@{}>, you\'ve never liked any songs.'.format(ctx.author.id))
        
        for i in self.bot.likes[ctx.author.id]:
            i = base64.b64decode(i.encode('ascii')).decode('utf-8')
            if song.lower() in i.lower():  # Replace with better algorithm later
                
                def check(m):
                    valid_message = (
                        m.content.lower()[0] in 'yn' or
                        m.content.lower().startswith('exit'))
                    is_author = m.author == ctx.author
                    is_channel = m.channel == ctx.channel
                    return valid_message and is_author and is_channel

                result_message = await ctx.send("I found **{}**".format(i))

                confirm_message = await ctx.send("Is this ok? Type `y`, `n` or `exit`")
                response_message = await ctx.bot.wait_for('message', check=check)

                try:
                    await response_message.delete()
                except discord.errors.Forbidden:
                    pass

                if not response_message:
                    await result_message.delete()
                    await confirm_message.delete()
                    return await ctx.send("Ok nevermind.")
                elif response_message.content.lower().startswith('exit'):
                    await result_message.delete()
                    await confirm_message.delete()
                    return await ctx.send("Ok nevermind.")

                if response_message.content.lower().startswith('y'):
                    await result_message.delete()
                    await confirm_message.delete()
                    
                    await ctx.send("<@{}>, **{}** has been removed from your likes.".format(ctx.author.id, i))
                    self.bot.likes[ctx.author.id].remove(base64.b64encode(i.encode('utf-8')).decode('ascii'))
                    self.bot.save_likes()
                    return
                else:
                    await result_message.delete()
                    await confirm_message.delete()
        await ctx.send("<@{}>, no song could be found. Sorry.".format(ctx.author.id))

    @category('music')
    @commands.command()
    @checks.not_dm()
    async def queue(self, ctx):
        """Shows the current queue."""
        if self.bot.queue:

            if len(self.bot.queue) > 10 and not ctx.channel.permissions_for(ctx.author).manage_channels:
                message = 'The queue has {} items. Ask a mod to see the queue.\n'.format(len(self.bot.queue))
                return await ctx.send(message)

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
    @checks.not_dm()
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
    @checks.not_dm()
    async def dequeue(self, ctx):
        '''Remove your song(s) from the queue'''
        for i in self.bot.queue[1:]:
            if i.user is not None:
                if i.user.id == ctx.author.id:
                    self.bot.queue.remove(i)
                    await ctx.send('<@{}>, your song **{}** has been removed from the queue.'.format(ctx.author.id, i.title))
                    return
        await ctx.send('<@{}>, you don\'t appear to have any songs in the queue.'.format(ctx.author.id))

    # Mod commands:
    @category('music')
    @commands.command()
    @checks.not_dm()
    async def remsong(self, ctx, *, song):
        '''Remove a song from the queue.
        `song` can either be the number of the song in the queue
        or it can be the name (or part of the name) of the song you
        wish to remove.'''
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
            for i in self.bot.queue[1:]:
                if song.lower() in i.title.lower():
                    player = i
                    break
            else:
                await ctx.send('<@{}>, no song found matching `{}` in the queue.'.format(ctx.author.id, song))
                return
            self.bot.queue.remove(player)
            await ctx.send('<@{}>, the song **{}** has been removed from the queue.'.format(ctx.author.id, player.title))

    @category('bot')
    @commands.command()
    @checks.not_dm()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Joins a voice channel"""

        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        self.bot.voice[ctx.guild.id] = await channel.connect()

    @category('bot')
    @commands.command()
    @checks.not_dm()
    async def summon(self, ctx):
        """Join the voice channel you're in."""
        voice = ctx.author.voice
        if voice is None:
            return await ctx.send('You are not in a voice channel!')

        self.bot.voice[ctx.guild.id] = await voice.channel.connect()

    @category('player')
    @commands.command()
    @checks.not_dm()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""

        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume/100
        await ctx.send("Changed volume to {}%".format(volume))

    @category('player')
    @commands.command()
    @checks.not_dm()
    async def resume(self, ctx):
        """Resumes player"""
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            ctx.voice_client.source.start_time += time.time() - ctx.voice_client.source.pause_start

    @category('player')
    @commands.command()
    @checks.not_dm()
    async def pause(self, ctx):
        """Pause the player"""
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            ctx.voice_client.source.pause_start = time.time()

    @category('player')
    @commands.command()
    @checks.not_dm()
    async def forceskip(self, ctx):
        """Forcefully skips a song"""

        ctx.voice_client.stop()

    @category('player')
    @commands.command()
    @checks.not_dm()
    async def clear(self, ctx):
        """Stops player and clears queue"""
        self.bot.queue = []
        ctx.voice_client.stop()

def setup(bot):
    bot.add_cog(Music(bot))
