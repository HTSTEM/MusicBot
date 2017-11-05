import asyncio
import base64
import random
import time
import os

import youtube_dl
import discord

from discord.ext import commands

from .util import checks
from .util.ytdl import YTDLSource
from .util.categories import category

should_continue = True

class Music:
    def __init__(self, bot):
        self.bot = bot
        self.jingle_last = False

    # Callbacks:
    def music_finished(self, e, ctx):
        if should_continue and not ctx.bot.dying:
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
        if self.bot.queue:
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            await self.start_playing(ctx, self.bot.queue[0])
            return

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

    def get_queued(self, user, after=0, before=None) -> int:
        queued = 0
        for i in self.bot.queue[after:before]:
            if i.user is not None:
                if i.user.id == user.id:
                    queued += 1

        return queued

    def insert_song(self, song):
        queue = self.bot.queue
        user = song.user
        if not user: return queue.append(song)
        queued = self.get_queued(user) + 1
        users = {}

        for n, entry in reversed(list(enumerate(queue))):
            if entry.user and entry.user.id != user.id and entry.user.id not in users:
                users[entry.user.id] = self.get_queued(entry.user, before=n+1)

            if all(queued >= x for x in users.values()):
                queue.insert(n+1, song)
                return n+1

            if entry.user.id in users: users[entry.user.id] -= 1

        queue.append(song)
        return len(queue) - 1

    def remove_from_queue(self, player):
        queue = self.bot.queue
        if not player.user: return queue.remove(player)

        i = queue.index(player)
        for n, p in list(enumerate(queue))[i+1:]:
            if p.user == player.user:
                queue[i] = p
                player = p
                i = n

        queue.pop(i)

    async def queue_url(self, url, ctx, dm=False, data=None):
        if dm:
            channel = ctx.author.dm_channel
            if channel is None:
                await ctx.author.create_dm()
                channel = ctx.author.dm_channel
        else:
            channel = ctx

        url = url.strip('<>')

        if ctx.voice_client is None:
            if ctx.author.voice:
                self.bot.voice[ctx.guild.id] = await ctx.author.voice.channel.connect()
            else:
                return await ctx.send('Not connected to a voice channel.')

        perms = await checks.permissions_for(ctx)

        # Check the queue limit before bothering to download the song
        queued = self.get_queued(ctx.author)
        if queued >= perms['max_songs_queued']:
            await channel.send('You can only have {} song{} in the queue at once.'.format(perms['max_songs_queued'], '' if perms['max_songs_queued'] == 1 else 's'))
            return 'Max songs'

        with ctx.typing():
            if data is None:
                data = await YTDLSource.data_for(url, loop=self.bot.loop)
            if await YTDLSource.is_playlist(url, data=data, loop=self.bot.loop):
                return 'Is playlist'

            duration, url = await YTDLSource.get_duration(url, data=data, loop=self.bot.loop)

            if duration > perms['max_song_length']:
                await channel.send(f'You don\'t have permission to queue songs longer than {perms["max_song_length"]}s. ({duration}s)')
                return 'Max length'

            player = await YTDLSource.from_url(url, ctx.author, loop=self.bot.loop)

        player.channel = ctx.channel

        if not self.bot.queue:
            self.bot.queue.append(player)

            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()

            await self.start_playing(ctx, player)
        else:
            position = self.insert_song(player)
            ttp = 0
            for i in self.bot.queue[:position]:
                ttp += i.duration
            playing = self.bot.queue[0]
            playing_time = int(time.time()-playing.start_time)
            if ctx.voice_client.is_paused():
                playing_time -= time.time() - ctx.voice_client.source.pause_start
            ttp -= playing_time

            await channel.send('Enqueued **{}** to be played. Position in queue: {} - estimated time until playing: {}'.format(
                      player.title,
                      position,
                      time.strftime('%H:%M:%S', time.gmtime(max(0,ttp)))
                      ))

    async def start_playing(self, ctx, player, announce=True):
        player.start_time = time.time()
        ctx.voice_client.play(player, after=lambda e: self.music_finished(e, ctx))

        if announce:
            if player.user is None:
                c = player.channel if player.channel is not None else ctx.channel
                await c.send(f'Now playing: **{player.title}**')
            else:
                c = player.channel if player.channel is not None else ctx.channel
                await c.send(f'<@{player.user.id}>, your song **{player.title}** is now playing in {ctx.voice_client.channel.name}!')

        game = discord.Game(name=player.title)
        await self.bot.change_presence(game=game)

    # User commands:
    @category('music')
    @commands.command()
    @commands.guild_only()
    @checks.in_vc()
    @checks.command_processed()
    async def play(self, ctx, *, url):
        '''Streams from a url (almost anything youtube_dl supports)'''
        url = url.strip('<>')

        if ctx.voice_client is None:
            if ctx.author.voice:
                self.bot.voice[ctx.guild.id] = await ctx.author.voice.channel.connect()
            else:
                return await ctx.send('Not connected to a voice channel.')

        perms = await checks.permissions_for(ctx)

        try:
            with ctx.typing():
                data = await YTDLSource.data_for(url, loop=self.bot.loop)

                if await YTDLSource.is_playlist(url, data=data, loop=self.bot.loop):
                    pl_title, songs = await YTDLSource.load_playlist(url, data=data, loop=self.bot.loop)

                    if len(songs) > perms['max_playlist_length']:
                        if len(songs) == 56:
                            return await ctx.send(f'It appears you have tried to queue a YouTube mix. Try putting some of the songs into a playlist that\'s got a maximum of {perms["max_playlist_length"]} songs.')
                        return await ctx.send(f'You can queue a maximun of {perms["max_playlist_length"]} songs from a playlist at once. ({len(songs)})')

                    await ctx.send(f'Queueing {len(songs)} songs from **{pl_title}**!')

                    print(songs)

                    for url, title in songs:
                        try:
                            await self.queue_url(url, ctx, dm=True)
                        except Exception as e:
                            await ctx.send(str(e))

                    return await ctx.send('Finished queueing playlist.')
                else:
                    await self.queue_url(url, ctx, data=data)
        except youtube_dl.utils.DownloadError:
            return await ctx.send('No song found.')
        except ValueError:
            return await ctx.send('A network error occured.')

    @category('music')
    @commands.command()
    @commands.guild_only()
    @checks.in_vc()
    @checks.command_processed()
    async def search(self, ctx, *, query):
        '''Search for a song'''

        perms = await checks.permissions_for(ctx)
        # Check the queue limit before bothering to download the song
        queued = self.get_queued(ctx.author)

        if queued >= perms['max_songs_queued']:
            await ctx.send('You can only have {} song{} in the queue at once.'.format(perms['max_songs_queued'], '' if perms['max_songs_queued'] == 1 else 's'))
            return


        if not query:
            await ctx.send('Please specify a search query.')
            return

        search_query = f'ytsearch{self.bot.config["search_limit"]}:{query}'

        search_msg = await ctx.send('Searching for videos...')
        await ctx.channel.trigger_typing()
        try:
            info = await YTDLSource.search(search_query, download=False, process=True)
        except Exception as e:
            await search_msg.edit(content=str(e))
            raise e
        else:
            await search_msg.delete()

        if not info:
            await ctx.send('No videos found.')

        def check(m):
            if not m.content: return False
            valid_message = (
                (m.content and m.content.lower()[0] in 'yn') or
                m.content.lower().startswith('exit'))
            is_author = m.author == ctx.author
            is_channel = m.channel == ctx.channel
            return valid_message and is_author and is_channel

        for e in info['entries']:
            result_message = await ctx.send( 'Result {}/{}: {}'.format(
                info['entries'].index(e) + 1, len(info['entries']), e['webpage_url']))

            confirm_message = await ctx.send('Is this ok? Type `y`, `n` or `exit`')
            response_message = await ctx.bot.wait_for('message', check=check)

            if not response_message:
                await result_message.delete()
                await confirm_message.delete()
                await ctx.send('Ok nevermind.')
                return

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
                await ctx.send('Alright, coming right up!')
                await ctx.invoke(self.play, url=e['webpage_url'])
                return
            else:
                await result_message.delete()
                await confirm_message.delete()
                try:
                    await response_message.delete()
                except discord.errors.Forbidden:
                    pass

        await ctx.send('Oh well :frowning:')

    @category('music')
    @commands.command()
    @commands.guild_only()
    @checks.in_vc()
    @checks.command_processed()
    async def jingle(self, ctx, number:int = None):
        '''Enqueues a jingle'''
        perms = await checks.permissions_for(ctx)
        # Check the queue limit before bothering to download the song
        queued = self.get_queued(ctx.author)

        if queued >= perms['max_songs_queued']:
            await ctx.send('You can only have {} song{} in the queue at once.'.format(perms['max_songs_queued'], '' if perms['max_songs_queued'] == 1 else 's'))
            return

        if number is None:
            await ctx.invoke(self.play, url=random.choice(ctx.bot.jingles))
            return

        if number > len(ctx.bot.jingles):
            return await ctx.send(f'There\'s only {len(ctx.bot.jingles)} jingles!')
        elif number < 1:
            return await ctx.send('I can\'t play a jingle that doesn\'t exist!')

        await ctx.invoke(self.play, url=ctx.bot.jingles[number-1])

    @jingle.before_invoke
    @search.before_invoke
    @play.before_invoke
    async def add_pending(self, ctx):
        ctx.bot.pending.add(ctx.author.id)

    @jingle.after_invoke
    @search.after_invoke
    @play.after_invoke
    async def clear_pending(self, ctx):
        ctx.bot.pending.discard(ctx.author.id)

    @category('music')
    @commands.command()
    @commands.guild_only()
    @checks.in_vc()
    async def skip(self, ctx):
        '''Registers that you want to skip the current song.'''
        skip_grace = self.bot.config['skip_grace']
        # Register skips
        if not self.bot.queue:
            return await ctx.send('There\'s nothing playing.')
        elif ctx.author.id in self.bot.queue[0].skips:
            pass
        elif time.time()-self.bot.queue[0].start_time < skip_grace:
            return await ctx.send(
                f'{ctx.author.mention} At least listen to {skip_grace} seconds of the song!'
            )
        else:
            self.bot.queue[0].skips.append(ctx.author.id)

        # Skip the song
        num_needed = min(8, len(ctx.voice_client.channel.members) // 2)
        if self.bot.queue[0].user is not None and ctx.author.id == self.bot.queue[0].user.id:
            await ctx.send('The current song was force-skipped by the queuer.')
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            return
        if len(self.bot.queue[0].skips) >= num_needed:
            await ctx.send('The skip ratio has been reached, skipping song...')
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            return

        left = num_needed - len(self.bot.queue[0].skips)
        await ctx.send('<@{}>, your skip for **{}** was acknowledged.\n**{}** more {} required to vote to skip this song.'.format(ctx.author.id, self.bot.queue[0].title, left, 'person is' if left == 1 else 'people are'))

    @category('music')
    @commands.command()
    @commands.guild_only()
    @checks.in_vc()
    async def unskip(self, ctx):
        '''Removes your vote to skip the current song.'''

        if not self.bot.queue:
            return await ctx.send('There\'s nothing playing.')
        elif ctx.author.id not in self.bot.queue[0].skips:
            pass
        else:
            self.bot.queue[0].skips.remove(ctx.author.id)
            return await ctx.send(f'{ctx.author.mention} You have removed your vote to skip this song.')

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
            with open(f'{ctx.author.id}-likes.txt', 'wb') as f:
                f.write(m.encode('utf-8'))
            with open(f'{ctx.author.id}-likes.txt', 'rb') as f:
                await ctx.author.send(file=discord.File(f))
            os.remove(f'{ctx.author.id}-likes.txt')
        await ctx.send(':mailbox_with_mail:')

    @category('music')
    @commands.command()
    @commands.guild_only()
    @checks.in_vc()
    async def like(self, ctx):
        ''''Like' the currently playing song'''
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

        await ctx.send(f'<@{ctx.author.id}>, your \'like\' for **{self.bot.queue[0].title}** was acknowledged.')

    @category('music')
    @commands.command(aliases=['remlike', 'dislike'])
    async def unlike(self, ctx, song):
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
            return await ctx.send(f'<@{ctx.author.id}>, you\'ve never liked any songs.')

        for i in self.bot.likes[ctx.author.id]:
            i = base64.b64decode(i.encode('ascii')).decode('utf-8')
            if song.lower() in i.lower():  # Replace with better algorithm later

                def check(m):
                    if not m.content: return False
                    valid_message = (
                        (m.content and m.content.lower()[0] in 'yn') or
                        m.content.lower().startswith('exit'))
                    is_author = m.author == ctx.author
                    is_channel = m.channel == ctx.channel
                    return valid_message and is_author and is_channel

                result_message = await ctx.send(f'I found **{i}**')

                confirm_message = await ctx.send('Is this ok? Type `y`, `n` or `exit`')
                response_message = await ctx.bot.wait_for('message', check=check)

                try:
                    await response_message.delete()
                except discord.errors.Forbidden:
                    pass

                if not response_message:
                    await result_message.delete()
                    await confirm_message.delete()
                    return await ctx.send('Ok nevermind.')
                elif response_message.content.lower().startswith('exit'):
                    await result_message.delete()
                    await confirm_message.delete()
                    return await ctx.send('Ok nevermind.')

                if response_message.content.lower().startswith('y'):
                    await result_message.delete()
                    await confirm_message.delete()

                    await ctx.send(f'<@{ctx.author.id}>, **{i}** has been removed from your likes.')
                    self.bot.likes[ctx.author.id].remove(base64.b64encode(i.encode('utf-8')).decode('ascii'))
                    self.bot.save_likes()
                    return
                else:
                    await result_message.delete()
                    await confirm_message.delete()
        await ctx.send('<@{ctx.author.id}>, no song could be found. Sorry.')

    @category('music')
    @commands.command()
    @commands.guild_only()
    async def minewhen(self, ctx):
        '''Tells you when your song will play'''
        if self.bot.queue:
            ttp = int(self.bot.queue[0].start_time-time.time())
        else:
            ttp = 0

        for i, entry in enumerate(self.bot.queue):
            if ctx.author == entry.user:
                if i == 0:
                    await ctx.send(f'Your song **{entry.title}** is playing right now!')
                else:
                    ttp = time.strftime('%H:%M:%S', time.gmtime(max(0,ttp)))
                    await ctx.send(
                        f'Your song **{entry.title}** is at position {i} in the queue and will be playing in {ttp}.'
                    )
                return
            else:
                ttp += entry.duration
        else:
            await ctx.send('You don\'t have a song in the queue!')


    @category('music')
    @commands.command()
    @commands.guild_only()
    async def queue(self, ctx):
        '''Shows the current queue.'''
        if self.bot.queue:

            manage_channels = ctx.channel.permissions_for(ctx.author).manage_channels

            playing = self.bot.queue[0]
            playing_time = int(time.time()-playing.start_time)
            if ctx.voice_client.is_paused():
                playing_time -= time.time() - ctx.voice_client.source.pause_start

            message = f'Now playing: **{playing.title}**'
            if playing.user: message += ' added by {}'.format(playing.user.name)
            message += ' `[{}/{}]`'.format(
                time.strftime('%M:%S', time.gmtime(max(0,playing_time))),
                time.strftime('%M:%S', time.gmtime(max(0,playing.duration)))
                )
            if ctx.voice_client.is_paused(): message += '(**PAUSED**)'
            message += '\n\n'
            for n, entry in enumerate(self.bot.queue[1:]):
                to_add = f'`{n+1}.` **{entry.title}** added by **{entry.user.name}**\n'
                if len(message) + len(to_add) > 1900:
                    message += f'*{len(self.bot.queue)-n-1} more*...'
                    break
                elif n > self.bot.config['public_queue_max'] and not manage_channels:
                    message += f'*{len(self.bot.queue)-n-1} more, ask a mod to see the entire queue*...'
                    break
                else:
                    message += to_add

        else:
            message = 'Not playing anything.'

        await ctx.send(message)

    @category('music')
    @commands.command()
    @commands.guild_only()
    async def np(self, ctx):
        '''Gets the currently playing song'''
        if self.bot.queue:
            playing = self.bot.queue[0]
            playing_time = int(time.time()-playing.start_time)
            if ctx.voice_client.is_paused():
                playing_time -= time.time() - ctx.voice_client.source.pause_start

            message = f'Now playing: **{playing.title}**'
            if playing.user: message += f' added by {playing.user.name}'
            message += ' `[{}/{}]`'.format(
                    time.strftime('%M:%S', time.gmtime(max(0,playing_time))),
                    time.strftime('%M:%S', time.gmtime(max(0,playing.duration)))
                    )
            if ctx.voice_client.is_paused(): message += '(**PAUSED**)'
        else:
            message = 'Not playing anything.'
        await ctx.send(message)

    @category('music')
    @commands.command(aliases=['unqueue'])
    @commands.guild_only()
    async def dequeue(self, ctx, *, title= None):
        '''Remove your song(s) from the queue'''
        songs = []
        for player in self.bot.queue[1:]:
            if player.user and player.user.id == ctx.author.id:
                songs.append(player)

        if len(songs) == 0:
            await ctx.send(f'<@{ctx.author.id}>, you don\'t appear to have any songs in the queue.')
        elif len(songs) == 1:
            player = songs[0]
        else:
            if not title:
                song_list = '\n'.join([f'**{song.title}**' for song in songs])
                mess = await ctx.send(f'Which song would you like to remove? \n{song_list}')
                def check(m): return m.channel == ctx.channel and m.author == ctx.author
                try: resp = await ctx.bot.wait_for('message', check=check, timeout=120)
                except asyncio.TimeoutError: return await ctx.send(f'{ctx.author.mention} nvm.')
                finally: await mess.delete()
                title = resp.content

            for song in songs:
                if title in song.title:
                    player = song
                    break
            else:
                return await ctx.send('Song not found.')


        self.remove_from_queue(player)

        await ctx.send(f'<@{ctx.author.id}>, your song **{player.title}** has been removed from the queue.')



    # Mod commands:
    @category('modding')
    @commands.command()
    @commands.guild_only()
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
                await ctx.send(f'<@{ctx.author.id}>, song must be in range 1-{len(self.bot.queue)-1} or the title.')
                return
            else:
                player = self.bot.queue.pop(song)
                await ctx.send(f'<@{ctx.author.id}>, the song **{player.title}** has been removed from the queue.')
        else:
            for i in self.bot.queue[1:]:
                if song.lower() in i.title.lower():
                    player = i
                    break
            else:
                await ctx.send(f'<@{ctx.author.id}>, no song found matching `{song}` in the queue.')
                return
            self.bot.queue.remove(player)
            await ctx.send(f'<@{ctx.author.id}>, the song **{player.title}** has been removed from the queue.')

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

    @category('player')
    @commands.command()
    @commands.guild_only()
    async def volume(self, ctx, volume: int):
        '''Changes the player's volume'''

        if ctx.voice_client is None:
            return await ctx.send('Not connected to a voice channel.')

        ctx.voice_client.source.volume = volume / 100
        await ctx.send('Changed volume to {volume}%')

    @category('bot')
    @commands.command()
    @commands.guild_only()
    async def reconnect(self, ctx):
        '''Reconnects the voice client'''
        global should_continue
        should_continue = False  # prevent music_finished from running
        if ctx.voice_client is not None:
            channel = ctx.voice_client.channel
            source = ctx.voice_client.source
            await ctx.voice_client.disconnect()
        else:
            channel = ctx.bot.get_channel(ctx.bot.config['default_channels'][ctx.guild.id])
            source = None
        ctx.bot.voice[ctx.guild.id] = await channel.connect()
        if source is not None:
            new_source = source.duplicate()  # gets a fresh copy, breaks if isn't done
            await self.start_playing(ctx, new_source)
        else:
            await self.read_queue(ctx)

        should_continue = True

    @category('player')
    @commands.command()
    @commands.guild_only()
    async def resume(self, ctx):
        '''Resumes player'''
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            ctx.voice_client.source.start_time += time.time() - ctx.voice_client.source.pause_start

    @category('player')
    @commands.command()
    @commands.guild_only()
    async def pause(self, ctx):
        '''Pause the player'''
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            ctx.voice_client.source.pause_start = time.time()

    @category('player')
    @commands.command()
    @commands.guild_only()
    async def forceskip(self, ctx):
        '''Forcefully skips a song'''
        ctx.voice_client.stop()
        await ctx.send('Song forceskipped.')

    @category('player')
    @commands.command()
    @commands.guild_only()
    async def clear(self, ctx):
        '''Stops player and clears queue'''
        while self.bot.queue:
            self.bot.queue.pop()

        ctx.voice_client.stop()


def setup(bot):
    bot.add_cog(Music(bot))
