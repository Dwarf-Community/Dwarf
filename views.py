from django.shortcuts import render
from dwarf.models import *
from dwarf.serializers import *
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics

def estimate_read_time(string):
    read_time = len(string) * 1000  # in milliseconds
    read_time /= 15  # Assuming 15 chars per second
    if read_time < 2400:
        read_time = 2400  # Minimum is 2.4 seconds
    return read_time

class GuildList(generics.ListCreateAPIView):
    queryset = Guild.objects.all()
    serializer_class = GuildSerializer
class GuildDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Guild.objects.all()
    serializer_class = GuildSerializer

class ChannelList(generics.ListCreateAPIView):
    queryset = Channel.objects.all()
    serializer_class = ChannelSerializer
class ChannelDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Channel.objects.all()
    serializer_class = ChannelSerializer

class RoleList(generics.ListCreateAPIView):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
class RoleDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer

class MemberList(generics.ListCreateAPIView):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer
class MemberDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer

class MessageList(generics.ListCreateAPIView):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
class MessageDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer

class StringList(generics.ListCreateAPIView):
    queryset = String.objects.all()
    serializer_class = StringSerializer
class StringDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = String.objects.all()
    serializer_class = StringSerializer

class LogList(generics.ListCreateAPIView):
    queryset = Log.objects.all()
    serializer_class = LogSerializer
class LogDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Log.objects.all()
    serializer_class = LogSerializer
    