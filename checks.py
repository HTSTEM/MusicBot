from discord.ext import commands

def manage_channels():
    async def predicate(ctx: commands.Context) -> bool:
        perms = ctx.channel.permissions_for(ctx.author)
        return perms.manage_channels
    return commands.check(predicate)
