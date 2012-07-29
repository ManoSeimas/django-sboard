from zope.component import getUtilitiesFor
from zope.component import getUtility
from zope.component import provideUtility
from zope.interface import Interface
from zope.interface import directlyProvides
from zope.interface import implementedBy
from zope.interface import implements

from django.conf import settings
from django.utils.importlib import import_module
from django.utils.module_loading import module_has_submodule


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


class IViewExtFactory(Interface): pass


class ViewExtFactory(object):
    implements(IViewExtFactory)

    def __init__(self, interface, ext):
        self.interface = interface
        self.ext = ext


def provideViewExt(interface, ext):
    factory = ViewExtFactory(interface, ext)
    provideUtility(factory, IViewExtFactory, ext)


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


def autodiscover():
    """
    Auto-discover INSTALLED_APPS nodes.py modules and fail silently when
    not present. This forces an import on them to register any node bits they
    may want.
    """

    for app in settings.INSTALLED_APPS:
        mod = import_module(app)

        # Make sure that models are imported. Without this, if the
        # ``nodes`` module doesn't import ``models``, nodes defined there may
        # not be registered with ZCA and doctypes won't be detected correcly.
        # This happens rarely under certain mysterious circumstances.
        if module_has_submodule(mod, 'models'):
            import_module('%s.models' % app)

        if module_has_submodule(mod, 'nodes'):
            import_module('%s.nodes' % app)


_search_handlers = None

def get_search_handlers():
    global _search_handlers
    if _search_handlers is None:
        _search_handlers = []
        for pth in settings.SBOARD_SEARCH_HANDLERS:
            pth, name = pth.rsplit('.', 1)
            mod = import_module(pth)
            handler = getattr(mod, name)
            _search_handlers.append(handler)
    return _search_handlers
