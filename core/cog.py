import aiohttp
import discord
from discord.ext import commands

from dwarf import permissions, formatting as f
from dwarf.controller import BaseController, ExtensionAlreadyInstalled, ExtensionNotFound, ExtensionNotInIndex
from dwarf.models import Guild, Channel, User
from dwarf.utils import answer_to_boolean, is_boolean_answer
from .controller import CoreController, PrefixAlreadyExists, PrefixNotFound
from . import strings

import asyncio
import logging
import traceback
import time
import os


class Core:
    """All commands that relate to management operations."""

    def __init__(self, bot):
        self.bot = bot
        self.core = CoreController(bot=bot)
        self.base = BaseController(bot=bot)
        self.log = logging.getLogger('dwarf.core.cog')
        self.session = aiohttp.ClientSession(loop=self.bot.loop)

    async def on_command_completion(self, command, ctx):
        author = ctx.message.author
        user = User.objects.get_or_create(id=author.id)[0]
        user_already_registered = User.objects.filter(id=author.id).exists()
        user.command_count += 1
        user.save()
        if not user_already_registered:
            await self.bot.send_message(author, strings.user_registered.format(author.name))

    async def on_ready(self):
        if self.core.get_owner_id() is None:
            await self.bot.set_bot_owner()
        
        restarted_from = self.core.get_restarted_from()
        if restarted_from is not None:
            restarted_from = self.bot.get_channel(restarted_from)
            await self.bot.send_message(restarted_from, "I'm back!")
            self.core.reset_restarted_from()
        
        # clear terminal screen
        if os.name == 'nt':
            os.system('cls')
        else:
            os.system('clear')
        
        print('------')
        # print(strings.bot_is_online.format(self.bot.user.name))
        print('------')
        print(strings.connected_to)
        print(strings.connected_to_servers.format(Guild.objects.count()))
        print(strings.connected_to_channels.format(Channel.objects.count()))
        print(strings.connected_to_users.format(User.objects.count()))
        print("\n{} active cogs".format(len(self.base.get_extensions())))
        prefix_label = strings.prefix_singular
        if len(self.core.get_prefixes()) > 1:
            prefix_label = strings.prefix_plural
        print("{}: {}\n".format(prefix_label, " ".join(list(self.core.get_prefixes()))))
        print("------\n")
        print(strings.use_this_url)
        url = await self.bot.get_oauth_url()
        self.bot.oauth_url = url
        print(url)
        print("\n------")
        self.core.enable_restarting()

    @commands.command(name='eval', pass_context=True, hidden=True)
    @permissions.owner()
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
        global_vars['server'] = ctx.message.server

        try:
            result = eval(code, global_vars, locals())
        except Exception as e:
            await self.bot.say(f.block(type(e).__name__ + ': ' + str(e), 'py'))
            return

        if asyncio.iscoroutine(result):
            result = await result

        result = f.block(result, 'py')
        
        await self.bot.say(result)

    @commands.command(pass_context=True)
    async def install(self, ctx, *, extensions):
        """Installs an extension."""
        # [p] install <extensions>
        
        bot = self.bot
        
        extensions = extensions.lower().split()
        
        installed_extensions = []
        installed_packages = []
        failed_to_install_extensions = []
        failed_to_install_packages = []

        def is_extension_name_check(extension_name):
                if isinstance(extension_name, discord.Message):
                    extension_name = extension_name.content
                return ' ' in extension_name
        
        async def _install(extension):
            repository = None
            if extension.startswith('https://'):
                repository = extension
                await bot.say(strings.specify_extension_name)
                extension = await bot.wait_for_message(author=ctx.message.author,
                    channel=ctx.message.channel,
                    check=is_extension_name_check,
                    timeout=60)
                if extension is None:
                    await bot.say(strings.skipping_this_extension)
                    return False
            await bot.say("Installing '**" + extension + "**'...")
            await bot.type()
            try:
                unsatisfied = self.base.install_extension(extension, repository)
            except ExtensionAlreadyInstalled:
                await bot.say("The extension '**" + extension + "**' is already installed.")
                failed_to_install_extensions.append(extension)
                return False
            except ExtensionNotInIndex:
                await bot.say("There is no extension called '**" + extension + "**'.")
                failed_to_install_extensions.append(extension)
                return False
            else:
                if unsatisfied is not None:
                    failure_message = strings.failed_to_install.format(extension)
                    
                    if unsatisfied['packages']:
                        failure_message += '\n' + strings.unsatisfied_requirements + '\n'
                        failure_message += "**" + "**\n**".join(unsatisfied['packages']) + "**"
                    
                    if unsatisfied['extensions']:
                        failure_message += '\n' + strings.unsatisfied_dependencies + '\n'
                        failure_message += "**" + "**\n**".join(unsatisfied['extensions']) + "**"
                    
                    await bot.say(failure_message)
                    
                    if unsatisfied['packages']:
                        await bot.say("Do you want to install the required packages now? (yes/no)")
                        answer = await bot.wait_for_message(author=ctx.message.author,
                                                            channel=ctx.message.channel,
                                                            check=is_boolean_answer,
                                                            timeout=60)
                        if answer is not None and answer_to_boolean(answer) is True:
                            for package in unsatisfied['packages']:
                                return_code = self.base.install_package(package)
                                if return_code is 0:
                                    unsatisfied['packages'].remove(package)
                                    await bot.say("Installed package '**"
                                                  + package + "**' successfully.")
                                    installed_packages.append(package)
                            
                            if unsatisfied['packages']:
                                await bot.say("Failed to install packages: '**"
                                              + "**', '**".join(unsatisfied['packages']) + "**'.")
                                failed_to_install_packages += unsatisfied['packages']
                                return False
                        else:
                            await bot.say("Alright, I will not install any packages the '**"
                                          + extension + "**' extension requires just now.")
                            failed_to_install_extensions.append(extension)
                            return False
                    
                    if not unsatisfied['packages'] and unsatisfied['extensions']:
                        await bot.say("Do you want to install the extensions '**"
                                      + extension + "**' depends on now? (yes/no)")
                        answer = await bot.wait_for_message(author=ctx.message.author,
                                                            channel=ctx.message.channel,
                                                            check=is_boolean_answer,
                                                            timeout=60)
                        if answer is not None and answer_to_boolean(answer) is True:
                            for extension_to_install in unsatisfied['extensions']:
                                extension_install_return_code = await _install(extension_to_install)
                                if extension_install_return_code is True:
                                    unsatisfied['extensions'].remove(extension_to_install)
                            
                            if unsatisfied['extensions']:
                                await bot.say("Failed to install one or more of '**"
                                              + extension + "**' dependencies.")
                                failed_to_install_extensions.append(extension)
                                return False
                            else:
                                return await _install(extension)
                        else:
                            await bot.say("Alright, I will not install any dependencies just now")
                            failed_to_install_extensions.append(extension)
                            return False
                
                else:
                    await bot.say("The extension '**" + extension + "**' was installed successfully.")
                    installed_extensions.append(extension)
                    return True
        
        for extension in extensions:
            await _install(extension)
        
        completed_message = "Installation completed.\n"
        if installed_extensions:
            completed_message += "Installed extensions:\n"
            completed_message += "**" + "**\n**".join(installed_extensions) + "**\n"
        if installed_packages:
            completed_message += "Installed packages:\n"
            completed_message += "**" + "**\n**".join(installed_packages) + "**\n"
        if failed_to_install_extensions:
            completed_message += "Failed to install extensions:\n"
            completed_message += "**" + "**\n**".join(failed_to_install_extensions) + "**\n"
        if failed_to_install_packages:
            completed_message += "Failed to install packages:\n"
            completed_message += "**" + "**\n**".join(failed_to_install_packages) + "**\n"
        await bot.say(completed_message)
        
        if installed_extensions:
            await bot.say("Reboot Dwarf for changes to take effect.\n"
                          "Would you like to restart now? (yes/no)")
            answer = await bot.wait_for_message(author=ctx.message.author,
                                       channel=ctx.message.channel,
                                       check=is_boolean_answer,
                                       timeout=60)
            if answer is not None and answer_to_boolean(answer) is True:
                await bot.say("Okay, I'll be right back!")
                await self.core.restart(restarted_from=ctx.message.channel)

    @commands.command(pass_context=True)
    async def update(self, ctx, *, extensions):
        """Updates an extension."""
        # [p]update <extensions>
        
        bot = self.bot
        
        extensions = extensions.lower().split()
        
        updated_extensions = []
        installed_packages = []
        failed_to_update_extensions = []
        failed_to_install_packages = []
        
        async def _update(extension):
            await bot.say("Updating '**" + extension + "**'...")
            await bot.type()
            try:
                unsatisfied = self.base.update_extension(extension)
            except ExtensionNotFound:
                await bot.say("The extension '**" + extension + "**' could not be found.")
                failed_to_update_extensions.append(extension)
                return False
            else:
                if unsatisfied is not None:
                    failure_message = strings.failed_to_update.format(extension)
                    
                    if unsatisfied['packages']:
                        failure_message += '\n' + strings.unsatisfied_requirements + '\n'
                        failure_message += "**" + "**\n**".join(unsatisfied['packages']) + "**"
                    
                    if unsatisfied['extensions']:
                        failure_message += '\n' + strings.unsatisfied_dependencies + '\n'
                        failure_message += "**" + "**\n**".join(unsatisfied['extensions']) + "**"
                    
                    await bot.say(failure_message)
                    
                    if unsatisfied['packages']:
                        await bot.say("Do you want to install the new requirements of " + extension + " now? (yes/no)")
                        answer = await bot.wait_for_message(author=ctx.message.author,
                                                            channel=ctx.message.channel,
                                                            check=is_boolean_answer,
                                                            timeout=60)
                        if answer is not None and answer_to_boolean(answer) is True:
                            for package in unsatisfied['packages']:
                                return_code = self.base.install_package(package)
                                if return_code is 0:
                                    unsatisfied['packages'].remove(package)
                                    await bot.say("Installed package '**"
                                                  + package + "**' successfully.")
                                    installed_packages.append(package)
                            
                            if unsatisfied['packages']:
                                await bot.say("Failed to install packages: '**"
                                              + "**', '**".join(unsatisfied['packages']) + "**'.")
                                failed_to_install_packages += unsatisfied['packages']
                                return False
                        else:
                            await bot.say("Alright, I will not install any packages the '**"
                                          + extension + "**' extension requires just now.")
                            failed_to_install_extensions.append(extension)
                            return False
                    
                    if not unsatisfied['packages'] and unsatisfied['extensions']:
                        await bot.say("Do you want to install the new dependencies of '**"
                                      + extension + "**' now? (yes/no)")
                        answer = await bot.wait_for_message(author=ctx.message.author,
                                                            channel=ctx.message.channel,
                                                            check=is_boolean_answer,
                                                            timeout=60)
                        if answer is not None and answer_to_boolean(answer) is True:
                            bot.invoke_command('install', ctx, ' '.join(unsatisfied['extensions']))
                        exts = self.base.get_extensions()
                        for extension_to_check in unsatisfied['extensions']:
                            if extension_to_check in exts:
                                unsatisfied['extensions'].remove(extension_to_check)
                            
                            if unsatisfied['extensions']:
                                await bot.say("Failed to install one or more of '**"
                                              + extension + "**' dependencies.")
                                failed_to_update_extensions.append(extension)
                                return False
                            else:
                                return await _update(extension)
                        else:
                            await bot.say("Alright, I will not install any dependencies just now")
                            failed_to_update_extensions.append(extension)
                            return False
                
                else:
                    await bot.say("The extension '**" + extension + "**' was updated successfully.")
                    updated_extensions.append(extension)
                    return True
        
        for extension in extensions:
            await _update(extension)
        
        completed_message = "Update completed.\n"
        if updated_extensions:
            completed_message += "Updated extensions:\n"
            completed_message += "**" + "**\n**".join(updated_extensions) + "**\n"
        if installed_packages:
            completed_message += "Installed packages:\n"
            completed_message += "**" + "**\n**".join(installed_packages) + "**\n"
        if failed_to_update_extensions:
            completed_message += "Failed to update extensions:\n"
            completed_message += "**" + "**\n**".join(failed_to_update_extensions) + "**\n"
        if failed_to_install_packages:
            completed_message += "Failed to install packages:\n"
            completed_message += "**" + "**\n**".join(failed_to_install_packages) + "**\n"
        await bot.say(completed_message)
        
        if updated_extensions:
            await bot.say("Reboot Dwarf for changes to take effect.\n"
                          "Would you like to restart now? (yes/no)")
            answer = await bot.wait_for_message(author=ctx.message.author,
                                                channel=ctx.message.channel,
                                                check=is_boolean_answer,
                                                timeout=60)
            if answer is not None and answer_to_boolean(answer) is True:
                await bot.say("Okay, I'll be right back!")
                await self.core.restart(restarted_from=ctx.message.channel)

    @commands.command(pass_context=True)
    async def uninstall(self, ctx, *, extensions):
        """Uninstalls extensions."""
        # [p]uninstall <extensions>
        
        bot = self.bot
        
        extensions = extensions.lower().split()
        
        uninstalled_extensions = []
        failed_to_uninstall_extensions = []
        
        async def _uninstall(extension):
            await bot.say("Uninstalling '**" + extension + "**'...")
            await bot.type()
            try:
                to_cascade = self.base.uninstall_extension(extension)
            except ExtensionNotFound:
                await bot.say("The extension '**" + extension + "**' could not be found.")
                failed_to_uninstall_extensions.append(extension)
                return False
            else:
                if to_cascade:
                    await bot.say(strings.would_be_uninstalled_too.format(extension) + "\n"
                                  + "**" + "**\n**".join(to_cascade) + "**")
                    await bot.say(strings.proceed_with_uninstallation)
                    answer = await bot.wait_for_message(author=ctx.message.author,
                                                        channel=ctx.message.channel,
                                                        check=is_boolean_answer,
                                                        timeout=60)
                    if answer is not None and answer_to_boolean(answer) is True:
                        for extension_to_uninstall in to_cascade:
                            return_code = await _uninstall(extension_to_uninstall)
                            if return_code is True:
                                to_cascade.remove(extension_to_uninstall)
                        
                        if to_cascade:
                            await bot.say("Failed to uninstall '**"
                                          + "**', '**".join(to_cascade) + "**'.")
                            failed_to_uninstall_extensions.append(extension)
                            return False

                        else:
                            return await _uninstall(extension)
                    else:
                            await bot.say("Alright, I will not install any extensions just now.")
                            failed_to_uninstall_extensions.append(extension)
                            return False
                
                else:
                    await bot.say("The '**" + extension + "**' extension was uninstalled successfully.")
                    uninstalled_extensions.append(extension)
                    return True
        
        for extension in extensions:
            await _uninstall(extension)
        
        completed_message = "Uninstallation completed.\n"
        if uninstalled_extensions:
            completed_message += "Uninstalled extensions:\n"
            completed_message += "**" + "**\n**".join(uninstalled_extensions) + "**\n"
        if failed_to_uninstall_extensions:
            completed_message += "Failed to uninstall extensions:\n"
            completed_message += "**" + "**\n**".join(failed_to_uninstall_extensions) + "**\n"
        await bot.say(completed_message)
        
        if uninstalled_extensions:
            await bot.say("Reboot Dwarf for changes to take effect.\n"
                    "Would you like to restart now? (yes/no)")
            answer = await bot.wait_for_message(author=ctx.message.author,
                                       channel=ctx.message.channel,
                                       check=is_boolean_answer,
                                       timeout=60)
            if answer is not None and answer_to_boolean(answer) is True:
                await bot.say("Okay, I'll be right back!")
                await self.core.restart(restarted_from=ctx.message.channel)

    @commands.group(name='set', pass_context=True)
    async def set(self, ctx):
        """Group of commands that change the bot's settings."""
        # [p]set <subcommand>

        if ctx.invoked_subcommand is None:
            await self.bot.send_command_help(ctx)
            pass
    
    @commands.group(name='get', pass_context=True)
    async def get(self, ctx):
        """Group of commands that show the bot's settings."""
        # [p]set <subcommand>

        if ctx.invoked_subcommand is None:
            await self.bot.send_command_help(ctx)
            pass

    @commands.group(name='add', pass_context=True)
    async def add(self, ctx):
        """Group of commands that add items to some of the bot's settings."""
        # [p]add <subcommand>
        
        if ctx.invoked_subcommand is None:
            await self.bot.send_command_help(ctx)
            pass

    @commands.group(name='remove', pass_context=True)
    async def remove(self, ctx):
        """Group of commands that remove items from some of the bot's settings."""
        # [p]remove <subcommand>
        
        if ctx.invoked_subcommand is None:
            await self.bot.send_command_help(ctx)
            pass
    
    @commands.group(name='setup', pass_context=True)
    async def setup(self, ctx):
        """Group of commands that configure and prepare things."""
        # [p]setup <subcommand>
        
        if ctx.invoked_subcommand is None:
            await self.bot.send_command_help(ctx)
            pass

    @set.command(pass_context=True)
    @permissions.owner()
    async def name(self, ctx, *, name):
        """Sets the bot's name."""
        # [p]set name <name>

        name = name.strip()
        if name != "":
            try:
                await self.bot.edit_profile(username=name)
            except:
                await self.bot.say("Failed to change name. Remember that you"
                                   " can only do it up to 2 times an hour."
                                   "Use nicknames if you need frequent "
                                   "changes. {}set nickname".format(ctx.prefix))
            else:
                await self.bot.say("Done.")
        else:
            await self.bot.send_command_help(ctx)

    @set.command(pass_context=True)
    @permissions.owner()
    async def nickname(self, ctx, *, nickname=""):
        """Sets the bot's nickname on the current server.
        Leaving this empty will remove it."""
        # [p]set nickname <nickname>

        nickname = nickname.strip()
        if nickname == "":
            nickname = None
        try:
            await self.bot.change_nickname(ctx.message.server.me, nickname)
            await self.bot.say("Done.")
        except discord.Forbidden:
            await self.bot.say("I cannot do that, I lack the "
                               "\"Change Nickname\" permission.")

    @set.command(pass_context=True)
    @permissions.owner()
    async def game(self, ctx, *, game=None):
        """Sets the bot's playing status
        Leaving this empty will clear it."""
        # [p]set game <game>

        server = ctx.message.server

        current_status = server.me.status if server is not None else None

        if game:
            game = game.strip()
            await self.bot.change_presence(game=discord.Game(name=game),
                                           status=current_status)
            await self.bot.say('Game set to "{}".'.format(game))
        else:
            await self.bot.change_presence(game=None, status=current_status)
            await self.bot.say('Not playing a game now.')

    @set.command(pass_context=True)
    @permissions.owner()
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

        server = ctx.message.server

        current_game = server.me.game if server is not None else None

        if status is None:
            await self.bot.change_presence(status=discord.Status.online,
                                           game=current_game)
            await self.bot.say("Status reset.")
        else:
            status = statuses.get(status.lower(), None)
            if status:
                await self.bot.change_presence(status=status,
                                               game=current_game)
                await self.bot.say("Status changed.")
            else:
                await self.bot.send_command_help(ctx)

    @set.command(pass_context=True)
    @permissions.owner()
    async def stream(self, ctx, streamer=None, *, stream_title=None):
        """Sets the bot's streaming status.
        Leaving both streamer and stream_title empty will clear it."""
        # [p]set stream <streamer> <stream_title>

        server = ctx.message.server

        current_status = server.me.status if server is not None else None

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
        await self.bot.say("Done.")

    @set.command(pass_context=True)
    @permissions.owner()
    async def avatar(self, url):
        """Sets the bot's avatar."""
        # [p]set avatar <url>

        try:
            async with self.session.get(url) as r:
                data = await r.read()
            await self.bot.edit_profile(avatar=data)
            await self.bot.say("Done.")
            self.log.debug("Changed avatar.")
        except Exception as e:
            await self.bot.say("Error, check your console or logs for "
                               "more information.")
            self.log.exception(e)
            traceback.print_exc()

    @set.command(pass_context=True)
    @permissions.owner()
    async def token(self, ctx, token):
        """Sets the bot's login token."""
        # [p]set token <token>

        if len(token) > 50:  # assuming token
            self.base.set_token(token)
            await self.bot.say("Token set. Restart Dwarf to use the new token.")
            self.log.info("Bot token changed.")
        else:
            await self.bot.say("Invalid token.")

    @set.command(pass_context=True)
    @permissions.owner()
    async def description(self, ctx, description):
        """Sets the bot's description."""

        self.core.set_description(description)
        await self.bot.say("My description has been set.")

    @set.command(pass_context=True)
    @permissions.owner()
    async def repository(self, ctx, repository):
        """Sets the bot's repository."""
        
        self.core.set_repository(repository)
        await self.bot.say("My repository is now located at:\n<" + repository + ">")

    @set.command(pass_context=True)
    @permissions.owner()
    async def officialinvite(self, ctx, invite):
        """Sets the bot's official server's invite URL."""
        
        self.core.set_official_invite(invite)
        await self.bot.say("My official server invite is now:\n<" + invite + ">")

    @add.command(pass_context=True)
    @permissions.owner()
    async def prefix(self, prefix):
        """Adds a prefix to the bot."""
        
        if prefix.startswith('"') and prefix.endswith('"'):
            prefix = prefix[1:len(prefix) - 1]
        
        try:
            self.core.add_prefix(prefix)
            self.bot.command_prefix = self.core.get_prefixes()
            await self.bot.say("The prefix '**" + prefix + "**' was added successfully.")
        except PrefixAlreadyExists:
            await self.bot.say("The prefix '**" + prefix + "**' could not be added "
                               "as it is already a prefix.")

    @remove.command(pass_context=True)
    @permissions.owner()
    async def prefix(self, ctx, prefix):
        """Removes a prefix from the bot."""
        
        if prefix.startswith('"') and prefix.endswith('"'):
            prefix = prefix[1:len(prefix) - 1]
        
        try:
            self.core.remove_prefix(prefix)
            self.bot.command_prefix = self.core.get_prefixes()
            await self.bot.say("The prefix '**" + prefix + "**' was removed successfully.")
        except PrefixNotFound:
            await self.bot.say("The prefix '**" + prefix + "**' could not be found.")

    @get.command(pass_context=True)
    @permissions.owner()
    async def prefixes(self, ctx):
        """Shows the bot's prefixes."""
        
        prefixes = self.core.get_prefixes()
        if len(prefixes) > 1:
            await self.bot.say("My prefixes are: '**" + "**', '**".join(prefixes) + "**'")
        else:
            await self.bot.say("My prefix is '**" + prefixes[0] + "**'.")

    @commands.command(pass_context=True)
    async def ping(self, ctx):
        """Calculates the ping time."""
        # [p]ping
        
        t1 = time.perf_counter()
        await self.bot.send_typing(ctx.message.channel)
        t2 = time.perf_counter()
        await self.bot.say("Pong.\nTime: " + str(round((t2-t1)*1000)) + "ms")

    async def on_shutdown_message(self, message):
        self.core.disable_restarting()
        print("Shutting down...")
        await self.bot.logout()
    
    async def on_restart_message(self, allow_restart):
        print("Restarting...")
        await self.bot.logout()
        print("Logged out.")
    
    @commands.command(pass_context=True)
    @permissions.owner()
    async def shutdown(self, ctx):
        """Shuts down Dwarf."""
        # [p]shutdown
        
        await self.bot.say("Goodbye!")
        await self.core.shutdown()
    
    @commands.command(pass_context=True)
    @permissions.owner()
    async def restart(self, ctx):
        """Restarts Dwarf."""
        # [p]restart
        
        await self.bot.say("I'll be right back!")
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

    async def on_logout(self):
        self.bot.stop_loop()
        if not self.base.restarting_enabled:
            self.bot.loop.close()

    @commands.command(pass_context=True, no_pm=True)
    @permissions.owner()
    async def leave(self, ctx):
        """Makes the bot leave the current server."""
        # [p]leave

        message = ctx.message

        await self.bot.say("Are you sure you want me to leave this server? "
                           "Type yes to confirm.")
        response = await self.bot.wait_for_message(author=message.author, timeout=30)

        if response is not None:
            if response.content.lower().strip() == "yes":
                await self.bot.say("Alright. Bye :wave:")
                self.log.debug('Leaving "{}"'.format(message.server.name))
                await self.bot.leave_server(message.server)
        else:
            await self.bot.say("Ok I'll stay here then.")

    @commands.command(pass_context=True)
    @permissions.owner()
    async def servers(self, ctx):
        """Lists and allows to leave servers."""
        # [p]servers

        owner = ctx.message.author
        servers = list(self.bot.servers)
        server_list = {}
        msg = ""
        for i in range(0, len(servers)):
            server_list[str(i)] = servers[i]
            msg += "{}: {}\n".format(str(i), servers[i].name)
        msg += "\nTo leave a server just type its number."
        for page in f.pagify(msg, ['\n']):
            await self.bot.say(page)
        while msg is not None:
            msg = await self.bot.wait_for_message(author=owner, timeout=15)
            if msg is not None:
                msg = msg.content.strip()
                if msg in server_list.keys():
                    await self.leave_confirmation(server_list[msg], owner, ctx)
                else:
                    break
            else:
                break

    @commands.command(pass_context=True)
    async def contact(self, ctx, *, message : str):
        """Sends message to the owner of the bot."""
        # [p]contact <message>

        owner_id = self.core.get_owner_id()
        if owner_id is None:
            await self.bot.say("I have no owner set.")
            return
        owner = await self.bot.get_user_info(owner_id)
        author = ctx.message.author
        if not ctx.message.channel.is_private:
            server = ctx.message.server
            source = ", server **{}** ({})".format(server.name, server.id)
        else:
            source = ", direct message"
        sender = "From **{}** ({}){}:\n\n".format(author, author.id, source)
        message = sender + message
        try:
            await self.bot.send_message(owner, message)
        except discord.errors.InvalidArgument:
            await self.bot.say("I cannot send your message, I'm unable to find "
                               "my owner... *sigh*")
        except discord.errors.HTTPException:
            await self.bot.say("Your message is too long.")
        except:
            await self.bot.say("I'm unable to deliver your message. Sorry.")
        else:
            await self.bot.say("Your message has been sent.")

    @commands.command()
    async def about(self):
        """Shows information about the bot."""
        # [p]info

        await self.bot.say("{}\n"
                           "**Repository:**\n"
                           "<{}>\n"
                           "**Official server:**\n"
                           "<{}>".format(self.core.get_description(),
                                         self.core.get_repository(),
                                         self.core.get_official_invite()))

    async def leave_confirmation(self, server, owner, ctx):
        if not ctx.message.channel.is_private:
            current_server = ctx.message.server
        else:
            current_server = None
        answers = ("yes", "y")
        await self.bot.say("Are you sure you want me "
                           "to leave **{}**? (yes/no)".format(server.name))
        msg = await self.bot.wait_for_message(author=owner, timeout=15)
        if msg is None:
            await self.bot.say("I'll stay then.")
        elif msg.content.lower().strip() in answers:
            await self.bot.leave_server(server)
            if server != current_server:
                await self.bot.say("Done.")
        else:
            await self.bot.say("Alright then.")

    @commands.command()
    async def version(self):
        """Shows the bot's current version"""
        # [p]version

        await self.bot.say("Current version: " + self.base.get_dwarf_version())


def setup(bot):
    core_cog = Core(bot)
    bot.loop.create_task(core_cog.core.cache.subscribe('shutdown', 1))
    bot.loop.create_task(core_cog.core.cache.subscribe('restart', 1))
    bot.add_cog(core_cog)
