from django import forms
from django.core.validators import EMPTY_VALUES

from couchdbkit.exceptions import ResourceNotFound

from .models import couch


class NodeField(forms.SlugField):
    def clean(self, value):
        value = super(NodeField, self).clean(value)
        if value in EMPTY_VALUES:
            return value
        try:
            return couch.get(value)
        except ResourceNotFound:
            raise forms.ValidationError("'%s' does not exists." % value)
