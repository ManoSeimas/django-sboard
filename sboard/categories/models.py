from zope.interface import implements

from sboard.factory import provideNode
from sboard.models import Node

from .interfaces import ICategory


class Category(Node):
    implements(ICategory)

provideNode(Category, 'category')
