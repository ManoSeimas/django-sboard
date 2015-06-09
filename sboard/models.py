import datetime
import functools
import itertools
import os
import os.path

from zope.interface import implements

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.db import models
from django.db import transaction
from django.dispatch import Signal
from django.utils.translation import ugettext_lazy as _

from couchdbkit.exceptions import BadValueError
from couchdbkit.exceptions import MultipleResultsFound
from couchdbkit.exceptions import NoResultFound
from couchdbkit.exceptions import ResourceNotFound
from couchdbkit.ext.django import schema
from couchdbkit.ext.django.loading import couchdbkit_handler

from sorl.thumbnail import get_thumbnail

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
from .interfaces import IPage
from .permissions import Permissions
from .utils import base36
from sboard import markup

node_pre_delete = Signal()

class DocTypeMap(dict):
    """Special dict, that provides doc_type map for instances returned by view.

    CouchDB view call can return documents with different types, this
    dictionary provides model classes for those document types.
    """
    def __init__(self, *args, **kwargs):
        super(DocTypeMap, self).__init__(*args, **kwargs)

        self.default = getNodeClass("node")
        for name, factory in getNodeFactories():
            doc_type = factory.node_class.__name__
            if doc_type not in self:
                self[doc_type] = factory.node_class

    def __getitem__(self, key):
        return self.get(key)

    def get(self, key, default=None):
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
        cls = self.get_doc_type_map().get(data['doc_type'])
        return cls.wrap(data)

    def get(self, docid, rev=None):
        assert docid, "``docid`` can't be empty"
        db = Node.get_db()
        return db.get(docid, rev=rev, wrapper=self.wrap)

    def check_kwargs(self, kwargs):
        # slice key
        if 'skey' in kwargs:
            skey = kwargs.pop('skey')
            if not isinstance(skey, (list, tuple)):
                skey = [skey]
            ekey = skey + [u'\ufff0']
            if kwargs.get('descending'):
                kwargs.update(dict(startkey=ekey, endkey=skey))
            else:
                kwargs.update(dict(startkey=skey, endkey=ekey))

    def view(self, view, **kwargs):
        self.check_kwargs(kwargs)
        kwargs.setdefault('include_docs', True)
        kwargs.setdefault('classes', self.get_doc_type_map())
        return Node.view(view, **kwargs)

    def iterchunks(self, view, **kwargs):
        counter = None
        rows_per_chunk = 50
        while counter is None or counter > rows_per_chunk:
            counter = 0
            kwargs['limit'] = rows_per_chunk + 1
            for row in self.view(view, **kwargs):
                counter += 1
                if counter > rows_per_chunk:
                    kwargs['startkey'] = row['key']
                    kwargs['startkey_docid'] = row['id']
                else:
                    yield row


couch = SboardCouchViews()


def parse_node_slug(slug):
    if slug and '+' in slug:
        return slug.split('+')
    else:
        return slug, None


def get_node_by_slug(slug=None):
    """Returns Node instance, None or ViewResults instance."""
    slug, key = parse_node_slug(slug)
    if key:
        try:
            return couch.get(key)
        except (ResourceNotFound, NoResultFound):
            return None

    if slug is None or slug == '~':
        return getRootNode()

    query = couch.by_slug(key=slug, limit=20)
    try:
        return query.one(except_all=True)
    except MultipleResultsFound:
        return query
    except (ResourceNotFound, NoResultFound):
        return None


class NodeRef(object):
    def __init__(self):
        self._id = None
        self._node = None

    def _set_id(self, id):
        """Update NodeRef by given node ID."""
        if self._id != id:
            self._id = id
            self._node = None

    def _set_node(self, node):
        """Update NodeRef by given node instance."""
        self._id = node._id
        self._node = node

    @property
    def ref(self):
        """Get node by this reference."""
        if self._node is None:
            self._node = couch.get(self._id)
        return self._node

    @property
    def key(self):
        return self._id


class NodeProperty(schema.Property):
    def __init__(self, *args, **kwargs):
        self._ref = NodeRef()
        super(NodeProperty, self).__init__(*args, **kwargs)

    def validate(self, value, required=True):
        value = super(NodeProperty, self).validate(value, required)
        if value and not isinstance(value, (NodeRef, BaseNode)):
            raise BadValueError(
                'Property %s must be BaseNode instance, not a %s' % (
                    self.name, type(value).__name__))
        return value

    def __set__(self, document_instance, value):
        if isinstance(value, BaseNode):
            self._ref._set_node(value)
            value = self._ref
        super(NodeProperty, self).__set__(document_instance, value)

    def to_python(self, value):
        if not value:
            return None
        self._ref._set_id(value)
        return self._ref

    def to_json(self, value):
        if value:
            return value._id
        else:
            return None

    data_type = unicode


