from django import forms

from couchdbkit.ext.django.forms import DocumentForm

from .models import Node, Comment


class NodeForm(DocumentForm):
    body = forms.CharField()

    class Meta:
        document = Node
        properties = ('title', 'body')


class TagForm(forms.Form):
    tag = forms.SlugField()

    def __init__(self, node, *args, **kwargs):
        super(TagForm, self).__init__(*args, **kwargs)
        self.node = node

    def clean_tag(self):
        tag = self.cleaned_data.get('tag')
        if tag and self.node.tags and tag in self.node.tags:
            raise forms.ValidationError(
                "This node already tagged with '%s' tag." % tag)
        return tag


class CommentForm(NodeForm):
    class Meta:
        document = Comment
        properties = ('body',)
