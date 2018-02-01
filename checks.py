from discord.ext import commands

from core.controllers import CoreController

core = CoreController()


@commands.check
async def is_admin(ctx):
    return core.get_user(ctx.message.author).is_staff


@commands.check
def is_guild_owner(ctx):
    return (ctx.message.guild is not None and
            ctx.message.author.id == ctx.message.guild.owner.id)
