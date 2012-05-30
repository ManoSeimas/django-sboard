Node models
===========

.. _node views:

Node views
==========

Example node view:

.. code:: python

    # nodes.py

    from zope.component import adapts
    from zope.component import provideAdapter

    class DetailsView(NodeView):
        # Mandatory part, defines which node this view is adapting.
        adapts(INode)

    # Below are listed possible ways, how to tell sistem about your view
    existence.

    # If name is not provided, it means, that this view is default view for
    # adapted node. For example if you access node using this URL: /my-node/,
    # then most specific view, without name will be used.
    provideAdapter(DetailsView)

    # If you specify name, then this view will be used for URL's like this:
    /my-node/details/. As you can see, details comes right after node ID.
    provideAdapter(DetailsView, name="details")

    # You can adapt any existing view to any node, by giving secont parameter,
    in this case (ICategory,). This parameter does axactly the same ting as
    adapts(ICategory).
    provideAdapter(DetailsView, (ICategory,), name="details")

.. _node URLs:

Node URLs
=========

Each node has unique key and may have not unique slug. If node does not have
specified slug, then node URL will be constructed from unique key::

    0002ar

If node has slug, then slug is unique, then URL will be constructed using that
slug::

    some-slug-string

If node slug is not unique across all nodes, then URL will be constructed from
slug and key::

    some-slug-string+0002ar

We know that slug is not unique from node property ``ambiguous``, if this
property is set to ``True`` it means, that slug of this node is not unique.

Each node can be accessed directly, just providing direct node URL, described
above and with specified action and action name (or action argument).
Examples::

    /some-slug-string/
    /some-slug-string/update/
    /some-slug-string/create/comment/

Also, in some cases, action can be a slug, in these cases address looks like
this::

    /some-slug-string/othre-slug-string/
    /some-slug-string/othre-slug-string/action/

See `node views`_ section for more information, how view can be accessed using
dynamic slugs instead actions.

You can get node URL using ``permalink`` method or ``nodeurl`` template tag.

In python files:

.. code:: python

    node.permalink()
    node.permalink('update')
    node.permalink('create', 'comment')

In templates:

.. code:: html

    {% load sboard %}

    <a href="{{ node.permalink }}">{{ node.title }}</a>
    <a href="{% nodeurl node 'update' %}">Edit</a>
    <a href="{% nodeurl node 'create' 'comment' %}">Create comment</a>
