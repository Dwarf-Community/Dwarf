import asyncio
import importlib

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Creates a bot instance and connects to Discord."
    )

    def handle(self, *args, **options):
        loop = asyncio.get_event_loop()
        if settings.DEBUG:
            loop.set_debug(True)
        bot = None
        while True:
            bot_module = importlib.import_module('dwarf.bot')
            bot = bot_module.main(loop=loop, bot=bot)
            if not bot.base.restarting_enabled():
                break
            else:
                bot.clear()
