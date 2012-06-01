from django.conf import settings
from django.http import HttpResponseBadRequest

from .nodes import JsonView


class AjaxView(JsonView):
    """Simple view, for rendering JSON response.

    This view validates if request is ajax request before render.

    Example how to use this view::

        from sboard.ajax import AjaxView
        from sboard.json import json_response

        from .interfaces import IMyNode

        class MyJsonView(AjaxView):
            adapts(IMyNode)

            def render(self, **overrides):
                return json_response({'message': 'hello world'})


    """
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE',)

    def set_view_func(self, view):
        view.csrf_exempt = True

    def validate(self):
        response = super(AjaxView, self).validate()
        if response:
            return response
        if self.request.method not in self.allowed_methods:
            return HttpResponseBadRequest()
        if not settings.DEBUG and not self.request.is_ajax():
            return HttpResponseBadRequest()

    def render(self, **overrides):
        raise NotImplementedError
