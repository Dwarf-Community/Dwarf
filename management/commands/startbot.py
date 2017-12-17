# import asyncio
# import uvloop

from dwarf.bot import run

# asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
# TODO make Dwarf compatible with uvloop


class Command:
    def __init__(self):
        pass
    
    def run_from_argv(self, argv):
        run()
