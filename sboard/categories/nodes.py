from zope.component import adapts
from zope.component import provideAdapter

from sboard.models import couch
from sboard.nodes import CreateView

from .forms import CategoryForm
from .interfaces import ICategory


class CategoryCreateView(CreateView):
    adapts(object, ICategory)

    form = CategoryForm

    listing = True

    def get_node_list(self):
        return couch.children(key=self.node._id, include_docs=True, limit=10)

provideAdapter(CategoryCreateView, name="create")

# Show category in ListView by default.
#provideAdapter(ListView, (ICategory,))
