from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import Http404
from django.shortcuts import render, redirect
from django.utils.importlib import import_module
from django.utils.translation import ugettext_lazy as _

from pyes import TermQuery, Search

from . import es
from .forms import NodeForm, TagForm, TagNodeForm, CommentForm
from .models import Node, Comment, Tag, TagsChange, History, DocTypeMap, couch


_nodes_by_model = None


def get_node_classes():
    global _nodes_by_model
    if _nodes_by_model is None:
        _nodes_by_model = {
            'tag': TagNode,
            'node': BaseNode,
            'comment': CommentNode,
            'history': HistoryNode,
            'tagschange': TagsChangeNode,
        }
        for item in settings.SBOARD_NODES:
            module_name, class_name = item.rsplit('.', 1)
            module = import_module(module_name)
            node_class = getattr(module, class_name)
            _nodes_by_model[node_class.model.__name__.lower()] = node_class
    return _nodes_by_model


def get_node_view_class(slug):
    """Return node view class by node slug."""
    node_classes = get_node_classes()
    return node_classes[slug]


def get_node_view(key=None, node_type=None):
    """Returns node view class instance by node key."""
    if key is None:
        if node_type is None:
            view_class = BaseNode
        else:
            view_class = get_node_view_class(node_type)
        return view_class()
    else:
        node = couch.get(key)
        if node_type is None:
            view_class = get_node_view_class(node.doc_type.lower())
        else:
            view_class = get_node_view_class(node_type)
        return view_class(node)


def get_node_urls():
    urls = []
    for node_class in get_node_classes().values():
        _urls = node_class.get_urls()
        if _urls is not None:
            urls += _urls
    return urls


