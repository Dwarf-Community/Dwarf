from django.conf.urls import url, include

from dwarf.api import BaseAPI
from dwarf import views

base = BaseAPI()


urlpatterns = [
    url(r'^guilds/$', views.GuildList.as_view()),
    url(r'^guilds/(?P<pk>[0-9]+)/$', views.GuildDetail.as_view()),
    url(r'^channels/$', views.ChannelList.as_view()),
    url(r'^channels/(?P<pk>[0-9]+)/$', views.ChannelDetail.as_view()),
    url(r'^roles/$', views.RoleList.as_view()),
    url(r'^roles/(?P<pk>[0-9]+)/$', views.RoleDetail.as_view()),
    url(r'^members/$', views.MemberList.as_view()),
    url(r'^members/(?P<pk>[0-9]+)/$', views.MemberDetail.as_view()),
    url(r'^messages/$', views.MessageList.as_view()),
    url(r'^messages/(?P<pk>[0-9]+)/$', views.MessageDetail.as_view()),
    url(r'^strings/$', views.StringList.as_view()),
    url(r'^strings/(?P<pk>[0-9]+)/$', views.StringDetail.as_view()),
    url(r'^logs/$', views.LogList.as_view()),
    url(r'^logs/(?P<pk>[0-9]+)/$', views.LogDetail.as_view()),
]

# link 'extension/' URLs to the extension's URLConfs
extensions = base.get_extensions()
for extension in extensions:
    urlpatterns.append(url(r'^' + extension + r'/', include('dwarf.' + extension + 'urls')))
