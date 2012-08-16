from django import forms
from django.core.exceptions import ValidationError
from django.conf import settings

from django.contrib.markup.templatetags import markup

from .fields import NodeField


class BaseNodeForm(forms.Form):
    def __init__(self, node, *args, **kwargs):
        self.node = node
        if self.node:
            initial = self.get_initial_values()
            if 'initial' in kwargs:
                initial = initial.update(kwargs['initial'])
            kwargs['initial'] = initial
        super(BaseNodeForm, self).__init__(*args, **kwargs)

    def get_initial_values(self):
        initial = dict(self.node._doc)
        initial['body'] = self.node.get_body()
        return initial


def validate_body(body):
    try:
        markup.restructuredtext(body)
    except Exception as e:
        raise ValidationError('Error in markup: %s' % e)


class NodeForm(BaseNodeForm):
    title = forms.CharField()
    parent = NodeField(required=False)
    summary = forms.CharField(widget=forms.Textarea, required=False)
    body = forms.CharField(widget=forms.Textarea, required=False, validators=[validate_body])


class TagForm(BaseNodeForm):
    tag = NodeField()

    def clean_tag(self):
        tag = self.cleaned_data.get('tag')
        if tag and self.node.tags and tag in self.node.tags:
            raise forms.ValidationError(
                "This node already tagged with '%s' tag." % tag)
        return tag


class TagNodeForm(BaseNodeForm):
    title = forms.CharField(required=True)


class CommentForm(BaseNodeForm):
    body = forms.CharField(required=True, widget=forms.Textarea)


SBOARD_PAGE_TEMPLATES = getattr(settings, 'SBOARD_PAGE_TEMPLATES', (('sboard/page.html', 'Plain page'),))

class PageForm(BaseNodeForm):
    title = forms.CharField()
    template = forms.ChoiceField(choices=SBOARD_PAGE_TEMPLATES)
    body = forms.CharField(widget=forms.Textarea, required=False, validators=[validate_body])
