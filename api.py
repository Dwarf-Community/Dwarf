from django.core import management
from django.conf import settings
from redis_cache import RedisCache
import aioredis

import dwarf.extensions
from . import version
 
import subprocess
import shutil
import os
import stat
import importlib
import pip
import asyncio


class ExtensionAlreadyInstalled(Exception):
    pass


class ExtensionNotInIndex(Exception):
    pass


class ExtensionNotFound(Exception):
    pass


class CacheAPI:
    """Represents a connection to the cache backend.
    This class is used to store keys into and retrieve keys
    from the cache.

    Parameters
    ----------
    extension : Optional[str]
        If specified, the :class:`CacheAPI` stores data in that
        extension's own storage area. The actual keys will be
        ``extension + '_' + key``; similar applies for channels when
        using :meth:`publish` or :meth:`subscribe`.
    bot
        The bot used to dispatch subscription events.

    Attributes
    -----------
    backend
        The cache backend the :class:`CacheAPI` connects to.
    extension : Optional[str]
        If specified, the :class:`CacheAPI` stores data in that
        extension's own storage area.
    bot
        The bot used to dispatch subscription events.
    """
    
    def __init__(self, extension='', bot=None, loop=None):
        self.config = settings.DWARF_CACHE_BACKEND['redis']
        self.backend = RedisCache('{}:{}'.format(self.config['HOST'], self.config['PORT']),
                                  {'db': self.config['DB'], 'password': self.config['PASSWORD']})
        self.extension = extension
        self.bot = bot
        if self.bot is not None and loop is None:
            self.loop = bot.loop
        else:
            self.loop = loop
    
    async def get_async_redis(self, loop=None):
        """Creates an asynchronous Redis connection.
        
        Parameters
        ----------
        loop = Optional[asyncio.AbstractEventLoop]
            The loop used for the asynchronous Redis connection.
        """
        
        if self.loop is not None and loop is None:
            loop = self.loop
        return await aioredis.create_redis(
            'redis://{}:{}'.format(self.config['HOST'], self.config['PORT']),
            db=self.config['DB'], password=self.config['PASSWORD'], loop=loop)
    
    def get(self, key, default=None):
        """Retrieves a key's value from the cache.
        
        Parameters
        ----------
        key : str
            The key to retrieve from the cache.
        default : Optional
            The value to return if the key wasn't found in the database.
        """
        
        if not self.extension:
            return self.backend.get(key=key, default=default)
        else:
            key = self.extension + '_' + key
            return self.backend.get(key=key, default=default)
    
    def set(self, key, value, timeout=None):
        """Sets a key in the cache.
        
        Parameters
        ----------
        key : str
            The key to set in the cache.
        value
            The value to assign to the key.
        timeout : Optional[int]
            After this amount of time (in seconds), the key will be deleted.
        """
        
        if self.extension:
            key = self.extension + '_' + key
        return self.backend.set(key=key, value=value, timeout=timeout)
    
    def get_many(self, keys):
        """Retrieves keys from the cache and returns them with their values as a dict.
        
        Parameters
        ----------
        keys : iter of str
            The keys to retrieve from the cache.
        """
        
        if self.extension:
            keys = [self.extension + '_' + key for key in keys]
        return self.backend.get_many(keys=keys)
    
    def set_many(self, data, timeout=None):
        """Sets an iterable of keys in the cache.
        If a key wasn't found, it inserts None into the list of values instead.
        
        Parameters
        ----------
        data : dict
            A dict consisting of key-value pairs.
        timeout : Optional[int]
            After this amount of time (in seconds), all keys in `data` will be deleted.
        """
        
        if self.extension:
            for key in data:
                value = data.pop(key)
                data[self.extension + '_' + key] = value
        return self.backend.set_many(data=data, timeout=timeout)
    
    def delete(self, key):
        """Deletes a key from the cache.
        
        Parameters
        ----------
        key : str
            The key to delete from the cache.
        """
        
        if self.extension:
            key = self.extension + '_' + key
        return self.backend.delete(key=key)
    
    async def subscribe(self, channel, limit=None):
        """Subscribes to a Redis Pub/Sub channel.
        When a message is received on the channel, `self.bot` is used to
        dispatch an event called `channel` + '_message' passing the message as a parameter.
        All cogs can implement a coroutine method called
        'on_' + `channel` + '_message' that will be executed when
        a message is sent to the `channel`.
        
        Parameters
        ----------
        channel : str
            The name of the Redis Pub/Sub channel to subscribe to.
            The internal channel name will be `'channel:' + channel`.
        limit : Optional[int]
            The maximum number of times messages published to the channel will be read.
        """
        
        if limit is not None:
            if not isinstance(limit, int):
                raise TypeError("limit must be of type int")
            if not limit > 0:
                raise ValueError("limit must be greater than 0")
        
        redis = await self.get_async_redis()
        channels = await redis.subscribe('channel:' + channel)
        actual_channel = channels[0]
        try:
            while (await actual_channel.wait_message()):
                message = await actual_channel.get(encoding='utf-8')
                self.bot.dispatch(channel + '_message', message)
                if limit == 1:
                    break
                else:
                    limit -= 1
                
            await redis.unsubscribe(actual_channel)
            redis.close()
            return
        except asyncio.CancelledError:
            await redis.unsubscribe(actual_channel)
            redis.close()
            return
    
    async def publish(self, channel, message=1):
        """Publishes a message to a Redis Pub/Sub channel.
        
        Parameters
        ----------
        channel : str
            The name of the channel to publish to.
            The internal channel name will be `'channel:' + channel`.
        message : Optional
            The message to publish. Defaults to 1.
        """
        
        channel = 'channel:' + channel
        redis = await self.get_async_redis()
        await redis.publish(channel, message)
        redis.close()
        return


