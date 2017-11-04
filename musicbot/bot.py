import traceback
import logging
import time
import os
import re
import sys
import asyncio
import sqlite3

import discord

from ruamel.yaml import YAML
from discord.ext import commands

from cogs.util.checks import can_use
from cogs.util.cache import QueueTable


class MusicBot(commands.AutoShardedBot):
    def __init__(self, command_prefix='!', *args, **kwargs):
        self.database = sqlite3.connect('musicbot/database.sqlite', check_same_thread=False)
        self.queue = None

        self.pending = set()
        logging.basicConfig(
            level=logging.INFO,
            format='[%(name)s %(levelname)s] %(message)s',
            handlers=[logging.FileHandler('musicbot.log'),
                      logging.StreamHandler()]
              )
        self.logger = logging.getLogger('bot')

        self.autoplaylist = open('config/autoplaylist.txt').read().split('\n')
        self.jingles = open('config/jingles.txt').read().split('\n')

        self.yaml = YAML(typ='safe')
        with open('config/config.yml') as conf_file:
            self.config = self.yaml.load(conf_file)

        with open('config/permissions.yml') as conf_file:
            self.permissions = self.yaml.load(conf_file)

        if 'command_prefix' in self.config:
            command_prefix = self.config['command_prefix']

        if os.path.exists('config/likes.yml'):
            with open('config/likes.yml') as conf_file:
                self.likes = self.yaml.load(conf_file)
        else:
            self.likes = {}
        if self.likes is None:
            self.likes = {}

        if os.path.exists('config/blacklist.txt'):
            with open('config/blacklist.txt') as bl_file:
                self.blacklist = [int(i) for i in bl_file.read().split('\n') if i]
        else:
            self.blacklist = []

        self.voice = {}
        self.dying = False
        self.like_comp_active = False
        self.like_comp = {}

        super().__init__(command_prefix=command_prefix, *args, **kwargs)

    def save_bl(self):
        with open('config/blacklist.txt', 'w') as bl_file:
            bl_file.write('\n'.join(str(i) for i in self.blacklist))
    def save_likes(self):
        with open('config/likes.yml', 'w') as conf_file:
            self.yaml.dump(self.likes, conf_file)

    # Async methods
    async def close(self):
        await super().close()

    async def notify_devs(self, info, ctx=None):
        with open('error.txt', 'w') as error_file:
            error_file.write(info)

        for dev_id in self.config['developers']:
            dev = self.get_user(dev_id)
            if dev is None:
                self.logger.warning(f'Could not get developer with an ID of {dev.id}, skipping.')
                continue
            try:
                with open('error.txt', 'r') as error_file:
                    if ctx is None:
                        await dev.send(file=discord.File(error_file))
                    else:
                        await dev.send(f'{ctx.author}: {ctx.message.content}',file=discord.File(error_file))
            except Exception as e:
                self.logger.error('Couldn\'t send error embed to developer {0.id}. {1}'
                                .format(dev, type(e).__name__ + ': ' + str(e)))

        os.remove('error.txt')

    async def wait_for_source(self, voice_client, timeout = 10):
        if timeout is None or timeout <= 0:
            while voice_client.source is None: await asyncio.sleep(0.5)
        else:
            for i in range(2*timeout):
                if voice_client.source is not None: break
                else: await asyncio.sleep(0.5)

        if voice_client.source is None: raise asyncio.TimeoutError
        else: return voice_client.source

    # Client events
    async def on_command_error(self, ctx: commands.Context, exception: Exception):
        if isinstance(exception, commands.CommandInvokeError):
            if isinstance(exception.original, discord.Forbidden):
                try: await ctx.send(f'Permissions error: `{exception}`')
                except discord.Forbidden: pass
                return
            if isinstance(exception.original, discord.ClientException):
                return await ctx.send(str(exception.original))

            lines = traceback.format_exception(type(exception), exception, exception.__traceback__)
            self.logger.error(''.join(lines))
            await ctx.send(f'{exception.original}, the devs have been notified.')
            await self.notify_devs(''.join(lines), ctx)

        elif isinstance(exception, commands.NoPrivateMessage):
            return

        elif isinstance(exception, commands.CheckFailure):
            if 'bot_in_vc' in exception.args:
                await ctx.send('I\'m not in a voice channel on this server.')
            elif 'user_in_vc' in exception.args:
                await ctx.send(f'You must be in `{ctx.bot.voice[ctx.guild.id].channel.name}` to use that command.')
            elif 'request_pending' in exception.args:
                await ctx.send('Wait until I\'m done processing your first request!')
            else:
                await ctx.send('You can\'t do that.')
        elif isinstance(exception, commands.CommandNotFound):
            pass
        elif isinstance(exception, commands.UserInputError):
            error = ' '.join(exception.args)
            error_data = re.findall('Converting to \"(.*)\" failed for parameter \"(.*)\"\.', error)
            if not error_data:
                await ctx.send('Error: {}'.format(' '.join(exception.args)))
            else:
                await ctx.send('Got to say, I *was* expecting `{1}` to be an `{0}`..'.format(*error_data[0]))
        else:
            info = traceback.format_exception(type(exception), exception, exception.__traceback__, chain=False)
            self.logger.error('Unhandled command exception - {}'.format(''.join(info)))
            await ctx.send(f'{exception}, the devs have been notified.')
            await self.notify_devs(''.join(info), ctx)

    async def on_error(self, event_method, *args, **kwargs):
        info = sys.exc_info()
        if info[0] == discord.ClientException: return
        info = traceback.format_exception(*info, chain=False)
        self.logger.error('Unhandled exception - {}'.format(''.join(info)))
        await self.notify_devs(''.join(info))

    async def on_voice_state_update(self, member, before, after):
        if (after.channel is None) and (before.channel is None):
            return

        if after.channel is None:
            channel = before.channel
            left = True
        else:
            channel = after.channel
            left = False

        if channel.guild.id in self.voice:
            vc = self.voice[channel.guild.id]

            if vc.channel != channel: return

            if len(channel.members) <= 1:
                await self.wait_for_source(vc)
                if vc.is_playing():
                    self.logger.info(f'{channel.name} empty. Pausing.')
                    vc.pause()
                    vc.source.pause_start = time.time()
            else:
                empty = True

                for m in channel.members:
                    if (not (m.voice.deaf or m.voice.self_deaf)) and (not m.bot):
                        empty = False

                if not empty:
                    if vc.is_paused():
                        self.logger.info(f'Someone appeared in {channel.name}! Resuming.')
                        vc.resume()
                        vc.source.start_time += time.time() - vc.source.pause_start
                else:
                    await self.wait_for_source(vc)
                    if vc.is_playing():
                        self.logger.info(f'{channel.name} empty. Pausing.')
                        vc.pause()
                        vc.source.pause_start = time.time()

    async def on_message(self, message):
        #if message.guild is None:  # DMs
        #    return

        if message.author.id in self.blacklist:
            return

        if message.guild is not None and 'bot_channels' in self.config:
            bc = self.config['bot_channels']
            if message.guild.id in bc:
                if message.channel.id not in bc[message.guild.id]:
                    return

        await self.process_commands(message)

    async def on_ready(self):
        self.logger.info(f'Connected to Discord')
        self.logger.info(f'Guilds  : {len(self.guilds)}')
        self.logger.info(f'Users   : {len(set(self.get_all_members()))}')
        self.logger.info(f'Channels: {len(list(self.get_all_channels()))}')

        self.queue = QueueTable(self, 'queue')

        await self.queue._populate()

        if 'default_channels' in self.config:
            class Holder:
                pass

            self.logger.info('Joining voice channels..')

            dc = self.config['default_channels']
            for guild_id in dc:
                guild = self.get_guild(guild_id)
                if guild is not None:
                    self.logger.info(f' - Found guild \'{guild.name}\'.')
                    channel = guild.get_channel(dc[guild_id])
                    if channel is None:
                        self.logger.info(f'   - Channel {dc[guild_id]} not found.')
                    elif not isinstance(channel, discord.VoiceChannel):
                        self.logger.info(f'   - Channel \'{channel.name}\' found, but is not voice channel.')
                    else:
                        self.logger.info(f'   - Channel \'{channel.name}\' found. Joining.')

                        success = False
                        while not success:
                            try:
                                vc = await channel.connect()
                                self.voice[guild_id] = vc
                                success = True
                            except discord.ClientException as e:
                                if guild_id in self.voice:
                                    vc = self.voice[guild_id]
                                else:
                                    self.logger.info('   - Error! Trying again in 1 second.' + str(e))
                                    await asyncio.sleep(1)

                        self.logger.info('   - Joined. Starting auto-playlist.')
                        cctx = Holder()
                        cctx.voice_client = vc
                        cctx.bot = self
                        c = guild.get_channel(self.config['bot_channels'][guild_id][0])
                        cctx.send = c.send
                        cctx.channel = c
                        await self.cogs['Music'].auto_playlist(cctx)

                        if len(vc.channel.members) <= 1:
                            self.logger.info(f'   - {vc.channel.name} empty. Pausing.')
                            if vc.is_playing():
                                vc.pause()
                                vc.source.pause_start = time.time()
                else:
                    self.logger.info(f' - Guild {guild_id} not found.')
            self.logger.info('Done.')


    def run(self, token):
        cogs = ['cogs.music', 'cogs.misc']
        self.remove_command("help")
        self.add_check(can_use)
        for cog in cogs:
            try:
                self.load_extension(cog)
            except Exception as e:
                self.logger.exception(f'Failed to load cog {cog}:')
                self.logger.exception(e)
            else:
                self.logger.info(f'Loaded cog {cog}.')

        self.logger.info(f'Loaded {len(self.cogs)} cogs')
        super().run(token)

if __name__ == '__main__':
    bot = MusicBot()
    token = open(bot.config['token_file'], 'r').read().split('\n')[0]
    bot.run(token)
