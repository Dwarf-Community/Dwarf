# Dwarf: Discord Web Application Rendering Framework

### Dwarf - Documentation

I'll have to write everything down ASAP, but for now, check the Django documentation about models, discord.py's documentation, dwarf.api.management and the following:
`from dwarf.api import CacheAPI`
The CacheAPI allows you to store key/value pairs in the Redis database. Syntax:
`CacheAPI.set(key='dwarf_your_key_here', value=12345)`
The value can be of any type. After you've set it, you can get it from the Redis database as follows:
`data = CacheAPI.get(key='dwarf_your_key_here')`
Have fun! If you need help, drop by [my Discord server](https://discord.me/AileenLumina). If you write an extension and want it to be installable for others, add it to the Dwarf Extension Index (dwarf/extensions.py).

### Dwarf - Quick Install Guide

First off, you need Python 3.5 or above, PostgreSQL and Redis (the Windows port works, too). After you installed the requirements (if necessary), start a terminal session (cmd.exe on Windows) and install virtualenv:
`pip3 install virtualenv`
Once you have that, create a virtual environment as follows:
`virtualenv path/to/where/you/want/to/create/your/virtualenv`
Any path will do; I'd suggest `/djangoenv`. After you've created the virtualenv, you'll need to enter/activate it. On Linux, that would be:
`source /djangoenv/bin/activate`
And on Windows:
`/djangoenv/Scripts/activate.bat`
(Replace /djangoenv with the path to your virtual environment.) You should now see the name of your virtualenv in brackets (e.g. `(djangoenv)`). If you do, you can now start installing the requirements:
`pip install django redis psycopg2 discord.py`
After you've done that, start a new Django project in a directory of your choice as follows:
`django-admin startproject project-name`
(Replace project-name with the name of your project, e.g. dwarfproject, mybot or mysite.) This will create the folder structure of your Django project. Now you can download Dwarf by going to your project directory (`cd project-name`) and issueing the following (use Git Bash for this if you're on Windows):
`git clone https://github.com/Dwarf-Community/dwarf`
`cd dwarf`
`git submodule update --init --recursive --remote`
You now need to adjust the settings.py file (in `/project-name/project-name`) as follows:
- Set the database backend to PostgreSQL (recommended):
    Example:
```python
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'databasename',
            'USER': 'someuser',
            'PASSWORD': 'S3kr1t!',
            'HOST': 'localhost',
            'PORT': '5432',
            'CONN_MAX_AGE': 30,  # in seconds
        }
    }
```
- Add Dwarf to your installed apps:
    Example:
```python
    INSTALLED_APPS = [
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'dwarf.apps.DwarfConfig',
    ]
```
- Register Dwarf's user model as the user model used for authentication:
```python
    AUTH_USER_MODEL = 'dwarf.User'
```
- You also have to add your Redis credentials to settings.py:
```python
DWARF_CACHE_BACKEND = {
    'default': {
        'HOST': 'localhost',
        'PORT': 6379,
        'PASSWORD': 'S3kr1t!',
        'DB': 1,
    }
}
```
Now that you've done that, you need to decide at which URL you want to make Dwarf's web front-end available. Open `/project-name/project-name/urls.py` and make it look something like this:
```python
from django.conf.urls import url, include
from django.contrib import admin

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^dwarf/', include('dwarf.urls')),
]
```
Take a closer look at `r'^dwarf/'`. That is a so-called regular expression that defines where Dwarf should be made accessible. If you want to host Dwarf at `discord/`, your `urlpatterns` would look like this:
```python
from django.conf.urls import url, include
from django.contrib import admin

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^discord/', include('dwarf.urls')),
]
```
If you want to host it at the root, your `urlpatterns` would look as follows:
```python
from django.conf.urls import url, include
from django.contrib import admin

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^', include('dwarf.urls')),
]
```
Keep in mind that Django checks these `urlpatterns` from top to bottom, so if you'd put the second urlpattern above the first in the above example, you wouldn't be able to access anything via the web interface but Dwarf.

Finally, you have to let Django setup the database for you:
`python manage.py makemigrations`
`python manage.py makemigrations dwarf`
`python manage.py migrate`

That should be it for now. There will be more things to install as soon as the web front-end part will be released, such as nginx and gunicorn, so keep an eye at [my Discord server](https://discord.me/AileenLumina)! :)

You can start the bot by going to your Django project's directory and issueing the following command (after you activated your virtualenv as described above):
`python manage.py startbot`
Have fun! If you need help, drop by the Discord server and we'll try to help you. ^-^