from discord.ext import commands

class NotInVCError(BaseException): pass

#general predicates
async def owner_pred(ctx: commands.Context, *, throw_error=True) -> bool:
    appinfo = await ctx.bot.application_info()
    return appinfo.owner == ctx.author

async def mod_pred(ctx: commands.Context, *, throw_error=True) -> bool:
    perms = ctx.channel.permissions_for(ctx.author)
    return perms.manage_channels

#checks
def manage_channels():
    async def predicate(ctx: commands.Context, *, throw_error=True) -> bool:
        return await mod_pred(ctx, throw_error=throw_error)
    return commands.check(predicate)

def event_team_or_higher():
    async def predicate(ctx: commands.Context, *, throw_error=True) -> bool:
        for role in ctx.author.roles:
            if role.id in [344352523466833930, 290757144863703040]:
                return True
        perms = ctx.channel.permissions_for(ctx.author)
        return perms.manage_channels
    return commands.check(predicate)

def bot_owner():
    async def predicate(ctx: commands.Context, *, throw_error=True) -> bool:
        return await owner_pred(ctx, throw_error=throw_error)
    return commands.check(predicate)

def owner_or_mod():
    async def predicate(ctx: commands.Context, *, throw_error=True) -> bool:
        owner = await owner_pred(ctx, throw_error=throw_error)
        mod = await mod_pred(ctx, throw_error=throw_error)
        return owner or mod
    return commands.check(predicate)

def in_vc():
    async def predicate(ctx: commands.Context, *, throw_error=True) -> bool:
        if ctx.guild.id not in ctx.bot.voice:
            if throw_error:
                await ctx.send('I\'m not in a voice channel on this server.')
                raise commands.CheckFailure('in_vc')
            return False

        vc = ctx.bot.voice[ctx.guild.id]
        if ctx.author not in vc.channel.members:
            if throw_error:
                await ctx.send('You must be in `{}` to use that command.'.format(vc.channel.name))
                raise commands.CheckFailure('in_vc')
            return False

        return True
    return commands.check(predicate)

