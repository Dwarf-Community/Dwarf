from collections import defaultdict

import aiohttp
import discord
from discord.ext import commands

from dwarf import formatting as f
from dwarf.controller import BaseController, ExtensionAlreadyInstalled, ExtensionNotFound, ExtensionNotInIndex
from .controller import CoreController, PrefixAlreadyExists, PrefixNotFound
from . import strings

import asyncio
import logging
import traceback
import time


class Core:
    """All commands that relate to management operations."""

    def __init__(self, bot):
        self.bot = bot
        self.core = CoreController(bot=bot)
        self.base = BaseController(bot=bot)
        self.log = logging.getLogger('dwarf.core.cog')
        self.session = aiohttp.ClientSession(loop=self.bot.loop)

    @commands.command(name='eval', hidden=True)
    @commands.is_owner()
    async def evaluate(self, ctx, *, code):
        """Evaluates code.
        Modified function, originally made by Rapptz"""
        # [p]eval <code>

        code = code.strip('` ')
        result = None

        global_vars = globals().copy()
        global_vars['bot'] = self.bot
        global_vars['ctx'] = ctx
        global_vars['message'] = ctx.message
        global_vars['author'] = ctx.message.author
        global_vars['channel'] = ctx.message.channel
        global_vars['guild'] = ctx.message.guild

        try:
            result = eval(code, global_vars, locals())
        except Exception as e:
            await ctx.send(f.block(type(e).__name__ + ': ' + str(e), 'py'))
            return

        if asyncio.iscoroutine(result):
            result = await result

        result = f.block(result, 'py')

        await ctx.send(result)

    @commands.command()
    async def install(self, ctx, *, extensions):
        """Installs an extension."""
        # [p] install <extensions>

        extensions = extensions.lower().split()

        installation_status = defaultdict(lambda: [])

        def extension_check(message):
            extension_name = message.content
            is_same_author = ctx.message.author == message.author
            is_same_channel = ctx.message.channel == message.channel
            is_proper_name = ' ' not in extension_name
            return is_same_author and is_same_channel and is_proper_name

        async def _install(_extension):
            repository = None
            if _extension.startswith('https://'):
                repository = _extension
                await ctx.send(strings.specify_extension_name)
                _extension = await self.bot.wait_for('message', check=extension_check, timeout=60)
                if _extension is None:
                    await ctx.send(strings.skipping_this_extension)
                    return False
                _extension = _extension.content
            await ctx.send("Installing '**" + _extension + "**'...")
            try:
                unsatisfied = self.base.install_extension(_extension, repository)
            except ExtensionAlreadyInstalled:
                await ctx.send("The extension '**" + _extension + "**' is already installed.")
                installation_status['failed_extensions'].append(_extension)
                return False
            except ExtensionNotInIndex:
                await ctx.send("There is no extension called '**" + _extension + "**'.")
                installation_status['failed_extensions'].append(_extension)
                return False
            else:
                if unsatisfied is not None:
                    failure_message = strings.failed_to_install.format(_extension)

                    if unsatisfied['packages']:
                        failure_message += '\n' + strings.unsatisfied_requirements + '\n'
                        failure_message += "**" + "**\n**".join(unsatisfied['packages']) + "**"

                    if unsatisfied['extensions']:
                        failure_message += '\n' + strings.unsatisfied_dependencies + '\n'
                        failure_message += "**" + "**\n**".join(unsatisfied['extensions']) + "**"

                    await ctx.send(failure_message)

                    if unsatisfied['packages']:
                        await ctx.send("Do you want to install the required packages now? (yes/no)")
                        _answer = await self.bot.wait_for_answer(ctx)
                        if _answer is True:
                            for package in unsatisfied['packages']:
                                return_code = self.base.install_package(package)
                                if return_code is 0:
                                    unsatisfied['packages'].remove(package)
                                    await ctx.send("Installed package '**"
                                                   + package + "**' successfully.")
                                    installation_status['installed_packages'].append(package)

                            if unsatisfied['packages']:
                                await ctx.send("Failed to install packages: '**"
                                               + "**', '**".join(unsatisfied['packages']) + "**'.")
                                installation_status['failed_packages'] += unsatisfied['packages']
                                return False
                        else:
                            await ctx.send("Alright, I will not install any packages the '**"
                                           + _extension + "**' extension requires just now.")
                            installation_status['failed_extensions'].append(_extension)
                            return False

                    if not unsatisfied['packages'] and unsatisfied['extensions']:
                        await ctx.send("Do you want to install the extensions '**"
                                       + _extension + "**' depends on now? (yes/no)")
                        _answer = await self.bot.wait_for_answer(ctx)
                        if _answer is True:
                            for extension_to_install in unsatisfied['extensions']:
                                extension_install_return_code = await _install(extension_to_install)
                                if extension_install_return_code is True:
                                    unsatisfied['extensions'].remove(extension_to_install)

                            if unsatisfied['extensions']:
                                await ctx.send("Failed to install one or more of the '**"
                                               + _extension + "**' extension's dependencies.")
                                installation_status['failed_extensions'].append(_extension)
                                return False
                            else:
                                return await _install(_extension)
                        else:
                            await ctx.send("Alright, I will not install any dependencies just now")
                            installation_status['failed_extensions'].append(_extension)
                            return False

                else:
                    await ctx.send("The extension '**" + _extension + "**' was installed successfully.")
                    installation_status['installed_extensions'].append(_extension)
                    return True

        for extension in extensions:
            await _install(extension)

        completed_message = "Installation completed.\n"
        if installation_status['installed_extensions']:
            completed_message += "Installed extensions:\n"
            completed_message += "**" + "**\n**".join(installation_status['installed_extensions']) + "**\n"
        if installation_status['installed_packages']:
            completed_message += "Installed packages:\n"
            completed_message += "**" + "**\n**".join(installation_status['installed_packages']) + "**\n"
        if installation_status['failed_extensions']:
            completed_message += "Failed to install extensions:\n"
            completed_message += "**" + "**\n**".join(installation_status['failed_extensions']) + "**\n"
        if installation_status['failed_packages']:
            completed_message += "Failed to install packages:\n"
            completed_message += "**" + "**\n**".join(installation_status['failed_packages']) + "**\n"
        await ctx.send(completed_message)

        if installation_status['installed_extensions']:
            await ctx.send("Reboot Dwarf for changes to take effect.\n"
                           "Would you like to restart now? (yes/no)")
            answer = await self.bot.wait_for_answer(ctx)
            if answer is True:
                await ctx.send("Okay, I'll be right back!")
                await self.core.restart(restarted_from=ctx.message.channel)

    @commands.command()
    async def update(self, ctx, *, extensions):
        """Updates an extension."""
        # [p]update <extensions>

        extensions = extensions.lower().split()

        update_status = defaultdict(lambda: [])

        async def _update(_extension):
            await ctx.send("Updating '**" + _extension + "**'...")
            try:
                unsatisfied = self.base.update_extension(_extension)
            except ExtensionNotFound:
                await ctx.send("The extension '**" + _extension + "**' could not be found.")
                update_status['failed_extensions'].append(_extension)
                return False
            else:
                if unsatisfied is not None:
                    failure_message = strings.failed_to_update.format(_extension)

                    if unsatisfied['packages']:
                        failure_message += '\n' + strings.unsatisfied_requirements + '\n'
                        failure_message += "**" + "**\n**".join(unsatisfied['packages']) + "**"

                    if unsatisfied['extensions']:
                        failure_message += '\n' + strings.unsatisfied_dependencies + '\n'
                        failure_message += "**" + "**\n**".join(unsatisfied['extensions']) + "**"

                    await ctx.send(failure_message)

                    if unsatisfied['packages']:
                        await ctx.send("Do you want to install the new requirements of "
                                       + _extension + " now? (yes/no)")
                        _answer = await self.bot.wait_for_answer(ctx)
                        if _answer is True:
                            for package in unsatisfied['packages']:
                                return_code = self.base.install_package(package)
                                if return_code is 0:
                                    unsatisfied['packages'].remove(package)
                                    await ctx.send("Installed package '**"
                                                   + package + "**' successfully.")
                                    update_status['installed_packages'].append(package)

                            if unsatisfied['packages']:
                                await ctx.send("Failed to install packages: '**"
                                               + "**', '**".join(unsatisfied['packages']) + "**'.")
                                update_status['failed_packages'] += unsatisfied['packages']
                                return False
                        else:
                            await ctx.send("Alright, I will not install any packages the '**"
                                           + _extension + "**' extension requires just now.")
                            update_status['failed_to_install_extensions'].append(_extension)
                            return False

                    if not unsatisfied['packages'] and unsatisfied['extensions']:
                        await ctx.send("Do you want to install the new dependencies of '**"
                                       + _extension + "**' now? (yes/no)")
                        _answer = await self.bot.wait_for_response(ctx)
                        if _answer is True:
                            self.bot.invoke_command('install', ctx, ' '.join(unsatisfied['extensions']))
                        exts = self.base.get_extensions()
                        for extension_to_check in unsatisfied['extensions']:
                            if extension_to_check in exts:
                                unsatisfied['extensions'].remove(extension_to_check)

                            if unsatisfied['extensions']:
                                await ctx.send("Failed to install one or more of '**"
                                               + _extension + "**' dependencies.")
                                update_status['failed_extensions'].append(_extension)
                                return False
                            else:
                                return await _update(_extension)
                        else:
                            await ctx.send("Alright, I will not install any dependencies just now")
                            update_status['failed_extensions'].append(_extension)
                            return False

                else:
                    await ctx.send("The extension '**" + _extension + "**' was updated successfully.")
                    update_status['updated_extensions'].append(_extension)
                    return True

        for extension in extensions:
            await _update(extension)

        completed_message = "Update completed.\n"
        if update_status['updated_extensions']:
            completed_message += "Updated extensions:\n"
            completed_message += "**" + "**\n**".join(update_status['updated_extensions']) + "**\n"
        if update_status['installed_packages']:
            completed_message += "Installed packages:\n"
            completed_message += "**" + "**\n**".join(update_status['installed_packages']) + "**\n"
        if update_status['failed_extensions']:
            completed_message += "Failed to update extensions:\n"
            completed_message += "**" + "**\n**".join(update_status['failed_extensions']) + "**\n"
        if update_status['failed_packages']:
            completed_message += "Failed to install packages:\n"
            completed_message += "**" + "**\n**".join(update_status['failed_packages']) + "**\n"
        await ctx.send(completed_message)

        if update_status['updated_extensions']:
            await ctx.send("Reboot Dwarf for changes to take effect.\n"
                           "Would you like to restart now? (yes/no)")
            answer = await self.bot.wait_for_response(ctx)
            if answer is True:
                await ctx.send("Okay, I'll be right back!")
                await self.core.restart(restarted_from=ctx.message.channel)

    @commands.command()
    async def uninstall(self, ctx, *, extensions):
        """Uninstalls extensions."""
        # [p]uninstall <extensions>

        extensions = extensions.lower().split()

        uninstall_status = defaultdict(lambda: [])

        async def _uninstall(_extension):
            await ctx.send("Uninstalling '**" + _extension + "**'...")
            try:
                to_cascade = self.base.uninstall_extension(_extension)
            except ExtensionNotFound:
                await ctx.send("The extension '**" + _extension + "**' could not be found.")
                uninstall_status['failed_extensions'].append(_extension)
                return False
            else:
                if to_cascade:
                    await ctx.send(strings.would_be_uninstalled_too.format(_extension) + "\n"
                                   + "**" + "**\n**".join(to_cascade) + "**")
                    await ctx.send(strings.proceed_with_uninstallation)
                    _answer = await self.bot.wait_for_answer(ctx)
                    if _answer is True:
                        for extension_to_uninstall in to_cascade:
                            return_code = await _uninstall(extension_to_uninstall)
                            if return_code is True:
                                to_cascade.remove(extension_to_uninstall)

                        if to_cascade:
                            await ctx.send("Failed to uninstall '**"
                                           + "**', '**".join(to_cascade) + "**'.")
                            uninstall_status['failed_extensions'].append(_extension)
                            return False

                        else:
                            return await _uninstall(_extension)
                    else:
                            await ctx.send("Alright, I will not install any extensions just now.")
                            uninstall_status['failed_extensions'].append(_extension)
                            return False

                else:
                    await ctx.send("The '**" + _extension + "**' extension was uninstalled successfully.")
                    uninstall_status['uninstalled_extensions'].append(_extension)
                    return True

        for extension in extensions:
            await _uninstall(extension)

        completed_message = "Uninstallation completed.\n"
        if uninstall_status['uninstalled_extensions']:
            completed_message += "Uninstalled extensions:\n"
            completed_message += "**" + "**\n**".join(uninstall_status['uninstalled_extensions']) + "**\n"
        if uninstall_status['failed_extensions']:
            completed_message += "Failed to uninstall extensions:\n"
            completed_message += "**" + "**\n**".join(uninstall_status['failed_extensions']) + "**\n"
        await ctx.send(completed_message)

        if uninstall_status['uninstalled_extensions']:
            await ctx.send("Reboot Dwarf for changes to take effect.\n"
                           "Would you like to restart now? (yes/no)")
            answer = await self.bot.wait_for_answer(ctx)
            if answer is True:
                await ctx.send("Okay, I'll be right back!")
                await self.core.restart(restarted_from=ctx.message.channel)

    @commands.group()
    async def set(self, ctx):
        """Group of commands that change the bot's settings."""
        # [p]set <subcommand>

        if ctx.invoked_subcommand is None:
            await self.bot.send_command_help(ctx)

    @commands.group()
    async def get(self, ctx):
        """Group of commands that show the bot's settings."""
        # [p]set <subcommand>

        if ctx.invoked_subcommand is None:
            await self.bot.send_command_help(ctx)

    @commands.group()
    async def add(self, ctx):
        """Group of commands that add items to some of the bot's settings."""
        # [p]add <subcommand>

        if ctx.invoked_subcommand is None:
            await self.bot.send_command_help(ctx)

    @commands.group()
    async def remove(self, ctx):
        """Group of commands that remove items from some of the bot's settings."""
        # [p]remove <subcommand>

        if ctx.invoked_subcommand is None:
            await self.bot.send_command_help(ctx)

    @commands.group()
    async def setup(self, ctx):
        """Group of commands that configure and prepare things."""
        # [p]setup <subcommand>

        if ctx.invoked_subcommand is None:
            await self.bot.send_command_help(ctx)

    @set.command()
    @commands.is_owner()
    async def name(self, ctx, *, name):
        """Sets the bot's name."""
        # [p]set name <name>

        name = name.strip()
        if name != "":
            await self.bot.user.edit(username=name)
        else:
            await self.bot.send_command_help(ctx)

    @set.command()
    @commands.is_owner()
    async def nickname(self, ctx, *, nickname=""):
        """Sets the bot's nickname on the current server.
        Leaving this empty will remove it."""
        # [p]set nickname <nickname>

        nickname = nickname.strip()
        if nickname == "":
            nickname = None
        try:
            await ctx.me.edit(nick=nickname)
            await ctx.send("Done.")
        except discord.Forbidden:
            await ctx.send("I cannot do that, I lack the \"Change Nickname\" permission.")

    @set.command()
    @commands.is_owner()
    async def game(self, ctx, *, game=None):
        """Sets the bot's playing status
        Leaving this empty will clear it."""
        # [p]set game <game>

        guild = ctx.message.guild

        current_status = guild.me.status if guild is not None else None

        if game:
            game = game.strip()
            await self.bot.change_presence(game=discord.Game(name=game),
                                           status=current_status)
            await ctx.send('Game set to "{}".'.format(game))
        else:
            await self.bot.change_presence(game=None, status=current_status)
            await ctx.send('Not playing a game now.')

    @set.command()
    @commands.is_owner()
    async def status(self, ctx, *, status=None):
        """Sets the bot's status
        Statuses:
            online
            idle
            dnd
            invisible"""
        # [p]set status <status>

        statuses = {
                    "online": discord.Status.online,
                    "idle": discord.Status.idle,
                    "dnd": discord.Status.dnd,
                    "invisible": discord.Status.invisible
                   }

        guild = ctx.message.guild

        current_game = guild.me.game if guild is not None else None

        if status is None:
            await self.bot.change_presence(status=discord.Status.online,
                                           game=current_game)
            await ctx.send("Status reset.")
        else:
            status = statuses.get(status.lower(), None)
            if status:
                await self.bot.change_presence(status=status,
                                               game=current_game)
                await ctx.send("Status changed.")
            else:
                await self.bot.send_command_help(ctx)

    @set.command()
    @commands.is_owner()
    async def stream(self, ctx, streamer=None, *, stream_title=None):
        """Sets the bot's streaming status.
        Leaving both streamer and stream_title empty will clear it."""
        # [p]set stream <streamer> <stream_title>

        guild = ctx.message.guild

        current_status = guild.me.status if guild is not None else None

        if stream_title:
            stream_title = stream_title.strip()
            if "twitch.tv/" not in streamer:
                streamer = "https://www.twitch.tv/" + streamer
            game = discord.Game(type=1, url=streamer, name=stream_title)
            await self.bot.change_presence(game=game, status=current_status)
            self.log.debug('Owner has set streaming status and url to "{}" and {}'.format(stream_title, streamer))
        elif streamer is not None:
            await self.bot.send_command_help(ctx)
            return
        else:
            await self.bot.change_presence(game=None, status=current_status)
            self.log.debug('stream cleared by owner')
        await ctx.send("Done.")

    @set.command()
    @commands.is_owner()
    async def avatar(self, ctx, url):
        """Sets the bot's avatar."""
        # [p]set avatar <url>

        try:
            async with self.session.get(url) as r:
                data = await r.read()
            await self.bot.user.edit(avatar=data)
            await ctx.send("Done.")
            self.log.debug("Changed avatar.")
        except Exception as e:
            await ctx.send("Error, check your console or logs for "
                           "more information.")
            self.log.exception(e)
            traceback.print_exc()

    @set.command()
    @commands.is_owner()
    async def token(self, ctx, token):
        """Sets the bot's login token."""
        # [p]set token <token>

        if len(token) > 50:  # assuming token
            self.base.set_token(token)
            await ctx.send("Token set. Restart Dwarf to use the new token.")
            self.log.info("Bot token changed.")
        else:
            await ctx.send("Invalid token.")

    @set.command()
    @commands.is_owner()
    async def description(self, ctx, *, description):
        """Sets the bot's description."""

        self.core.set_description(description)
        self.bot.description = description
        await ctx.send("My description has been set.")

    @set.command()
    @commands.is_owner()
    async def repository(self, ctx, repository):
        """Sets the bot's repository."""

        self.core.set_repository(repository)
        await ctx.send("My repository is now located at:\n<" + repository + ">")

    @set.command()
    @commands.is_owner()
    async def officialinvite(self, ctx, invite):
        """Sets the bot's official server's invite URL."""

        self.core.set_official_invite(invite)
        await ctx.send("My official server invite is now:\n<" + invite + ">")

    @add.command(name='prefix')
    @commands.is_owner()
    async def add_prefix(self, ctx, prefix):
        """Adds a prefix to the bot."""

        if prefix.startswith('"') and prefix.endswith('"'):
            prefix = prefix[1:len(prefix) - 1]

        try:
            self.core.add_prefix(prefix)
            self.bot.command_prefix = self.core.get_prefixes()
            await ctx.send("The prefix '**" + prefix + "**' was added successfully.")
        except PrefixAlreadyExists:
            await ctx.send("The prefix '**" + prefix + "**' could not be added "
                           "as it is already a prefix.")

    @remove.command(name='prefix')
    @commands.is_owner()
    async def remove_prefix(self, ctx, prefix):
        """Removes a prefix from the bot."""

        if prefix.startswith('"') and prefix.endswith('"'):
            prefix = prefix[1:len(prefix) - 1]

        try:
            self.core.remove_prefix(prefix)
            self.bot.command_prefix = self.core.get_prefixes()
            await ctx.send("The prefix '**" + prefix + "**' was removed successfully.")
        except PrefixNotFound:
            await ctx.send("'**" + prefix + "**' is not a prefix of this bot.")

    @get.command()
    @commands.is_owner()
    async def prefixes(self, ctx):
        """Shows the bot's prefixes."""

        prefixes = self.core.get_prefixes()
        if len(prefixes) > 1:
            await ctx.send("My prefixes are: '**" + "**', '**".join(prefixes) + "**'")
        else:
            await ctx.send("My prefix is '**" + prefixes[0] + "**'.")

    @commands.command()
    async def ping(self, ctx):
        """Calculates the ping time."""
        # [p]ping

        t1 = time.perf_counter()
        await ctx.trigger_typing()
        t2 = time.perf_counter()
        await ctx.send("Pong.\nTime: " + str(round((t2-t1)*1000)) + "ms")

    async def on_shutdown_message(self, message):
        self.core.disable_restarting()
        print("Shutting down...")
        await self.bot.logout()

    async def on_restart_message(self, message):
        print("Restarting...")
        await self.bot.logout()
        print("Logged out.")

    async def do_wait_for_shutdown(self):
        print("do_wait_for_shutdown started")
        await self.core.cache.subscribe('shutdown', 1)
        print("do_wait_for_shutdown ended")

    async def do_wait_for_restart(self):
        print("do_wait_for_restart started")
        await self.core.cache.subscribe('restart', 1)
        print("do_wait_for_restart ended")

    async def on_logout(self):
        self.bot.stop_loop()
        if not self.base.restarting_enabled():
            self.bot.loop.close()

    @commands.command()
    @commands.is_owner()
    async def shutdown(self, ctx):
        """Shuts down Dwarf."""
        # [p]shutdown

        await ctx.send("Goodbye!")
        await self.core.shutdown()

    @commands.command()
    @commands.is_owner()
    async def restart(self, ctx):
        """Restarts Dwarf."""
        # [p]restart

        await ctx.send("I'll be right back!")
        await self.core.restart(restarted_from=ctx.message.channel)

    async def get_command(self, command):
        command = command.split()
        try:
            comm_obj = self.bot.commands[command[0]]
            if len(command) > 1:
                command.pop(0)
                for cmd in command:
                    comm_obj = comm_obj.commands[cmd]
        except KeyError:
            return KeyError
        for check in comm_obj.checks:
            if check.__name__ == "is_owner_check":
                return False
        return comm_obj

    @commands.command(no_pm=True)
    @commands.is_owner()
    async def leave(self, ctx):
        """Makes the bot leave the current server."""
        # [p]leave

        message = ctx.message

        await ctx.send("Are you sure you want me to leave this server? (yes/no)")
        answer = await self.bot.wait_for_answer(ctx, timeout=30)
        if answer is True:
            await ctx.send("Alright. Bye :wave:")
            self.log.debug('Leaving "{}"'.format(message.guild.name))
            await self.bot.leave_guild(message.guild)

        else:
            await ctx.send("Ok I'll stay here then.")

    @commands.command()
    @commands.is_owner()
    async def servers(self, ctx):
        """Lists and allows to leave servers."""
        # [p]servers

        guilds = list(self.bot.guilds)
        guild_list = {}
        msg = ""
        for i in range(0, len(guilds)):
            guild_list[str(i)] = guilds[i]
            msg += "{}: {}\n".format(str(i), guilds[i].name)
        msg += "\nTo leave a server just type its number."
        for page in f.pagify(msg, ['\n']):
            await ctx.send(page)
        while msg is not None:
            msg = await self.bot.wait_for_response(ctx, timeout=30)
            if msg is not None:
                msg = msg.content.strip()
                if msg in guild_list.keys():
                    await self.leave_confirmation(guild_list[msg], ctx)
                else:
                    break
            else:
                break

    @commands.command()
    async def contact(self, ctx, *, message: str):
        """Sends message to the owner of the bot."""
        # [p]contact <message>

        owner_id = self.core.get_owner_id()
        if owner_id is None:
            await ctx.send("I have no owner set.")
            return
        owner = await self.bot.get_user_info(owner_id)
        author = ctx.message.author
        if isinstance(ctx.message.channel, discord.abc.GuildChannel):
            guild = ctx.message.guild
            source = ", server **{}** ({})".format(guild.name, guild.id)
        else:
            source = ", direct message"
        sender = "From **{}** ({}){}:\n\n".format(author, author.id, source)
        message = sender + message
        try:
            await owner.send(message)
        except discord.errors.InvalidArgument:
            await ctx.send("I cannot send your message, I'm unable to find "
                           "my owner... *sigh*")
        except discord.errors.HTTPException:
            await ctx.send("Your message is too long.")
        else:
            await ctx.send("Your message has been sent.")

    @commands.command()
    async def about(self, ctx):
        """Shows information about the bot."""
        # [p]info

        await ctx.send("{}\n"
                       "**Repository:**\n"
                       "<{}>\n"
                       "**Official server:**\n"
                       "<{}>".format(self.core.get_description(),
                                     self.core.get_repository(),
                                     self.core.get_official_invite()))

    async def leave_confirmation(self, guild, ctx):
        if not ctx.message.channel.is_private:
            current_guild = ctx.message.guild
        else:
            current_guild = None
        await ctx.send("Are you sure you want me to leave **{}**? (yes/no)".format(guild.name))
        answer = await self.bot.wait_for_answer(ctx, timeout=30)
        if answer is None or answer is False:
            await ctx.send("I'll stay then.")
        else:
            await self.bot.leave_guild(guild)
            if guild != current_guild:
                await ctx.send("Done.")

    @commands.command()
    async def version(self, ctx):
        """Shows the bot's current version"""
        # [p]version

        await ctx.send("Current version: " + self.base.get_dwarf_version())


def setup(bot):
    core = Core(bot)
    bot.add_cog(core)
