from django.conf import settings
from django.http import Http404
from django.shortcuts import render, redirect
from django.utils.importlib import import_module
from django.utils.translation import ugettext_lazy as _

from .forms import NodeForm, TagForm, CommentForm
from .models import Node, Comment, Tag, TagsChange, History, couch

_nodes_by_name = None


def get_node_classes():
    global _nodes_by_name
    if _nodes_by_name is None:
        _nodes_by_name = {
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
            _nodes_by_name[node_class.name] = node_class
    return _nodes_by_name


def get_node_view(key=None):
    """Returns node view class instance by node key."""
    if key is None:
        return BaseNode()
    else:
        node = Node.get(key)
        node_classes = get_node_classes()
        view_class = node_classes[node.doc_type.lower()]
        return view_class(node)


class BaseNode(object):
    """Base node view class.

    Each node must be associated with node view class, where goes all request
    handling logic and response preparation.
    """

    slug = 'node'
    name = _('Node')
    node = None
    model = Node
    form = NodeForm

    def __init__(self, node=None):
        self.node = node

    def details(self, request, context_overrides=None):
        if self.node:
            # TODO: a hi-tech algorithm needed here, that can take all
            # comment tree, two levels deep and display this tree in one
            # cycle.
            children = couch.children(key=self.node._id,
                                      include_docs=True, limit=10)
            template = 'sboard/node_details.html'
        else:
            children = couch.topics(include_docs=True, limit=10)
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

    def create(self, request):
        if request.method == 'POST':
            form = self.form(request.POST)
            if form.is_valid():
                node = form.save(commit=False)
                node._id = node.get_new_id()
                node.set_parents(self.node)
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

    def update(self, request):
        raise NotImplementedError

    def delete(self, request):
        raise NotImplementedError

    def tag(self, request):
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
            return self.details(request, {
                'tag_form': form,
            })


class CommentNode(BaseNode):
    slug = 'comment'
    name = _('Comment')
    node = None
    model = Comment
    form = CommentForm

    def create(self, request):
        if not self.node:
            raise Http404
        else:
            return super(CommentNode, self).create(request)


class TagNode(BaseNode):
    slug = 'tag'
    name = _('Tag')
    model = Tag

    def details(self, request, context_overrides=None):
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
    slug = 'history'
    name = _('History')
    model = History


class TagsChangeNode(BaseNode):
    slug = 'tags-change'
    name = _('Tags change')
    model = TagsChange
