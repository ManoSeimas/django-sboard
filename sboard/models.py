import datetime
import unidecode
import uuid

from django.core.urlresolvers import reverse
from django.template.defaultfilters import slugify

from couchdbkit.ext.django import schema


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
        return Comment.view('sboard/children', key=self._id, include_docs=True)

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
