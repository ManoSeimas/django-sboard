import StringIO

from PIL import Image

from django.http import HttpResponse, Http404

from couchdbkit.exceptions import ResourceNotFound

from .models import Media
from .nodes import get_node_view, get_node_classes


def node(request, key=None, view='list'):
    if key is not None:
        for node_class in get_node_classes().values():
            if node_class.slug == key:
                node = node_class()
                return node.list_view(request)

    try:
        node = get_node_view(key)
    except ResourceNotFound:
        raise Http404

    _view = getattr(node, '%s_view' % view, None)
    if _view is None:
        raise Http404
    else:
        return _view(request)


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
