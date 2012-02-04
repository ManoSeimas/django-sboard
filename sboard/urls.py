from django.conf.urls.defaults import patterns, url, include

slug = r'[a-z0-9-]+'

node = patterns('sboard.views',
    url(r'^$', 'node_details', name='node_details'),
    url(r'^create/$', 'node_create', name='node_create_child'),
    url(r'^update/$', 'node_update', name='node_update'),
    url(r'^delete/$', 'node_delete', name='node_delete'),
    url(r'^tag/$', 'node_tag', name='node_tag'),
)

media = patterns('sboard.views',
    url(r'^(?P<slug>%s)/normal.(?P<ext>[a-z0-9]+)$' % slug, 'render_image',
        name='media_normal_size'),
)

urlpatterns = patterns('sboard.views',
    url(r'^$', 'node_details', name='node_list'),
    url(r'^create/$', 'node_create', name='node_create'),
    url(r'^media/', include(media)),
    url(r'^(?P<key>%s)/' % slug, include(node)),
)
