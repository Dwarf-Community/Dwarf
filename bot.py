import discord
from discord.ext import commands
import aiohttp

from .controller import BaseController
from .cache import Cache
from .core.controller import CoreController
from .models import Guild, Channel, User
from . import strings, utils, __version__

import os
import sys
import inspect
import traceback
import importlib
import logging
import asyncio


class CommandConflict(Exception):
    pass


class Cog:
    def __init__(self, bot, extension, log=True, cache=False, session=False):
        self.bot = bot
        self.extension = extension
        if log:
            self.log = logging.getLogger('dwarf.' + extension + '.cog')
        if cache:
            self.cache = Cache(extension, bot=bot)
        if session:
            self.session = aiohttp.ClientSession(loop=bot.loop)


class Bot(commands.Bot):
    """Represents a Discord bot."""

    def __init__(self, loop=None):
        self.base = BaseController(self)
        self.core = CoreController(self)
        super().__init__(command_prefix=self.core.get_prefixes(), loop=loop, description=self.core.get_description(),
                         pm_help=None, cache_auth=False, command_not_found=strings.command_not_found,
                         command_has_no_subcommands=strings.command_has_no_subcommands)
        self.base.cache.loop = self.loop
        self.core.cache.loop = self.loop
        self._cache = Cache(bot=self)
        self.add_check(self.user_allowed)
        self._main_task = None
        self._core_tasks = []
        self.create_task(self.wait_for_restart, protect=True)
        self.create_task(self.wait_for_shutdown, protect=True)
        self.extra_tasks = {}
        user_agent = 'Dwarf (https://github.com/Dwarf-Community/Dwarf {0}) Python/{1} aiohttp/{2} discord.py/{3}'
        self.http.user_agent = user_agent.format(__version__, sys.version.split(maxsplit=1)[0],
                                                 aiohttp.__version__, discord.__version__)

    @property
    def is_configured(self):
        return self.base.get_token() is not None

    def initial_config(self):
        print(strings.setup_greeting)

        entered_token = input("> ")

        if len(entered_token) >= 50:  # assuming token
            self.base.set_token(entered_token)
        else:
            print(strings.not_a_token)
            exit(1)

        while True:
            print(strings.choose_prefix)
            while True:
                chosen_prefix = input('> ')
                if chosen_prefix:
                    break
            print(strings.confirm_prefix.format(chosen_prefix))
            if input("> ") in ['y', 'yes']:
                self.core.add_prefix(chosen_prefix)
                break

        print(strings.setup_finished)
        input("\n")

    async def on_command_completion(self, ctx):
        author = ctx.message.author
        user = User.objects.get_or_create(id=author.id)[0]
        user_already_registered = User.objects.filter(id=author.id).exists()
        user.command_count += 1
        user.save()
        if not user_already_registered:
            await author.send(strings.user_registered.format(author.name))

    async def on_ready(self):
        if self.core.get_owner_id() is None:
            await self.set_bot_owner()

        restarted_from = self.core.get_restarted_from()
        if restarted_from is not None:
            restarted_from = self.get_channel(restarted_from)
            await restarted_from.send("I'm back!")
            self.core.reset_restarted_from()

        # clear terminal screen
        if os.name == 'nt':
            os.system('cls')
        else:
            os.system('clear')

        print('------')
        print(strings.bot_is_online.format(self.user.name))
        print('------')
        print(strings.connected_to)
        print(strings.connected_to_servers.format(Guild.objects.count()))
        print(strings.connected_to_channels.format(Channel.objects.count()))
        print(strings.connected_to_users.format(User.objects.count()))
        print("\n{} active extensions".format(len(self.base.get_extensions())))
        prefix_label = strings.prefix_singular
        if len(self.core.get_prefixes()) > 1:
            prefix_label = strings.prefix_plural
        print("{}: {}\n".format(prefix_label, " ".join(list(self.core.get_prefixes()))))
        print("------\n")
        print(strings.use_this_url)
        url = await self.get_oauth_url()
        print(url)
        print("\n------")
        self.core.enable_restarting()

    async def logout(self):
        await super().logout()
        self.stop()

    def stop(self):
        def silence_gathered(future):
            try:
                future.result()
            finally:
                self.loop.stop()

        # cancel lingering tasks
        pending = asyncio.Task.all_tasks(loop=self.loop)
        if pending:
            for core_task in self._core_tasks:
                pending.discard(core_task)
            pending.discard(self._main_task)
            gathered = asyncio.gather(*pending, loop=self.loop)
            gathered.add_done_callback(silence_gathered)
            gathered.cancel()
        else:
            self.loop.stop()

        self.dispatch('stopped')

    def add_cog(self, cog):
        super().add_cog(cog)

        members = inspect.getmembers(cog)
        for name, member in members:
            # register tasks the cog has
            if name.startswith('do_'):
                self.add_task(member, name=name, resume_check=self.core.restarting_enabled)

    def _resolve_groups(self, cog_or_command=None):
        if cog_or_command is None:
            for extension in ['core'] + self.base.get_extensions():
                # find the extension's cog
                for cog in [_cog for _cog in self.cogs.values() if _cog.extension == extension]:
                    self._resolve_groups(cog)

        elif isinstance(cog_or_command, Cog):
            for name, member in inspect.getmembers(cog_or_command):
                if isinstance(member, commands.Command):
                    self._resolve_groups(member)

        elif isinstance(cog_or_command, commands.Command):
            # if command is in a group
            if '_' in cog_or_command.name:
                # resolve groups recursively
                entire_group, command_name = cog_or_command.name.rsplit('_', 1)
                group_name = entire_group.rsplit('_', 1)[0]
                if group_name in self.all_commands:
                    if not isinstance(self.all_commands[group_name], commands.Group):
                        raise CommandConflict("cannot group command {0} under {1} because {1} is already a "
                                              "command".format(command_name, group_name))
                    group_command = self.all_commands[group_name]
                else:
                    async def groupcmd(ctx):
                        if ctx.invoked_subcommand is None:
                            await self.send_command_help(ctx)

                    group_help = strings.group_help.format(group_name)
                    group_command = self.group(name=entire_group, invoke_without_command=True,
                                               help=group_help)(groupcmd)
                    self._resolve_groups(group_command)

                self.all_commands.pop(cog_or_command.name)
                cog_or_command.name = command_name
                group_command.add_command(cog_or_command)

        else:
            raise TypeError("cog_or_command must be either a cog, a command or None")

    def create_task(self, coro, resume_check=None, protect=False, *args, **kwargs):
        def actual_resume_check():
            return resume_check() and not self.is_closed()

        async def pause():
            if not self.is_ready():
                await asyncio.wait((self.wait_for('resumed'), self.wait_for('ready')),
                                   loop=self.loop, return_when=asyncio.FIRST_COMPLETED)

        task = self.loop.create_task(utils.restart_after_disconnect(pause, self.wait_until_ready,
                                                                    actual_resume_check)(coro)(*args, **kwargs))
        if protect:
            self._core_tasks.append(task)
        return task

    def add_task(self, coro, name=None, unique=True, resume_check=None):
        """The non decorator alternative to :meth:`.task`.

        Parameters
        -----------
        coro : coroutine
            The extra coro to register and execute in the background.
        name : Optional[str]
            The name of the coro to register as a task. Defaults to ``coro.__name__``.
        unique : Optional[bool]
            If this is ``True``, tasks with the same name that are already in
            :attr:`extra_tasks` will not be overwritten, and the original task will
            not be cancelled. Defaults to ``True``.
        resume_check : Optional[predicate]
            A predicate used to determine whether a task should be
            cancelled on logout or restarted instead when the bot is
            ready again. Defaults to ``None``, in which case the task
            will be cancelled on logout.

        Example
        --------

        .. code-block:: python3

            async def do_stuff: pass
            async def my_message(message): pass

            bot.add_task(do_stuff)
            bot.add_task(my_other_task, name='do_something_else')

        """
        if not asyncio.iscoroutinefunction(coro):
            raise discord.ClientException('Tasks must be coroutines')

        name = coro.__name__ if name is None else name

        if name in self.extra_tasks:
            if not unique:
                self.extra_tasks[name].append(self.create_task(coro, resume_check))
            else:
                return
        else:
            self.extra_tasks[name] = [coro]

    async def wait_for_shutdown(self):
        await self.core.cache.subscribe('shutdown')

    async def wait_for_restart(self):
        await self.core.cache.subscribe('restart')

    async def on_shutdown_message(self, message):
        self.core.disable_restarting()
        print("Shutting down...")
        await self.logout()

    async def on_restart_message(self, message):
        print("Restarting...")
        await self.logout()

    def load_extension(self, name):
        """Loads an extension's cog module.

        Parameters
        ----------
        name: str
            The name of the extension.

        Raises
        ------
        ImportError
            The cog module could not be imported
            or didn't have any ``Cog`` subclass.
        """

        if name in self.extensions:
            return

        cog_module = importlib.import_module('dwarf.' + name + '.cog')

        if hasattr(cog_module, 'setup'):
            cog_module.setup(self, name)
        else:
            cog_classes = inspect.getmembers(cog_module, lambda member: isinstance(member, type) and
                                             issubclass(member, Cog) and member is not Cog)
            for _, _Cog in cog_classes:
                if _Cog is None:
                    raise ImportError("The {} extension's cog module didn't have "
                                      "any Cog subclass and no setup function".format(name))
                self.add_cog(_Cog(self, name))

        self.extensions[name] = cog_module
        return cog_module

    def _load_cogs(self):
        self.load_extension('core')

        core_cog = self.get_cog('Core')
        if core_cog is None:
            raise ImportError("Could not find the Core cog.")

        failed = []
        extensions = self.base.get_extensions()
        for extension in extensions:
            try:
                self.load_extension(extension)
            except Exception as e:
                print("{}: {}".format(e.__class__.__name__, str(e)))
                failed.append(extension)

        if failed:
            print("\nFailed to load: " + ", ".join(failed))

        self._resolve_groups()

        return core_cog

    def user_allowed(self, ctx):
        if self.core.get_owner_id() == ctx.message.author.id:
            return True

        # TODO blacklisting users

        return True

    def task(self, unique=True, resume_check=None):
        """A decorator that registers a task to execute in the background.

        The task must accept only one argument (usually called ``state``),
        if not, ``TypeError``\ is raised. The ``state`` passed is a ``dict``.
        If a task is running when the Client disconnects from Discord
        because it logged itself out, it will cancel the execution of the
        task. If the Client loses the connection to Discord because
        of network issues or similar, it will cancel the execution of the task,
        wait for itself to reconnect, then restart the task with the
        ``state`` it had when it was cancelled.

        Examples
        ---------

        Creating a task that executes once on startup: ::

            @bot.task
            async def say_hello(state):
                step = state.setdefault('step', 1)
                if step == 1:
                    print('Step 1')
                    step = state['step'] = 2
                if step == 2:
                    print('Step 2')
                    step = state['step'] = 3
                if step == 3:
                    print('Step 3')
                return

        Creating a task inside a cog that will execute continuously: ::

            async def do_say_hello_every_minute(self):
                seconds_passed = state.setdefault('seconds_passed', 0)
                while True:
                    if seconds_passed == 60:
                        print("Hello World!")
                        seconds_passed = state['seconds_passed'] = 0
                    yield from asyncio.sleep(1)
                    seconds_passed = state['seconds_passed'] += 1

        Creating a task from a coroutine function dynamically: ::

            bot.task(my_coroutine_function)

        Parameters
        ------------
        unique : Optional[bool]
            If this is ``True``, tasks with the same name that are already in
            :attr:`tasks` will not be overwritten, and the original task will
            not be cancelled. Defaults to ``True``.
        resume_check : Optional[predicate]
            A predicate used to determine whether a task should be
            cancelled on logout or restarted instead when the bot is
            ready again. Defaults to ``None``, in which case the task
            will be cancelled on logout.

        Raises
        -------
        TypeError
            The decorated ``coro`` is not a coroutine function.
        """

        async def wrapped(coro):
            if not asyncio.iscoroutinefunction(coro):
                raise TypeError('task registered must be a coroutine function')

            name = coro.__name__
            if hasattr(self, name):
                if unique:
                    return coro
            setattr(self, name, self.create_task(coro, resume_check))

        return wrapped

    def run_tasks(self):
        members = inspect.getmembers(self)
        for name, member in [_member for _member in members if _member[0].startswith('do')]:
            self.create_task(member)

    async def wait_for_response(self, ctx, message_check=None, timeout=60):
        def response_check(message):
            is_response = ctx.message.author == message.author and ctx.message.channel == message.channel
            return is_response and message_check(message) if callable(message_check) else True

        try:
            response = await self.wait_for('message', check=response_check, timeout=timeout)
        except asyncio.TimeoutError:
            return
        return response

    async def wait_for_answer(self, ctx, timeout=60):
        def answer_check(message):
            return utils.is_boolean_answer(message)

        answer = await self.wait_for_response(ctx, message_check=answer_check, timeout=timeout)
        if answer is None:
            return
        return utils.answer_to_boolean(answer)

    async def wait_for_choice(self, ctx, choices: list, timeout=60):
        choice_format = "**{}**: {}"
        choice_messages = []

        def choice_check(message):
            return message.content[0] - 1 in range(len(choices))

        for i in range(len(choices)):
            choice_messages.append(choice_format.format(i + 1, choices[i]))

        choices_message = "\n".join(choice_messages)
        final_message = "{}\n\n{}".format(ctx.message, choices_message)
        await ctx.send(final_message)
        choice = await self.wait_for_response(ctx, message_check=choice_check, timeout=timeout)
        if choice is None:
            return
        return int(choice)

    async def send_command_help(self, ctx):
        if ctx.invoked_subcommand:
            pages = await self.formatter.format_help_for(ctx, ctx.invoked_subcommand)
            for page in pages:
                await ctx.send(page)
        else:
            pages = await self.formatter.format_help_for(ctx, ctx.command)
            for page in pages:
                await ctx.send(page)

    async def get_oauth_url(self):
        try:
            data = await self.application_info()
        except AttributeError:
            print(strings.update_the_api)
            raise
        return discord.utils.oauth_url(data.id)

    async def set_bot_owner(self):
        try:
            data = await self.application_info()
            self.core.set_owner_id(data.owner.id)
        except AttributeError:
            print(strings.update_the_api)
            raise
        print(strings.owner_recognized.format(data.owner.name))

    async def run(self):
        self._main_task = asyncio.Task.current_task(loop=self.loop)

        self._load_cogs()

        if self.core.get_prefixes():
            self.command_prefix = list(self.core.get_prefixes())
        else:
            print(strings.no_prefix_set)
            self.command_prefix = ["!"]

        self.run_tasks()

        print(strings.logging_into_discord)
        print(strings.keep_updated.format(self.command_prefix[0]))
        print(strings.official_server.format(strings.invite_link))

        await self.start(self.base.get_token())

        await self.wait_for('stopped')


def main(loop=None, bot=None):
    if loop is None:
        loop = asyncio.get_event_loop()

    if bot is None:
        bot = Bot(loop=loop)

    if not bot.is_configured:
        bot.initial_config()

    error = False
    error_message = ""
    try:
        loop.run_until_complete(bot.run())
    except discord.LoginFailure:
        error = True
        error_message = 'Invalid credentials'
        choice = input(strings.invalid_credentials)
        if choice.strip() == 'reset':
            bot.base.delete_token()
        else:
            bot.base.disable_restarting()
    except KeyboardInterrupt:
        bot.base.disable_restarting()
        loop.run_until_complete(bot.logout())
    except Exception as e:
        error = True
        print(e)
        error_message = traceback.format_exc()
        bot.base.disable_restarting()
        loop.run_until_complete(bot.logout())
    finally:
        if error:
            print(error_message)
        return bot
