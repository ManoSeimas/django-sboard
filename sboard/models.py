import datetime
import functools

from zope.interface import implements

from django.contrib.markup.templatetags import markup
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.db import models
from django.db import transaction
from django.utils.translation import ugettext_lazy as _

from couchdbkit.exceptions import ResourceNotFound
from couchdbkit.ext.django import schema
from couchdbkit.ext.django.loading import couchdbkit_handler

from docutils.parsers.rst import directives
from docutils.parsers.rst.directives.images import Image

from .factory import getNodeClass
from .factory import getNodeFactories
from .factory import provideNode
from .interfaces import IComment
from .interfaces import IHistory
from .interfaces import INode
from .interfaces import IRoot
from .interfaces import ITag
from .interfaces import ITagsChange
from .utils import base36


class DocTypeMap(dict):
    """Special dict, that provides doc_type map for instances returned by view.

    CouchDB view call can return documents with different types, this
    dictionary provides model classes for those document types.
    """
    def __init__(self, *args, **kwargs):
        super(DocTypeMap, self).__init__(*args, **kwargs)

        self.default = getNodeClass("node")
        for name, factory in getNodeFactories():
            if name not in self:
                self[name] = factory.node_class


    def get(self, key, default=None):
        key = key.lower()
        return super(DocTypeMap, self).get(key, default) or self.default


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
        self._doc_type_map = None
        self.kwargs = dict(kwargs)
        self.kwargs.setdefault('include_docs', True)

    def get_doc_type_map(self):
        if self._doc_type_map is None:
            self._doc_type_map = DocTypeMap()
        return self._doc_type_map

    def __getattr__(self, attr):
        return functools.partial(Node.view, 'sboard/%s' % attr,
                                 classes=self.get_doc_type_map(), **self.kwargs)

    def wrap(self, data):
        # TODO: change doc_type to node_type
        cls = self.get_doc_type_map().get(data['doc_type'].lower())
        return cls.wrap(data)

    def get(self, docid, rev=None):
        assert docid, "``docid`` can't be empty"
        db = Node.get_db()
        return db.get(docid, rev=rev, wrapper=self.wrap)

    def view(self, view, **kwargs):
        kwargs.setdefault('include_docs', True)
        kwargs.setdefault('classes', self.get_doc_type_map())
        return Node.view(view, **kwargs)


couch = SboardCouchViews()


class UniqueKeyManager(models.Manager):
    @transaction.commit_on_success
    def create(self):
        obj = UniqueKey()
        obj.save()
        obj.key = base36(obj.pk).zfill(6)
        obj.save()
        return obj


class UniqueKey(models.Model):
    """Unique key generator.

    This model ensures unique key generation, incremented by 1 and converted to
    base36.

    Generated key is 6 characters length and can identify 2 176 782 335 nodes.

    >>> UniqueKey.objects.create().key
    '000001'
    >>> UniqueKey.objects.create().key
    '000002'
    >>> UniqueKey.objects.create().key
    '000003'

    """
    key = models.PositiveIntegerField(unique=True, null=True)

    objects = UniqueKeyManager()


class NodeProperty(schema.StringProperty):
    def validate(self, value, required=True):
        if isinstance(value, Node):
            value = value._id
        return super(NodeProperty, self).validate(value, required)


class BaseNode(schema.Document):
    @classmethod
    def get_db(cls):
        """Returns CouchDB database associated with this model.

        In addition to ``schema.Document.get_db``, this method provides same
        database as bound to ``Node``, to all other models, that extends
        ``Node``.
        """
        db = getattr(cls, '_db', None)
        if db is None:
            app_label = getattr(cls._meta, "app_label")
            if app_label in couchdbkit_handler._databases:
                db = couchdbkit_handler.get_db(app_label)
            elif cls is not Node:
                db = Node.get_db()
            else:
                raise ImproperlyConfigured(
                    ('Can not find CouchDB database for %s model. Check '
                     'settings.COUCHDB_DATABASES setting.' % cls))
            cls._db = db
        return db


