from django.conf import settings
from django.http import Http404
from django.shortcuts import render, redirect
from django.utils.importlib import import_module
from django.utils.translation import ugettext_lazy as _

from .forms import NodeForm, CommentForm
from .models import Node, Comment

_nodes_by_name = None


def get_node_view_class(name):
    global _nodes_by_name
    if _nodes_by_name is None:
        _nodes_by_name = {
            'node': BaseNode,
            'comment': CommentNode,
        }
        for item in settings.SBOARD_NODES:
            module_name, class_name = item.rsplit('.', 1)
            module = import_module(module_name)
            node_class = getattr(module, class_name)
            _nodes_by_name[node_class.name] = node_class
    return _nodes_by_name[name]


def get_node_view(key=None):
    """Returns node view class instance by node key."""
    if key is None:
        return BaseNode()
    else:
        node = Node.get(key)
        view_class = get_node_view_class(node.doc_type.lower())
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

    def details(self, request):
        if self.node:
            # TODO: a hi-tech algorithm needed here, that can take all
            # comment tree, two levels deep and display this tree in one
            # cycle.
            children = Comment.view('sboard/children', key=self.node._id,
                                    include_docs=True, limit=10)
            template = 'sboard/node_details.html'
        else:
            children = Comment.view('sboard/topics', include_docs=True,
                                    limit=10)
            template = 'sboard/node_list.html'

        return render(request, template, {
              'node': self.node,
              'children': children,
              'comment_form': CommentForm(),
          })

    def create(self, request):
        if request.method == 'POST':
            form = self.form(request.POST)
            if form.is_valid():
                node = form.save(commit=False)
                node._id = node.get_new_id()
                if self.node:
                    node.parents = self.node.parents or []
                    node.parents.append(self.node._id)
                    node.save()
                    return redirect(self.node.permalink())
                else:
                    node.save()
                    return redirect(node.permalink())
        else:
            form = self.form()

        return render(request, 'sboard/node_form.html', {
              'form': form,
          })

    def update(self, request):
        pass

    def delete(self, request):
        pass


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
