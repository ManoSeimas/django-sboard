import StringIO

import Image

from zope.component import ComponentLookupError
from zope.component import getAdapter
from zope.component import getMultiAdapter
from zope.component import getUtility

from django.http import Http404
from django.http import HttpResponse

from couchdbkit.client import ViewResults

from .factory import INodeFactory
from .factory import get_search_handlers
from .interfaces import INodeView
from .models import couch
from .models import getRootNode
from .models import get_node_by_slug
from .models import set_nodes_ambiguous


def get_node_view(node, action='', name=''):
    view = None
    if name:
        try:
            factory = getUtility(INodeFactory, name)
        except ComponentLookupError:
            # /node/action/name/ - dynamic action, static name
            view = getMultiAdapter((node, action), INodeView, name)
        else:
            # /node/action/factory/ - static action
            view = getMultiAdapter((node, factory), INodeView, action)
    else:
        try:
            # /node/action/ - static action
            view = getAdapter(node, INodeView, action)
        except ComponentLookupError:
            # /node/action/ - dynamic action
            view = getMultiAdapter((node, action), INodeView)

    return view


def node(request, slug=None, action='', name=''):
    node = get_node_by_slug(slug)
    if node is None:
        raise Http404
    elif isinstance(node, ViewResults):
        return duplicate_slug_nodes(request, node)

    view = get_node_view(node, action, name)
    view.request = request
    return view.render()


def duplicate_slug_nodes(request, nodes):
    set_nodes_ambiguous(nodes)
    node = getRootNode()
    view = getAdapter(node, INodeView, 'list')
    view.request = request
    return view.render(node_list=nodes)


def search(request):
    query = request.GET.get('q')
    if not query:
        raise Http404

    for handler in get_search_handlers():
        view = handler(query)
        if view:
            if INodeView.providedBy(view):
                view.request = request
                return view.render()
            else:
                return view

    raise Http404


def render_image(request, slug, ext):
    node = couch.get(slug)
    infile = node.fetch_attachment('file.%s' % node.ext, stream=True)

    infile = StringIO.StringIO(infile.read())
    image = Image.open(infile)
    image.thumbnail((724, 1024), Image.ANTIALIAS)

    response = HttpResponse(mimetype='image/%s' % ext)

    extmap = {'jpg': 'jpeg',}
    image.save(response, extmap.get(ext, ext).upper())

    return response
