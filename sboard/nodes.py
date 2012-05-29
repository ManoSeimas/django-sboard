import re
import unidecode

from zope.component import adapts
from zope.component import provideAdapter
from zope.interface import implements

from django.http import Http404
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils.translation import ugettext_lazy as _

from .factory import getNodeFactories
from .factory import getNodeFactory
from .forms import CommentForm
from .forms import NodeForm
from .forms import TagForm
from .interfaces import IComment
from .interfaces import IHistory
from .interfaces import INode
from .interfaces import INodeView
from .interfaces import IRoot
from .interfaces import ITagsChange
from .models import BaseNode
from .models import Node
from .models import Tag
from .models import TagsChange
from .models import couch
from .models import getRootNode
from .permissions import Permissions
from .utils import slugify


_nodes_by_model = None

search_words_re = re.compile(r'[^a-z]+')


class NodeView(object):
    """Base node view class.

    Each node must be associated with node view class, where goes all request
    handling logic and response preparation.
    """

    implements(INodeView)
    adapts(INode)

    slug = None
    name = _('Node')
    node = None
    model = Node
    form = NodeForm

    # This property specifies if node can be created from list view.
    list_create = True

    # Tells if a node can be converted to this node.
    convert_to = True

    # If True, tells that this node is mainly used for listing other nodes and
    # by default ``list_view`` method will be called instead of
    # ``details_view``.
    # This property should be set to True for such nodes like CategoryNode,
    # TagNode, etc.
    listing = False

    permissions = []

    # Used to cache permissions object.
    _permissions = None

    template = None

    def __init__(self, node_or_factory=None):
        if isinstance(node_or_factory, BaseNode):
            self.node = node_or_factory
        else:
            self.node = None

    @classmethod
    def get_urls(cls):
        return None

    def get_permissions(self):
        if self._permissions is not None:
            return self._permissions

        permissions = Permissions()
        permissions.update(getRootNode().permissions)

        if self.node:
            for ancestor in self.node.get_ancestors():
                permissions.update(ancestor.permissions)
            permissions.update(self.node.permissions)

        self._permissions = permissions
        return self._permissions

    @classmethod
    def has_child_permission(cls, node, action):
        return True

    def can(self, action, factory=None):
        if factory is None:
            factory = getNodeFactory("node")

        if not factory.has_child_permission(self.node, action):
            return False

        permissions = self.get_permissions()
        return permissions.can(self.request, action, factory.name)

    def get_node_list(self):
        if self.node:
            key = self.node._id
            return couch.children_by_date(startkey=[key, 'Z'], endkey=[key],
                                          descending=True, limit=50)
        else:
            return couch.all_nodes(descending=True, limit=50)

    def get_form(self, *args, **kwargs):
        return self.form(self.node, *args, **kwargs)

    def form_save(self, form, node=None):
        create = node is None
        data = form.cleaned_data

        if node is None:
            node = self.factory()
            node._id = node.get_new_id()
            parent = data.pop('parent', None) or self.node
        else:
            parent = data.pop('parent', None)

        for key, val in data.items():
            setattr(node, key, val)

        if 'title' in data:
            node.slug = slugify(node.title)

        if 'parent' in data:
            # XXX: actualy parent is always known from self.node, some here more
            # strict checking must be implemented. Only privileged users should be
            # able to change node parent, since this is expensive operation...
            if parent:
                node.parent = parent
                node.set_parents(parent)

        if self.node:
            self.node.before_child_save(form, node, create=create)

        self.before_save(form, node, create=create)
        node.save()
        return node

    def before_save(self, form, node, create):
        pass

    def get_create_links(self, active=tuple()):
        nav = []
        if self.node:
            for name, factory in getNodeFactories():
                if self.can('create', factory):
                    nav.append({
                        'key': name,
                        'url': self.node.permalink('create', name),
                        'title': name,
                        'children': [],
                        'active': name in active,
                    })
        return nav

    def get_convert_to_links(self, active=tuple()):
        nav = []
        for name, factory in getNodeFactories():
            if self.can('create', factory):
                nav.append({
                    'key': name,
                    'url': self.node.permalink('convert', name),
                    'title': name,
                    'children': [],
                    'active': name in active,
                })
        return nav

    def nav(self, active=tuple()):
        nav = []

        # Edit
        if self.node and self.can('update'):
            key = 'update'
            link = self.node.permalink('update')
            nav.append({
                'key': key,
                'url': link,
                'title': _('Edit'),
                'children': [],
                'active': key in active,
            })

        # Create
        create_links = self.get_create_links()
        if create_links:
            key = 'create'
            nav.append({
                'key': key,
                'url': '#',
                'title': _('New entry'),
                'children': create_links,
                'active': key in active,
            })

        return nav


class ListView(NodeView):
    adapts(INode)

    template = 'sboard/node_list.html'

    def render(self, **overrides):
        node_list = overrides.pop('node_list', self.get_node_list)
        template = overrides.pop('template', self.template)

        if callable(node_list):
            node_list = node_list()

        if self.node:
            title = self.node.title
        else:
            title = _('All nodes')

        context = {
            'title': title,
            'view': self,
            'node': self.node,
            'children': node_list,
        }
        context.update(overrides or {})
        return render(self.request, template, context)

