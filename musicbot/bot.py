import traceback
import logging
import time
import re

import discord

from ruamel.yaml import YAML
from discord.ext import commands

class MusicBot(commands.Bot):
    def __init__(self, command_prefix='!', *args, **kwargs):
        self.queue = []
        logging.basicConfig(level=logging.INFO, format='[%(name)s %(levelname)s] %(message)s')
        self.logger = logging.getLogger('bot')
        self.autoplaylist = open('config/autoplaylist.txt').read().split('\n')
        self.jingles = open('config/jingles.txt').read().split('\n')

        self.yaml = YAML(typ='safe')
        with open('config/config.yaml') as conf_file:
            self.config = self.yaml.load(conf_file)

        if 'command_prefix' in self.config:
            command_prefix = self.config['command_prefix']
        
        self.voice = {}
        self.dying = False

        super().__init__(command_prefix=command_prefix, *args, **kwargs)

    async def close(self):
        await super().close()

    async def on_command_error(self, ctx: commands.Context, exception: Exception):
        if isinstance(exception, commands.CommandInvokeError):
            if isinstance(exception.original, discord.Forbidden):
                try: await ctx.send('Permissions error: `{}`'.format(exception))
                except discord.Forbidden: return

            lines = traceback.format_exception(type(exception), exception, exception.__traceback__)
            self.logger.error(''.join(lines))

        elif isinstance(exception, commands.CheckFailure):
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
            raise exception
    
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
        if 'bot_channels' in self.config:
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
                        ctx = Holder()
                        ctx.voice_client = vc
                        ctx.bot = self
                        await self.cogs['Music'].auto_playlist(ctx)
                else:
                    self.logger.info(' - Guild {} not found.'.format(guild_id))
            self.logger.info('Done.')

    def run(self, token):
        cogs = ['cogs.music', 'cogs.misc']
        self.remove_command("help")
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