class NodeRefDescriptor(object):
    def __init__(self, field):
        self._field = field
        self.refattr = '_%s_noderef' % field.name

    def __set__(self, instance, value):
        if isinstance(value, NodeRef):
            setattr(instance, self.refattr, value)

        ref = self._get_ref(instance)
        if value is None:
            ref._set_id(None)
        elif isinstance(value, BaseNode):
            ref._set_node(value)
        else:
            ref._set_id(value)

    def __get__(self, instance, instance_type=None):
        return self._get_ref(instance)

    def _get_ref(self, instance):
        if not hasattr(instance, self.refattr):
            setattr(instance, self.refattr, NodeRef())
        return getattr(instance, self.refattr)


class NodeForeignKey(models.CharField):
    def __init__(self, **kwargs):
        kwargs.setdefault('max_length', 16)
        super(NodeForeignKey, self).__init__(**kwargs)

    def to_python(self, value):
        if value is None or isinstance(value, NodeRef):
            return value

        ref = NodeRef()
        if isinstance(value, BaseNode):
            ref._set_node(value)
        else:
            ref._set_id(value)
        return ref

    def get_prep_value(self, value):
        return self.to_python(value)

    def get_db_prep_value(self, value, connection, prepared=False):
        if not prepared:
            value = self.get_prep_value(value)
        return value._id

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_db_prep_value(value)

    def contribute_to_class(self, cls, name):
        super(NodeForeignKey, self).contribute_to_class(cls, name)
        setattr(cls, self.name, NodeRefDescriptor(self))


class UniqueKeyManager(models.Manager):
    @transaction.atomic
    def create(self):
        obj = UniqueKey()
        obj.save()
        obj.key = base36(obj.pk).zfill(6)
        obj.save()
        return obj

    def last_key(self):
        return self.latest('pk')._id


class UniqueKey(models.Model):
    """Unique key generator.

    This model ensures unique key generation, incremented by 1 and converted to
    base36.

    Generated key is 6 characters length and can identify 2 176 782 335 nodes.

    XXX: Thsese tests or whole UniqueKey model should be refactored, since now,
    id is not predictible, because now fixtures have user, and that user
    triggers signal that creates profile not for that user and UniqueKey
    inclreases. If there is more situations like this, ID again can chainge.

    Maybe UniqueKey, should only store one record, with lates key... (?)

        >>> keys = set()
        >>> keys.add(UniqueKey.objects.create().key._id)
        >>> keys.add(UniqueKey.objects.create().key._id)
        >>> keys.add(UniqueKey.objects.create().key._id)
        >>> len(keys)
        3

    """
    key = NodeForeignKey(unique=True, null=True)

    objects = UniqueKeyManager()


def get_new_id():
    last_id = couch.view('sboard/max_id', reduce=True, group=False,
                         include_docs=False,
                         startkey='000000', endkey='ffffff').one()['value']
    next_numeric_id = int(last_id, 36) + 1
    return base36(next_numeric_id).zfill(6)


def set_nodes_ambiguous(nodes):
    """Sets all nodes as ambiguous if not set already."""
    for node in nodes:
        if not node.ambiguous:
            node.ambiguous = True
            node.save()


class BaseNode(schema.Document):
    # Node slug, that is used to get node from human readable url address.
    slug = schema.StringProperty()

    # If True, tells that there is more than one node with this same slug.
    ambiguous = schema.BooleanProperty(default=False)

    # Node title.
    title = schema.StringProperty()

    # Node keywords, used in search.
    keywords = schema.ListProperty()

    # Shor node summary, mostly used in list, search results, to show small
    # summary about node.
    summary = schema.StringProperty()

    # Node creation datetime.
    created = schema.DateTimeProperty(default=datetime.datetime.utcnow)

    # Immediate node parent.
    parent = NodeProperty(required=False)

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
    # If importance is 0, then this node will not appear in any list including
    # search.
    importance = schema.IntegerProperty()

    permissions = schema.ListProperty()

    # Number that shows how many people likes or dislikes content of this node.
    likes = schema.IntegerProperty(default=0)
    dislikes = schema.IntegerProperty(default=0)

    # An image related to this node.
    image = NodeProperty(required=False)

    _parent = None

    def __init__(self, *args, **kwargs):
        self._properties['importance'].default = self._default_importance
        self._permissions = None
        super(BaseNode, self).__init__(*args, **kwargs)

    def __repr__(self):
        class_name = self.__class__.__name__
        return '<%s %s>' % (class_name, self._id)

    @property
    def key(self):
        return self._id

    def __hash__(self):
        return hash(self._id)

    def __eq__(self, other):
        return self._id == other._id

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

    def get_slug(self):
        return self.slug or self._id

    def get_slug_with_key(self):
        if self.slug:
            return '%s+%s' % (self.slug, self._id)
        else:
            return '+%s' % (self._id,)

    def urlslug(self):
        if self.ambiguous and self.slug:
            return self.get_slug_with_key()
        else:
            return self.get_slug()

    def permalink(self, *args, **kwargs):
        name = 'node'
        args = (self.urlslug(),) + args
        ext = kwargs.get('ext')
        if ext:
            args += (ext,)
            name = 'node_ext'
        return reverse(name, args=args)

    def get_new_id(self):
        return get_new_id()

    def set_new_id(self):
        self._id = self.get_new_id()

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

    def set_parent(self, parent):
        self.parent = parent
        self.set_parents(parent)

    def set_parents(self, parent):
        """Sets ``parents`` property by given parent node."""
        if parent:
            self.parents = list(parent.parents) or []
            self.parents.append(parent._id)
        else:
            self.parents = []

    def is_root(self):
        return IRoot.providedBy(self)

    def get_title(self):
        return self.title

    @classmethod
    def get_or_none(cls, id):
        try:
            return cls.get(id)
        except ResourceNotFound:
            return None

    def image_url(self, size):
        if self.image:
            geometry = '%dx%d' % (size, size)
            return self.image.ref.thumbnail(geometry=geometry).url

    def set_image(self, data, ext):
        if self.image:
            image = self.image.ref
        else:
            image = ImageNode()
            image.set_new_id()
        image.title = self.title
        image.set_parent(self)
        image.ext = ext
        image.save()
        image.put_attachment(
            data,
            'file.%s' % ext,
            content_length=getattr(data, 'size', None),
        )
        self.image = image


    def get_permissions(self):
        if self._permissions is not None:
            return self._permissions

        permissions = Permissions()
        permissions.update(getRootNode().permissions)

        for ancestor in self.get_ancestors():
            permissions.update(ancestor.permissions)
        permissions.update(self.permissions)

        self._permissions = permissions
        return self._permissions

    def can(self, request, action, factory=None):
        permissions = self.get_permissions()
        return permissions.can(request, action, factory)

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

    def delete(self):
        node_pre_delete.send(sender=self)
        super(BaseNode, self).delete()


