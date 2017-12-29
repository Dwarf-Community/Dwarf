import discord

from dwarf.cache import Cache
from dwarf.models import User, Guild, Channel, Role, Member, Message


class PrefixNotFound(Exception):
    """Raised when a prefix was searched for but could not be found."""
    pass


class PrefixAlreadyExists(Exception):
    """Raised when a prefix equal to one that already exists would be added."""
    pass


class CoreController:
    """Transforms Discord objects into Dwarf objects
    that are connected to the database backend.
    Also provides some basic management and settings functions.
    
    Parameters
    ----------
    bot
        The bot that will be restarted, shut down etc.
    
    Attributes
    ----------
    cache : :class:`Cache`
        The cache backend connection of the controller.
    bot
        The bot that will be restarted, shut down etc.
    """

    def __init__(self, bot=None):
        self.cache = Cache(bot=bot)
        self.bot = bot

    def enable_restarting(self):
        """Makes Dwarf restart whenever it is terminated until `disable_restarting` is called."""
        
        return self.cache.set('is_supposed_to_be_running', True)
    
    def disable_restarting(self):
        """Prevents Dwarf from restarting for the rest of the current session."""
        
        return self.cache.set('is_supposed_to_be_running', False)
    
    def restarting_enabled(self):
        """Checks if Dwarf should be restarted when terminated."""
        
        return self.cache.get('is_supposed_to_be_running', False)
    
    def get_restarted_from(self):
        """Gets the ID of the channel the bot was restarted from."""
        
        return self.cache.get('restarted_from')
    
    def set_restarted_from(self, channel):
        """Sets the channel the bot was restarted from."""
        
        if isinstance(channel, discord.TextChannel) or isinstance(channel, discord.DMChannel):
            channel = channel.id
        return self.cache.set('restarted_from', channel)
    
    def reset_restarted_from(self):
        """Resets the channel the bot was restarted from."""
        
        self.cache.delete('restarted_from')
    
    async def restart(self, restarted_from=None):
        """Triggers the bot to restart itself."""
        
        if restarted_from is not None:
            self.set_restarted_from(restarted_from)
        await self.cache.publish('restart')
    
    async def shutdown(self):
        """Triggers the bot to shutdown."""
        
        await self.cache.publish('shutdown')
    
    def get_prefixes(self):
        """Returns a list of the bot's prefixes."""
        
        return self.cache.get('prefixes', default=[])

    def set_prefixes(self, prefixes, bot=None):
        """Sets the bot's prefixes.
        
        Parameters
        ----------
        prefixes
            A list of `str`s that represent prefixes.
        bot
            A `Bot` whose prefixes should be set to `prefixes`.
        """
        
        if bot is not None:
            bot.command_prefix = prefixes
        self.cache.set('prefixes', prefixes)

    def add_prefix(self, prefix, bot=None):
        """Adds a prefix to the bot's prefixes.
        
        Parameters
        ----------
        prefix
            The prefix to add to the `bot`'s prefixes.
        bot
            The `Bot` whose prefixes to add the `prefix` to.
        """
        
        prefixes = self.get_prefixes()
        if prefix in prefixes:
            raise PrefixAlreadyExists
        prefixes.append(prefix)
        self.set_prefixes(prefixes, bot=bot)

    def remove_prefix(self, prefix, bot=None):
        """Removes a prefix from the bot's prefixes.
        
        Parameters
        ----------
        prefix
            The prefix to remove from the `bot`'s prefixes.
        bot
            The `Bot` whose prefixes to remove the `prefix` from.
        """
        
        prefixes = self.get_prefixes()
        if prefix not in prefixes:
            raise PrefixNotFound
        prefixes.remove(prefix)
        self.set_prefixes(prefixes, bot=bot)

    def get_owner_id(self):
        return self.cache.get('owner')

    def set_owner_id(self, user_id):
        self.cache.set('owner', user_id)

    def get_description(self):
        """Retrieves a description about the application."""

        return self.cache.get('description')

    def set_description(self, description):
        """Retrieves a description about the application."""

        return self.cache.set('description', description)

    def get_repository(self):
        """Retrieves Dwarf's official repository's URL."""
        
        return self.cache.get('repository')

    def set_repository(self, repository):
        """Sets Dwarf's official repository.
        
        Parameters
        ----------
        repository
            The repository's URL.
        """
        
        self.cache.set('repository', repository)

    def get_official_invite(self):
        """Retrieves the invite link to the Dwarf instance's official guild."""
        
        return self.cache.get('official_invite')

    def set_official_invite(self, invite_link):
        """Sets the invite link to the bot's official guild.
        
        Parameters
        ----------
        invite_link
            The URL to set the Dwarf instance's official guild's invite link to.
        """
        
        self.cache.set('official_invite', invite_link)

    @staticmethod
    def get_user(user):
        """Retrieves a Dwarf `User` object from the database.
        
        Parameters
        ----------
        user
            Can be a Discord `User` object or `Member` object, or a user ID.
        """
        
        if isinstance(user, discord.User) or isinstance(user, discord.Member):
            return User.objects.get_or_create(id=user.id)
        else:
            return User.objects.get_or_create(id=user)

    @staticmethod
    def user_is_registered(user):
        """Checks whether a ˋUserˋ is registered in the database.
        
        Parameters
        ----------
        user
            Can be a Discord `User` object or `Member` object, or a user ID.
        """
        
        if isinstance(user, discord.User) or isinstance(user, discord.Member):
            try:
                User.objects.get(id=user.id)
                return True
            except User.DoesNotExist:
                return False
        else:
            try:
                User.objects.get(id=user)
                return True
            except User.DoesNotExist:
                return False

    @staticmethod
    def get_guild(guild):
        """Retrieves a Dwarf `Guild` object from the database.
        
        Parameters
        ----------
        guild  
            Can be a Discord `guild` object or a guild ID.
        """

        if isinstance(guild, discord.Guild):
            return Guild.objects.get(id=guild.id)
        else:
            return Guild.objects.get(id=guild)

    @staticmethod
    def new_guild(guild):
        """Creates a new Dwarf ˋGuildˋ object and connects it to the database.
        
        Parameters
        ----------
        guild
            Can be a Discord ˋguildˋ object or a guild ID.
        """
        
        if isinstance(guild, discord.Guild):
            return Guild(id=guild.id)
        else:
            return Guild(id=guild)

    @staticmethod
    def get_channel(channel):
        """Retrieves a Dwarf ˋChannelˋ object from the database.
        
        Parameters
        ----------
        channel
            Can be a Discord ˋChannelˋ object or a channel ID.
        """

        if isinstance(channel, discord.TextChannel):
            return Channel.objects.get(id=channel.id)
        else:
            return Channel.objects.get(id=channel)

    def new_channel(self, channel, guild=None):
        """Creates a new Dwarf ˋChannelˋ object and connects it to the database.
        
        Parameters
        ----------
        channel
            Can be a Discord ˋChannelˋ object or a channel ID.
        guild : Optional
            Can be a Discord ˋguildˋ object or a guild ID.
            Is not an optional parameter if ˋchannelˋ is not a Discord ˋChannelˋ object.
        """
        
        if isinstance(channel, discord.TextChannel):
            return Channel(id=channel.id, guild=channel.guild.id)
        else:
            if guild is None:
                raise ValueError("Either a Channel object or both channel ID "
                                 "and guild ID must be given as argument(s).")
            return Channel(id=channel, guild=guild)
    
    def get_role(self, role):
        """Retrieves a Dwarf ˋChannelˋ object from the database.
        
        Parameters
        ----------
        role
            Can be a Discord ˋRoleˋ object or a role ID.
        """
        
        if isinstance(role, discord.Role):
            return Role.objects.get(id=role.id)
        else:
            return Role.objects.get(id=role)

    def new_role(self, role, guild=None):
        """Creates a new Dwarf ˋRoleˋ object and connects it to the database.
        
        Parameters
        ----------
        role
            Can be a Discord ˋRoleˋ object or a role ID.
        guild : Optional
            Can be a Discord ˋGuildˋ object or a guild ID.
            Is not an optional parameter if ˋroleˋ is not a Discord ˋRoleˋ object.
        """
        
        if isinstance(role, discord.Role):
            return Role(id=role.id)
        else:
            if guild is None:
                raise ValueError("Either a Role object or both role ID "
                                 "and guild ID must be given as argument(s)")
            return Role(id=role)

    def get_member(self, member=None, user=None, guild=None):
        """Retrieves a Dwarf ˋMemberˋ object from the database.
        Either ˋmemberˋ or both ˋuserˋ and ˋguildˋ must be given as arguments.
        
        Parameters
        ----------
        member : Optional
            Has to be a Discord ˋMemberˋ object.
        user : Optional
            Can be a Discord `User` object or a user ID.
        guild : Optional
            Can be a Discord ˋGuildˋ object or a guild ID.
        """
        
        if isinstance(member, discord.Member):
            user_id = member.id
            guild_id = member.guild.id
        else:
            if user is None or guild is None:
                raise ValueError("Either a Member object or both user ID "
                                 "and guild ID must be given as argument(s).")
            if isinstance(user, discord.User):
                user_id = user.id
            else:
                user_id = user
            if isinstance(guild, discord.Guild):
                guild_id = guild.id
            else:
                guild_id = guild
        
        return Member.objects.get(user=user_id, guild=guild_id)

    def new_member(self, member=None, user=None, guild=None):
        """Creates a new Dwarf ˋMemberˋ object and connects it to the database.
        Either ˋmemberˋ or both ˋuserˋ and ˋguildˋ must be given as arguments.
        
        Parameters
        ----------
        member : Optional
            Has to be a Discord ˋMemberˋ object.
        user : Optional
            Can be a Discord `User` object or a user ID.
        guild : Optional
            Can be a Discord ˋGuildˋ object or a guild ID.
        """
        
        if isinstance(member, discord.Member):
            user_id = member.id
            guild_id = member.guild.id
        else:
            if user is None or guild is None:
                raise ValueError("Either a Member object or both user ID "
                                 "and guild ID must be given as argument(s).")
            if isinstance(user, discord.User):
                user_id = user.id
            else:
                user_id = user
            if isinstance(guild, discord.Guild):
                guild_id = guild.id
            else:
                guild_id = guild
        
        return Member(user=user_id, guild=guild_id)

    def get_message(self, message):
        """Retrieves a Message from the database.
        
        Parameters
        ----------
        message
            Can be a Message object or a message ID."""

        if isinstance(message, discord.Message):
            return Message.objects.get(id=message.id)
        else:
            return Message.objects.get(id=message)

    def new_message(self, message):
        """Creates a new Dwarf ˋMessageˋ object and connects it to the database.
        
        Parameters
        ----------
        message
            Has to be a Discord ˋMessageˋ object.
        """
        
        if isinstance(message, discord.Message):
            return Message(id=message.id, author=message.author.id, channel=message.channel,
                           content=message.content, clean_content=message.clean_content,)
        else:
            raise ValueError("A Message object must be given as an argument")
