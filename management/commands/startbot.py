from django.core.management.base import BaseCommand

import importlib
import asyncio


class Command(BaseCommand):

    def handle(self):
        loop = asyncio.get_event_loop()
        bot = None
        while True:
            bot_module = importlib.import_module('dwarf.bot')
            bot = bot_module.main(loop=loop, bot=bot)
            if not bot.base.restarting_enabled():
                break
            else:
                bot.clear()
