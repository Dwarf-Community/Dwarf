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
            await self.bot.say(f.block(type(e).__name__ + ': ' + str(e)), 'py')
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
                unsatisfied = base.install_extension(extension, repository)
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
        if installed_extensions:
            completed_message += "Reboot Dwarf for changes to take effect."
        
        await bot.say(completed_message)

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
                unsatisfied = base.update_extension(extension)
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
                        exts = base.get_extensions()
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
            completed_message += "