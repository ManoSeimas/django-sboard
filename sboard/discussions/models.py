from sboard.models import Node


class Discussion(Node):
    pass

Discussion.set_db(Node.get_db())
