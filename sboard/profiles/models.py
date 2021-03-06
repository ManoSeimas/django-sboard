import datetime
import hashlib

from zope.interface import implements

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from couchdbkit.ext.django import schema

from sorl.thumbnail import get_thumbnail

from sboard.factory import provideNode
from sboard.models import BaseNode
from sboard.models import NodeForeignKey
from sboard.models import NodeProperty
from sboard.models import couch

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
    user = models.OneToOneField(settings.AUTH_USER_MODEL, verbose_name=_('User'))
    karma = models.IntegerField(_('Karma'), default=0, choices=KARMA_CHOICES)
    name = models.CharField(_('Name'), max_length=255)
    node = NodeForeignKey()

    objects = ProfileManager()

    class Meta:
        verbose_name = _('Profile')
        verbose_name_plural = _('Profiles')

    def __unicode__(self):
        return self.name

    # XXX: deprecated, use self.node.ref instead.
    def get_node(self):
        return self.node.ref


def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # Create profile node instance
        node = ProfileNode()
        node._id = node.get_new_id()
        node.uid = instance.pk
        node.save()

        # Create profile model instance
        Profile.objects.create(user=instance, node=node._id)

post_save.connect(create_user_profile, sender=settings.AUTH_USER_MODEL)


class ProfileNode(BaseNode):
    implements(IProfile)

    # Reference to Django user model.
    uid = schema.IntegerProperty()

    first_name = schema.StringProperty()
    last_name = schema.StringProperty()

    dob = schema.StringProperty()
    home_page = schema.StringProperty()

    def age(self):
        if not self.dob:
            return None
        # source: http://stackoverflow.com/questions/2217488/age-from-birthdate-in-python
        today = datetime.date.today()
        born = datetime.datetime.strptime(self.dob, '%Y-%m-%d').date()
        try: # raised when birth date is February 29 and the current year is
             # not a leap year
            birthday = born.replace(year=today.year)
        except ValueError:
            birthday = born.replace(year=today.year, day=born.day-1)
        if birthday > today:
            return today.year - born.year - 1
        else:
            return today.year - born.year

    def private(self):
        return Profile.objects.get(user=self.uid)

    def user(self):
        return get_user_model().objects.get(pk=self.uid)

    def image_url(self, size=40):
        url = super(ProfileNode, self).image_url(size=size)
        if url:
            return url
        elif self.user().email:
            email = self.user().email.lower()
            key = hashlib.md5(email).hexdigest()
            return 'http://www.gravatar.com/avatar/%s?s=%s' % (key, size)
        else:
            key = '0' * 32
            return 'http://www.gravatar.com/avatar/%s?s=%s' % (key, size)

provideNode(ProfileNode, "profile")


class GroupNode(BaseNode):
    implements(IGroup)

provideNode(GroupNode, "group")


class MembershipNode(BaseNode):
    implements(IMembership)

    # Reference to profile node.
    profile = NodeProperty()

    # Reference to group node.
    group = NodeProperty()

    term_from = schema.DateProperty()
    term_to = schema.DateProperty()

    position = schema.StringProperty()

    _default_importance = 0

    def is_current(self):
        today = datetime.date.today()
        return \
            (not self.term_from or self.term_from <= today) and \
            (not self.term_to or self.term_to >= today)

provideNode(MembershipNode, "membership")


def query_group_membership(group_id):
    kwargs = dict(
        startkey=[group_id],
        endkey=[group_id, u'\ufff0']
    )
    query = couch.view('profiles/group_members', **kwargs).iterator()
    for node in query:
        profile = next(query)
        node.profile = profile
        yield node


def query_profile_membership(profile_id):
    kwargs = dict(
        startkey=[profile_id],
        endkey=[profile_id, u'\ufff0']
    )
    query = couch.view('profiles/profile_groups', **kwargs).iterator()
    for node in query:
        group = next(query)
        node.group = group
        yield node


def query_profiles(profile_keys):
    return couch.view('_all_docs', keys=profile_keys)
