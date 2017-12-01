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
