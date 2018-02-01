from rest_framework import viewsets

from .models import Guild, Channel, Role, Member, Message, String
from .permissions import (GuildPermissions, ChannelPermissions, RolePermissions,
                          MemberPermissions, MessagePermissions, StringPermissions)
from .serializers import (GuildSerializer, ChannelSerializer, RoleSerializer,
                          MemberSerializer, MessageSerializer, StringSerializer)


class GuildViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list`, `create`, `retrieve`,
    `update` and `destroy` actions for the guild model.
    """
    queryset = Guild.objects.all()
    serializer_class = GuildSerializer
    permission_classes = (GuildPermissions,)


class ChannelViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list`, `create`, `retrieve`,
    `update` and `destroy` actions for the channel model.
    """
    queryset = Channel.objects.all()
    serializer_class = ChannelSerializer
    permission_classes = (ChannelPermissions,)


class RoleViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list`, `create`, `retrieve`,
    `update` and `destroy` actions for the role model.
    """
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = (RolePermissions,)


class MemberViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list`, `create`, `retrieve`,
    `update` and `destroy` actions for the member model.
    """
    queryset = Member.objects.all()
    serializer_class = MemberSerializer
    permission_classes = (MemberPermissions,)


class MessageViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list`, `create`, `retrieve`,
    `update` and `destroy` actions for the message model.
    """
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = (MessagePermissions,)


class StringViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list`, `create`, `retrieve`,
    `update` and `destroy` actions for the string model.
    """
    queryset = String.objects.all()
    serializer_class = StringSerializer
    permission_classes = (StringPermissions,)
