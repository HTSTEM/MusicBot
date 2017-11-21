import time
import asyncio

from discord.ext import commands

from .util.categories import category


class Player:
    def __init__(self, bot):
        self.bot = bot
        self.clearer = None

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
        while self.bot.queues[ctx.guild.id]:
            self.bot.queues[ctx.guild.id].pop()

        ctx.voice_client.stop()

    @category('player')
    @commands.command()
    @commands.guild_only()
    async def volume(self, ctx, volume: int):
        '''Changes the player's volume'''

        if ctx.voice_client is None:
            return await ctx.send('Not connected to a voice channel.')

        ctx.voice_client.source.volume = volume / 100
        await ctx.send('Changed volume to {volume}%')

    def pause_player(self, vc):
        self.bot.logger.info(f'{vc.channel.name} empty. Pausing.')
        vc.pause()
        vc.source.pause_start = time.time()
        period = self.bot.config.get('clear_time', 10)
        if period < 0: return

        async def clear_queue():
            await asyncio.sleep(period*60)
            self.logger.info(f'{vc.channel.name} empty for {period} minutes. Clearing queue.')
            while len(self.bot.queues[vc.channel.guild.id]) > 1:
                self.bot.queues[vc.channel.guild.id].pop(1)

            self.clearer = None

        self.clearer = asyncio.ensure_future(clear_queue())

    async def on_voice_state_update(self, member, before, after):
        if (after.channel is None) and (before.channel is None):
            return

        if after.channel is None:
            channel = before.channel
        else:
            channel = after.channel

        if channel.guild.id in self.bot.voice:
            vc = self.bot.voice[channel.guild.id]

            if vc.channel != channel: return

            if len(channel.members) <= 1:
                await self.bot.wait_for_source(vc)
                if vc.is_playing():
                    self.pause_player(vc)
            else:
                empty = True

                for m in channel.members:
                    if (not (m.voice.deaf or m.voice.self_deaf)) and (not m.bot):
                        empty = False

                if not empty:
                    if vc.is_paused():
                        self.bot.logger.info(f'Someone appeared in {channel.name}! Resuming.')
                        vc.resume()
                        vc.source.start_time += time.time() - vc.source.pause_start

                    if self.clearer and not self.clearer.cancelled():
                        try: self.clearer.cancel()
                        except asyncio.CancelledError: pass
                        self.clearer = None

                else:
                    await self.bot.wait_for_source(vc)
                    if vc.is_playing():
                        self.pause_player(vc)


def setup(bot):
    bot.add_cog(Player(bot))
