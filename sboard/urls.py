from django.conf.urls.defaults import patterns, url, include

from .nodes import get_node_urls

slug = r'[a-z0-9-]+'

node = patterns('sboard.views',
    url(r'^$', 'node', {'view': 'details'}, name='node_details'),
    url(r'^create/$', 'node', {'view': 'create'}, name='node_create_child'),
    url(r'^update/$', 'node', {'view': 'update'}, name='node_update'),
    url(r'^delete/$', 'node', {'view': 'delete'}, name='node_delete'),
    url(r'^tag/$', 'node', {'view': 'tag'}, name='node_tag'),
)

node += get_node_urls()

media = patterns('sboard.views',
    url(r'^(?P<slug>%s)/normal.(?P<ext>[a-z0-9]+)$' % slug, 'render_image',
        name='media_normal_size'),
)

urlpatterns = patterns('sboard.views',
    url(r'^$', 'node', {'view': 'list'}, name='node_list'),
    url(r'^create/$', 'node', {'view': 'create'}, name='node_create'),
    url(r'^search/$', 'node', {'view': 'search'}, name='node_search'),
    url(r'^media/', include(media)),
    url(r'^(?P<key>%s)/' % slug, include(node)),
)
