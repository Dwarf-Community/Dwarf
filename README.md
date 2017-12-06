# Dwarf — Discord Web Application Rendering Framework

Dwarf is a framework for developers designed to make it easy to enhance Discord while staying out of your way.

The straightforward **extension system** allows you to create or download extensions that provide useful additional functionality, such as economy, music, basic RPG elements and more. Extensions can be submitted to [DwEI, the Dwarf Extension Index](https://github.com/Dwarf-Community/Dwarf-Extensions), from where they are easily accessible to everybody. Dwarf and its extensions build the foundation for your app, so you can **focus on writing the actual app without reinventing the wheel**.

Dwarf was built on top of [Django](https://www.djangoproject.com/start/overview/) and [discord.py](https://github.com/Rapptz/discord.py) to get your Discord web app from concept to reality as quickly as possible. It **does a lot of the heavy lifting for you**, such as database connectivity, caching, user authentication and bot sharding. Every Dwarf app consists of a Discord bot, a web frontend and an API. Dwarf uses [Redis](https://redis.io/topics/introduction) to allow instant communication between the frontend and the backend via a straightforward cache API layer.

**Every part of Dwarf is extendable**, meaning that every extension can add new ORM models, REST API endpoints, frontend views, elements to views of other extensions, bot commands, cache keys for other extensions to listen to, or something completely new. Your imagination is the limit!

## Getting Started

Want to spin up your own Dwarf instance to develop an app or extension? [This wiki article](https://github.com/Dwarf-Community/Dwarf/wiki/Getting-started) guides you through the installation process.

Extensions are themselves very powerful. If you want to build an extension and maybe even submit it to DwEI, check out [these handy instructions](https://github.com/Dwarf-Community/Dwarf/wiki/Create-a-new-Dwarf-extension) on how to start developing a new extension.

### Let's forge some great apps that make Discord even more awesome!

Still have some questions? Need some help? Want to check out what others have built? [Join us on Discord!](https://discord.gg/rAHwvyE)
