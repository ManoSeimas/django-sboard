from django import template
from django.core.cache import cache

from cgi import escape

from sorl.thumbnail.templatetags.thumbnail import margin

register = template.Library()


@register.simple_tag
def nodeurl(node, *args):
    return node.permalink(*args)


@register.simple_tag
def nodeexturl(node, *args):
    args, ext = args[:-1], args[-1]
    return node.permalink(*args, **dict(ext=ext))


@register.assignment_tag(takes_context=True)
def nodepermission(context, node, action):
    return node.can(context['request'], action)


SIZES = {
    'small': 24,
    'normal': 40,
    'large': 135,
}

@register.simple_tag
def nodeimage(node, size='normal', additional_classes=''):
    if not node:
        return ''
    key = ':'.join(['nodeimage', node._id, unicode(size), additional_classes])

    value = cache.get(key)

    if value:
        return value
    else:
        if size in SIZES:
            html_class = 'node-image-%s' % size
            size = SIZES[size]
        else:
            html_class = 'node-image'

        if additional_classes:
            html_class += ' ' + additional_classes

        attrs = {
            'alt': node.title,
            'class': html_class,
        }

        if node.image:
            geometry = '%dx%d' % (size, size)
            thumbnail = node.image.ref.thumbnail(geometry)
            attrs['src'] = thumbnail.url
            attrs['style'] = 'padding:%s' % margin(thumbnail, geometry)
        else:
            attrs['src'] = node.image_url(size=size)

        if attrs['src']:
            attr_string = u' '.join(u'%s="%s"' % (name, escape(value)) for name, value in attrs.items() if value)
            value = u'<img %s>' % attr_string
        else:
            value = ''

        cache.set(key, value)
        return value

