"""A collection of various helper functions and utility functions."""

import discord
from discord.errors import HTTPException, GatewayNotFound, ConnectionClosed
import aiohttp
import websockets

import asyncio
import functools


def estimate_reading_time(text):
    """Estimates the time needed for a user to read a piece of text

    This is assuming 0.9 seconds to react to start reading
    plus 15 chars per second to actually read the text.

    Parameters
    ----------
    text : str
        The text the reading time should be estimated for.
    """
    read_time = 0.9 + len(text) / 15
    read_time = round(read_time, 1)
    return read_time if read_time > 2.4 else 2.4  # minimum is 2.4 seconds


def autorestart(delay_start=None, pause=None, restart_check=None):
    """Decorator that automatically restarts the decorated
    coroutine function when a connection issue occurs.

    Parameters
    ----------
    delay_start : Callable
        Will be yielded from before starting the
        execution of the decorated coroutine function.
    pause : Callable
        Will be yielded from before restarting the
        execution of the decorated coroutine function.
    restart_check : Callable
        A callable that checks whether the decorated
        coroutine function should be restarted if it
        has been cancelled. Should return a truth value.
        May be a coroutine function.
    """
    if not (delay_start is None or callable(delay_start)):
        raise TypeError("delay_start must be a callable")
    if not (pause is None or callable(pause)):
        raise TypeError("pause must be a callable")
    if not (restart_check is None or callable(restart_check)):
        raise TypeError("restart_check must be a callable")

    def wrapper(coro):
        if not asyncio.iscoroutinefunction(coro):
            raise TypeError("decorated function must be a coroutine function")

        @functools.wraps(coro)
        @asyncio.coroutine
        def wrapped(*args, **kwargs):
            if delay_start is not None:
                yield from discord.utils.maybe_coroutine(delay_start)
            try:
                if pause is not None:
                    yield from discord.utils.maybe_coroutine(pause)
                return (yield from coro(*args, **kwargs))
            except asyncio.CancelledError:
                if restart_check is not None and (yield from discord.utils.maybe_coroutine(restart_check)):
                    yield from wrapped(*args, **kwargs)
                else:
                    raise
                # catch connection issues
            except (OSError,
                    HTTPException,
                    GatewayNotFound,
                    ConnectionClosed,
                    aiohttp.ClientError,
                    asyncio.TimeoutError,
                    websockets.InvalidHandshake,
                    websockets.WebSocketProtocolError) as e:
                if any((isinstance(e, ConnectionClosed) and e.code == 1000,  # clean disconnect
                        not isinstance(e, ConnectionClosed))):
                    yield from wrapped(*args, **kwargs)
                else:
                    raise

        return wrapped
    return wrapper
