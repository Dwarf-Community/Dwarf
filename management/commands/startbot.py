from dwarf.bot import *
import dwarf

# import uvloop

import asyncio
import traceback


# asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
# TODO make Dwarf compatible with uvloop


class Command:
    def __init__(self):
        pass
    
    def run_from_argv(self, argv):
        global bot
        while True:
            if not is_configured():
                initial_config()
            
            error = False
            error_message = ""
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(main())
            except discord.LoginFailure:
                error = True
                error_message = 'Invalid credentials'
                choice = input(strings.invalid_credentials)
                if choice.strip() == "reset":
                    base.delete_token()
                else:
                    base.disable_restarting()
            except KeyboardInterrupt:
                loop.run_until_complete(bot.logout())
                base.disable_restarting()
            except Exception as e:
                error = True
                print(e)
                error_message = traceback.format_exc()
                loop.run_until_complete(bot.logout())
                base.disable_restarting()
            finally:
                if error:
                    print(error_message)
            if not base.restarting_enabled():
                break
            else:
                bot = Bot(command_prefix=core.get_prefixes(), description=dwarf.bot.__doc__, pm_help=core.is_help_private())
