from django.conf.urls.defaults import patterns, url

from sboard.utils import reverse_lazy


urlpatterns = patterns('sboard.profiles.views',
    url(r'^profile/$', 'profile', name='profile'),
    url(r'^login/$', 'login', name='login'),
)

urlpatterns += patterns('django.contrib.auth.views',
    url(r'^logout/', 'logout', {'next_page': reverse_lazy('index')},
        name="logout"),
)
