from zope.interface import implements

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _

from couchdbkit.ext.django import schema

from sboard.factory import provideNode
from sboard.models import BaseNode

from .interfaces import IProfile
from .interfaces import IGroup
from .interfaces import IMembership

KARMA_LEVEL_1 = 1
KARMA_LEVEL_2 = 99
KARMA_CHOICES = (
    (KARMA_LEVEL_1, _('Beginner')),
    (KARMA_LEVEL_2, _('Expert')),
)


class ProfileManager(models.Manager):
    def get_profile(self, user):
        if not user.is_authenticated():
            return None
        try:
            return user.profile
        except Profile.DoesNotExist:
            return self.create(user=user)


class Profile(models.Model):
    user = models.OneToOneField(User, verbose_name=_('User'))
    karma = models.IntegerField(_('Karma'), default=0, choices=KARMA_CHOICES)
    name = models.CharField(_('Name'), max_length=255)

    objects = ProfileManager()

    class Meta:
        verbose_name = _('Profile')
        verbose_name_plural = _('Profiles')

    def __unicode__(self):
        return self.name


def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

post_save.connect(create_user_profile, sender=User)


class ProfileNode(BaseNode):
    implements(IProfile)

    # Reference to Django user model.
    uid = schema.IntegerProperty()

    slug = schema.StringProperty()
    keywords = schema.ListProperty()
    importance = schema.IntegerProperty()

    title = schema.StringProperty()

    first_name = schema.StringProperty()
    last_name = schema.StringProperty()

    dob = schema.StringProperty()
    home_page = schema.StringProperty()

provideNode(ProfileNode, "profile")


class GroupNode(BaseNode):
    implements(IGroup)

    slug = schema.StringProperty()
    keywords = schema.ListProperty()
    importance = schema.IntegerProperty()

    title = schema.StringProperty()

provideNode(GroupNode, "group")


class MembershipNode(BaseNode):
    implements(IMembership)

    # Reference to profile node.
    profile = schema.StringProperty()

    # Reference to group node.
    group = schema.StringProperty()

    term_from = schema.DateProperty()
    term_to = schema.DateProperty()

    position = schema.StringProperty()

provideNode(MembershipNode, "membership")