class BaseAPI:
    """Internal API that manages extensions and makes data available that
    needs to be loaded before Django loads any models.
    It also makes rebooting available to the bot and the web interface.
    
    Parameters
    ----------
    bot
        The bot used for specific methods.
    
    Attributes
    ----------
    cache : :class:`CacheAPI`
        The cache backend connection of the API.
    bot
        The bot used for specific methods.
    """
    
    def __init__(self, bot=None):
        self.cache = CacheAPI(bot=bot)
        self.bot = bot
    
    def get_token(self):
        """Retrieves the bot's token."""
        return self.cache.get('token')
    
    def set_token(self, token):
        """Sets the bot's token.
        
        Parameters
        ----------
        token : str
            The bot's new token.
        """
        
        self.cache.set('token', token)
    
    def delete_token(self):
        self.cache.delete('token')

    def enable_restarting(self):
        """Makes Dwarf restart whenever it is terminated until `disable_restarting` is called."""
        
        return self.cache.set('is_supposed_to_be_running', True)
    
    def disable_restarting(self):
        """Prevents Dwarf from restarting for the rest of the current session."""
        
        return self.cache.set('is_supposed_to_be_running', False)
    
    def restarting_enabled(self):
        """Checks if Dwarf should be restarted when terminated."""
        
        return self.cache.get('is_supposed_to_be_running', False)
    
    def install_extension(self, extension, repository=None):
        """Installs an extension via the Dwarf Extension Index or directly from a repository.
        
        Parameters
        ----------
        extension : str
            The name of the extension that should be installed.
        repository : Optional[str]
            The Git repository URL of the extension.
        """
        
        extensions = self.get_extensions()
        if extension in extensions:
            raise ExtensionAlreadyInstalled(extension)
        self.download_extension(extension, repository)
        module_obj = importlib.import_module('dwarf.' + extension)
        # libraries and packages the extension requires
        requirements = module_obj.requirements if hasattr(module_obj, 'requirements') else []
        # other extensions the extension requires
        dependencies = module_obj.dependencies if hasattr(module_obj, 'dependencies') else []
        
        failed_to_import = {
            'packages': [],
            'extensions': [],
        }
        
        for requirement in requirements:
            try:
                importlib.import_module(requirement)
            except ImportError:
                failed_to_import['packages'].append(requirement)
        
        for dependency in dependencies:
            try:
                importlib.import_module(dependency)
            except ImportError:
                failed_to_import['extensions'].append(dependency)
        
        if failed_to_import['packages'] or failed_to_import['extensions']:
            self.delete_extension(extension)
            self.unregister_extension(extension)
            return failed_to_import
        
        self.sync_database()
        self.register_extension(extension)
        self.set_dependencies(dependencies, extension)
    
    def update_extension(self, extension):
        """Updates an extension via the Dwarf Extension Index.
        
        Parameters
        ----------
        extension : str
            The name of the extension that should be updated.
        """
        
        extensions = self.get_extensions()
        if extension not in extensions:
            raise ExtensionNotFound(extension)
        
        self.download_extension_update(extension)
        
        module_obj = importlib.import_module('dwarf.' + extension)
        # libraries and packages the extension requires
        requirements = module_obj.requirements if hasattr(module_obj, 'requirements') else []
        # other extensions the extension requires
        dependencies = module_obj.dependencies if hasattr(module_obj, 'dependencies') else []
        
        failed_to_import = {
            'packages': [],
            'extensions': [],
        }
        
        for requirement in requirements:
            try:
                importlib.import_module(requirement)
            except ImportError:
                failed_to_import['packages'].append(requirement)
        
        for dependency in dependencies:
            try:
                importlib.import_module(dependency)
            except ImportError:
                failed_to_import['extensions'].append(dependency)
        
        if failed_to_import['packages'] or failed_to_import['extensions']:
            self.delete_extension(extension)
            self.unregister_extension(extension)
            return failed_to_import
        
        self.sync_database()
        self.register_extension(extension)
        self.set_dependencies(dependencies, extension)
    
    def uninstall_extension(self, extension):
        """Uninstalls an installed extension.
        Raises :exception:`ExtensionNotFound`
        if the extension is not installed.
        
        Parameters
        ----------
        extension : str
            The name of the extension that should be installed.
        """
        
        extensions = self.get_extensions()
        if extension not in extensions:
            raise ExtensionNotFound(extension)
        
        dependencies_tree = self.get_dependencies()
        
        depending = []
        
        for _extension in list(dependencies_tree.keys()):
            for dependency in dependencies_tree[_extension]:
                if dependency is extension:
                    depending.append(_extension)
        
        if depending:
            return depending
        
        self.delete_extension(extension)
        self.sync_database()
        self.unregister_extension(extension)
    
    def get_dependencies(self, extension=None):
        if extension is None:
            return self.cache.get('dependencies', default={})
        else:
            try:
                return self.get_dependencies()[extension]
            except KeyError:
                raise ExtensionNotFound(extension)
    
    def set_dependencies(self, dependencies, extension=None):
        if extension is None:
            return self.cache.set('dependencies', dependencies)
        else:
            _dependencies = self.get_dependencies()
            _dependencies[extension] = dependencies
            return self.set_dependencies(_dependencies)
    
    @staticmethod
    def download_extension(extension, repository=None):
        if repository is None:
            try:
                repository = dwarf.extensions.index[extension]['repository']
            except KeyError:
                raise ExtensionNotInIndex(extension)

        subprocess.run(['git', 'clone', repository, 'dwarf/' + extension])

    @staticmethod
    def download_extension_update(extension):
        try:
            repository = dwarf.extensions.index[extension]['repository']
        except KeyError:
            raise ExtensionNotInIndex(extension)

        subprocess.run(['git', 'pull', repository, 'dwarf/' + extension])

    @staticmethod
    def delete_extension(extension):
        def onerror(func, path, exc_info):
            """``shutil.rmtree`` error handler that helps deleting read-only files on Windows."""
            if not os.access(path, os.W_OK):
                os.chmod(path, stat.S_IWUSR)
                func(path)
            else:
                raise exc_info[0](exc_info[1])
        
        return shutil.rmtree('dwarf/' + extension, onerror=onerror)
    
    def register_extension(self, extension):
        extensions = self.get_extensions()
        if extension not in extensions:
            extensions.append(extension)
            return self.set_extensions(extensions)
        return False
    
    def unregister_extension(self, extension):
        extensions = self.get_extensions()
        if extension in extensions:
            extensions.remove(extension)
            return self.set_extensions(extensions)
        return False
    
    def get_extensions(self):
        """Retrieves the names of all installed extensions and
        returns them as a list of `str`s.
        """
        
        return self.cache.get('extensions', default=[])
    
    def set_extensions(self, extensions):
        """Sets the list of the installed extensions.
        
        Parameters
        ----------
        extensions : iter of str
            The names of the extensions to set as installed.
        """
        
        return self.cache.set('extensions', extensions)
    
    @staticmethod
    def sync_database():
        management.call_command('makemigrations', 'dwarf')
        management.call_command('migrate', 'dwarf')
    
    @staticmethod
    def install_package(package):
        """Installs a package from PyPI.
        
        Parameters
        ----------
        package : str
            The name of the package to install.
        """
        
        return pip.main(['install', '--upgrade', package])
    
    @staticmethod
    def get_dwarf_version():
        """Returns Dwarf's version."""
        
        return version
