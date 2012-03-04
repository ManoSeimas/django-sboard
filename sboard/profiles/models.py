from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _

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
