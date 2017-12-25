"""Externalized strings for better structure and easier localization"""


info = str("This is an instance of Dwarf, the "
           "Discord Web Application Framework created by AileenLumina.\n"
           "**Repository:**\n"
           "<{}>\n"
           "**Official server:**\n"
           "<{}>")

failed_to_install = "Failed to install '**{}**'."

failed_to_update = "Failed to update '**{}**'."

specify_extension_name = "Please specify a name for this extension (must be a valid Python package name)."

skipping_this_extension = "Not installing this extension."

unsatisfied_requirements = "Missing required packages:"

unsatisfied_dependencies = "Missing required extensions:"

prompt_install_requirements = "Do you want to install the missing required packages?"

would_be_uninstalled_too = str("Extensions that would be uninstalled as well "
                               "as they depend on '**{}**':")

proceed_with_uninstallation = str("Do you want to proceed? This will uninstall "
                                  "the above listed extensions. (yes/no)")

prefix_singular = "Prefix"

prefix_plural = "Prefixes"

use_this_url = "Use this URL to bring your bot to a server:"

bot_is_online = "{} is now online."

connected_to = "Connected to:"

connected_to_servers = "{} servers"

connected_to_channels = "{} channels"

connected_to_users = "{} users"

user_registered = """{}, thanks for using my commands!
I just registered you in my database so you can use all my features. I hope that's okay for you.
If it isn't, please use the `unregister` command. That will remove all of the data I store about you.
The only thing I will still keep is your ID so I don't forget that you don't want data about you to be stored.
Keep in mind that if I'm not allowed to store data about you, you won't be able to use many of my commands.
If you ever change your mind about this, use the `register` command.

Whatever your decision looks like, I wish you lots of fun on Discord."""
