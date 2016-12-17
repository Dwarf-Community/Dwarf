"""A collection of different utilities and shortcuts."""

import discord


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
    message_lower = message.lower()
    return message_lower.startswith('y') or content_lower.startswith('n')


def estimate_read_time(text):
    read_time = len(text) * 1000  # in milliseconds
    read_time /= 15  # Assuming 15 chars per second
    if read_time < 2400.0:
        read_time = 2400.0  # Minimum is 2.4 seconds
    return read_time / 1000  # return read time in seconds
