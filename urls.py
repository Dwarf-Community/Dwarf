from django.conf.urls import url, include

from dwarf.api import CoreAPI


urlpatterns = []
extensions = CoreAPI.get_extensions()
for extension in extensions:
    urlpatterns.append(url(r'^' + extension.encode('string-escape') + r'/', include('dwarf.urls')))





# importing URLConfs introduced by extensions

