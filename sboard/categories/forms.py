from django import forms

from couchdbkit.ext.django.forms import DocumentForm

from .models import Category


class CategoryForm(DocumentForm):
    title = forms.CharField()
    parent = forms.SlugField(required=False)
    body = forms.CharField(widget=forms.Textarea, required=False)

    class Meta:
        document = Category
        properties = ('title', 'parent', 'body')
