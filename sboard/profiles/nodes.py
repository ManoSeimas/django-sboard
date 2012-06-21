from zope.component import adapts
from zope.component import provideAdapter

from django.shortcuts import render

from sboard.nodes import ListView
from sboard.nodes import NodeView
from sboard.nodes import UpdateView

from .forms import ProfileForm
from .interfaces import IGroup
from .interfaces import IProfile
from .models import query_group_membership


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


class ProfileUpdateView(UpdateView):
    form = ProfileForm

provideAdapter(ProfileUpdateView, name="update")


class GroupView(ListView):
    adapts(IGroup)
    template = 'sboard/group_members.html'

    def get_node_list(self):
        return query_group_membership(self.node._id)

provideAdapter(GroupView)
