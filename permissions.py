"""REST API permissions"""

from rest_framework.permissions import BasePermission

from .models import Member


class GuildPermissions(BasePermission):
    def has_permission(self, request, view):
        return (request.user.is_superuser or
                (request.user.is_staff and view.action == 'list') or
                (request.user.is_authenticated and view.action == 'retrieve'))

    def has_object_permission(self, request, view, obj):
        return (request.user.is_superuser or request.user.is_staff or
                Member.objects.filter(user=request.user, guild=obj).exists())


class StringPermissions(BasePermission):
    def has_permission(self, request, view):
        return (request.user.is_superuser or
                (request.user.is_staff and view.action == 'destroy') or
                (request.user.is_authenticated and view.action == 'create') or
                view.action == 'list' or
                view.action == 'retrieve')


class MessagePermissions(BasePermission):
    def has_permission(self, request, view):
        return (request.user.is_superuser or
                (request.user.is_staff and
                 (view.action == 'list' or view.action == 'retrieve')))


class UserPermissions(BasePermission):
    def has_permission(self, request, view):
        return (request.user.is_superuser or
                (request.user.is_staff and
                 (view.action == 'list' or view.action == 'retrieve')))


class MemberPermissions(BasePermission):
    def has_permission(self, request, view):
        return (request.user.is_superuser or
                (request.user.is_staff and view.action == 'list') or
                (request.user.is_authenticated and view.action == 'retrieve'))

    def has_object_permission(self, request, view, obj):
        return (request.user.is_superuser or
                request.user.is_staff or
                Member.objects.filter(user=request.user, guild=obj.guild).exists())


class RolePermissions(BasePermission):
    def has_permission(self, request, view):
        return (request.user.is_superuser or
                (request.user.is_staff and view.action == 'list') or
                (request.user.is_authenticated and view.action == 'retrieve'))

    def has_object_permission(self, request, view, obj):
        return (request.user.is_superuser or
                request.user.is_staff or
                Member.objects.filter(user=request.user, guild=obj.guild).exists())


class ChannelPermissions(BasePermission):
    def has_permission(self, request, view):
        return (request.user.is_superuser or
                (request.user.is_staff and
                 (view.action == 'list' or view.action == 'retrieve')))

    def has_object_permission(self, request, view, obj):
        return request.user.is_superuser or request.user.is_staff
