import discord
from discord.ext import commands

from dwarf import permissions
from dwarf.api import CoreAPI, CacheAPI
from dwarf.formatting import pagify
from dwarf.models import User
from dwarf.bot import send_command_help
from dwarf.strings import management as strings

import asyncio
import logging
import traceback
import aiohttp


log = logging.getLogger("dwarf.management")


class Management:
    """All owner-only commands that relate to bot management operations."""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession(loop=self.bot.loop)

    @commands.command(pass_context=True, hidden=True)
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

        result = python.format(result)
        if not ctx.message.channel.is_private:
            censor = CacheAPI.get(key='dwarf_token')
            r = "[EXPUNGED]"
            for w in censor:
                if w != "":
                    result = result.replace(w, r)
                    result = result.replace(w.lower(), r)
                    result = result.replace(w.upper(), r)
        await self.bot.say(result)

    @commands.group(name="set", pass_context=True)
    async def set(self, ctx):
        """Group of commands that change the bot's settings."""
        # [p]set <subcommand>

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
    async def token(self, token):
        """Sets the bot's login token."""
        # [p]set token <token>

        if len(token) < 50:
            await self.bot.say("Invalid token.")
        else:
            CacheAPI.set(key='dwarf_token', value=token, timeout=None)
            await self.bot.say("Token set. Restart me.")
            log.debug("Token changed.")

    @set.command(pass_context=True)
    @permissions.owner()
    async def shutdown(self):
        """Shuts down Dwarf."""
        # [p]shutdown

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
        """Leaves server"""
        # [p]leave

        message = ctx.message

        await self.bot.say("Are you sure you want me to leave this server?"
                           " Type yes to confirm.")
        response = await self.bot.wait_for_message(author=message.author, timeout=15)

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
        """Lists and allows to leave servers"""
        # [p]servers

        owner = ctx.message.author
        servers = list(self.bot.servers)
        server_list = {}
        msg = ""
        for i in range(0, len(servers)):
            server_list[str(i)] = servers[i]
            msg += "{}: {}\n".format(str(i), servers[i].name)
        msg += "\nTo leave a server just type its number."
        for page in pagify(msg, ['\n']):
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
        """Sends message to the owner"""
        # [p]contact

        if not User.objects.get(is_owner=True).exists():
            await self.bot.say("I have no owner set.")
            return
        owner = User.objects.get(is_owner=True)[0].id
        author = ctx.message.author
        if ctx.message.channel.is_private is False:
            server = ctx.message.server
            source = ", server **{}** ({})".format(server.name, server.id)
        else:
            source = ", direct message"
        sender = "From **{}** ({}){}:\n\n".format(author, author.id, source)
        message = sender + message
        try:
            await self.bot.send_message(owner, message)
        except discord.errors.InvalidArgument:
            await self.bot.say("I cannot send your message, I'm unable to find"
                               " my owner... *sigh*")
        except discord.errors.HTTPException:
            await self.bot.say("Your message is too long.")
        except:
            await self.bot.say("I'm unable to deliver your message. Sorry.")
        else:
            await self.bot.say("Your message has been sent.")

    @commands.command()
    async def info(self):
        """Shows info about the bot"""
        # [p]info

        await self.bot.say(strings.info.format(
            CacheAPI.get(key='dwarf_repository'),
            CacheAPI.get(key='dwarf_invite_link')))

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

        await self.bot.say("Current version: " + CoreAPI.get_version())


def setup(bot):
    bot.add_cog(Management(bot))
