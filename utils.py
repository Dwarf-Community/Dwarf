"""A collection of different utilities and shortcuts."""

import discord
from discord.errors import HTTPException, GatewayNotFound, ConnectionClosed
import aiohttp
import websockets

import asyncio
from functools import wraps


def answer_to_boolean(answer):
    if isinstance(answer, discord.Message):
        answer = answer.content
    answer_lower = answer.lower()
    if answer_lower.startswith('y'):
        return True
    if answer_lower.startswith('n'):
        return False
    return None


def is_boolean_answer(message):
    if isinstance(message, discord.Message):
        message = message.content
    return message.lower().startswith('y') or message.lower().startswith('n')


def estimate_read_time(text):
    read_time = len(text) * 1000  # in milliseconds
    read_time /= 15  # Assuming 15 chars per second
    if read_time < 2400.0:
        read_time = 2400.0  # Minimum is 2.4 seconds
    return read_time / 1000  # return read time in seconds


def restart_after_disconnect(pause=None, delay_start=None, resume_check=None):
    """Decorator that makes the decorated coro restart itself when a Discord connection issue occurs,

    Parameters
    ----------
    pause : coro
        The coroutine to yield from before restarting the task

    """

    if not (pause is None or callable(pause)):
        raise TypeError("pause must be a coroutine function")
    if not (delay_start is None or callable(delay_start)):
        raise TypeError("delay_start must be a coroutine function")

    def wrapper(coro):
        if not asyncio.iscoroutinefunction(coro):
            raise TypeError("decorated function must be a coroutine function")

        @wraps(coro)
        @asyncio.coroutine
        def wrapped(*args, **kwargs):
            if delay_start is not None:
                yield from delay_start()
            while True:
                try:
                    if pause is not None:
                        yield from pause()
                    return (yield from coro(*args, **kwargs))
                except asyncio.CancelledError:
                    if resume_check is not None and resume_check():
                        yield from wrapped(*args, **kwargs)
                    else:
                        return
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
