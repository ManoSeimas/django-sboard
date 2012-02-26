from sboard.models import Node


class Category(Node):
    pass

Category.set_db(Node.get_db())
