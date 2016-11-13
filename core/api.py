from django.contrib.auth import get_user_model
import discord

from dwarf.api import Cache
from dwarf.models import Guild, Channel, Role, Member, Message
from dwarf.utils import set_digits


class PrefixNotFound(Exception):
    pass


class PrefixAlreadyExists(Exception):
    pass


class _ManagementAPI:

    def __init__(self):
        self.cache = Cache()

    def get_number_of_prefixes(self):
        return self.cache.get(key='number_of_prefixes', default=0)

    def _set_number_of_prefixes(self, number):
        return self.cache.set(key='number_of_prefixes', value=number, timeout=None)

    def add_prefix(self, prefix):
        prefixes = self.get_prefixes()
        if prefix in prefixes:
            raise PrefixAlreadyExists
        number_of_prefixes = self.get_number_of_prefixes()
        self.cache.set(key='prefix_' + set_digits(number_of_prefixes + 1, 6), value=prefix, timeout=None)
        number_of_prefixes += 1
        self._set_number_of_prefixes(number_of_prefixes)

    def remove_prefix(self, prefix):
        number_of_prefixes = self.get_number_of_prefixes()
        prefixes = self.get_prefixes()
        prefix_nr = 0
        for i in range(number_of_prefixes - 1):
            if prefixes[i] == prefix:
                prefix_nr = i + 1
                break
        if prefix_nr == 0:
            raise PrefixNotFound
        if prefix_nr != number_of_prefixes:
            self.cache.set(key='prefix_' + set_digits(prefix_nr, 6),
                         value=self.cache.get(key='prefix_' + set_digits(number_of_prefixes, 6)),
                         timeout=None)
        self.cache.delete(key='prefix_' + set_digits(number_of_prefixes, 6))
        number_of_prefixes -= 1
        self._set_number_of_prefixes(number_of_prefixes)

    def get_default_prefix(self):
        default_prefix_id = self.cache.get(key='default_prefix')
        return self.cache.get(key='prefix_' + set_digits(default_prefix_id, 6))

    def set_default_prefix(self, prefix):
        prefixes = self.get_prefixes()
        found_prefix = False
        for i in range(self.get_number_of_prefixes()):
            if prefixes[i] == prefix:
                self.cache.set(key='default_prefix', value=i, timeout=None)
                found_prefix = True
        if not found_prefix:
            raise PrefixNotFound

    def get_prefixes(self):
        number_of_prefixes = self.get_number_of_prefixes()
        prefix_keys = []
        for i in range(number_of_prefixes):
            prefix_keys.append('prefix_' + set_digits(i + 1, 6))
        return self.cache.get_many(keys=prefix_keys)

    def get_owner_id(self):
        return self.cache.get(key='owner')

    def _set_owner(self, user_id):
        self.cache.set(key='owner', value=user_id, timeout=None)

    def get_repository(self):
        return self.cache.get('repository')

    def set_repository(self, repository):
        self.cache.set('repository', repository)

    def get_official_invite(self):
        return self.cache.get('official_invite')

    def set_official_invite(self, invite_link):
        self.cache.set('official_invite', invite_link)

    def get_user(self, user):
        """Retrieves a User from the database using a User object, Member object or the User's id."""

        if isinstance(user, discord.User) or isinstance(user, discord.Member):
            return get_user_model().objects.get_or_create(id=user.id)
        else:
            return get_user_model().objects.get_or_create(id=user)

    def get_guild(self, guild):
        """Retrieves a Guild from the database using a Server object or the Guild's id."""

        if isinstance(guild, discord.Server):
            return Guild.objects.get(id=guild.id)
        else:
            return Guild.objects.get(id=guild)

    def new_guild(self, guild):
        if isinstance(guild, discord.Server):
            guild_object = Guild(id=guild.id)
            guild_object.save()
        else:
            guild_object = Guild(id=guild)
            guild_object.save()
        return guild_object

    def get_channel(self, channel):
        """Retrieves a Channel from the database using a Channel object or the Channel's id."""

        if isinstance(channel, discord.Channel):
            return Channel.objects.get(id=channel.id)
        else:
            return Channel.objects.get(id=channel)

    def new_channel(self, channel, guild=None):
        if isinstance(channel, discord.Channel):
            channel_object = Channel(id=channel.id)
            channel_object.save()
        else:
            if guild is None:
                raise ValueError("Either a Channel object or both Channel id and Guild id must be given as argument(s)")
            channel_object = Channel(id=channel)
            channel_object.save()
        return channel_object

    def get_role(self, role):
        """Retrieves a Role from the database using a Role object or the Role's id."""

        if isinstance(role, discord.Role):
            return Role.objects.get(id=role.id)
        else:
            return Role.objects.get(id=role)

    def new_role(self, role, guild=None):
        if isinstance(role, discord.Role):
            role_object = Role(id=role.id)
            role_object.save()
        else:
            if guild is None:
                raise ValueError("Either a Role object or both Role id and Guild id must be given as argument(s)")
            role_object = Channel(id=role)
            role_object.save()
        return role_object

    def get_member(self, member, user=None, guild=None):
        """Retrieves a Channel from the database using a Channel object or the Channel's id."""

        if isinstance(member, discord.Member):
            return Member.objects.get(id=member.id)
        else:
            return Member.objects.get(id=member)

    def new_member(self, member, user=None, guild=None):
        if isinstance(member, discord.Member):
            member_object = Member(user=member.id, guild=member.server)
            member_object.save()
        else:
            if user is None or guild is None:
                raise ValueError("Either a Member object or both User id and Guild id must be given as argument(s)")
            member_object = Channel(id=member)
            member_object.save()
        return member_object

    def get_message(self, message):
        """Retrieves a Message from the database using a Channel object or the Message's id."""

        if isinstance(message, discord.Message):
            return Channel.objects.get(id=message.id)
        else:
            return Channel.objects.get(id=message)

    def new_message(self, message):
        if isinstance(message, discord.Message):
            message_object = Message(id=message.id)
            message_object.save()
            return message_object
        else:
            raise ValueError("A Message object must be given as an argument")


ManagementAPI = _ManagementAPI()