provideAdapter(ListView, (IRoot,))
provideAdapter(ListView, name="list")


class SearchView(ListView):
    def __init__(self, query):
        self.node = None
        self.query = query

    def get_node_list(self):
        qry = unidecode.unidecode(self.query)
        qry = qry.lower()
        qry = search_words_re.split(qry)
        qry = filter(None, qry)
        if len(qry):
            key = qry[0]
            args = dict(startkey=[key, 'Z'], endkey=[key])
            return couch.search(descending=True, limit=50, **args)
        else:
            return []


class DetailsView(NodeView):
    template = 'sboard/node_details.html'

    def render(self, **overrides):
        # TODO: a hi-tech algorithm needed here, that can take all
        # comment tree, two levels deep and display this tree in one
        # cycle.
        comments = couch.comments(startkey=[self.node._id, 'Z'],
                                  endkey=[self.node._id], descending=True,
                                  include_docs=True, limit=10)
        template = overrides.pop('template', self.template)

        context = {
            'title': self.node.title,
            'view': self,
            'node': self.node,
            'comments': comments,
        }
        context.update(overrides)

        if 'tag_form' not in context:
            context['tag_form'] = TagForm(None)

        if 'comment_form' not in context:
            context['comment_form'] = CommentForm(None)

        return render(self.request, template, context)

provideAdapter(DetailsView)
provideAdapter(DetailsView, name="details")


class CreateView(NodeView):
    # adapts(<parent_node>, <child_node_factory>)
    adapts(object, INode)

    def __init__(self, node, factory):
        self.node = node
        self.factory = factory

    def get_form(self, *args, **kwargs):
        return self.form(None, *args, **kwargs)

    def nav(self, active=tuple()):
        active = active or ('create',)
        return super(CreateView, self).nav(active)

    def render(self):
        if not self.can('create', self.factory):
            return render(self.request, '403.html', status=403)

        if self.request.method == 'POST':
            form = self.get_form(self.request.POST)
            if form.is_valid():
                child = self.form_save(form)
                if self.node:
                    return redirect(self.node.permalink())
                else:
                    return redirect(child.permalink())
        else:
            form = self.get_form()

        return render(self.request, 'sboard/node_form.html', {
              'title': _('Create new entry'),
              'form': form,
              'view': self,
          })

provideAdapter(CreateView, name="create")


class UpdateView(NodeView):
    def nav(self, active=tuple()):
        active = active or ('update',)
        return super(UpdateView, self).nav(active)

    def render(self):
        if not self.can('update'):
            return render(self.request, '403.html', status=403)

        if self.request.method == 'POST':
            form = self.get_form(self.request.POST)
            if form.is_valid():
                node = self.form_save(form, self.node)
                return redirect(node.permalink())
        else:
            form = self.get_form()

        return render(self.request, 'sboard/node_form.html', {
              'title': self.node.title,
              'form': form,
              'view': self,
          })

provideAdapter(UpdateView, name="update")


class ConvertView(NodeView):
    def render(self):
        if self.request.method == 'POST':
            doc = dict(self.node._doc)
            doc.pop('doc_type')
            node = self.model.wrap(doc)
            form = self.form(self.node, self.request.POST)
            if form.is_valid():
                node = self.form_save(form, node)
                return redirect(node.permalink())
        else:
            form = self.form(self.node)

        return render(self.request, 'sboard/node_form.html', {
              'title': self.node.title,
              'form': form,
          })

provideAdapter(ConvertView, name="convert")


class DeleteView(NodeView):
    def render(self):
        raise NotImplementedError

provideAdapter(DeleteView, name="delete")


class CommentCreateView(CreateView):
    adapts(object, IComment)

    form = CommentForm

    @classmethod
    def has_child_permission(cls, node, action):
        if action in ('create', 'convert'):
            return node is not None
        return True

    def render(self):
        # Can not create comment if parent node is not provided.
        if not self.node:
            raise Http404

        if self.request.method == 'POST':
            return super(CommentCreateView, self).render()
        else:
            details = DetailsView(self.node)
            details.request = self.request
            return self.render(comment_form=self.get_form())

provideAdapter(CommentCreateView, name="create")


class TagListView(ListView):
    adapts(INode)

    def get_node_list(self):
        return couch.by_tag(key=self.node._id, include_docs=True, limit=10)

provideAdapter(TagListView, name="tags")


class TagView(NodeView):
    adapts(INode)

    def render(self):
        if self.request.method != 'POST':
            raise Http404

        form = TagForm(self.node, self.request.POST)
        if form.is_valid():
            Tag.create_if_not_exists(form.cleaned_data['tag'])
            history_node = TagsChange.create(self.node, 'tags-change')
            self.node.tags.append(form.cleaned_data['tag'])
            self.node.history = history_node._id
            self.node.save()
            return redirect(self.node.permalink())
        else:
            details = DetailsView(self.node)
            details.request = self.request
            return self.render(tag_form=form)


provideAdapter(TagView, name="tag")


class HistoryView(NodeView):
    adapts(IHistory)


provideAdapter(HistoryView, name="history")


class TagsChangeView(NodeView):
    adapts(ITagsChange)

provideAdapter(TagsChangeView, name="tags-change")
