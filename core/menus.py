import discord
from discord.ext import commands

import asyncio


class Menu(discord.Embed):
    """
    Represents an interactive menu to represent data in an interactive way.

    Attaching a message by setting the `message` attribute starts the menu without explicitly telling it to start.

    Parameters
    ----------
    options : Dict[Union[str, int], Callable]
        Dictionary of emoji and callbacks which will be called on the reaction with the emoji being clicked.
        To use custom emoji simply pass the emojis ID instead of a string.
    bot : commands.Bot
        The Bot the menu runs on.
    users : List[Union[discord.Member, discord.User]]
        The users the menu interacts with.
    close_emoji : Optional[str]
        The emoji used to close the menu. By default this is a unicode stop sign.
    timeout : Optional[int]
        The amount of seconds to wait for a reaction before the menu closes itself,
        unless any submenus are still open, in which case the timeout will be waited again. Defaults to 60 seconds.
    delete_after : bool
        Whether the message associated with the menu should be deleted when the menu closes. Defaults to true.

    Attributes
    ----------
    parent : Optional[Menu]
        The parent menu of this menu, None if none exists.
    children : List[Menu]
        Child menus of this menu.
    message : discord.Message
        The message the menu operates on.
    is_closed : bool
        Whether the menu is active and waiting for reactions or has been closed.
    closed : asyncio.Event
        An event that is fired when this menu is closed.
    """

    def __init__(self, options, bot, users, close_emoji=None, timeout=60, delete_after=True, **kwargs):
        super().__init__(**kwargs)

        if not isinstance(self.color, discord.Color) or self.color == discord.Color.default():
            self._modified_color = True
            self.color = discord.Color.blurple()
        else:
            self._modified_color = False

        self.bot = bot
        self.users = users

        default_opts = {close_emoji if close_emoji is not None else '\N{BLACK SQUARE FOR STOP}': self.close}
        self.options = default_opts.update(options)

        self.is_closed = False
        self.timeout = timeout
        self.delete_after = delete_after

        self.parent = None
        self.children = []

        self._message = None
        self._waiter = None

        self.closed = asyncio.Event()

    @property
    def message(self):
        return self._message

    @message.setter
    def message(self, message):
        self._waiter = self.bot.loop.create_task(self._wait_for_reaction())
        self._message = message

    def add_submenu(self, menu):
        """Add a submenu, this prevents the main menu from closing until the submenu is closed."""

        self.children.append(menu)

    async def run(self):
        """Wait for the menu to close, if it's already closed this will reopen it."""

        if self.closed.is_set():
            self.closed.clear()

            if self._modified_color:
                self.color = discord.Color.blurple()

            self._waiter = self.bot.loop.create_task(self._wait_for_reaction())

        await self.closed.wait()

    async def _add_reactions(self):
        for emoji in self.options:

            if isinstance(emoji, int):
                emoji = self.bot.get_emoji(emoji)

            await self.message.add_reaction(emoji)

    async def _wait_for_reaction(self):
        def check(reaction: discord.Reaction, user: discord.User) -> bool:
            if reaction.message.id != self.message.id:
                return False

            if not any(x.id == user.id for x in self.users):
                return False

            if reaction.custom_emoji:
                return reaction.emoji.id in self.options

            return reaction.emoji.name in self.options

        self.bot.loop.create_task(self._add_reactions())

        while not self.is_closed:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', check=check, timeout=self.timeout)
            except asyncio.TimeoutError:
                if any(not x.closed for x in self.children):
                    continue  # if any children are still open don't close the menu - just wait again

                await self.close(self)
                return

            coro = self.options[reaction.emoji.id if reaction.custom_emoji else reaction.emoji.name]
            self.bot.loop.create_task(coro(self))

            channel = self.message.channel

            if not hasattr(channel, 'guild') or not channel.permissions_for(self.message.guild.me).manage_messages:
                continue

            coro = self.message.remove_reaction(reaction.emoji, user)
            self.bot.loop.create_task(coro)

    async def close(self, _):
        """Close the menu and all children."""
        self.closed.set()
        self.is_closed = True

        self._waiter.cancel()
        await asyncio.gather(*[x.close() for x in self.children])

        if self.delete_after:
            await self.message.delete()
        else:
            # reset the color of the embed in the message
            current_color = self.color

            self.color = discord.Color.default()
            await self.message.edit(embed=self)

            # in case we restart the menu
            self.color = current_color

        if not self._modified_color:
            return

        self.color = discord.Color.default()
