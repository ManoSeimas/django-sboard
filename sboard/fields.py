import re

from django import forms
from django.core.validators import EMPTY_VALUES
from django.core.validators import RegexValidator
from django.utils.translation import ugettext_lazy as _

from couchdbkit.client import ViewResults
from couchdbkit.exceptions import ResourceNotFound

from .models import get_node_by_slug
from .models import couch
from .urls import slug

slug_re = re.compile(r'^%s$' % slug)
validate_slug = RegexValidator(slug_re,
        _(u"Enter a valid 'slug' consisting of letters, numbers, underscores "
          u"or hyphens."), 'invalid')


class NodeField(forms.SlugField):
    default_validators = [validate_slug]

    def prepare_value(self, value):
        if value:
            try:
                node = couch.get(value)
                return node.urlslug()
            except ResourceNotFound:
                return value

    def clean(self, value):
        value = super(NodeField, self).clean(value)
        if value in EMPTY_VALUES:
            return None

        try:
            node = couch.get(value)
        except ResourceNotFound:
            node = get_node_by_slug(value)

        if node is None:
            raise forms.ValidationError(_("'%s' does not exists.") % value)
        elif isinstance(node, ViewResults):
            raise forms.ValidationError(
                    _("More than one node matched '%s' slug.") % value)
        else:
            return node