class BaseNode(object):
    """Base node view class.

    Each node must be associated with node view class, where goes all request
    handling logic and response preparation.
    """

    slug = None
    name = _('Node')
    node = None
    model = Node
    form = NodeForm

    # This property specifies if node can be created from list view.
    list_create = False

    # Tells if a node can be converted to this node.
    convert_to = True

    # If True, tells that this node is mainly used for listing other nodes and
    # by default ``list_view`` method will be called instead of
    # ``details_view``.
    # This property should be set to True for such nodes like CategoryNode,
    # TagNode, etc.
    listing = False

    templates = {}

    def __init__(self, node=None):
        self.node = node

    @classmethod
    def get_urls(cls):
        return None

    def get_create_links(self):
        for node in get_node_classes().values():
            if node.list_create:
                if self.node:
                    args = (self.node._id, node.model.__name__.lower())
                    link = reverse('node_create_child', args=args)
                    yield link, node.name
                else:
                    args = (node.model.__name__.lower(),)
                    link = reverse('node_create', args=args)
                    yield link, node.name

    @classmethod
    def can_convert_to(cls, node):
        return (cls.convert_to and node.__class__ is not cls.model and
                cls is not BaseNode)

    def get_convert_to_links(self):
        for node in get_node_classes().values():
            if node.can_convert_to(self.node):
                args = (self.node._id, node.model.__name__.lower())
                link = reverse('node_convert_to', args=args)
                yield link, node.name

    def get_node_list(self):
        if self.node:
            node_type = self.node.__class__.__name__
            return couch.by_type(startkey=[node_type, 'Z'], endkey=[node_type],
                                 descending=True, limit=50)
        else:
            node_type = self.node.__class__.__name__
            return couch.all_nodes(descending=True, limit=50)

    def list_view(self, request, overrides=None):
        overrides = overrides or {}
        get_node_list = overrides.pop('get_node_list', self.get_node_list)
        template = self.templates.get('list', 'sboard/node_list.html')
        template = overrides.pop('template', template)

        context = {
            'view': self,
            'node': self.node,
            'children': get_node_list(),
        }
        context.update(overrides or {})
        return render(request, template, context)

    def search_view(self, request, overrides=None):
        query = request.GET.get('q')
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
        return render(request, template, context)

    def details_view(self, request, overrides=None):
        # TODO: a hi-tech algorithm needed here, that can take all
        # comment tree, two levels deep and display this tree in one
        # cycle.
        children = couch.children(key=self.node._id,
                                  include_docs=True, limit=10)

        overrides = overrides or {}
        template = self.templates.get('details', 'sboard/node_details.html')
        template = overrides.pop('template', template)

        context = {
            'view': self,
            'node': self.node,
            'children': children,
        }
        context.update(overrides)

        if 'tag_form' not in context:
            context['tag_form'] = TagForm(self.node)

        if 'comment_form' not in context:
            context['comment_form'] = CommentForm()

        return render(request, template, context)

    def create_view(self, request):
        if request.method == 'POST':
            form = self.form(request.POST)
            if form.is_valid():
                node = form.save(commit=False)
                node._id = node.get_new_id()
                node.set_parents(self.node)
                if self.node:
                    self.node.before_child_save(form, node, create=True)
                node.before_save(form, node, create=True)
                node.save()

                if self.node:
                    return redirect(self.node.permalink())
                else:
                    return redirect(node.permalink())
        else:
            form = self.form()

        return render(request, 'sboard/node_form.html', {
              'form': form,
          })

    def update_view(self, request):
        if request.method == 'POST':
            form = self.form(request.POST, instance=self.node)
            if form.is_valid():
                # TODO: create history entry
                node = form.save(commit=False)
                if self.node:
                    self.node.before_child_save(form, node, create=False)
                node.before_save(form, node, create=False)
                node.save()
                return redirect(node.permalink())
        else:
            form = self.form(instance=self.node,
                             initial={'body': self.node.get_body()})

        return render(request, 'sboard/node_form.html', {
              'form': form,
          })

    def convert_to_view(self, request):
        if request.method == 'POST':
            doc = dict(self.node._doc)
            doc.pop('doc_type')
            node = self.model.wrap(doc)
            form = self.form(request.POST, instance=node)
            if form.is_valid():
                # TODO: create history entry
                node = form.save(commit=False)
                if self.node:
                    self.node.before_child_save(form, node, create=False)
                node.before_save(form, node, create=False)
                node.save()
                return redirect(node.permalink())
        else:
            initial = dict(self.node._doc)
            initial['body'] = self.node.get_body()
            form = self.form(instance=self.node, initial=initial)

        return render(request, 'sboard/node_form.html', {
              'form': form,
          })

    def delete_view(self, request):
        raise NotImplementedError

    def tag_view(self, request):
        if request.method != 'POST':
            raise Http404

        form = TagForm(self.node, request.POST)
        if form.is_valid():
            Tag.create_if_not_exists(form.cleaned_data['tag'])
            history_node = TagsChange.create(self.node, 'tags-change')
            self.node.tags.append(form.cleaned_data['tag'])
            self.node.history = history_node._id
            self.node.save()
            return redirect(self.node.permalink())
        else:
            return self.details_view(request, {
                'tag_form': form,
            })


class CommentNode(BaseNode):
    slug = 'comments'
    name = _('Comment')
    node = None
    model = Comment
    form = CommentForm

    @classmethod
    def can_convert_to(cls, node):
        return (super(CommentNode, cls).can_convert_to(node) and
                node.has_parent())

    def create_view(self, request):
        if not self.node:
            raise Http404
        else:
            return super(CommentNode, self).create(request)


class TagNode(BaseNode):
    slug = 'tags'
    name = _('Tag')
    model = Tag
    form = TagNodeForm

    listing = True

    def get_node_list(self):
        return couch.by_tag(key=self.node._id, include_docs=True, limit=10)


class HistoryNode(BaseNode):
    name = _('History')
    model = History
    convert_to = False


class TagsChangeNode(BaseNode):
    name = _('Tags change')
    model = TagsChange
    convert_to = False
