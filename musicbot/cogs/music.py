import asyncio
import base64
import random
import time
import os
import re

import youtube_dl
import discord

from discord.ext import commands

from .util import checks
from .util.ytdl import YTDLSource
from .util.categories import category


should_continue = True

URL_REGEX = re.compile(r'^\w+://(?:\w+\.)*?(\w+)\.(?:co\.)?\w+(?:$|/.*$)')
WHITELIST = [
    'youtube',
    'soundcloud',
    'dropbox',
    'bandcamp'
]


def escape(string):
    return string.replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')

#silent failure
class QueueLimitError(commands.CommandNotFound): pass

class Music:
    def __init__(self, bot):
        self.bot = bot
        self.jingle_last = False

    # Callbacks:
    def music_finished(self, e, ctx):
        if ctx.bot.die_soon:
            coro = ctx.bot.die_soon.send(':wave:')
            fut = asyncio.run_coroutine_threadsafe(coro, ctx.bot.loop)
            try:
                fut.result()
            except:
                import traceback
                traceback.print_exc()

            coro = ctx.bot.logout()
            fut = asyncio.run_coroutine_threadsafe(coro, ctx.bot.loop)
            try:
                fut.result()
            except:
                import traceback
                traceback.print_exc()

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
        if self.bot.queues[ctx.guild.id]:
            just_played = self.bot.queues[ctx.guild.id].pop(0)
            if just_played.likes and just_played.channel is not None:
                if just_played.user is not None:
                    await just_played.channel.send('<@{}>, your song **{}** recieved **{}** like{}.'.format(
                        just_played.user.id, just_played.title, len(just_played.likes), '' if len(just_played.likes) == 1 else 's'))
                else:
                    await just_played.channel.send('The song **{}** recieved **{}** like{}.'.format(
                        just_played.title, len(just_played.likes), '' if len(just_played.likes) == 1 else 's'))

        if self.bot.queues[ctx.guild.id]:
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            await self.start_playing(ctx, self.bot.queues[ctx.guild.id][0])
        else:
            self.bot.logger.info('Queue empty. Using auto-playlist.')
            await self.auto_playlist(ctx)

    async def auto_playlist(self, ctx):
        if self.bot.queues[ctx.guild.id]:
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            await self.start_playing(ctx, self.bot.queues[ctx.guild.id][0])
            return

        found = False
        while not found and not self.bot.queues[ctx.guild.id]:
            if (not self.jingle_last) and (not bool(random.randint(0, self.bot.config['jingle_chance'] - 1))):
                url = random.choice(self.bot.jingles)
                self.jingle_last = True
            else:
                url = random.choice(self.bot.autoplaylist)
                self.jingle_last = False

            player = None
            try:
                if ctx.typing is not None:
                    async with ctx.typing():
                        player = await YTDLSource.from_url(url, None, loop=self.bot.loop)
                else:
                    player = await YTDLSource.from_url(url, None, loop=self.bot.loop)
                found = True
            except youtube_dl.utils.DownloadError:
                self.bot.logger.warn('Download error. Skipping.')

            if player is None:
                found = False

        if not self.bot.queues[ctx.guild.id]:
            self.bot.queues[ctx.guild.id].append(player)

            if ctx.voice_client.is_playing():
                return

            await self.start_playing(ctx, player, announce=False)

    def get_queued(self, user, guild_id, after=0, before=None) -> int:
        queued = 0
        for i in self.bot.queues[guild_id][after:before]:
            if i.user is not None:
                if i.user.id == user.id:
                    queued += 1

        return queued

    def insert_song(self, song, guild_id):
        queue = self.bot.queues[guild_id]
        user = song.user
        if not user: return queue.append(song)
        queued = self.get_queued(user, guild_id) + 1
        users = {}

        for n, entry in reversed(list(enumerate(queue))):
            if entry.user and entry.user.id != user.id and entry.user.id not in users:
                users[entry.user.id] = self.get_queued(entry.user, guild_id, before=n+1)

            if all(queued >= x for x in users.values()):
                queue.insert(n+1, song)
                return n+1

            if entry.user.id in users: users[entry.user.id] -= 1

        queue.append(song)
        return len(queue) - 1

    def remove_from_queue(self, player, guild_id):
        queue = self.bot.queues[guild_id]
        if not player.user: return queue.remove(player)

        i = queue.index(player)
        for n, p in list(enumerate(queue))[i+1:]:
            if p.user == player.user:
                queue[i] = p
                player = p
                i = n

        queue.pop(i)

    def get_queue_length(self, guild_id):
        if self.bot.queues[guild_id]:
            ttp = int(self.bot.queues[guild_id][0].start_time-time.time())
        else:
            ttp = 0

        for entry in self.bot.queues[guild_id]:
            ttp += entry.duration

        return ttp

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
        queued = self.get_queued(ctx.author, ctx.guild.id)
        if queued >= perms['max_songs_queued']:
            await channel.send('You can only have {} song{} in the queue at once.'.format(perms['max_songs_queued'], '' if perms['max_songs_queued'] == 1 else 's'))
            raise QueueLimitError

        with ctx.typing():
            if data is None:
                data = await YTDLSource.data_for(url, loop=self.bot.loop)
            if await YTDLSource.is_playlist(url, data=data, loop=self.bot.loop):
                return 'Is playlist'

            duration, url = await YTDLSource.get_duration(url, data=data, loop=self.bot.loop)

            match = URL_REGEX.match(url)

            if match is None:
                await channel.send(f'Unable to confirm URL is valid.')
                return 'Regex failed'
            if match.groups()[0].lower() not in WHITELIST:
                await channel.send(f'Attempt to queue from non-listed site rejected!')
                return 'Whitelist faied'

            if duration > perms['max_song_length']:
                await channel.send(f'You don\'t have permission to queue songs longer than {perms["max_song_length"]}s. ({duration}s)')
                return 'Max length'

            for song in ctx.bot.queues[ctx.guild.id]:
                if song.user and song.user.id == ctx.author.id and song.origin_url == url:
                    await channel.send('You already have that song queued!')
                    return 'Already queued'

            player = await YTDLSource.from_url(url, ctx.author, loop=self.bot.loop)

        player.channel = ctx.channel

        if not self.bot.queues[ctx.guild.id]:
            self.bot.queues[ctx.guild.id].append(player)

            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()

            await self.start_playing(ctx, player)
        else:
            position = self.insert_song(player, ctx.guild.id)
            ttp = 0
            for i in self.bot.queues[ctx.guild.id][:position]:
                ttp += i.duration
            playing = self.bot.queues[ctx.guild.id][0]
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
    @commands.cooldown(2, 15, type=commands.BucketType.user)
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
                        await ctx.send(f'Your playlist has been truncated to the first {perms["max_playlist_length"]} songs. (Originally {len(songs)})')
                        songs = songs[:perms['max_playlist_length']]
                    await ctx.send(f'Queueing {len(songs)} songs from **{pl_title}**!')

                    for url, title in songs:
                        try:
                            await self.queue_url(url, ctx, dm=True)
                        except QueueLimitError:
                            break
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
    @commands.cooldown(2, 15, type=commands.BucketType.user)
    @checks.command_processed()
    async def search(self, ctx, *, query):
        '''Search for a song'''

        perms = await checks.permissions_for(ctx)
        # Check the queue limit before bothering to download the song
        queued = self.get_queued(ctx.author, ctx.guild.id)

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
    @commands.cooldown(2, 15, type=commands.BucketType.user)
    @checks.command_processed()
    async def jingle(self, ctx, number:int = None):
        '''Enqueues a jingle'''
        perms = await checks.permissions_for(ctx)
        # Check the queue limit before bothering to download the song
        queued = self.get_queued(ctx.author, ctx.guild.id)

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
        if not self.bot.queues[ctx.guild.id]:
            return await ctx.send('There\'s nothing playing.')
        elif ctx.author.id in self.bot.queues[ctx.guild.id][0].skips:
            pass
        elif time.time()-self.bot.queues[ctx.guild.id][0].start_time < skip_grace:
            return await ctx.send(
                f'{ctx.author.mention} At least listen to {skip_grace} seconds of the song!'
            )
        else:
            self.bot.queues[ctx.guild.id][0].skips.append(ctx.author.id)

        # Skip the song
        num_needed = min(8, len(ctx.voice_client.channel.members) // 2)
        if self.bot.queues[ctx.guild.id][0].user is not None and ctx.author.id == self.bot.queues[ctx.guild.id][0].user.id:
            await ctx.send('The current song was force-skipped by the queuer.')
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            return
        if len(self.bot.queues[ctx.guild.id][0].skips) >= num_needed:
            await ctx.send('The skip ratio has been reached, skipping song...')
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            return

        left = num_needed - len(self.bot.queues[ctx.guild.id][0].skips)
        await ctx.send('<@{}>, your skip for **{}** was acknowledged.\n**{}** more {} required to vote to skip this song.'.format(ctx.author.id, self.bot.queues[ctx.guild.id][0].title, left, 'person is' if left == 1 else 'people are'))

    @category('music')
    @commands.command()
    @commands.guild_only()
    @checks.in_vc()
    async def unskip(self, ctx):
        '''Removes your vote to skip the current song.'''

        if not self.bot.queues[ctx.guild.id]:
            return await ctx.send('There\'s nothing playing.')
        elif ctx.author.id not in self.bot.queues[ctx.guild.id][0].skips:
            pass
        else:
            self.bot.queues[ctx.guild.id][0].skips.remove(ctx.author.id)
            return await ctx.send(f'{ctx.author.mention} You have removed your vote to skip this song.')

    @category('music')
    @commands.command()
    @commands.cooldown(1, 120, type=commands.BucketType.user)
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
        if not self.bot.queues[ctx.guild.id]:
            await ctx.send('There\'s nothing playing.')
            return
        elif ctx.author.id in self.bot.queues[ctx.guild.id][0].likes:
            pass
        else:
            self.bot.queues[ctx.guild.id][0].likes.append(ctx.author.id)

        if self.bot.queues[ctx.guild.id][0].channel is None:
            self.bot.queues[ctx.guild.id][0].channel = ctx.channel

        if ctx.author.id not in self.bot.likes:
            self.bot.likes[ctx.author.id] = []
        if base64.b64encode(self.bot.queues[ctx.guild.id][0].title.encode('utf-8')).decode('ascii') not in self.bot.likes[ctx.author.id]:
            self.bot.likes[ctx.author.id].append(base64.b64encode(self.bot.queues[ctx.guild.id][0].title.encode('utf-8')).decode('ascii'))
            self.bot.save_likes()

        if self.bot.like_comp_active:
            just_played = self.bot.queues[ctx.guild.id][0].title
            song_queuer = self.bot.queues[ctx.guild.id][0].user

            if song_queuer is not None:
                if song_queuer not in self.bot.like_comp:
                    self.bot.like_comp[song_queuer] = {}

                if just_played not in self.bot.like_comp[song_queuer]:
                    self.bot.like_comp[song_queuer][just_played] = []

                if ctx.author.id != song_queuer.id:
                    if ctx.author.id not in self.bot.like_comp[song_queuer][just_played]:
                        self.bot.like_comp[song_queuer][just_played].append(ctx.author.id)

        await ctx.send(f'<@{ctx.author.id}>, your \'like\' for **{self.bot.queues[ctx.guild.id][0].title}** was acknowledged.')

    @category('music')
    @commands.command(aliases=['remlike', 'dislike'])
    @commands.cooldown(1, 1, type=commands.BucketType.user)
    async def unlike(self, ctx, song):
        '''Remove your 'like' from a song.
        This does not affect like competitions.'''

        if ctx.author.id not in self.bot.likes:
            return await ctx.send(f'{ctx.author.mention}, you\'ve never liked any songs.')

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

                    await ctx.send(f'{ctx.author.mention}, **{i}** has been removed from your likes.')
                    self.bot.likes[ctx.author.id].remove(base64.b64encode(i.encode('utf-8')).decode('ascii'))
                    self.bot.save_likes()
                    return
                else:
                    await result_message.delete()
                    await confirm_message.delete()
        await ctx.send(f'{ctx.author.mention}, no song could be found. Sorry.')

    @category('music')
    @commands.command()
    @commands.guild_only()
    @commands.cooldown(1, 30, type=commands.BucketType.user)
    async def minewhen(self, ctx):
        '''Tells you when your song will play'''
        if self.bot.queues[ctx.guild.id]:
            ttp = int(self.bot.queues[ctx.guild.id][0].start_time-time.time())
        else:
            ttp = 0

        for i, entry in enumerate(self.bot.queues[ctx.guild.id]):
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
    @commands.cooldown(1, 60, type=commands.BucketType.guild)
    async def queue(self, ctx):
        '''Shows the current queue.'''
        if self.bot.queues[ctx.guild.id]:
            manage_channels = ctx.channel.permissions_for(ctx.author).manage_channels

            playing = self.bot.queues[ctx.guild.id][0]
            playing_time = int(time.time()-playing.start_time)
            if ctx.voice_client.is_paused():
                playing_time -= time.time() - ctx.voice_client.source.pause_start
            ttp = time.gmtime(max(0, self.get_queue_length(ctx.guild.id)))

            message = f'`{time.strftime("%H:%M:%S", ttp)}` in queue.\n'
            message += f'Queue can also be viewed at <https://htcraft.ml/queue?g={ctx.guild.id}>\n'
            message += f'Now playing: **{playing.title}**'
            if playing.user: message += ' added by {}'.format(playing.user.name)
            message += ' `[{}/{}]`'.format(
                time.strftime('%M:%S', time.gmtime(max(0,playing_time))),
                time.strftime('%M:%S', time.gmtime(max(0,playing.duration)))
                )
            if ctx.voice_client.is_paused(): message += '(**PAUSED**)'
            message += '\n\n'
            for n, entry in enumerate(self.bot.queues[ctx.guild.id][1:]):
                if entry.user:
                    to_add = f'`{n+1}.` **{entry.title}** added by **{escape(entry.user.name)}**\n'
                else:
                    to_add = f'`{n+1}.` **{entry.title}**\n'

                if len(message) + len(to_add) > 1900:
                    message += f'*{len(self.bot.queues[ctx.guild.id])-n-1} more*...'
                    break
                elif n > self.bot.config['public_queue_max'] and not manage_channels:
                    message += f'*{len(self.bot.queues[ctx.guild.id])-n-1} more, ask a mod to see the entire queue*...'
                    break
                else:
                    message += to_add

        else:
            message = 'Not playing anything.'

        await ctx.send(message)

    @category('music')
    @commands.command()
    @commands.guild_only()
    @commands.cooldown(1, 30, type=commands.BucketType.user)
    async def pldump(self, ctx):
        if self.bot.queues[ctx.guild.id]:
            playing = self.bot.queues[ctx.guild.id][0]
            playing_time = int(time.time()-playing.start_time)
            if ctx.voice_client.is_paused():
                playing_time -= time.time() - ctx.voice_client.source.pause_start
            ttp = time.gmtime(max(0, self.get_queue_length(ctx.guild.id)))

            message = f'`{time.strftime("%H:%M:%S", ttp)}` in queue.\n'
            message += f'Queue can also be viewed at <https://htcraft.ml/queue?g={ctx.guild.id}>\n'
            message += f'Now playing: **{playing.title}**'
            if playing.user: message += ' added by {}'.format(playing.user.name)
            message += ' `[{}/{}]`'.format(
                time.strftime('%M:%S', time.gmtime(max(0,playing_time))),
                time.strftime('%M:%S', time.gmtime(max(0,playing.duration)))
                )
            if ctx.voice_client.is_paused(): message += '(**PAUSED**)'
            message += '\n\n'
            for n, entry in enumerate(self.bot.queues[ctx.guild.id][1:]):
                if entry.user:
                    to_add = f'`{n+1}.` **{entry.title}** added by **{escape(entry.user.name)}**\n'
                else:
                    to_add = f'`{n+1}.` **{entry.title}**\n'

                message += to_add
        else:
            message = 'Not playing anything.'

        with open('tmp.txt', 'w') as dump:
            dump.write(message)

        with open('tmp.txt', 'r') as dump:
            await ctx.author.send('Playlist Dump:', file=discord.File(dump, filename='playlist.txt'))


    @category('music')
    @commands.command()
    @commands.guild_only()
    @commands.cooldown(2, 30, type=commands.BucketType.guild)
    async def np(self, ctx):
        '''Gets the currently playing song'''
        if self.bot.queues[ctx.guild.id]:
            playing = self.bot.queues[ctx.guild.id][0]
            playing_time = int(time.time()-playing.start_time)
            if ctx.voice_client.is_paused():
                playing_time -= time.time() - ctx.voice_client.source.pause_start

            message = f'Now playing: **{escape(playing.title)}**'
            if playing.user: message += f' added by {escape(playing.user.name)}'
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
        for player in self.bot.queues[ctx.guild.id][1:]:
            if player.user and player.user.id == ctx.author.id:
                songs.append(player)

        if len(songs) == 0:
            await ctx.send(f'<@{ctx.author.id}>, you don\'t appear to have any songs in the queue.')
            return
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
                if title.lower() in song.title.lower():
                    player = song
                    break
            else:
                return await ctx.send('Song not found.')


        self.remove_from_queue(player, ctx.guild.id)

        await ctx.send(f'<@{ctx.author.id}>, your song **{player.title}** has been removed from the queue.')


    @category('music')
    @commands.command()
    @commands.guild_only()
    async def remall(self, ctx, user: discord.Member = None):
        '''Remove all of your songs from the queue'''

        if user:
            perms = await checks.permissions_for(ctx)
            if 'moderation' not in perms['categories']:
                user = ctx.author

        else: user = ctx.author

        songs = [song for song in ctx.bot.queues[ctx.guild.id][1:] if song.user.id == user.id]
        for song in songs:
            ctx.bot.queues[ctx.guild.id].remove(song)

        await ctx.send(f'{user.mention} all of your songs have been removed from the queue!')


    # Mod commands:
    @category('moderation')
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
            if song < 1 or song >= len(self.bot.queues[ctx.guild.id]):
                await ctx.send(f'<@{ctx.author.id}>, song must be in range 1-{len(self.bot.queues[ctx.guild.id])-1} or the title.')
                return
            else:
                player = self.bot.queues[ctx.guild.id][song]
                self.remove_from_queue(player, ctx.guild.id)
                await ctx.send(f'<@{ctx.author.id}>, the song **{player.title}** has been removed from the queue.')
        else:
            for i in self.bot.queues[ctx.guild.id][1:]:
                if song.lower() in i.title.lower():
                    player = i
                    break
            else:
                await ctx.send(f'<@{ctx.author.id}>, no song found matching `{song}` in the queue.')
                return
            self.remove_from_queue(player, ctx.guild.id)
            await ctx.send(f'<@{ctx.author.id}>, the song **{player.title}** has been removed from the queue.')

    @category('bot')
    @commands.command()
    @commands.guild_only()
    async def reconnect(self, ctx):
        '''Reconnects the voice client'''
        global should_continue
        should_continue = False  # prevent music_finished from running

        for i in self.bot.voice_clients:
            if i.channel.guild == ctx.guild:
                vc = i
                break
        else:
            vc = ctx.voice_client

        if vc is not None:
            channel = ctx.voice_client.channel
            source = ctx.voice_client.source
            await ctx.voice_client.disconnect()
            await asyncio.sleep(0.5)
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


def setup(bot):
    bot.add_cog(Music(bot))
