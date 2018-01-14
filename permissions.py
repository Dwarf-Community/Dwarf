"""Permission system

The bot owner will always have permission to issue all commands.
Server owners can specify roles that have more permissions than others.
They can also specify channels in which specific commands are disallowed.
And they can make the bot fully ignore specific channels.
"""
#TODO


from dwarf.models import User, Role, Channel, Member
from dwarf.core.api import CoreAPI
from rest_framework.permissions import BasePermission, SAFE_METHODS
from discord.ext import commands


core = CoreAPI()


def is_owner_check(ctx):
    return ctx.message.author.id == core.get_owner_id()


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


#REST Framework Permissions


class GuildPermissions(BasePermission):


    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True        
        elif request.user.is_staff and view.action == 'list':
            return True
        elif request.user.is_authenticated and view.action == 'retrieve':
            return True
        else:
            return False


    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser or request.user.is_staff or Member.objects.exists(user=request.user, guild=obj.id):
            return True
        else:
            return False
            

class StringPermissions(BasePermission):
    

    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True        
        elif request.user.is_staff and view.action == 'destroy':
            return True
        elif request.user.is_authenticated and view.action == 'create':
            return True
        elif view.action == 'list' or view.action == 'retrieve':
            return True
        else:
            return False


class MessagePermissions(BasePermission):


    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True        
        elif request.user.is_staff and view.action == 'list' or view.action == 'retrieve':
            return True
        else:
            return False


class UserPermissions(BasePermission):


    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        elif request.user.is_staff and view.action == 'list' or view.action == 'retrieve':
            return True
        else:
            return False


class MemberPermissions(BasePermission):


    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        elif request.user.is_staff and view.action == 'list':
            return True
        elif request.user.is_authenticated and view.action == 'retrieve':
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser or request.user.is_staff or Member.objects.exists(guild=obj.guild.id, user=request.user.id):
            return True
        else:
            return False


class RolePermissions(BasePermission):


    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        elif request.user.is_staff and view.action == 'list':
            return True
        elif request.user.is_authenticated and view.action == 'retrieve':
            return True
        else:
            return False


    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser or request.user.is_staff or Member.objects.exists(user=request.user, guild=obj.guild.id):    
            return True
        else:
            return False


class ChannelPermissions(BasePermission):

    
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        elif request.user.is_staff and view.action == 'list':
            return True
        else:
            return False


    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser or request.user.is_staff:    
            return True
