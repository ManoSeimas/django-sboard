from zope.component import adapts
from zope.component import provideAdapter

from django.shortcuts import render

from ..nodes import NodeView
from .interfaces import IProfile


class ProfileView(NodeView):
    adapts(IProfile)

    def render(self, **overrides):
        template = self.templates.get('profile', 'sboard/profile.html')
        template = overrides.pop('template', template)

        context = {
            'view': self,
            'profile': self.node,
        }
        context.update(overrides)

        return render(self.request, template, context)

provideAdapter(ProfileView)
