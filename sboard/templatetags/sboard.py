from django import template

register = template.Library()

@register.simple_tag
def nodeurl(node, *args):
    return node.permalink(*args)
