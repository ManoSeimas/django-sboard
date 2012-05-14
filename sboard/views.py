import StringIO

try:
    from PIL import Image
except ImportError:
    import Image

from zope.component import getAdapter
from zope.component import getMultiAdapter
from zope.component import getUtility

from django.http import Http404
from django.http import HttpResponse

from couchdbkit.exceptions import MultipleResultsFound
from couchdbkit.exceptions import NoResultFound

from .factory import INodeFactory
from .factory import get_search_handlers
from .interfaces import INodeView
from .models import couch
from .models import getRootNode


def node(request, slug=None, action='', name=''):
    if slug is None or slug == '~':
        node = getRootNode()
    else:
        query = couch.by_slug(key=slug, limit=20)
        try:
            node = query.one(True)
        except MultipleResultsFound:
            return duplicate_slug_nodes(request, query)
        except NoResultFound:
            raise Http404

    if name:
        factory = getUtility(INodeFactory, name)
        view = getMultiAdapter((node, factory), INodeView, action)
    else:
        view = getAdapter(node, INodeView, action)

    view.request = request
    return view.render()


def duplicate_slug_nodes(request, nodes):
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
