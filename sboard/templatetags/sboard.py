from django import template

from cgi import escape

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
    if size in SIZES:
        html_class = 'node-image-%s' % size
        size = SIZES[size]
    else:
        html_class = 'node-image'

    if additional_classes:
        html_class += ' ' + additional_classes

    url = node.image_url(size=size)

    if url:
        return u'<img alt="%s" src="%s" class="%s">' % tuple(map(escape, (node.title or '', url, html_class)))
    else:
        return ''

