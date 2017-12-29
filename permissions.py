"""Permission system

The bot owner will always have permission to issue all commands.
Server owners can specify roles that have more permissions than others.
They can also specify channels in which specific commands are disallowed.
And they can make the bot fully ignore specific channels.
"""
# TODO completely remake this and move most of it to the bot module


from dwarf.models import User
from dwarf.core.controller import CoreController

from discord.ext import commands


core = CoreController()


async def is_admin_check(ctx):
    is_admin = False
    author = ctx.message.author
    admins = User.objects.all(is_admin=True)
    for i in range(len(admins)):
        if author.id == admins[i].id:
            is_admin = True
    return is_admin


def admin():
    return commands.check(is_admin_check)


def has_permissions(ctx, perms):
    ch = ctx.message.channel
    author = ctx.message.author
    resolved = ch.permissions_for(author)
    return all(getattr(resolved, name, None) == value for name, value in perms.items())


def guildowner():
    def predicate(ctx):
        if ctx.message.guild is None:
            return False

        if ctx.message.author.id == ctx.message.guild.owner.id:
            return True
        return False
    return commands.check(predicate)
