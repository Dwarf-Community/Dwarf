from django.conf.urls import url, include

from dwarf.api import CoreAPI


core = CoreAPI()


urlpatterns = []
# link 'extension/' URLs to the extension's URLConfs
extensions = core.get_extensions()
for extension in extensions:
    urlpatterns.append(url(r'^' + extension + r'/', include('dwarf.' + extension + 'urls')))
