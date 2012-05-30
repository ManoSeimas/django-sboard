import datetime
import hashlib

from zope.interface import implements

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _

from couchdbkit.ext.django import schema

from sorl.thumbnail import get_thumbnail

from sboard.factory import provideNode
from sboard.models import BaseNode
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
    user = models.OneToOneField(User, verbose_name=_('User'))
    karma = models.IntegerField(_('Karma'), default=0, choices=KARMA_CHOICES)
    name = models.CharField(_('Name'), max_length=255)
    node = models.CharField(_('Profile node ID'), max_length=20)

    objects = ProfileManager()

    class Meta:
        verbose_name = _('Profile')
        verbose_name_plural = _('Profiles')

    def __unicode__(self):
        return self.name

    def get_node(self):
        return couch.get(self.node)


def create_user_profile(sender, instance, created, **kwargs):
    if created:
        node = ProfileNode()
        node._id = node.get_new_id()
        profile = Profile.objects.create(user=instance, node=node._id)
        node.uid = profile.pk
        node.save()

post_save.connect(create_user_profile, sender=User)


class ProfileNode(BaseNode):
    implements(IProfile)

    # Reference to Django user model.
    uid = schema.IntegerProperty()

    first_name = schema.StringProperty()
    last_name = schema.StringProperty()

    dob = schema.StringProperty()
    home_page = schema.StringProperty()

    # Profile photo node ID
    photo = NodeProperty(required=False)

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
        return User.objects.get(pk=self.uid)

    def avatar_url(self, size=40):
        if self.photo:
            path = self.photo.ref.path()
            geom = '%d' % size
            im = get_thumbnail(path, geom, upscale=False)
            url = im.url
        elif self.user().email:
            email = self.user().email.lower()
            key = hashlib.md5(email).hexdigest()
            url = 'http://www.gravatar.com/avatar/%s?s=%s' % (key, size)
        else:
            key = '0' * 32
            url = 'http://www.gravatar.com/avatar/%s?s=%s' % (key, size)
        return url

    def avatar_url_big(self):
        return self.avatar_url(135)

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
