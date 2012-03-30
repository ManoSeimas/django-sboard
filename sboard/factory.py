from zope.component import getUtilitiesFor
from zope.component import getUtility
from zope.component import provideUtility
from zope.interface import Interface
from zope.interface import directlyProvides
from zope.interface import implementedBy
from zope.interface import implements


class INodeFactory(Interface): pass


class NodeFactory(object):
    implements(INodeFactory)

    def __init__(self, node_class, name):
        self.node_class = node_class
        self.name = name

    def __call__(self, *args, **kw):
        return self.node_class(*args, **kw)

    def __repr__(self):
        return '<%s for %s>' % (self.__class__.__name__, repr(self.node_class))

    # TODO: move this method some where
    # think, how node factories should be implemented overall.
    def has_child_permission(self, node, action):
        return True


def provideNode(node_class, name=""):
    """Provides ``node_class`` to global component registry."""
    node_factory = NodeFactory(node_class, name)
    directlyProvides(node_factory, implementedBy(node_class))
    provideUtility(node_factory, INodeFactory, name)


def getNodeFactory(name):
    """Returns node class by given ``name``."""
    return getUtility(INodeFactory, name)


def getNodeClass(name):
    """Returns node class by given ``name``."""
    return getNodeFactory(name).node_class


def createNode(name, *args, **kwargs):
    """Returns new node instance by given ``name``."""
    return getNodeClass(name)(*args, **kwargs)


def getNodeFactories():
    return getUtilitiesFor(INodeFactory)
