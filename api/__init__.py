# from django.core.management import call_command
from redis_cache import RedisCache
from dwarf import version


CacheAPI = RedisCache('127.0.0.1:6379', {'PASSWORD': 'S3kr1t!', 'DB': 2})


def set_digits(integer, number_of_digits):
    return '0' * (number_of_digits - len(str(integer))) + str(integer)


class _CoreAPI:
    """Internal API that makes data available that needs to be loaded before Django loads any models.
    It also makes rebooting available to the bot and the web interface."""

    def get_number_of_extensions(self):
        return CacheAPI.get(key='dwarf_number_of_extensions', default=0)

    def _set_number_of_extensions(self, number):
        CacheAPI.set(key='dwarf_number_of_extensions', value=number, timeout=None)

    def _install_extension(self, extension_name):
        number_of_extensions = self.get_number_of_extensions()
        key = 'dwarf_extension_' + set_digits(number_of_extensions + 1, 6)
        CacheAPI.add(key=key, value=extension_name)
        number_of_extensions += 1
        CacheAPI.set(key='dwarf_number_of_extensions', value=number_of_extensions, timeout=None)

    # TODO def _uninstall_extension(self, extension):

    def get_extensions(self):
        number_of_extensions = self.get_number_of_extensions()
        extension_keys = []
        for i in range(number_of_extensions):
            extension_keys.append('dwarf_extension_' + set_digits(i, 6))
        extensions = CacheAPI.get_many(keys=extension_keys).values()
        return extensions

    def is_installed(self, extension_name):
        for i in range(self.get_number_of_extensions()):
            if CacheAPI.get(key='dwarf_extension_' + set_digits(i, 6), default='') == extension_name:
                return True
        return False

    def get_version(self):
        return version


CoreAPI = _CoreAPI()
