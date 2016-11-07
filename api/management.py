from django.contrib.auth import get_user_model
from dwarf.api import set_digits, CacheAPI
from dwarf.models import Guild, Channel, Role, Member, Message


class PrefixNotFound(Exception):
    pass


class PrefixAlreadyExists(Exception):
    pass


class _ManagementAPI:

    def get_number_of_prefixes(self):
        return CacheAPI.get(key='dwarf_number_of_prefixes', default=0)

    def _set_number_of_prefixes(self, number):
        return CacheAPI.set(key='dwarf_number_of_prefixes', value=number, timeout=None)

    def add_prefix(self, prefix):
        prefixes = self.get_prefixes()
        if prefix in prefixes:
            raise PrefixAlreadyExists
        number_of_prefixes = self.get_number_of_prefixes()
        CacheAPI.set(key='dwarf_prefix_' + set_digits(number_of_prefixes + 1, 6), value=prefix, timeout=None)
        self._set_number_of_prefixes(number_of_prefixes + 1)

    def remove_prefix(self, prefix):
        number_of_prefixes = self.get_number_of_prefixes()
        CacheAPI.set(key='dwarf_prefix_' + set_digits(number_of_prefixes, 6), value=prefix, timeout=None)
        self._set_number_of_prefixes(number_of_prefixes - 1)

    def get_default_prefix(self):
        default_prefix_id = CacheAPI.get(key='dwarf_default_prefix')
        return CacheAPI.get(key='dwarf_prefix_' + set_digits(default_prefix_id, 6))

    def set_default_prefix(self, prefix):
        prefixes = self.get_prefixes()
        found_prefix = False
        for i in range(self.get_number_of_prefixes()):
            if prefixes[i] == prefix:
                CacheAPI.set(key='dwarf_default_prefix', value=i, timeout=None)
                found_prefix = True
        if not found_prefix:
            raise PrefixNotFound

    def get_prefixes(self):
        number_of_prefixes = self.get_number_of_prefixes()
        prefix_keys = []
        for i in range(number_of_prefixes):
            prefix_keys.append('dwarf_prefix_' + set_digits(i + 1, 6))
        prefixes = CacheAPI.get_many(keys=prefix_keys).values()
        return prefixes

    def get_owner_id(self):
        return CacheAPI.get(key='dwarf_owner')

    def _set_owner(self, user_id):
        CacheAPI.set(key='dwarf_owner', value=user_id, timeout=None)

    def get_user(self, user_id):
        """Retrieves a User from the database using their id."""

        return get_user_model().objects.get_or_create(id=user_id)

    def guild_is_registered(self, guild_id):
        return bool(Guild.objects.get(id=guild_id).objects.exists())

    def get_guild(self, guild_id):
        """Retrieves a Guild from the database using their id."""

        return Guild.objects.get(id=guild_id)

    def add_guild(self, guild_id):
        Guild.objects.create(id=guild_id)


ManagementAPI = _ManagementAPI()
