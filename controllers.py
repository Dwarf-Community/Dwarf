import subprocess
import shutil
import os
import stat
import importlib
import pip

from django.core import management

from . import __version__
from .cache import Cache

try:
    import dwarf.extensions
except ImportError:
    raise ImportError("the Dwarf Extension Index could not be found; install it using:\n"
                      "git clone https://github.com/Dwarf-Community/Dwarf-Extensions dwarf/extensions")


class InstallationError(Exception):
    pass


class ExtensionAlreadyInstalled(Exception):
    pass


class ExtensionNotInIndex(Exception):
    pass


class ExtensionNotFound(Exception):
    pass


class BaseController:
    """Internal API that manages extensions and makes data available that
    needs to be loaded before Django loads any models.
    It also makes rebooting available to the bot and the web interface.

    Parameters
    ----------
    bot
        The bot used for specific methods.

    Attributes
    ----------
    cache : :class:`cache.Cache`
        The cache backend connection of the controller.
    bot
        The bot used for specific methods.
    """

    def __init__(self, bot=None):
        self.cache = Cache(bot=bot)
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
        requirements = []
        try:
            with open('dwarf/{}/requirements.txt') as requirements_file:
                requirements = requirements_file.readlines()
        except FileNotFoundError:
            pass
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
        return None

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
        return None

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
        return None

    def get_dependencies(self, extension=None):
        if extension is None:
            return self.cache.get('dependencies', default={})

        try:
            return self.get_dependencies()[extension]
        except KeyError:
            raise ExtensionNotFound(extension)

    def set_dependencies(self, dependencies, extension=None):
        if extension is None:
            return self.cache.set('dependencies', dependencies)

        _dependencies = self.get_dependencies()
        _dependencies[extension] = dependencies
        return self.set_dependencies(_dependencies)

    def download_extension(self, extension, repository=None):
        if repository is None:
            try:
                repository = dwarf.extensions.INDEX[extension]['repository']
            except KeyError:
                raise ExtensionNotInIndex(extension)

        exit_code = subprocess.run(['git', 'clone', '-q', repository, 'dwarf/' + extension]).returncode
        if exit_code > 0:
            self.delete_extension(extension)
            raise InstallationError('could not clone repository "{0}" (git exited with '
                                    'exit code: {1})'.format(repository, exit_code))

    @staticmethod
    def download_extension_update(extension):
        try:
            repository = dwarf.extensions.INDEX[extension]['repository']
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

        return __version__
