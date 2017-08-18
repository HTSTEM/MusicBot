from discord.ext import commands

class NotInVCError(BaseException): pass

def manage_channels():
    async def predicate(ctx: commands.Context) -> bool:
        perms = ctx.channel.permissions_for(ctx.author)
        return perms.manage_channels
    return commands.check(predicate)

def event_team_or_higher():
    async def predicate(ctx: commands.Context) -> bool:
        for role in ctx.author.roles:
            if role.id in [344352523466833930, 290757144863703040]:
                return True
        perms = ctx.channel.permissions_for(ctx.author)
        return perms.manage_channels
    return commands.check(predicate)
    

def bot_owner():
    async def predicate(ctx: commands.Context) -> bool:
        appinfo = await ctx.bot.application_info()
        return appinfo.owner == ctx.author
    return commands.check(predicate)

def in_vc():
    async def predicate(ctx: commands.Context) -> bool:
        if ctx.guild.id not in ctx.bot.voice:
            await ctx.send('I\'m not in a voice channel on this server.')
            raise commands.CheckFailure('in_vc')
            return False
            
        vc = ctx.bot.voice[ctx.guild.id]
        if ctx.author not in vc.channel.members:
            await ctx.send('You must be in `{}` to use that command.'.format(vc.channel.name))
            raise commands.CheckFailure('in_vc')
            return False
            
        return True
    return commands.check(predicate)

