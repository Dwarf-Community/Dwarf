from discord.ext import commands

from .core.controllers import CoreController

core = CoreController()


def is_admin():
    def predicate(ctx):
        return core.get_user(ctx.message.author).is_staff
    return commands.check(predicate)


def is_guild_owner():
    def predicate(ctx):
        return ((ctx.message.guild is not None and
                 ctx.message.author.id == ctx.message.guild.owner.id) or
                ctx.message.author.id == core.get_owner_id())
    return commands.check(predicate)
