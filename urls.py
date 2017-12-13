from django.conf.urls import url, include
from dwarf import views
from dwarf.api import BaseAPI


base = BaseAPI()


urlpatterns = [
    url(r'^api/guilds/$', views.GuildList.as_view()),
    url(r'^api/guilds/(?P<pk>[0-9]+)/$', views.GuildDetail.as_view()),
    url(r'^api/channels/$', views.ChannelList.as_view()),
    url(r'^api/channels/(?P<pk>[0-9]+)/$', views.ChannelDetail.as_view()),
    url(r'^api/roles/$', views.RoleList.as_view()),
    url(r'^api/roles/(?P<pk>[0-9]+)/$', views.RoleDetail.as_view()),
    url(r'^api/members/$', views.MemberList.as_view()),
    url(r'^api/members/(?P<pk>[0-9]+)/$', views.MemberDetail.as_view()),
    url(r'^api/messages/$', views.MessageList.as_view()),
    url(r'^api/messages/(?P<pk>[0-9]+)/$', views.MessageDetail.as_view()),
    url(r'^api/strings/$', views.StringList.as_view()),
    url(r'^api/strings/(?P<pk>[0-9]+)/$', views.StringDetail.as_view()),
    url(r'^api/logs/$', views.LogList.as_view()),
    url(r'^api/logs/(?P<pk>[0-9]+)/$', views.LogDetail.as_view()),
]
# link 'extension/' URLs to the extension's URLConfs
extensions = base.get_extensions()
for extension in extensions:
    try:
        urlpatterns.append(url(r'^' + extension + r'/', include('dwarf.' + extension + '.urls')))
    except ImportError:
        pass
