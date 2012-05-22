import pprint

from zope.component import getAdapter
from zope.component import getMultiAdapter
from zope.component import getUtility

from django.utils.translation import ugettext_lazy as _

from debug_toolbar.panels import DebugPanel

from couchdbkit.client import ViewResults
from couchdbkit.exceptions import MultipleResultsFound
from couchdbkit.exceptions import NoResultFound

from .factory import INodeFactory
from .interfaces import INodeView
from .models import couch
from .models import getRootNode
from .views import node as node_view


def get_node(request, slug=None, action='', name=''):
    key = request.GET.get('key')
    if key:
        try:
            return couch.get(key)
        except NoResultFound:
            return None
    elif slug is None or slug == '~':
        return getRootNode()
    else:
        query = couch.by_slug(key=slug, limit=20)
        try:
            return query.one(True)
        except MultipleResultsFound:
            return getRootNode()
        except NoResultFound:
            return None


def get_node_view(node, slug=None, action='', name=''):
    if name:
        factory = getUtility(INodeFactory, name)
        return getMultiAdapter((node, factory), INodeView, action)
    else:
        return getAdapter(node, INodeView, action)


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
            node = get_node(request, *view_args, **view_kwargs)

            if node is None:
                view = None
            elif isinstance(node, ViewResults):
                node = getRootNode()
                view = get_node_view(node, action='list')
            else:
                view = get_node_view(node, *view_args, **view_kwargs)

            context = {
                'view': view,
                'node': node,
                'doc': None,
            }

            if node:
                context['doc'] = pprint.pformat(node._doc)

            self.record_stats(context)
            self.has_content = True
        else:
            self.has_content = False
