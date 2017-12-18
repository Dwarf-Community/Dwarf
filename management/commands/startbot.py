import importlib
import asyncio


class Command:
    def __init__(self):
        pass
    
    def run_from_argv(self, argv):
        loop = asyncio.get_event_loop()
        while True:
            bot_module = importlib.import_module('dwarf.bot')
            bot_module.main()
            # if loop.is_running():
                # bot_module.cleanup(loop)
            if not bot_module.base.restarting_enabled():
                break
