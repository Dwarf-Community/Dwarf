"""Permission system

The bot owner will always have permission to issue all commands.
Server owners can specify roles that have more permissions than others.
They can also specify channels in which specific commands are disallowed.
And they can make the bot fully ignore specific channels.
"""
# TODO


from dwarf.models import User, Role, Channel
from dwarf.api.management import ManagementAPI
from discord.ext import commands


def is_owner_check(ctx):
    return ctx.message.author.id == ManagementAPI.get_owner_id()


def owner():
    return commands.check(is_owner_check)


async def is_admin_check(ctx):
    is_admin = False
    author = ctx.message.author
    admins = await User.objects.all(is_admin=True)
    for i in range(len(admins)):
        if author.id == admins[i].id:
            is_admin = True
    return is_admin


def admin():
    return commands.check(is_admin_check)


def has_permissions(ctx, perms):
    if is_owner_check(ctx):
        return True

    ch = ctx.message.channel
    author = ctx.message.author
    resolved = ch.permissions_for(author)
    return all(getattr(resolved, name, None) == value for name, value in perms.items())


def serverowner():
    def predicate(ctx):
        if ctx.message.server is None:
            return False

        if ctx.message.author.id == ctx.message.server.owner.id:
            return True

        # return check_permissions(ctx, perms)
        return False
    return commands.check(predicate)
