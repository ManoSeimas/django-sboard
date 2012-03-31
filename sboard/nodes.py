from zope.component import adapts
from zope.component import provideAdapter
from zope.interface import implements

from django.core.urlresolvers import reverse
from django.http import Http404
from django.shortcuts import render, redirect
from django.utils.translation import ugettext_lazy as _

from pyes import TermQuery, Search

from . import es
from .factory import getNodeFactories
from .factory import getNodeFactory
from .forms import NodeForm, TagForm, TagNodeForm, CommentForm
from .interfaces import IComment
from .interfaces import IHistory
from .interfaces import INode
from .interfaces import INodeView
from .interfaces import ITag
from .interfaces import ITagsChange
from .interfaces import IRoot
from .models import Node, Comment, Tag, TagsChange, History, DocTypeMap, couch
from .models import getRootNode
from .permissions import Permissions


_nodes_by_model = None



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

    templates = {}

    def __init__(self, node_or_factory=None):
        if isinstance(node_or_factory, Node):
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

        # TODO: root node permissions should be also taken

        if self.node:
            for ancestor in self.node.get_ancestors():
                permissions.update(ancestor.permissions)
            permissions.update(self.node.permissions)

        self._permissions = permissions
        return self._permissions

    @classmethod
    def has_child_permission(cls, node, action):
        return True

    def can(self, action, factory):
        if factory is None:
            factory = getNodeFactory("node")

        if not factory.has_child_permission(self.node, action):
            return False

        permissions = self.get_permissions()
        return permissions.can(self.request, action, factory.name)

    def get_create_links(self):
        links = []
        for name, factory in getNodeFactories():
            if self.can('create', factory):
                if self.node:
                    args = (self.node._id, name)
                    link = reverse('node_create_child', args=args)
                    links.append((link, name))
                else:
                    args = (name,)
                    link = reverse('node_create', args=args)
                    links.append((link, name))
        return links

    def get_convert_to_links(self):
        links = []
        for name, factory in getNodeFactories():
            if self.can('create', factory):
                args = (self.node._id, name)
                link = reverse('node_convert_to', args=args)
                links.append((link, name))
        return links

    def get_node_list(self):
        if self.node:
            key = self.node._id
            return couch.children_by_date(startkey=[key, 'Z'], endkey=[key],
                                          descending=True, limit=50)
        else:
            return couch.all_nodes(descending=True, limit=50)

    def list_actions(self):
        actions = []
        if self.node:
            link = reverse('node_update', args=[self.node._id])
            actions.append((link, _('Edit'), None))

        create_links = self.get_create_links()
        if create_links:
            actions.append((None, _('Create new entry'), create_links))

        return actions

    def details_actions(self):
        actions = []
        if self.node:
            link = reverse('node_update', args=[self.node._id])
            actions.append((link, _('Edit'), None))

        actions.append((None, _('Convert to'),
                       self.get_convert_to_links()))

        return actions

    def get_form(self, *args, **kwargs):
        if self.node and not self.node.is_root():
            kwargs['initial'] = {'parent': self.node._id}
        return self.form(*args, **kwargs)

    def form_save(self, form, create):
        node = form.save(commit=False)
        if create:
            node._id = node.get_new_id()
        else:
            # TODO: create history entry
            pass
        # XXX: actualy parent is always known from self.node, some here more
        # strict checking must be implemented. Only privileged users should be
        # able to change node parent, since this is expensive operation...
        parent = form.cleaned_data.get('parent') or getRootNode()
        node.parent = parent._id
        node.set_parents(parent)
        if self.node:
            self.node.before_child_save(form, node, create=create)
        node.before_save(form, node, create=create)
        node.save()
        return node


class ListView(NodeView):
    adapts(INode)

    def render(self, overrides=None):
        overrides = overrides or {}
        get_node_list = overrides.pop('get_node_list', self.get_node_list)
        template = self.templates.get('list', 'sboard/node_list.html')
        template = overrides.pop('template', template)

        context = {
            'view': self,
            'node': self.node,
            'children': get_node_list(),
            'actions': self.list_actions(),
        }
        context.update(overrides or {})
        return render(self.request, template, context)

