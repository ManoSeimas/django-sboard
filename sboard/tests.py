from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db.models import get_apps
from django.test import TestCase

from couchdbkit.exceptions import ResourceNotFound
from couchdbkit.ext.django import loading

from .models import couch, Node


class NodesTestsMixin(object):
    """Some handy utils for nodes testing.

    This test case creates new test database in CouchDB, and prepared all
    models to use that database. Also prepares some settings, like
    authetication, to not use socialauth.

    """

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
                if issubclass(cls, Node):
                    cls.set_db(cls.get_db())
                else:
                    cls.set_db(loading.get_db(app))

        for app in get_apps():
            loading.couchdbkit_handler.sync(app, verbosity=2)

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
        self.client.login(username='superuser', password='supersecret')

    def _login_user(self):
        self.client.logout()
        self.client.login(username='simpleuser', password='secret')

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

        # Create user.
        User.objects.create_user('simpleuser', 'simpleuser@example.com',
                                 'secret')


class NodesTests(NodesTestsMixin, TestCase):
    """Big and fat functional test for nodes."""

    def testNodes(self):
        self._login_superuser()

        # Create root node
        create_category_url = reverse('node_create', args=['category'])
        response = self.client.post(create_category_url, {
                'title': 'Main test category',
                'parent': '',
                'body': '',
            })
        main_url = reverse('node_details', args=['main-test-category'])
        self.assertRedirects(response, main_url)

        self._login_user()

        # Create child node
        create_comment_url = reverse('node_create_child',
                args=['main-test-category', 'comment'])
        response = self.client.post(create_comment_url, {
                'body': 'comment body',
            })
        self.assertEqual(response.status_code, 403)

        # Set permissions to allow create comments
        node = couch.get('main-test-category')
        node.permissions = [
           ['create', 'all', None, 'comment', 0],
        ]
        node.save()

        # Try create child node again
        response = self.client.post(create_comment_url, {
                'body': 'comment body',
            })
        self.assertRedirects(response, main_url)
