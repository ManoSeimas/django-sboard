from zope.component import adapts
from zope.component import provideAdapter

from django.shortcuts import render

from ..nodes import NodeView
from .interfaces import IProfile


class ProfileView(NodeView):
    adapts(IProfile)
    template = 'sboard/profile.html'

    def render(self, **overrides):
        template = overrides.pop('template', self.template)

        context = {
            'view': self,
            'profile': self.node,
        }
        context.update(overrides)

        return render(self.request, template, context)

provideAdapter(ProfileView)