provideAdapter(ListView, (IRoot,))
provideAdapter(ListView, name="list")


class SearchView(ListView):
    def render(self, overrides=None):
        query = self.request.GET.get('q')
        if not query:
            raise Http404

        doc_type_map = DocTypeMap()
        q = TermQuery('title', query)
        search = Search(q, sort=[
                {'importance': {'order': 'desc'}},
                {'created': {'order': 'desc'}},
            ])

        results = es.conn.search(search)[:25]
        results = [doc_type_map[doc.get('doc_type')].wrap(doc)
                   for doc in results]

        overrides = overrides or {}
        template = self.templates.get('list', 'sboard/node_list.html')
        template = overrides.pop('template', template)

        context = {
            'view': self,
            'node': self.node,
            'children': results,
        }
        context.update(overrides or {})
        return render(self.request, template, context)

provideAdapter(SearchView, name="search")


class DetailsView(NodeView):
    def render(self, overrides=None):
        # TODO: a hi-tech algorithm needed here, that can take all
        # comment tree, two levels deep and display this tree in one
        # cycle.
        comments = couch.comments(startkey=[self.node._id, 'Z'],
                                  endkey=[self.node._id], descending=True,
                                  include_docs=True, limit=10)

        overrides = overrides or {}
        template = self.templates.get('details', 'sboard/node_details.html')
        template = overrides.pop('template', template)

        context = {
            'view': self,
            'node': self.node,
            'comments': comments,
            'actions': self.details_actions(),
        }
        context.update(overrides)

        if 'tag_form' not in context:
            context['tag_form'] = TagForm(self.node)

        if 'comment_form' not in context:
            context['comment_form'] = CommentForm()

        return render(self.request, template, context)

provideAdapter(DetailsView)
provideAdapter(DetailsView, name="details")


class CreateView(NodeView):
    # adapts(<parent_node>, <child_node_factory>)
    adapts(object, INode)

    def __init__(self, node, factory):
        self.node = node
        self.factory = factory

    def render(self):
        if not self.can('create', self.factory):
            return render(self.request, '403.html', status=403)

        if self.request.method == 'POST':
            form = self.get_form(self.request.POST)
            if form.is_valid():
                child = self.form_save(form, create=True)
                if self.node:
                    return redirect(self.node.permalink())
                else:
                    return redirect(child.permalink())
        else:
            form = self.get_form()

        return render(self.request, 'sboard/node_form.html', {
              'form': form,
          })

provideAdapter(CreateView, name="create")


class UpdateView(NodeView):
    def render(self):
        if self.request.method == 'POST':
            form = self.form(self.request.POST, instance=self.node)
            if form.is_valid():
                node = self.form_save(form, create=False)
                return redirect(node.permalink())
        else:
            form = self.form(instance=self.node,
                             initial={'body': self.node.get_body()})

        return render(self.request, 'sboard/node_form.html', {
              'form': form,
          })

provideAdapter(UpdateView, name="update")


class ConvertView(NodeView):
    def render(self):
        if self.request.method == 'POST':
            doc = dict(self.node._doc)
            doc.pop('doc_type')
            node = self.model.wrap(doc)
            form = self.form(self.request.POST, instance=node)
            if form.is_valid():
                node = self.form_save(form, create=False)
                return redirect(node.permalink())
        else:
            initial = dict(self.node._doc)
            initial['body'] = self.node.get_body()
            form = self.form(instance=self.node, initial=initial)

        return render(self.request, 'sboard/node_form.html', {
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
            return self.render({
                'comment_form': self.get_form(),
            })

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
            return self.render({
                'tag_form': form,
            })


provideAdapter(TagView, name="tag")


class HistoryView(NodeView):
    adapts(IHistory)


provideAdapter(HistoryView, name="history")


class TagsChangeView(NodeView):
    adapts(ITagsChange)

provideAdapter(TagsChangeView, name="tags-change")
