from django.db import models
from django.contrib.auth.models import AbstractBaseUser

from dwarf.api import CoreAPI

import importlib


class User(AbstractBaseUser):
    id = models.BigIntegerField(primary_key=True)
    # is_self = models.BooleanField(default=False)
    is_owner = models.BooleanField(default=False, db_index=True)
    is_admin = models.BooleanField(default=False, db_index=True)
    message_count = models.IntegerField(default=0)
    command_count = models.IntegerField(default=0)

    USERNAME_FIELD = 'id'
    REQUIRED_FIELDS = []

    def get_full_name(self):
        return str(self.id)

    def get_short_name(self):
        return str(self.id)[0:7]


class Guild(models.Model):
    # I can't normalize this any further :/
    id = models.BigIntegerField(primary_key=True)
    name = models.CharField(max_length=64, unique=True, db_index=True)
    register_time = models.TimeField('date registered', auto_now=True)
    invite_link = models.CharField(max_length=64, unique=True, db_index=True)
    url = models.CharField(max_length=256, unique=True)
    is_removed = models.BooleanField(default=False)


class Channel(models.Model):
    id = models.BigIntegerField(primary_key=True)
    guild = models.ForeignKey(Guild, on_delete=models.CASCADE)
    # TODO is_stats_channel = models.BooleanField(default=False)


class Role(models.Model):
    id = models.BigIntegerField(primary_key=True)
    guild = models.ForeignKey(Guild, on_delete=models.CASCADE)


class Member(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    guild = models.ForeignKey(Guild, on_delete=models.CASCADE)


class Message(models.Model):
    id = models.BigIntegerField(primary_key=True)
    user = models.ForeignKey(User, db_index=True, on_delete=models.CASCADE)
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
    content = models.TextField(max_length=2048)


class String(models.Model):
    name = models.CharField(primary_key=True, max_length=64)
    en_us = models.CharField(max_length=2048)


class Log(models.Model):
    time = models.TimeField('timestamp')
    level = models.CharField(max_length=64)
    type = models.CharField(max_length=64)
    message = models.CharField(max_length=2048)


# importing models introduced by extensions
extensions = CoreAPI.get_extensions()
for extension in extensions:
    importlib.import_module(extension, '.')
