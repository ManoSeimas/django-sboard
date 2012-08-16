import pprint

from django.utils.translation import ugettext_lazy as _

from debug_toolbar.panels import DebugPanel

from .models import get_node_by_slug
from .views import get_node_view
from .views import node_view


class NodeDebugPanel(DebugPanel):
    """
    A panel to display request variables (POST/GET, session, cookies).
    """
    name = 'Node'
    template = 'sboard/debug_toolbar.html'
    has_content = True

    def nav_title(self):
        return _('Node')

    def title(self):
        return _('Node')

    def nav_subtitle(self):
        stats = self.get_stats()
        return stats.get('node') or ''

    def url(self):
        return ''

    def process_view(self, request, view_func, view_args, view_kwargs):
        if view_func is node_view:
            slug = view_kwargs.get('slug', None)
            if slug is None and view_args:
                slug = view_args[0]
            node = get_node_by_slug(slug)

            if node is None:
                view = None
            else:
                action = view_kwargs.get('action', '')
                name = view_kwargs.get('name', '')
                ext = view_kwargs.get('ext', '')
                view = get_node_view(node, action, name, ext)

            context = {
                'view': view,
                'node': node,
                'doc': None,
            }

            if node and hasattr(node, '_doc'):
                context['doc'] = pprint.pformat(node._doc)

            self.record_stats(context)
            self.has_content = True
        else:
            self.has_content = False
