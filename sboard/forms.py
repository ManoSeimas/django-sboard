from couchdbkit.ext.django.forms import DocumentForm

from .models import Node, Comment


class NodeForm(DocumentForm):
    class Meta:
        document = Node
        properties = ('title', 'body')


class CommentForm(NodeForm):
    class Meta:
        document = Comment
        properties = ('body',)
