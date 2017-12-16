from django.shortcuts import render
from dwarf.serializers import *
from dwarf.models import *
from dwarf.permissions import IsAdminThenAllPerms
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework import viewsets


def estimate_read_time(string):
    read_time = len(string) * 1000  # in milliseconds
    read_time /= 15  # Assuming 15 chars per second 
    if read_time < 2400:
        read_time = 2400  # Minimum is 2.4 seconds
    return read_time


class GuildViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list`, `create`, `retrieve`,
    `update` and `destroy` actions for the guild model.
    """
    queryset = Guild.objects.all()
    serializer_class = GuildSerializer
    permission_classes = ()


class ChannelViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list`, `create`, `retrieve`,
    `update` and `destroy` actions for the channel model.
    """
    queryset = Channel.objects.all()
    serializer_class = ChannelSerializer
    permission_classes = ()


class RoleViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list`, `create`, `retrieve`,
    `update` and `destroy` actions for the role model.
    """
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = ()


class MemberViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list`, `create`, `retrieve`,
    `update` and `destroy` actions for the member model.
    """
    queryset = Member.objects.all()
    serializer_class = MemberSerializer
    permission_classes = ()


class MessageViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list`, `create`, `retrieve`,
    `update` and `destroy` actions for the message model.
    """
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = ()


class StringViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list`, `create`, `retrieve`,
    `update` and `destroy` actions for the string model.
    """
    queryset = String.objects.all()
    serializer_class = StringSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,IsAdminThenAllPerms,)


class LogViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list`, `create`, `retrieve`,
    `update` and `destroy` actions for the log model.
    """
    queryset = Log.objects.all()
    serializer_class = LogSerializer
    permission_classes = ()
