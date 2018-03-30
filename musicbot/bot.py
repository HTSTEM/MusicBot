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
        self.queues = {}

        self.pending = set()
        logging.basicConfig(
            level=logging.INFO,
            format='[%(name)s %(levelname)s] %(message)s',
            handlers=[logging.FileHandler('musicbot.log'),
                      logging.StreamHandler()]
              )
        self.logger = logging.getLogger('bot')

        self.autoplaylist = open('config/autoplaylist.txt').read().split('\n')

        self.yaml = YAML(typ='safe')
        with open('config/config.yml') as conf_file:
            self.config = self.yaml.load(conf_file)

        with open('config/default_channels.yml') as conf_file:
            default_channels = conf_file.readlines()  # self.yaml.load(conf_file)
            self.default_channels = []
            for i in default_channels:
                i = i.strip()
                if i.startswith('#'):
                    self.default_channels.append(i[1:])
                    continue
                if not i: continue

                key, rest = i.split(':')
                rest = rest.split('#')
                value = rest[0]
                comment = '#'.join(rest[1:])
                key = int(key.strip())
                value = int(value.strip())

                self.default_channels.append((key, value, comment))

        with open('config/bot_channels.yml') as conf_file:
            self.bot_channels = self.yaml.load(conf_file) or {}

        with open('config/permissions.yml') as conf_file:
            self.permissions = self.yaml.load(conf_file)

        if os.path.exists('config/patrons.yml'):
            with open('config/patrons.yml') as patron_file:
                self.patrons = self.yaml.load(patron_file)

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
                self.blacklist = [(int(i.split(',')[0]), int(i.split(',')[1])) for i in bl_file.read().split('\n') if i]
        else:
            self.blacklist = []

        self.voice = {}
        self.dying = False
        self.die_soon = False
        self.like_comp_active = False
        self.like_comp = {}

        super().__init__(command_prefix=command_prefix, *args, **kwargs)

    def save_bl(self):
        with open('config/blacklist.txt', 'w') as bl_file:
            bl_file.write('\n'.join(f'i[0],i[1]' for i in self.blacklist))
    def save_likes(self):
        with open('config/likes.yml', 'w') as conf_file:
            self.yaml.dump(self.likes, conf_file)
    def save_bot_channels(self):
        with open('config/bot_channels.yml', 'w') as conf_file:
            self.yaml.dump(self.bot_channels, conf_file)
    def save_default_channels(self):
        text = ''
        for i in self.default_channels:
            if isinstance(i, str):
                text += f'#{i}\n'
            else:
                if len(i) == 2:
                    text += f'{i[0]}: {i[1]}\n'
                else:
                    text += f'{i[0]}: {i[1]}  #{i[2]}\n'

        with open('config/default_channels.yml', 'w') as conf_file:
            conf_file.write(text)

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

    async def wait_for_source(self, voice_client, timeout=10):
        if timeout is None or timeout <= 0:
            while voice_client.source is None: await asyncio.sleep(0.5)
        else:
            for i in range(2 * timeout):
                if voice_client.source is not None: break
                else: await asyncio.sleep(0.5)

        if voice_client.source is None:
            self.logger.warning('wait_for_source timed out!')

        return voice_client.source

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

        elif isinstance(exception, commands.CommandOnCooldown):
            await ctx.send(
                f'{ctx.author.mention} You\'re going a bit fast, try again in {exception.retry_after:.2f} seconds.',
                delete_after = 5
            )

        elif isinstance(exception, commands.CheckFailure):
            if 'bot_in_vc' in exception.args:
                await ctx.send('I\'m not in a voice channel on this server.')
            elif 'user_in_vc' in exception.args:
                await ctx.send(f'You must be in `{ctx.bot.voice[ctx.guild.id].channel.name}` to use that command.')
            elif 'request_pending' in exception.args:
                await ctx.send('Wait until I\'m done processing your first request!')
            elif 'silent' in exception.args:
                pass
            else:
                await ctx.send('You can\'t do that.')
        elif isinstance(exception, commands.CommandNotFound):
            return

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

    async def on_message(self, message):
        #if message.guild is None:  # DMs
        #    return
        if message.author.bot:
            return

        if message.guild is not None:
            if (message.guild.id, message.author.id) in self.blacklist:
                return

        await self.process_commands(message)

    async def on_ready(self):
        self.logger.info(f'Connected to Discord')
        self.logger.info(f'Guilds  : {len(self.guilds)}')
        self.logger.info(f'Users   : {len(set(self.get_all_members()))}')
        self.logger.info(f'Channels: {len(list(self.get_all_channels()))}')

        for i in self.guilds:
            q = QueueTable(self, f'queue-{i.id}')
            await q._populate()

            self.queues[i.id] = q

        class Holder:
            pass

        self.logger.info('Joining voice channels..')

        dc = self.default_channels
        for default in dc:
            if not isinstance(default, tuple): continue

            if default[0] in self.voice: continue

            guild = self.get_guild(default[0])
            if guild is not None:
                self.logger.info(f' - Found guild \'{guild.name}\'.')
                channel = guild.get_channel(default[1])
                if channel is None:
                    self.logger.info(f'   - Channel {default[1]} not found.')
                elif not isinstance(channel, discord.VoiceChannel):
                    self.logger.info(f'   - Channel \'{channel.name}\' found, but is not voice channel.')
                else:
                    self.logger.info(f'   - Channel \'{channel.name}\' found. Joining.')

                    success = False
                    while not success:
                        try:
                            vc = await channel.connect()
                            self.voice[default[0]] = vc
                            success = True
                        except discord.ClientException:
                            if default[0] in self.voice:
                                vc = self.voice[default[0]]
                            else:
                                self.logger.info('   - Error! Trying again in 1 second.')
                                await asyncio.sleep(1)

                    self.logger.info('   - Joined. Starting auto-playlist.')
                    cctx = Holder()
                    cctx.voice_client = vc
                    cctx.bot = self
                    cctx.typing = None
                    if default[0] in self.bot_channels and self.bot_channels[default[0]]:
                        c = guild.get_channel(self.bot_channels[default[0]][0])
                    else:
                        c = guild.channels[0]
                    cctx.send = c.send
                    cctx.channel = c
                    cctx.guild = guild
                    await self.cogs['Music'].auto_playlist(cctx)

                    if len(vc.channel.members) <= 1:
                        self.logger.info(f'   - {vc.channel.name} empty. Pausing.')
                        if vc.is_playing():
                            vc.pause()
                            vc.source.pause_start = time.time()
            else:
                self.logger.info(f' - Guild {default[0]} not found.')
        self.logger.info('Done.')


    def run(self, token):
        cogs = ['cogs.music', 'cogs.misc', 'cogs.comp', 'cogs.core',
                'cogs.git', 'cogs.moderation', 'cogs.player']

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
    with open(bot.config['creds_file']) as cred_file:
        creds = bot.yaml.load(cred_file)
    bot.run(creds['token'])
