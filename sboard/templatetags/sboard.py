from django import template

register = template.Library()


@register.simple_tag
def nodeurl(node, *args):
    return node.permalink(*args)


@register.assignment_tag(takes_context=True)
def nodepermission(context, node, action):
    return node.can(context['request'], action)
