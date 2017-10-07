from discord import Member
from discord.ext import commands

class NotInVCError(BaseException): pass

async def permissions_for(ctx):
    bot_perms = ctx.bot.permissions
    member = ctx.author

    user_perms = {
        'categories': {cat.lower() for cat in bot_perms['default']['whitelist']},
        'max_song_length': bot_perms['default']['max_song_length'],
        'max_songs_queued': bot_perms['default']['max_songs_queued'],
        }

    if not isinstance(ctx.author, Member):
        for serv_id in ctx.bot.config['bot_channels'].keys():
            guild = ctx.bot.get_guild(serv_id)
            if guild is not None and guild.get_member(ctx.author.id) is not None:
                member = guild.get_member(ctx.author.id)
                break
        else:
            return user_perms

    def add_perms(perms):
        if 'blacklist' in perms: user_perms['categories'] -= {cat.lower() for cat in perms['blacklist']}
        if 'whitelist' in perms: user_perms['categories'] |= {cat.lower() for cat in perms['whitelist']}
        if 'max_song_length' in perms: user_perms['max_song_length'] = perms['max_song_length']
        if 'max_songs_queued' in perms: user_perms['max_songs_queued'] = perms['max_songs_queued']

    for role in sorted(member.roles):
        if role.id in bot_perms['roles']: add_perms(bot_perms['roles'][role.id])

    if member.id in bot_perms['users']: add_perms(bot_perms['users'][member.id])
    if 'owner' in bot_perms['users'] and await owner_pred(ctx): add_perms(bot_perms['users']['owner'])

    return user_perms

#general predicates
async def owner_pred(ctx: commands.Context) -> bool:
    return await ctx.bot.is_owner(ctx.author)

async def mod_pred(ctx: commands.Context) -> bool:
    perms = ctx.channel.permissions_for(ctx.author)
    return perms.manage_channels


#checks
#proper perms/user

async def can_use(ctx: commands.Context) -> bool:
    perms = await permissions_for(ctx)
    cat = 'misc'
    if hasattr(ctx.command,'category'): cat = ctx.command.category.lower()

    if cat in perms['categories']: return True
    else: return False


# DEPRECATED use permissions.yml
def manage_channels():
    async def predicate(ctx: commands.Context) -> bool:
        return await mod_pred(ctx) or await owner_pred(ctx)
    return commands.check(predicate)
# DEPRECATED use permissions.yml
def event_team_or_higher():
    async def predicate(ctx: commands.Context) -> bool:
        for role in ctx.author.roles:
            if role.id in [344352523466833930, 290757144863703040]:
                return True
        perms = ctx.channel.permissions_for(ctx.author)
        return perms.manage_channels or await owner_pred(ctx)
    return commands.check(predicate)
# DEPRECATED use permissions.yml
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

def command_processed():
    async def predicate(ctx: commands.Context) -> bool:
        if ctx.author.id in ctx.bot.pending:
            raise commands.CheckFailure('request_pending')
        else:
            return True
    return commands.check(predicate)

#probably DEPRECATED in favor of commands.guild_only()
def not_dm():
    async def predicate(ctx: commands.Context) -> bool:
        return ctx.guild != None
    return commands.check(predicate)
