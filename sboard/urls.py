from django.conf.urls.defaults import patterns, url, include

slug = r'[a-z0-9~-]+'

node = patterns('sboard.views',
    url(r'^$', 'node', name='node'),
    url(r'^(?P<action>%s)/$' % slug, 'node', name='node'),
    url(r'^(?P<action>%s)/(?P<name>%s)/$' % (slug, slug), 'node', name='node'),
)

media = patterns('sboard.views',
    url(r'^(?P<slug>%s)/normal.(?P<ext>[a-z0-9]+)$' % slug, 'render_image',
        name='media_normal_size'),
)

urlpatterns = patterns('sboard.views',
    url(r'^$', 'node', {'action': 'list'}, name='index'),
    url(r'^search/$', 'search', name='search'),
    url(r'^media/', include(media)),
    url(r'^(?P<slug>%s)/' % slug, include(node)),
)
