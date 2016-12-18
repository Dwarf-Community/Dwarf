import discord
from discord.ext import commands

from dwarf import permissions
from dwarf import formatting as f
from dwarf.api import BaseAPI, ExtensionAlreadyInstalled, ExtensionNotFound, ExtensionNotInIndex
from dwarf.bot import send_command_help
from dwarf.utils import answer_to_boolean, is_boolean_answer
from .api import CoreAPI, PrefixAlreadyExists, PrefixNotFound
from . import strings

import asyncio
import logging
import traceback
import aiohttp
import time


log = logging.getLogger('dwarf.core')

base = BaseAPI()
core = CoreAPI()


class Core:
    """All commands that relate to management operations."""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession(loop=self.bot.loop)

    @commands.command(name='eval', pass_context=True, hidden=True)
    @permissions.owner()
    async def evaluate(self, ctx, *, code):
        """Evaluates code.
        Modified function, originally made by Rapptz"""
        # [p]evaluate <code>

        code = code.strip('` ')
        python = '```py\n{}\n```'
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
            await self.bot.say(python.format(type(e).__name__ + ': ' + str(e)))
            return

        if asyncio.iscoroutine(result):
            result = await result

        result = f.block(result, 'py')
        if not ctx.message.channel.is_private:
            censor = base.get_token()
            r = "[EXPUNGED]"
            for w in censor:
                if w != "":
                    result = result.replace(w, r)
                    result = result.replace(w.lower(), r)
                    result = result.replace(w.upper(), r)
        await self.bot.say(result)

    @commands.command(pass_context=True)
    async def install(self, ctx, *, extensions):
        """Installs an extension."""
        
        bot = self.bot
        
        extensions = extensions.lower().split()
        
        installed_extensions = []
        installed_packages = []
        failed_to_install_extensions = []
        failed_to_install_packages = []
        
        async def _install(extension):
            await bot.say("Installing '**" + extension + "**'...")
            await bot.type()
            try:
                unsatisfied = base.install_extension(extension)
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
                                return_code = base.install_package(package)
                                if return_code is 0:
                                    unsatisfied['packages'].remove(package)
                                    await bot.say("Installed package '**"
                                                  + package + "**' successfully.")
                                    installed_packages.append(package)
                            
                            if unsatisfied['packages']:
                                self.bot.say("Failed to install packages: '**"
                                             + "**', '**".join(unsatisfied['packages']) + "**'.")
                                failed_to_install_packages += unsatisfied['packages']
                                return False
                        else:
                            await bot.say("Alright, I will not install any packages the '**"
                                          + extension + "**' extension depends on just now.")
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
        if installed_extensions:
            completed_message += "Reboot Dwarf for changes to take effect."
        
        await bot.say(completed_message)

    @commands.command(pass_context=True)
    async def uninstall(self, ctx, *, extensions):
        """Uninstalls an extension."""
        
        bot = self.bot
        
        extensions = extensions.lower().split()
        
        uninstalled_extensions = []
        failed_to_uninstall_extensions = []
        
        async def _uninstall(extension):
            await bot.say("Uninstalling '**" + extension + "**'...")
            await bot.type()
            try:
                to_cascade = base.uninstall_extension(extension)
            except ExtensionNotFound:
                await bot.say("The extension '**" + extension + "**' is not installed.")
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
                                to_cascade.remove(_extension)
                        
                        if to_cascade:
                            await bot.say("Failed to uninstall '**"
                                          + "**', '**".join(to_cascade) + "**'.")
                            return False
                            failed_to_uninstall_extensions.append(extension)
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
        if uninstalled_extensions:
            completed_message += "Reboot Dwarf for changes to take effect."
        
        await bot.say(completed_message)

    @commands.group(name="set", pass_context=True)
    async def set(self, ctx):
        """Group of commands that change the bot's settings."""
        # [p]set <subcommand>

        if ctx.invoked_subcommand is None:
            await send_command_help(ctx)
            pass
    
    @commands.group(name="get", pass_context=True)
    async def get(self, ctx):
        """Group of commands that show the bot's settings."""
        # [p]set <subcommand>

        if ctx.invoked_subcommand is None:
            await send_command_help(ctx)
            pass

    @commands.group(name="add", pass_context=True)
    async def add(self, ctx):
        """Group of commands that add items to some of the bot's settings."""
        # [p]add <subcommand>
        
        if ctx.invoked_subcommand is None:
            await send_command_help(ctx)
            pass

    @commands.group(name="remove", pass_context=True)
    async def remove(self, ctx):
        """Group of commands that remove items from some of the bot's settings."""
        # [p]remove <subcommand>
        
        if ctx.invoked_subcommand is None:
            await send_command_help(ctx)
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
            await send_command_help(ctx)

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
                await send_command_help(ctx)

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
            log.debug('Owner has set streaming status and url to "{}" and {}'.format(stream_title, streamer))
        elif streamer is not None:
            await send_command_help(ctx)
            return
        else:
            await self.bot.change_presence(game=None, status=current_status)
            log.debug('stream cleared by owner')
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
            log.debug("Changed avatar.")
        except Exception as e:
            await self.bot.say("Error, check your console or logs for "
                               "more information.")
            log.exception(e)
            traceback.print_exc()

    @set.command(pass_context=True)
    @permissions.owner()
    async def token(self, ctx, token):
        """Sets the bot's login token."""
        # [p]set token <token>

        if len(token) < 50:
            await self.bot.say("Invalid token.")
        else:
            base.set_token(token)
            await self.bot.say("Token set. Restart me.")
            log.debug("Token changed.")

    @set.command(pass_context=True)
    @permissions.owner()
    async def repo(self, ctx, repository):
        """Sets the bot's repository."""
        
        core.set_repository(repository)
        await self.bot.say("My repository is now located at:\n<" + repository + ">")

    @set.command(pass_context=True)
    @permissions.owner()
    async def officialinvite(self, ctx, invite):
        """Sets the bot's official server's invite URL."""
        
        core.set_official_invite(invite)
        await self.bot.say("My official server invite is now:\n<" + invite + ">")

    @add.command(pass_context=True)
    @permissions.owner()
    async def prefix(self, prefix):
        """Adds a prefix to the bot."""
        
        if prefix.startswith('"') and prefix.endswith('"'):
            prefix = prefix[1:len(prefix)-1]
        
        try:
            core.add_prefix(prefix)
            self.bot.command_prefix = core.get_prefixes()
            await self.bot.say("The prefix '**" + prefix + "**' was added successfully.")
        except PrefixAlreadyExists:
            await self.bot.say("The prefix '**" + prefix + "**' could not be added "
                               "as it is already a prefix.")

    @remove.command(pass_context=True)
    @permissions.owner()
    async def prefix(self, ctx, prefix):
        """Removes a prefix from the bot."""
        
        if prefix.startswith('"') and prefix.endswith('"'):
            prefix = prefix[1:len(prefix)-1]
        
        try:
            core.remove_prefix(prefix)
            self.bot.command_prefix = core.get_prefixes()
            await self.bot.say("The prefix '**" + prefix + "**' was removed successfully.")
        except PrefixNotFound:
            await self.bot.say("The prefix '**" + prefix + "**' could not be found.")

    @get.command(pass_context=True)
    @permissions.owner()
    async def prefixes(self, ctx):
        """Shows the bot's prefixes."""
        
        prefixes = core.get_prefixes()
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

    @commands.command(pass_context=True)
    @permissions.owner()
    async def shutdown(self):
        """Shuts down Dwarf."""
        # [p]shutdown

        
        await self.bot.say("I'll be right back!")
        await self.bot.logout()

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
                log.debug('Leaving "{}"'.format(message.server.name))
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

        owner_id = core.get_owner_id()
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

        await self.bot.say(strings.info.format(
            core.get_repository(),
            core.get_official_invite()))

    async def leave_confirmation(self, server, owner, ctx):
        if not ctx.message.channel.is_private:
            current_server = ctx.message.server
        else:
            current_server = None
        answers = ("yes", "y")
        await self.bot.say("Are you sure you want me "
                           "to leave {}? (yes/no)".format(server.name))
        msg = await self.bot.wait_for_message(author=owner, timeout=15)
        if msg is None:
            await self.bot.say("I guess not.")
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

        await self.bot.say("Current version: " + base.get_dwarf_version())


def setup(bot):
    bot.add_cog(Core(bot))
