import asyncio

import aioredis
from django.conf import settings
from redis_cache import RedisCache


class Cache:
    """Represents a connection to the cache backend.
    This class is used to store keys into and retrieve keys
    from the cache.

    Parameters
    ----------
    extension : Optional[str]
        If specified, the :class:`Cache` stores data in that
        extension's own storage area. The actual keys will be
        ``extension + '_' + key``; similar applies for channels when
        using :meth:`publish` or :meth:`subscribe`.
    bot
        The bot used to dispatch subscription events.

    Attributes
    -----------
    backend
        The cache backend the :class:`Cache` connects to.
    extension : Optional[str]
        If specified, the :class:`Cache` stores data in that
        extension's own storage area.
    bot
        The bot used to dispatch subscription events.
    """

    def __init__(self, extension='', bot=None, loop=None):
        self.config = settings.DWARF_CACHE_BACKEND['redis']
        self.backend = RedisCache('{}:{}'.format(self.config['HOST'], self.config['PORT']),
                                  {'db': self.config['DB'], 'password': self.config['PASSWORD']})
        self.extension = extension
        self.bot = bot
        if loop is None and self.bot is not None and hasattr(bot, 'loop'):
            self.loop = bot.loop
        else:
            self.loop = loop

    async def get_async_redis(self, loop=None):
        """Creates an asynchronous Redis connection.

        Parameters
        ----------
        loop = Optional[asyncio.AbstractEventLoop]
            The loop used for the asynchronous Redis connection.
        """

        if self.loop is not None and loop is None:
            loop = self.loop
        return await aioredis.create_redis(
            'redis://{}:{}'.format(self.config['HOST'], self.config['PORT']),
            db=self.config['DB'], password=self.config['PASSWORD'], loop=loop)

    def get(self, key, default=None):
        """Retrieves a key's value from the cache.

        Parameters
        ----------
        key : str
            The key to retrieve from the cache.
        default : Optional
            The value to return if the key wasn't found in the database.
        """

        if not self.extension:
            return self.backend.get(key=key, default=default)
        else:
            key = self.extension + '_' + key
            return self.backend.get(key=key, default=default)

    def set(self, key, value, timeout=None):
        """Sets a key in the cache.

        Parameters
        ----------
        key : str
            The key to set in the cache.
        value
            The value to assign to the key.
        timeout : Optional[int]
            After this amount of time (in seconds), the key will be deleted.
        """

        if self.extension:
            key = self.extension + '_' + key
        return self.backend.set(key=key, value=value, timeout=timeout)

    def get_many(self, keys):
        """Retrieves keys from the cache and returns them with their values as a dict.

        Parameters
        ----------
        keys : iter of str
            The keys to retrieve from the cache.
        """

        if self.extension:
            keys = [self.extension + '_' + key for key in keys]
        return self.backend.get_many(keys=keys)

    def set_many(self, data, timeout=None):
        """Sets an iterable of keys in the cache.
        If a key wasn't found, it inserts None into the list of values instead.

        Parameters
        ----------
        data : dict
            A dict consisting of key-value pairs.
        timeout : Optional[int]
            After this amount of time (in seconds), all keys in `data` will be deleted.
        """

        if self.extension:
            for key in data:
                value = data.pop(key)
                data[self.extension + '_' + key] = value
        return self.backend.set_many(data=data, timeout=timeout)

    def delete(self, key):
        """Deletes a key from the cache.

        Parameters
        ----------
        key : str
            The key to delete from the cache.
        """

        if self.extension:
            key = self.extension + '_' + key
        return self.backend.delete(key=key)

    async def subscribe(self, channel, limit=None):
        """Subscribes to a Redis Pub/Sub channel.
        When a message is received on the channel, `self.bot` is used to
        dispatch an event called `channel` + '_message' passing the message as a parameter.
        All cogs can implement a coroutine method called
        'on_' + `channel` + '_message' that will be executed when
        a message is sent to the `channel`.

        Parameters
        ----------
        channel : str
            The name of the Redis Pub/Sub channel to subscribe to.
            The internal channel name will be `'channel:' + channel`.
        limit : Optional[int]
            The maximum number of times messages published to the channel will be read.
        """

        if limit is not None:
            if not isinstance(limit, int):
                raise TypeError("limit must be of type int")
            if not limit > 0:
                raise ValueError("limit must be greater than 0")

        redis = await self.get_async_redis()
        channels = await redis.subscribe('channel:' + channel)
        actual_channel = channels[0]
        try:
            while await actual_channel.wait_message():
                message = await actual_channel.get(encoding='utf-8')
                self.bot.dispatch(channel + '_message', message)
                if limit == 1:
                    break
                elif limit is not None:
                    limit -= 1

            await redis.unsubscribe(actual_channel)
            redis.close()
            return
        except asyncio.CancelledError:
            await redis.unsubscribe(actual_channel)
            redis.close()
            return

    async def publish(self, channel, message=1):
        """Publishes a message to a Redis Pub/Sub channel.

        Parameters
        ----------
        channel : str
            The name of the channel to publish to.
            The internal channel name will be `'channel:' + channel`.
        message : Optional
            The message to publish. Defaults to 1.
        """

        channel = 'channel:' + channel
        redis = await self.get_async_redis()
        await redis.publish(channel, message)
        redis.close()
        return
