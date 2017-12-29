import discord
from discord.ext import commands

from .controller import BaseController
from .cache import Cache
from .core.controller import CoreController
from .models import Guild, Channel, User
from . import strings, utils

import os
import traceback
import asyncio


class Bot(commands.Bot):
    """Represents a Discord bot."""

    def __init__(self, loop=None):
        self.base = BaseController()
        self.core = CoreController()
        super().__init__(command_prefix=self.core.get_prefixes(), loop=loop, description=self.core.get_description(),
                         pm_help=None, cache_auth=False, command_not_found=strings.command_not_found,
                         command_has_no_subcommands=strings.command_has_no_subcommands)
        self.cache = Cache(bot=self)
        self.add_check(self.user_allowed)

    @property
    def is_configured(self):
        if self.base.get_token() is None:
            return False
        else:
            return True

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
        print("\n{} active cogs".format(len(self.base.get_extensions())))
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
        await self.close()
        self.dispatch('logout')
    
    def stop_loop(self):
        def silence_gathered(future):
            try:
                future.result()
            finally:
                self.loop.stop()

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
            self.load_extension('dwarf.' + cogname + '.cog')

        load_cog('core')

        core_cog = self.get_cog('Core')
        if core_cog is None:
            raise ImportError("Could not find the Core cog.")

        failed = []
        cogs = self.base.get_extensions()
        for cog in cogs:
            try:
                load_cog(cog)
            except Exception as e:
                print("{}: {}".format(e.__class__.__name__, str(e)))
                failed.append(cog)

        if failed:
            print("\nFailed to load: " + ", ".join(failed))

        return core_cog

    def user_allowed(self, ctx):
        # bots are not allowed to interact with other bots
        if ctx.message.author.bot:
            return False

        if self.core.get_owner_id() == ctx.message.author.id:
            return True

        # TODO

        return True

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
        self.load_cogs()
        if self.core.get_prefixes():
            self.command_prefix = list(self.core.get_prefixes())
        else:
            print(strings.no_prefix_set)
            self.command_prefix = ["!"]

        print(strings.logging_into_discord)
        print(strings.keep_updated.format(self.command_prefix[0]))
        print(strings.official_server.format(strings.invite_link))

        await self.start(self.base.get_token())


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
