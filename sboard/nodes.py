from django.conf import settings
from django.http import Http404
from django.shortcuts import render, redirect
from django.utils.importlib import import_module
from django.utils.translation import ugettext_lazy as _

from pyes import TermQuery, Search

from . import es
from .forms import NodeForm, TagForm, CommentForm
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
        return BaseNode()
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

    templates = {}

    def __init__(self, node=None):
        self.node = node

    @classmethod
    def get_urls(cls):
        return None

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
        raise NotImplementedError

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

    def create_view(self, request):
        if not self.node:
            raise Http404
        else:
            return super(CommentNode, self).create(request)


class TagNode(BaseNode):
    slug = 'tags'
    name = _('Tag')
    model = Tag

    def details_view(self, request, context_overrides=None):
        children = couch.by_tag(key=self.node._id, include_docs=True, limit=10)
        template = 'sboard/node_list.html'

        context = {
            'node': self.node,
            'children': children,
        }
        context.update(context_overrides or {})

        if 'tag_form' not in context:
            context['tag_form'] = TagForm(self.node)

        if 'comment_form' not in context:
            context['comment_form'] = CommentForm()

        return render(request, template, context)


class HistoryNode(BaseNode):
    name = _('History')
    model = History


class TagsChangeNode(BaseNode):
    name = _('Tags change')
    model = TagsChange
