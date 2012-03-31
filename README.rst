Node models
===========

Node views
==========

Example node view::

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
