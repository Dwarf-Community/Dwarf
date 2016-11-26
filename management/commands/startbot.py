from dwarf.bot import *
import asyncio
import traceback


if not is_configured():
    initial_config()

error = False
error_message = ""
loop = asyncio.get_event_loop()
try:
    loop.run_until_complete(main())
except discord.LoginFailure:
    error = True
    error_message = 'Invalid credentials'
    bot.logger.error(traceback.format_exc())
    choice = input(strings.invalid_credentials)
    if choice.strip() == "reset":
        base.delete_token()
except KeyboardInterrupt:
    loop.run_until_complete(bot.logout())
except Exception as e:
    error = True
    print(e)
    error_message = traceback.format_exc()
    bot.logger.error(traceback.format_exc())
    loop.run_until_complete(bot.logout())
finally:
    loop.close()
    if error:
        exit(error_message)
