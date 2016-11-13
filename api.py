from django.core.management import call_command
from redis_cache import RedisCache
from . import app_name, version
from .utils import set_digits


redis = RedisCache('127.0.0.1:6379', {'PASSWORD': 'S3kr1t!', 'DB': 2})


class Cache:

    def __init__(self, extension=""):
        self.backend = redis
        self.extension = extension

    def get(self, key, default=None):
        if not self.extension:
            return self.backend.get(key='_'.join([app_name, key]), default=default)
        return self.backend.get(key='_'.join([app_name, self.extension, key]), default=default)

    def set(self, key, value, timeout=None):
        if not self.extension:
            return self.backend.set(key='_'.join([app_name, key]), value=value, timeout=timeout)
        return self.backend.set(key='_'.join([app_name, self.extension, key]), value=value, timeout=timeout)

    def get_many(self, keys):
        actual_keys = []
        if not self.extension:
            for key in keys:
                actual_keys.append('_'.join([app_name, key]))
        else:
            for key in keys:
                actual_keys.append('_'.join([app_name, self.extension, key]))
        return list(self.backend.get_many(keys=actual_keys).values())

    def set_many(self, keys, values, timeout=None):
        actual_keys = []
        if not self.extension:
            for key in keys:
                actual_keys.append('_'.join([app_name, key]))
        else:
            for key in keys:
                actual_keys.append('_'.join([app_name, self.extension, key]))
        return list(self.backend.set_many(data=dict(zip(actual_keys, values)), timeout=timeout).values())

    def delete(self, key):
        if not self.extension:
            return self.backend.get(key='_'.join([app_name, key]))
        return self.backend.get(key='_'.join([app_name, self.extension, key]))


class _CoreAPI:
    """Internal API that makes data available that needs to be loaded before Django loads any models.
    It also makes rebooting available to the bot and the web interface."""

    def __init__(self):
        self.cache = Cache()

    def get_token(self):
        self.cache.get('token')

    def set_token(self, token):
        self.cache.set('token', token)

    def get_number_of_extensions(self):
        return self.cache.get(key='number_of_extensions', default=0)

    def _set_number_of_extensions(self, number):
        self.cache.set(key='number_of_extensions', value=number)

    def install_extension(self, extension_name):
        number_of_extensions = self.get_number_of_extensions()
        key = 'extension_' + set_digits(number_of_extensions + 1, 6)
        self.cache.set(key=key, value=extension_name)
        number_of_extensions += 1
        self.cache.set(key='number_of_extensions', value=number_of_extensions)

    # TODO def _uninstall_extension(self, extension):

    def get_extensions(self):
        number_of_extensions = self.get_number_of_extensions()
        extension_keys = []
        for i in range(number_of_extensions):
            extension_keys.append('extension_' + set_digits(i, 6))
        extensions = self.cache.get_many(keys=extension_keys)
        return extensions

    def is_installed(self, extension_name):
        for i in range(self.get_number_of_extensions()):
            if self.cache.get(key='extension_' + set_digits(i, 6), default='') == extension_name:
                return True
        return False

    def get_uri(self, extension):
        return self.cache.get('uri', extension)

    def set_uri(self, extension, uri):
        return self.cache.set('uri', uri, extension)

    def get_version(self):
        return version

    def get_app_name(self):
        return app_name


CoreAPI = _CoreAPI()
