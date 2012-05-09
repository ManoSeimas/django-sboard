from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db.models import get_apps
from django.test import TestCase

from couchdbkit.exceptions import ResourceNotFound
from couchdbkit.ext.django import loading

from .models import couch, BaseNode
from .profiles.models import Profile


class NodesTestsMixin(object):
    """Some handy utils for nodes testing.

    This test case creates new test database in CouchDB, and prepared all
    models to use that database. Also prepares some settings, like
    authetication, to not use socialauth.

    """

    _f_title = 'Consectetuer adipiscing elit'

    _f_body = ('Lorem ipsum dolor sit amet, consectetuer adipiscing elit, '
               'sed diam nonummy nibh euismod tincidunt ut laoreet dolore '
               'magna aliquam erat volutpat.')

    def _set_setting(self, key, val):
        self._settings[key] = getattr(settings, key)
        setattr(settings, key, val)

    def _restore_set_settings(self):
        for key, val in self._settings.items():
            setattr(settings, key, val)

    def _setup_couchdb(self):
        self._couch_databases = []
        for app, url in getattr(settings, "COUCHDB_DATABASES", []):
            self._couch_databases.append((app, url + '_unittestdb'))

        self._set_setting('COUCHDB_DATABASES', self._couch_databases)

        old_handler = loading.couchdbkit_handler
        couchdbkit_handler = loading.CouchdbkitHandler(self._couch_databases)
        loading.couchdbkit_handler = couchdbkit_handler
        loading.register_schema = couchdbkit_handler.register_schema
        loading.get_schema = couchdbkit_handler.get_schema
        loading.get_db = couchdbkit_handler.get_db

        # register our dbs with the extension document classes
        for app, value in old_handler.app_schema.items():
            for name, cls in value.items():
                if issubclass(cls, BaseNode):
                    cls.set_db(cls.get_db())
                else:
                    cls.set_db(loading.get_db(app))

        for app in get_apps():
            loading.couchdbkit_handler.sync(app, verbosity=0)

    def _teardown_couchdb(self):
        deleted_databases = []
        skipcount = 0
        for app, item in self._couch_databases:
            app_label = app.split('.')[-1]
            db = loading.get_db(app_label)
            if db.dbname in deleted_databases: 
                skipcount += 1
                continue
            try:
                db.server.delete_db(db.dbname)
                deleted_databases.append(db.dbname)
            except ResourceNotFound:
                pass

    def _login_superuser(self):
        self.client.logout()
        assert self.client.login(username='superuser', password='supersecret')
        return User.objects.get(username='superuser')

    def _login_user1(self):
        self.client.logout()
        assert self.client.login(username='u1', password='secret')
        return User.objects.get(username='u1')

    def _login_user2(self):
        self.client.logout()
        assert self.client.login(username='u2', password='secret')
        return User.objects.get(username='u2')

    def _login_user3(self):
        self.client.logout()
        assert self.client.login(username='u3', password='secret')
        return User.objects.get(username='u3')

    def _logout(self):
        self.client.logout()

    def _create(self, node, **kwargs):
        fields = kwargs.pop('_f', ())
        for f in fields:
            kwargs[f] = getattr(self, '_f_%s' % f)

        parent = kwargs.get('parent', '~')
        url = reverse('node', args=[parent, 'create', node])

        return self.client.post(url, kwargs)

    def _set_perm(self, node, *permissions):
        """Set node permissions.

        Example::

            self._set_perm('c1',
                ('create', 'owner', None, 'comment', 0),
                ('create', 'all', 'authenticated', 'comment', 0),
            )

        """
        node = couch.by_slug(key=node).first()
        node.permissions = [list(p) for p in permissions]
        node.save()

    def _set_karma(self, user, karma):
        p = Profile.objects.get(user__username=user)
        p.karma = karma
        p.save()

    def setUp(self):
        self._settings = {}
        self.addCleanup(self._restore_set_settings)
        self.addCleanup(self._teardown_couchdb)

        self._set_setting('AUTHENTICATION_BACKENDS', (
            'django.contrib.auth.backends.ModelBackend',
        ))
        self._setup_couchdb()

        # Create superuser.
        User.objects.create_superuser('superuser', 'superuser@example.com',
                                      'supersecret')

        # Create users.
        User.objects.create_user('u1', 'u1@example.com', 'secret')
        User.objects.create_user('u2', 'u2@example.com', 'secret')
        User.objects.create_user('u3', 'u3@example.com', 'secret')


class NodesTests(NodesTestsMixin, TestCase):
    """Big and fat functional test for nodes."""

    def testNodes(self):
        # Anonymous user: create root category
        response = self._create('category', title='C1')
        self.assertEqual(response.status_code, 403)

        self._login_superuser()

        # Create root category with superuser rights
        response = self._create('category', title='C1')
        self.assertRedirects(response, reverse('node', args=['~']))

        self._login_user1()

        # Create child node
        response = self._create('comment', parent='c1', _f=('body',))
        self.assertEqual(response.status_code, 403)

        # Set permissions to allow create comments to all authenticated users
        self._set_perm('c1', ('create', 'all', 'authenticated', 'comment', 0))
        response = self._create('comment', parent='c1', _f=('body',))
        self.assertRedirects(response, reverse('node', args=['c1']))

        # Require higher karma to create comments
        self._set_perm('c1', ('create', 'all', 'authenticated', 'comment', 10))
        response = self._create('comment', parent='c1', _f=('body',))
        self.assertEqual(response.status_code, 403)

        # Give user needed karma to be able to create comment
        self._set_karma('u1', 10)
        response = self._create('comment', parent='c1', _f=('body',))
        self.assertRedirects(response, reverse('node', args=['c1']))

        self._logout()

        # Try to create child node with anonymous user
        response = self._create('comment', parent='c1', _f=('body',))
        self.assertEqual(response.status_code, 403)

        # Allow anonymous users to create comments
        self._set_perm('c1', ('create', 'all', None, 'comment', 0))
        response = self._create('comment', parent='c1', _f=('body',))
        self.assertRedirects(response, reverse('node', args=['c1']))


class TestNodeSlug(NodesTestsMixin, TestCase):
    def testNotExisting(self):
        url = reverse('node', args=['not-existing-node'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
