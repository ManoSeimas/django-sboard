from sboard.models import Node


class Question(Node):
    pass

Question.set_db(Node.get_db())
