import functools
import datetime
import unidecode
import uuid

from django.core.urlresolvers import reverse
from django.template.defaultfilters import slugify

from couchdbkit.ext.django import schema

from docutils.parsers.rst import directives
from docutils.parsers.rst.directives.images import Image


def get_doctype_map():
    """Returns dictionary which maps between ``doc_type`` to approporate model
    class.""" 
    return {
        'Comment': Comment,
        'Node': Node,
    }


class SboardCouchViews(object):
    """A helper to access views from couch-db easier, for example::

      docviews = SboardDocumentViews(key=doc)
      views.children(include_docs=False)

    Is equivalent to::

      Node.view('sboad/children', key=doc.id, include_docs=False)

    Is useful when you need to call many different views from sboard with same
    arguments.

    """
        
    def __init__(self, **kwargs):
        self.kwargs = dict(kwargs)

    def __getattr__(self, attr):
        return functools.partial(Node.view,
            'sboard/%s' % attr, 
            classes=get_doctype_map(),
            **self.kwargs)


couch = SboardCouchViews()


class Node(schema.Document):
    author = schema.StringProperty()
    title = schema.StringProperty()
    body = schema.StringProperty(required=True)
    created = schema.DateTimeProperty(default=datetime.datetime.utcnow)
    parents = schema.ListProperty()

    _parent = None

    def get_children(self):
        # TODO: here each returned document must be mapped to model specified
        # in ``doc_type`` of that document. How to do that?
        return couch.children(key=self.get_id, include_docs=True)

    def get_children_count(self):
        res = couch.children_count(key=self.get_id, group=True,
                                   include_docs=False).all()
        if(len(res) == 0):
            return 0
        return res[0]['value']

    def get_latest_children(self):
        return couch.children_by_date(
            limit=3,
            descend=True,
            include_docs=True,
            startkey=[self.get_id, '0000-00-00T00:00:00'],
            endkey=[self.get_id, '9999-99-99T99:99:99'],
        )

    def get_new_id(self):
        if self.title:
            return slugify(unidecode.unidecode(self.title))
        else:
            return str(uuid.uuid4())

    def has_parent(self):
        return self.parents and len(self.parents) > 0

    def get_parent(self):
        if self._parent is None:
            if self.has_parent:
                # TODO: returned instance must bu mapped to model described in
                # ``doc_type``.
                self._parent = self.get(self.parents[-1])
        return self._parent

    def get_title(self):
        return self.title

    def permalink(self):
        return reverse('node_details', args=[self._id])


class Comment(Node):
    pass


class Media(schema.Document):
    ext = schema.StringProperty(required=True)
    author = schema.StringProperty()
    name = schema.StringProperty()
    created = schema.DateTimeProperty(default=datetime.datetime.utcnow)


class CustomImage(Image):
    def run(self):
        media = Media.get(self.arguments[0])
        self.arguments[0] = reverse('media_normal_size',
                                    args=[media._id, media.ext])
        return super(CustomImage, self).run()

directives.register_directive('image', CustomImage)


