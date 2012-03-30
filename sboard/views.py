import StringIO

try:
    from PIL import Image
except ImportError:
    import Image

from zope.component import getAdapter
from zope.component import getMultiAdapter
from zope.component import getUtility

from django.http import HttpResponse, Http404

from couchdbkit.exceptions import ResourceNotFound

from .factory import INodeFactory
from .interfaces import INodeView
from .models import Media, couch
from .models import getRootNode


def node(request, key=None, action='', name=''):
    if key is None:
        node = getRootNode()
    else:
        try:
            node = couch.get(key)
        except ResourceNotFound:
            raise Http404

    if name:
        factory = getUtility(INodeFactory, name)
        view = getMultiAdapter((node, factory), INodeView, action)
    else:
        view = getAdapter(node, INodeView, action)

    view.request = request
    return view.render()


def render_image(request, slug, ext):
    media = Media.get(slug)
    infile = media.fetch_attachment('orig.%s' % ext, stream=True)

    infile = StringIO.StringIO(infile.read())
    image = Image.open(infile)
    image.thumbnail((724, 1024), Image.ANTIALIAS)

    response = HttpResponse(mimetype='image/%s' % ext)

    extmap = {'jpg': 'jpeg',}
    image.save(response, extmap.get(ext, ext).upper())

    return response
