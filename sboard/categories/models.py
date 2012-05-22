from zope.interface import implements

from sboard.factory import provideNode
from sboard.models import Node

from .interfaces import ICategory


def _get_tree_node(row, last_level, current_level, next_level):
    row['open_levels'] = row['close_levels'] = []
    if current_level > last_level:
        row['open_levels'] = range(current_level - last_level)
    if current_level > next_level:
        row['close_levels'] = range(current_level - next_level)
    row['level'] = current_level
    return row


def iterate_tree(view):
    last_level = 0
    current_row = None
    for next_row in view:
        if current_row:
            current_level = len(current_row['key'])
            next_level = len(next_row['key'])
            yield _get_tree_node(current_row, last_level, current_level,
                                 next_level)
            last_level = current_level
        current_row = next_row
    if current_row:
        current_level = len(current_row['key'])
        next_level = 0
        yield _get_tree_node(current_row, last_level, current_level,
                             next_level)


class Category(Node):
    implements(ICategory)

provideNode(Category, 'category')
