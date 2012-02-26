from django.utils.translation import ugettext_lazy as _

from sboard.models import couch
from sboard.nodes import BaseNode

from .forms import CategoryForm
from .models import Category


class CategoryNode(BaseNode):
    slug = 'categories'
    name = _('Category')
    model = Category
    form = CategoryForm

    listing = True

    def get_node_list(self):
        return couch.children(key=self.node._id, include_docs=True, limit=10)
