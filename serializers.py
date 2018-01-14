from rest_framework import serializers
from dwarf.models import Guild, Channel, Role, Member, Message, String, Log


class GuildSerializer(serializers.ModelSerializer):
    """Serializes the Guild model"""
    class Meta:
        model = Guild
        fields = ('__all__')


class ChannelSerializer(serializers.ModelSerializer):
    """Serializes the Channel model"""
    class Meta:
        model = Channel
        fields = ('__all__')


class RoleSerializer(serializers.ModelSerializer):
    """Serializes the Role model"""
    class Meta:
        model = Role
        fields = ('__all__')


class MemberSerializer(serializers.ModelSerializer):
    """Serializes the Member model"""
    class Meta:
        model = Member
        fields = ('__all__')


class MessageSerializer(serializers.ModelSerializer):
    """Serializes the Message model"""
    class Meta:
        model = Message
        fields = ('__all__')


class StringSerializer(serializers.ModelSerializer):
    """Serializes the String model"""
    class Meta:
        model = String
        fields = ('__all__')

