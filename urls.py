from django.conf.urls import url, include

from dwarf.api import BaseAPI


base = BaseAPI()


urlpatterns = []
# link 'extension/' URLs to the extension's URLConfs
extensions = base.get_extensions()
for extension in extensions:
    urlpatterns.append(url(r'^' + extension + r'/', include('dwarf.' + extension + 'urls')))
