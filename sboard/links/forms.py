from django import forms

from sboard.forms import NodeForm

from .models import Link


class LinkForm(NodeForm):
    link = forms.URLField(required=True)

    class Meta:
        document = Link
        properties = ('title', 'link', 'body')
