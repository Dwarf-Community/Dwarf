from django.core.management.base import BaseCommand

import importlib
import asyncio


class Command(BaseCommand):
    
    def handle(self):
        loop = asyncio.get_event_loop()
        bot = None
        while True:
            bot_module = importlib.import_module('dwarf.bot')
            bot = bot_module.main(loop, bot)
            if bot_module.base.restarting_enabled():
                break
