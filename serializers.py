from rest_framework import serializers
from dwarf.models import *

class GuildSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guild
        fields = ('__all__')

class ChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Channel
        fields = ('__all__')

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ('__all__')

class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = ('__all__')

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ('__all__')

class StringSerializer(serializers.ModelSerializer):
    class Meta:
        model = String
        fields = ('__all__')

class LogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Log
        fields = ('__all__')
