from zope.interface import Interface


class INodeView(Interface):
    """A view, that takes request and node instances and renders response."""


class IHttpRequest(Interface): pass


class INode(Interface):
    """Node is a content object stored in database.

    Each node at least stores author and body.

    Optionally all nodes can have a parent node.
    """


class IComment(INode):
    """Comment node is a spacial node object that acts as a comment for
    existing node."""


class IComment(INode): pass
class ITag(INode): pass
class IHistory(INode): pass
class ITagsChange(INode): pass
