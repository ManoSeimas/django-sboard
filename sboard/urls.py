from django.conf.urls.defaults import patterns, url, include

slug = r'[a-z0-9~-]+'

node = patterns('sboard.views',
    url(r'^$', 'node', name='node_details'),
    # URL bellow will never match, but is used only for name to be possible to
    # reverse to node_list instead of node_details
    url(r'^$', 'node', name='node_list'),
    url(r'^create/$', 'node', {'action': 'create'}, name='node_create_child'),
    url(r'^create/(?P<name>%s)/$' % slug, 'node', {'action': 'create'},
        name='node_create_child'),
    url(r'^update/$', 'node', {'action': 'update'}, name='node_update'),
    url(r'^convert-to/(?P<name>%s)/$' % slug, 'node',
        {'action': 'convert_to'}, name='node_convert_to'),
    url(r'^delete/$', 'node', {'action': 'delete'}, name='node_delete'),
    url(r'^tag/$', 'node', {'action': 'tag'}, name='node_tag'),
    url(r'^comment/$', 'node', {'action': 'comment'}, name='node_comment'),
    url(r'^(?P<action>%s)/$' % slug, 'node', {}, name='node_action'),
)

media = patterns('sboard.views',
    url(r'^(?P<slug>%s)/normal.(?P<ext>[a-z0-9]+)$' % slug, 'render_image',
        name='media_normal_size'),
)

urlpatterns = patterns('sboard.views',
    url(r'^$', 'node', {'action': 'list'}, name='node_list'),
    url(r'^create/$', 'node', {'action': 'create'}, name='node_create'),
    url(r'^create/(?P<name>%s)/$' % slug, 'node', {'action': 'create'},
        name='node_create'),
    url(r'^search/$', 'node', {'action': 'search'}, name='node_search'),
    url(r'^media/', include(media)),
    url(r'^(?P<key>%s)/' % slug, include(node)),
)
