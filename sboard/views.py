import StringIO

from PIL import Image

from django.http import HttpResponse

from .models import Node, Media
from .nodes import get_node_view, CommentNode


def node_details(request, key=None):
    if request.method == 'POST':
        node = Node.get(key)
        view = CommentNode(node)
        return view.create(request)
    else:
        view = get_node_view(key)
        return view.details(request)


def node_create(request, key=None):
    if key is None:
        view = get_node_view(key)
    else:
        node = Node.get(key)
        view = CommentNode(node)
    return view.create(request)


def node_update(request, key):
    view = get_node_view(key)
    return view.update(request)


def node_delete(request, key):
    view = get_node_view(key)
    return view.delete(request)


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
