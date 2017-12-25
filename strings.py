"""Externalized strings for better structure and easier localization"""


setup_greeting = """
Dwarf - First run configuration

Insert your bot's token, or enter 'cancel' to cancel the setup:"""

not_a_token = "Invalid input. Restart Dwarf and repeat the configuration process."

choose_prefix = """Choose a prefix. A prefix is what you type before a command.
A typical prefix would be the exclamation mark.
Can be multiple characters. You will be able to change it later and add more of them.
Choose your prefix:"""

confirm_prefix = """Are you sure you want {0} as your prefix?
You will be able to issue commands like this: {0}help
Type yes to confirm or no to change it"""

no_prefix_set = "No prefix set. Defaulting to !"

setup_finished = """
The configuration is done. Leave this window always open to keep your bot online.
All commands will have to be issued through Discord's chat,
*this window will now be read only*.
Press enter to continue"""

logging_into_discord = "Logging into Discord..."

invalid_credentials = """Invalid login credentials.
If they worked before Discord might be having temporary technical issues.
In this case, press enter and try again later.
Otherwise you can type 'reset' to delete the current configuration and
redo the setup process again the next start.
> """

keep_updated = "Make sure to keep Dwarf updated by using the {}update command."

official_server = "Official server: {}"

invite_link = "https://discord.gg/rAHwvyE"

update_the_api = """\nYou are using an outdated discord.py.\n
Update using pip3 install -U discord.py"""

command_not_found = "No command called {} found."

command_disabled = "That command is disabled."

exception_in_command = "Exception in command '{}'"

error_in_command = "Error in command '{}' - {}: {}"

not_available_in_dm = "That command is not available in DMs."

command_has_no_subcommands = "Command {0.name} has no subcommands."

owner_recognized = "{} has been recognized and set as owner."
