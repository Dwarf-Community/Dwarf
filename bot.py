"""A Discord bot by AileenLumina, written on top of discord.py and Django."""

import aiohttp
import discord
from discord.ext import commands
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist

from .api import BaseAPI
from .core.api import CoreAPI
from .models import Guild, Channel
from . import strings

import sys
import traceback
import asyncio


base = BaseAPI()
core = CoreAPI()

def force_input(msg):
    entered_input = input(msg)
    if entered_input:
        return entered_input
    return force_input(msg)


def get_answer():
    choices = ("yes", "y", "no", "n")
    c = ""
    while c not in choices:
        c = input(">").lower()
    if c is choices[0] or c is choices[1]:
        return True
    else:
        return False


def is_configured():
    if base.get_token() is None:
        return False
    else:
        return True


def initial_config():
    print(strings.setup_greeting)

    entered_token = input("> ")

    if len(entered_token) >= 50:  # assuming token
        base.set_token(entered_token)
    else:
        print(strings.not_a_token)
        exit(1)

    confirmation = False
    while not confirmation:
        print(strings.choose_prefix)
        new_prefix = force_input("\n> ").strip()
        print(strings.confirm_prefix.format(new_prefix))
        if input("> ") in ['y', 'yes']:
            core.add_prefix(new_prefix)
            confirmation = True

    print(strings.setup_finished)
    input("\n")


class Bot(commands.Bot):
    async def logout(self):
        await self.close()
        self._is_logged_in.clear()
        self.dispatch('logout')
    
    def clear_loop(self):
        def silence_gathered(future):
            try:
                future.result()
            finally:
                print("stopping loop...")
                loop.stop()
                print("loop stopped!")

        # cancel lingering tasks
        pending = asyncio.Task.all_tasks(loop=self.loop)
        if pending:
            gathered = asyncio.gather(*pending, loop=self.loop)
            gathered.add_done_callback(silence_gathered)
            gathered.cancel()
        else:
            self.loop.stop()
    
    def load_cogs(self):
        def load_cog(cogname):
            self.load_extension('dwarf.' + cogname + '.commands')

        load_cog('core')

        core_cog = self.get_cog('Core')
        if core_cog is None:
            raise ImportError("Could not find the Core cog.")

        failed = []
        cogs = base.get_extensions()
        for cog in cogs:
            try:
                load_cog(cog)
            except Exception as e:
                print("{}: {}".format(e.__class__.__name__, str(e)))
                failed.append(cog)

        if failed:
            print("\nFailed to load: " + ", ".join(failed))

        return core_cog
    
    def subcommand(self, command_group, cog='Core'):
        """A decorator that adds a command to a command group.
        
        Parameters
        ----------
        command_group : str
            The name of the command group to add the decorated command to.
        cog : str
            The name of the cog the command group belongs to. Defaults to 'Core'.
        """
        
        def command_as_subcommand(command):
            cog_obj = self.get_cog(cog)
            getattr(cog_obj, command_group).add_command(command)
            return command
        
        return command_as_subcommand

    async def wait_for_choice(self, author, channel, message, choices : iter, timeout=0):
        choice_format = "**{}**: {}"
        choice_messages = []
        def choice_check(message):
            return int(message.content[0]) - 1 in range(len(choices))
        
        for i in range(choices):
            choice_messages.append(choice_format.format(i + 1, choices[i]))
        
        choices_message = "\n".join(choice_messages)
        final_message = "{}\n\n{}".format(message, choices_message)
        await self.send_message(channel, final_message)
        return await self.wait_for_message(author=author, channel=channel,
                                           check=choice_check, timeout=timeout)


def user_allowed(message):

    # bots are not allowed to interact with other bots
    if message.author.bot:
        return False

    if core.get_owner_id() == message.author.id:
        return True
    
    # TODO

    return True


async def send_command_help(ctx):
    if ctx.invoked_subcommand:
        pages = ctx.bot.formatter.format_help_for(ctx, ctx.invoked_subcommand)
        for page in pages:
            await ctx.bot.send_message(ctx.message.channel, page)
    else:
        pages = ctx.bot.formatter.format_help_for(ctx, ctx.command)
        for page in pages:
            await ctx.bot.send_message(ctx.message.channel, page)


async def get_oauth_url(bot):
    try:
        data = await bot.application_info()
    except AttributeError:
        return strings.update_the_api
    return discord.utils.oauth_url(data.id)


async def set_bot_owner(bot):
    try:
        data = await bot.application_info()
        core.set_owner_id(data.owner.id)
    except AttributeError:
        print(strings.update_the_api)
        raise
    print(strings.owner_recognized.format(data.owner.name))


async def run(bot):
    bot.load_cogs()
    if core.get_prefixes():
        bot.command_prefix = list(core.get_prefixes())
    else:
        print(strings.no_prefix_set)
        bot.command_prefix = ["!"]

    print(strings.logging_into_discord)
    print(strings.keep_updated.format(bot.command_prefix[0]))
    print(strings.official_server.format(strings.invite_link))

    try:
        await bot.login(base.get_token())
    except TypeError as e:
        print(e)
        print(strings.update_the_api)
        sys.exit(1)

    await bot.connect()


def main(loop=None):
    if loop is None:
        loop = asyncio.get_event_loop()
    
    bot = Bot(loop=loop, command_prefix=core.get_prefixes(), description=__doc__, pm_help=core.is_help_private())
    
    if not is_configured():
        initial_config()

    error = False
    error_message = ""
    try:
        loop.run_until_complete(run(bot))
    except discord.LoginFailure:
        error = True
        error_message = 'Invalid credentials'
        choice = input(strings.invalid_credentials)
        if choice.strip() == 'reset':
            base.delete_token()
        else:
            base.disable_restarting()
    except KeyboardInterrupt:
        base.disable_restarting()
        loop.run_until_complete(bot.logout())
    except Exception as e:
        error = True
        print(e)
        error_message = traceback.format_exc()
        base.disable_restarting()
        loop.run_until_complete(bot.logout())
    finally:
        if error:
            print(error_message)
