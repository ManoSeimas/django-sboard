from django.utils.translation import ugettext_lazy as _

from sboard.nodes import BaseNode

from .models import Question


class QuestionNode(BaseNode):
    slug = 'questions'
    name = _('Question')
    model = Question

    list_create = True
