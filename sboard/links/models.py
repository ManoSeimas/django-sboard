from couchdbkit.ext.django import schema

from sboard.models import Node


class Link(Node):
    link = schema.StringProperty(required=True)

Link.set_db(Node.get_db())
