import StringIO

import Image

from zope.component import ComponentLookupError
from zope.component import getAdapter
from zope.component import getMultiAdapter
from zope.component import getUtility

from django.http import Http404
from django.http import HttpResponse

from couchdbkit.client import ViewResults
from couchdbkit.exceptions import MultipleResultsFound

from .factory import INodeFactory
from .factory import IViewExtFactory
from .factory import get_search_handlers
from .interfaces import INodeView
from .models import couch
from .models import get_node_by_slug


def get_node_view(node, action='', name='', ext=''):
    if ext:
        view_interface = getUtility(IViewExtFactory, ext).interface
    else:
        view_interface = INodeView

    if isinstance(node, ViewResults):
        return getAdapter(node, view_interface)

    view = None
    if name:
        try:
            factory = getUtility(INodeFactory, name)
        except ComponentLookupError:
            # /node/action/name/ - dynamic action, static name
            view = getMultiAdapter((node, action), view_interface, name)
        else:
            # /node/action/factory/ - static action
            view = getMultiAdapter((node, factory), view_interface, action)
    else:
        try:
            # /node/action/ - static action
            view = getAdapter(node, view_interface, action)
        except ComponentLookupError:
            # /node/action/ - dynamic action
            view = getMultiAdapter((node, action), view_interface)

    return view


def node_view(request, slug=None, action='', name='', ext=''):
    node = get_node_by_slug(slug)
    if node is None:
        raise Http404

    if ext and isinstance(node, ViewResults):
        length = len(node)
        raise MultipleResultsFound("%s results found." % length)

    try:
        view = get_node_view(node, action, name, ext)
    except ComponentLookupError:
        raise Http404

    view.set_request(request)
    view.set_view_func(node_view)
    return view.validate() or view.render()


def search(request):
    query = request.GET.get('q')
    if not query:
        raise Http404

    for handler in get_search_handlers():
        view = handler(query)
        if view:
            if INodeView.providedBy(view):
                view.set_request(request)
                view.set_view_func(search)
                return view.validate() or view.render()
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
