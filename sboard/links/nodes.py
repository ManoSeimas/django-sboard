from django.utils.translation import ugettext_lazy as _

from sboard.nodes import BaseNode

from .forms import LinkForm
from .models import Link


class LinkNode(BaseNode):
    slug = 'links'
    name = _('Link')
    model = Link
    form = LinkForm
