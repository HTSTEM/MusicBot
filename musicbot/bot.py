import traceback
import logging
import time
import os
import re
import sys

import discord

from ruamel.yaml import YAML
from discord.ext import commands

from cogs.util.checks import NotInVCError, can_use


class MusicBot(commands.Bot):
    def __init__(self, command_prefix='!', *args, **kwargs):
        self.queue = []
        self.pending = set()
        logging.basicConfig(level=logging.INFO, format='[%(name)s %(levelname)s] %(message)s')
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

    async def close(self):
        await super().close()

    async def on_command_error(self, ctx: commands.Context, exception: Exception):
        if isinstance(exception, commands.CommandInvokeError):
            if isinstance(exception.original, discord.Forbidden):
                try: await ctx.send('Permissions error: `{}`'.format(exception))
                except discord.Forbidden: pass
                return
            
            lines = traceback.format_exception(type(exception), exception, exception.__traceback__)
            self.logger.error(''.join(lines))
            await ctx.send('{}, the devs have been notified.'.format(exception.original))
            await self.notify_devs(''.join(lines), ctx)
        elif isinstance(exception, commands.CheckFailure):
            if 'bot_in_vc' in exception.args:
                await ctx.send('I\'m not in a voice channel on this server.')
            elif 'user_in_vc' in exception.args:
                await ctx.send('You must be in `{}` to use that command.'.format(ctx.bot.voice[ctx.guild.id].channel.name))
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
            await ctx.send('{}, the devs have been notified.'.format(exception))
            await self.notify_devs(''.join(info), ctx)
            
    async def on_error(self, event_method, *args, **kwargs):
        info = sys.exc_info()
        info = traceback.format_exception(*info, chain=False)
        self.logger.error('Unhandled exception - {}'.format(''.join(info)))
        await self.notify_devs(''.join(info))
    
    async def notify_devs(self, info, ctx=None):
        with open('error.txt', 'w') as error_file:
            error_file.write(info)
        
        for dev_id in self.config['developers']:
            dev = self.get_user(dev_id)
            if dev is None:
                self.logger.warning('Could not get developer with an ID of {0.id}, skipping.'.format(dev))
                continue
            try:
                with open('error.txt', 'r') as error_file:
                    if ctx is None:
                        await dev.send(file=discord.File(error_file))
                    else:
                        await dev.send('{}: {}'.format(ctx.author, ctx.message.content),file=discord.File(error_file))
            except Exception as e:
                self.logger.error('Couldn\'t send error embed to developer {0.id}. {1}'
                                .format(dev, type(e).__name__ + ': ' + str(e)))
            
        os.remove('error.txt')

    async def on_voice_state_update(self, member, before, after):
        if not ((after.channel is None) ^ (before.channel is None)):
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
                self.logger.info('{} empty. Pausing.'.format(channel.name))
                if vc.is_playing():
                    vc.pause()
                    vc.source.pause_start = time.time()
            else:
                self.logger.info('Someone appeared in {}! Resuming.'.format(channel.name))
                if vc.is_paused():
                    vc.resume()
                    vc.source.start_time += time.time() - vc.source.pause_start

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
        self.logger.info('Connected to Discord')
        self.logger.info('Guilds  : {}'.format(len(self.guilds)))
        self.logger.info('Users   : {}'.format(len(set(self.get_all_members()))))
        self.logger.info('Channels: {}'.format(len(list(self.get_all_channels()))))

        if 'default_channels' in self.config:
            class Holder:
                pass

            self.logger.info('Joining voice channels..')

            dc = self.config['default_channels']
            for guild_id in dc:
                guild = self.get_guild(guild_id)
                if guild is not None:
                    self.logger.info(' - Found guild \'{}\'.'.format(guild.name))
                    channel = guild.get_channel(dc[guild_id])
                    if channel is None:
                        self.logger.info('   - Channel {} not found.'.format(dc[guild_id]))
                    elif not isinstance(channel, discord.VoiceChannel):
                        self.logger.info('   - Channel \'{}\' found, but is not voice channel.'.format(channel.name))
                    else:
                        self.logger.info('   - Channel \'{}\' found. Joining.'.format(channel.name))
                        vc = await channel.connect()
                        self.voice[guild_id] = vc
                        
                        self.logger.info('   - Joined. Starting auto-playlist.')
                        cctx = Holder()
                        cctx.voice_client = vc
                        cctx.bot = self
                        c = guild.get_channel(self.config['bot_channels'][guild_id][0])
                        cctx.send = c.send
                        cctx.channel = c
                        await self.cogs['Music'].auto_playlist(cctx)
                        
                        if len(vc.channel.members) <= 1:
                            self.logger.info('   - {} empty. Pausing.'.format(vc.channel.name))
                            if vc.is_playing():
                                vc.pause()
                                vc.source.pause_start = time.time()
                else:
                    self.logger.info(' - Guild {} not found.'.format(guild_id))
            self.logger.info('Done.')

    def run(self, token):
        cogs = ['cogs.music', 'cogs.misc']
        self.remove_command("help")
        self.add_check(can_use)
        for cog in cogs:
            try:
                self.load_extension(cog)
            except Exception as e:
                self.logger.exception('Failed to load cog {}.'.format(cog))
            else:
                self.logger.info('Loaded cog {}.'.format(cog))
                
        self.logger.info('Loaded {} cogs'.format(len(self.cogs)))
        super().run(token)

if __name__ == '__main__':
    bot = MusicBot()
    token = open(bot.config['token_file'], 'r').read().split('\n')[0]
    bot.run(token)