class Node(BaseNode):
    implements(INode)

    # Node slug, that is used to get node from human readable url address.
    slug = schema.StringProperty()

    # Node keywords, used in search.
    keywords = schema.ListProperty()

    # Author, who initially created this node.
    author = schema.StringProperty()

    # Node title.
    title = schema.StringProperty()

    # Node creation datetime.
    created = schema.DateTimeProperty(default=datetime.datetime.utcnow)

    # Node parent.
    parent = NodeProperty()

    # List of all node ancestors.
    # TODO: rename ``parents`` to ``ancestors``
    parents = schema.ListProperty()

    # Node tags. Each item in this list is reference to a node.
    tags = schema.ListProperty()

    # Reference to history node (last revision of current node), this attribute
    # can be None if node was never modified.
    history = schema.StringProperty()

    # Each node can override this value, tho change default node importance.
    _default_importance = 5

    # This property specifies node importance. This property is mainly used
    # when searching nodes. Nodes with bigger importance appears at the top of
    # search results.
    #
    # If importance is less than 5, then node will node appear in lists.
    importance = schema.IntegerProperty()

    permissions = schema.ListProperty()

    _parent = None

    def __init__(self, *args, **kwargs):
        self._properties['importance'].default = self._default_importance
        super(Node, self).__init__(*args, **kwargs)

    def get_slug(self):
        return self.slug or self._id

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
        return UniqueKey.objects.create().key

    def has_parent(self):
        # TODO: this method is not needed any more in favor of self.parent
        return self.parents and len(self.parents) > 0

    def get_parent(self):
        if self._parent is None:
            if self.parent:
                # TODO: returned instance must be mapped to model described in
                # ``doc_type``.
                self._parent = self.get(self.parents[-1])
        return self._parent

    def get_ancestors(self):
        if self.parent:
            return couch.ancestors(key=self._id)
        else:
            return []

    def set_parents(self, parent_node):
        """Sets ``parents`` property by given parent node."""
        if parent_node:
            self.parents = list(parent_node.parents) or []
            self.parents.append(parent_node._id)
        else:
            self.parents = []

    def get_title(self):
        return self.title

    @classmethod
    def get_or_none(cls, id):
        try:
            return cls.get(id)
        except ResourceNotFound:
            return None

    def get_body(self):
        try:
            return self.fetch_attachment('body')
        except ResourceNotFound:
            return None

    def set_body(self, body, content_type='text/restructured'):
        self.put_attachment(body, 'body', 'text/html')

    def save(self):
        body = self._doc.pop('body', None)
        super(Node, self).save()
        if body is not None:
            self.set_body(body)

    def render_body(self):
        # TODO: only render content with restructuredtext if content type is
        # text/restructured
        return markup.restructuredtext(self.get_body())
    render_body.is_safe = True

    def permalink(self):
        return reverse('node', args=[self.get_slug()])

    def before_save(self, form, node, create=False):
        """This method will be called before saving node.

        You can override this method to some extra work with node before saving
        it.
        """
        pass

    def before_child_save(self, form, node, create=False):
        """This method will be called before saving child node.

        This method does same as before_save, except is called on parent node.
        """
        pass

    def is_root(self):
        return IRoot.providedBy(self)


provideNode(Node, "node")


class Root(Node):
    implements(IRoot)

provideNode(Root, "root")


_root_node = None

def getRootNode():
    global _root_node
    if _root_node is None:
        key = '~'
        try:
            _root_node = couch.get(key)
        except ResourceNotFound:
            _root_node = Root()
            _root_node._id = key
            _root_node.save()
    return _root_node


class Comment(Node):
    implements(IComment)

provideNode(Comment, "comment")


class History(Node):
    implements(IHistory)

    change_choices = tuple()

    # Full node dict, that was some how changed.
    node = schema.DictProperty()

    # A slug, that describes what kind of change was made.
    change = schema.StringProperty()

    @classmethod
    def create(cls, node, change):
        self = cls()
        self._id = self.get_new_id()
        if change in self.change_choices:
            self.change = change
        else:
            raise KeyError("Change '%s' is not in change choices." % change)
        self.set_parents(node)
        self.node = dict(node)
        self.save()
        return self

    def render_body(self):
        return _('Node was modified.')

provideNode(History, "history")


class Tag(Node):
    implements(ITag)

    @classmethod
    def create(cls, tag):
        self = cls()
        self._id = tag
        self.save()
        return self

    @classmethod
    def create_if_not_exists(cls, tag):
        self = cls.get_or_none(tag)
        if self is None:
            return cls.create(tag)
        else:
            return self

    def before_child_save(self, form, node, create=False):
        if create:
            node.tags = [self._id]

provideNode(Tag, "tag")


class TagsChange(History):
    implements(ITagsChange)

    change_choices = ('tags-change',)

provideNode(TagsChange, "tags-change")


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