class Node(BaseNode):
    implements(INode)

    # Author, who initially created this node.
    author = schema.StringProperty()

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
    _default_importance = 0

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

def get_file_node_cache_path(id,with_ext=True):
        """Returns the path to a previously cached file node. This method expects
        a symlink to cache extension data, allowing it to be used without
        a File Node instance.
        """
        prefix = id[-2:]
        suffix = id[:-2]
        dirpath = os.path.join(settings.MEDIA_ROOT, 'node', prefix)
        linkpath = os.path.join(dirpath, suffix)

        if not with_ext:
            return linkpath

        if not os.path.exists(linkpath):
            return None

        return os.path.join(dirpath, os.readlink(linkpath))


class FileNode(Node):
    _default_importance = 0

    ext = schema.StringProperty(required=True)

    def path(self, fetch=True):
        """Returns file path.

        If file is not already stored from attachment to file system, then first it
        will be located and stored.
        """

        linkpath = get_file_node_cache_path(self._id, False)
        filepath = linkpath + "." + self.ext
        dirpath = os.path.dirname(filepath)

        if not fetch:
            return filepath

        if not os.path.exists(filepath):
            if not os.path.exists(dirpath):
                os.makedirs(dirpath)

            stream = self.fetch_attachment('file.%s' % self.ext, stream=True)
            f = open(filepath, 'wb')
            while True:
                chunk = stream.read(1024)
                if chunk:
                    f.write(chunk)
                else:
                    break
            f.close()

        if os.path.exists(linkpath):
            linktarget = os.path.join(dirpath, os.readlink(linkpath))
            if linktarget is not filepath:
                os.unlink(linkpath)
                os.symlink(filepath, linkpath)
        else:
            if not os.path.exists(dirpath):
                os.makedirs(dirpath)
            os.symlink(filepath, linkpath)

        return filepath



provideNode(FileNode, "file")

def get_image_node_thumbnail(id, geometry):
    """ Returns ImageNode thumbnail path without instantiating
        an ImageNode unless necessary.
    """
    image_path = get_file_node_cache_path(id, True)
    if image_path and os.path.exists(image_path):
        return get_thumbnail(image_path, geometry, upscale=False)
    else:
        image_node = get_node_by_slug("+"+id)
        return image_node.thumbnail(geometry)


class ImageNode(FileNode):
    def thumbnail(self, geometry):
        path = self.path()
        return get_thumbnail(path, geometry, upscale=False)

provideNode(ImageNode, "image")


class CustomImage(Image):
    def run(self):
        media = get_node_by_slug(self.arguments[0])
        self.arguments[0] = reverse('media_normal_size',
                                    args=[media._id, media.ext])
        return super(CustomImage, self).run()

directives.register_directive('image-node', CustomImage)


class Page(Node):
    implements(IPage)

    template = schema.StringProperty(required=True, default='sboard/page.html')

provideNode(Page, "page")



def prefetch_nodes(attr, objects):
    if not isinstance(objects, tuple):
        objects = (objects,)

    # Get all keys
    keys, keymap = [], {}
    for obj in itertools.chain(*objects):
        key = getattr(obj, attr)._id
        keys.append(key)
        keymap[key] = obj

    # Get all nodes and assign to attributes.
    for node in couch.view('_all_docs', keys=keys):
        obj = keymap[node._id]
        setattr(obj, attr, node)
