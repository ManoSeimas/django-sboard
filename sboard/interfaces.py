from zope.interface import Interface


class INodeView(Interface):
    """Node view.

    All implementing classes must provide render method, that returns Django
    HttpResponse object.

    """

class INodeJsonView(Interface):
    """Node AJAX view."""


class INodeDbView(Interface):
    """Views implementing this interface redirects to database record of
    requested node.."""


class IHttpRequest(Interface): pass


class IViewResults(Interface): pass


class INode(Interface):
    """Node is a content object stored in database.

    Each node at least stores author and body.

    Optionally all nodes can have a parent node.
    """

class IRoot(INode):
    """Special node where all settings are stored."""


class IComment(INode):
    """Comment node is a spacial node object that acts as a comment for
    existing node."""


class IComment(INode): pass
class ITag(INode): pass
class IHistory(INode): pass
class ITagsChange(INode): pass
