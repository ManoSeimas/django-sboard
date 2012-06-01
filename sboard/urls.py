from django.conf.urls.defaults import patterns, url, include

slug = r'[a-z0-9~+-]+'
ext = r'[a-z]+'

node = patterns('sboard.views',
    url(r'^$', 'node_view', name='node'),
    url(r'^(?P<action>%s)/$' % slug, 'node_view', name='node'),
    url(r'^(?P<action>%s)/(?P<name>%s)/$' % (slug, slug), 'node_view',
        name='node'),

    # Node with extension urls.
    url(r'^(?P<action>%s)\.(?P<ext>%s)$' % (slug, ext), 'node_view',
        name='node_ext'),
    url(r'^(?P<action>%s)/(?P<name>%s)\.(?P<ext>%s)$' % (slug, slug, ext),
        'node_view', name='node_ext'),
)

media = patterns('sboard.views',
    url(r'^(?P<slug>%s)/normal.(?P<ext>[a-z0-9]+)$' % slug, 'render_image',
        name='media_normal_size'),
)

urlpatterns = patterns('sboard.views',
    url(r'^$', 'node_view', {'action': 'list'}, name='index'),
    url(r'^search/$', 'search', name='search'),
    url(r'^media/', include(media)),
    url(r'^(?P<slug>%s)\.(?P<ext>%s)' % (slug, ext), 'node_view',
        name="node_ext"),
    url(r'^(?P<slug>%s)/' % slug, include(node)),
)
