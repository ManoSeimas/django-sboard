from django import template

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
