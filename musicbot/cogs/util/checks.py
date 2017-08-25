from discord.ext import commands

class NotInVCError(BaseException): pass

#general predicates
async def owner_pred(ctx: commands.Context) -> bool:
    appinfo = await ctx.bot.application_info()
    return appinfo.owner == ctx.author

async def mod_pred(ctx: commands.Context) -> bool:
    perms = ctx.channel.permissions_for(ctx.author)
    return perms.manage_channels

#checks

#proper perms/user
def manage_channels():
    async def predicate(ctx: commands.Context) -> bool:
        return await mod_pred(ctx) or await owner_pred(ctx)
    return commands.check(predicate)

def event_team_or_higher():
    async def predicate(ctx: commands.Context) -> bool:
        for role in ctx.author.roles:
            if role.id in [344352523466833930, 290757144863703040]:
                return True
        perms = ctx.channel.permissions_for(ctx.author)
        return perms.manage_channels or await owner_pred(ctx)
    return commands.check(predicate)

def bot_owner():
    async def predicate(ctx: commands.Context) -> bool:
        return await owner_pred(ctx)
    return commands.check(predicate)

#proper location
def in_vc():
    async def predicate(ctx: commands.Context) -> bool:
        if ctx.guild.id not in ctx.bot.voice:
            raise commands.CheckFailure('bot_in_vc')
            return False

        vc = ctx.bot.voice[ctx.guild.id]
        if ctx.author not in vc.channel.members:
            raise commands.CheckFailure('user_in_vc')
            return False

        return True
    return commands.check(predicate)

def not_dm():
    async def predicate(ctx: commands.Context) -> bool:
        return ctx.guild != None
    return commands.check(predicate)
