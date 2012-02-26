from django.utils.translation import ugettext_lazy as _

from sboard.nodes import BaseNode

from .models import Discussion


class DiscussionNode(BaseNode):
    slug = 'discussions'
    name = _('Discussion')
    model = Discussion

    list_create = True
