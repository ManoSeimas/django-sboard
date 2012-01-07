from django.conf.urls.defaults import patterns, url, include

node = patterns('sboard.views',
    url(r'^$', 'node_details', name='node_details'),
    url(r'^create/$', 'node_create', name='node_create_child'),
    url(r'^update/$', 'node_update', name='node_update'),
    url(r'^delete/$', 'node_delete', name='node_delete'),
)

urlpatterns = patterns('sboard.views',
    url(r'^$', 'node_details', name='node_list'),
    url(r'^create/$', 'node_create', name='node_create'),
    url(r'^(?P<key>[a-z0-9-]+)/$', include(node)),
)
