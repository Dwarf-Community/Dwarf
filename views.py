from django.shortcuts import render
from dwarf.serializers import *
from dwarf.models import *
from rest_framework import generics


def estimate_read_time(string):
    read_time = len(string) * 1000  # in milliseconds
    read_time /= 15  # Assuming 15 chars per second
    if read_time < 2400:
        read_time = 2400  # Minimum is 2.4 seconds
    return read_time


class GuildList(generics.ListCreateAPIView):
    """Lists all Guilds"""
    queryset = Guild.objects.all()
    serializer_class = GuildSerializer


class GuildDetail(generics.RetrieveUpdateDestroyAPIView):
    """Allows GET, PUT, DELETE POST operations on each guild"""
    queryset = Guild.objects.all()
    serializer_class = GuildSerializer


class ChannelList(generics.ListCreateAPIView):
     """Lists all Channels"""
    queryset = Channel.objects.all()
    serializer_class = ChannelSerializer


class ChannelDetail(generics.RetrieveUpdateDestroyAPIView):
    """Allows GET, PUT, DELETE POST operations on each channel"""
    queryset = Channel.objects.all()
    serializer_class = ChannelSerializer


class RoleList(generics.ListCreateAPIView):
     """Lists all Roles"""
    queryset = Role.objects.all()
    serializer_class = RoleSerializer


class RoleDetail(generics.RetrieveUpdateDestroyAPIView):
    """Allows GET, PUT, DELETE POST operations on each role"""
    queryset = Role.objects.all()
    serializer_class = RoleSerializer


class MemberList(generics.ListCreateAPIView):
     """Lists all Members"""
    queryset = Member.objects.all()
    serializer_class = MemberSerializer


class MemberDetail(generics.RetrieveUpdateDestroyAPIView):
    """Allows GET, PUT, DELETE POST operations on each member"""
    queryset = Member.objects.all()
    serializer_class = MemberSerializer


class MessageList(generics.ListCreateAPIView):
     """Lists all Messages"""
    queryset = Message.objects.all()
    serializer_class = MessageSerializer


class MessageDetail(generics.RetrieveUpdateDestroyAPIView):
    """Allows GET, PUT, DELETE POST operations on each message"""
    queryset = Message.objects.all()
    serializer_class = MessageSerializer


class StringList(generics.ListCreateAPIView):
     """Lists all Strings"""
    queryset = String.objects.all()
    serializer_class = StringSerializer


class StringDetail(generics.RetrieveUpdateDestroyAPIView):
    """Allows GET, PUT, DELETE POST operations on each string"""
    queryset = String.objects.all()
    serializer_class = StringSerializer


class LogList(generics.ListCreateAPIView):
     """Lists all Logs"""
    queryset = Log.objects.all()
    serializer_class = LogSerializer


class LogDetail(generics.RetrieveUpdateDestroyAPIView):
    """Allows GET, PUT, DELETE and POST operations on each log"""
    queryset = Log.objects.all()
    serializer_class = LogSerializer

    