import StringIO
import os.path
import shutil
import unittest

from mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db.models import get_app
from django.test import TestCase

from couchdbkit.exceptions import ResourceNotFound
from couchdbkit.ext.django import loading

from .factory import provideNode
from .models import BaseNode
from .models import FileNode
from .models import Node
from .models import NodeProperty
from .models import UniqueKey
from .models import couch
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
        # XXX: should be better way to do this...

        loading.couchdbkit_handler
        couchdbkit_handler = loading.CouchdbkitHandler(settings.COUCHDB_DATABASES)
        loading.couchdbkit_handler = couchdbkit_handler
        loading.register_schema = couchdbkit_handler.register_schema
        loading.get_schema = couchdbkit_handler.get_schema
        loading.get_db = couchdbkit_handler.get_db

        created_databases = []
        for app, url in getattr(settings, "COUCHDB_DATABASES", []):
            app_label = app.split('.')[-1]
            db = loading.get_db(app_label)
            if db.dbname in created_databases:
                continue
            app = get_app(app_label)
            loading.couchdbkit_handler.sync(app, verbosity=0)
            created_databases.append(db.dbname)

    def _teardown_couchdb(self):
        deleted_databases = []
        for app, url in getattr(settings, "COUCHDB_DATABASES", []):
            app_label = app.split('.')[-1]
            db = loading.get_db(app_label)
            if db.dbname in deleted_databases:
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


class TestFilePath(unittest.TestCase):
    def setUp(self):
        self.old_media_root = settings.MEDIA_ROOT
        settings.MEDIA_ROOT = os.path.join(
                settings.BUILDOUT_DIR, 'var', 'test-media')

    def tearDown(self):
        if os.path.exists(settings.MEDIA_ROOT):
            shutil.rmtree(settings.MEDIA_ROOT)
        settings.MEDIA_ROOT = self.old_media_root

    @patch.object(FileNode, 'fetch_attachment')
    def test_file_path(self, fetch_attachment):
        fetch_attachment.return_value = StringIO.StringIO('content')

        node = FileNode()
        node._id = '000123'
        node.ext = 'txt'
        path = node.path()

        expected_path = os.path.join(
                settings.MEDIA_ROOT, 'node', '23', '0001.txt')
        self.assertEqual(path, expected_path)
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            self.assertEqual(f.read(), 'content')


class FakeNodeWithRef(BaseNode):
    photo = NodeProperty()

provideNode(FakeNodeWithRef, "fake-node-with-ref")


class TestNodeRef(unittest.TestCase):
    @patch('sboard.models.couch')
    def test_ref(self, couch_mock):
        ref = Node()
        ref._id = 'photo'
        ref.title = 'ref title'
        couch_mock.get.return_value = ref

        # Create node with photo reference attribute
        node = couch.wrap({
            '_id': 'fake',
            'doc_type': 'FakeNodeWithRef',
            'photo': 'photo',
        })

        self.assertEqual(node._id, 'fake')
        self.assertEqual(node.photo._id, 'photo')
        self.assertEqual(couch_mock.get.call_count, 0)

        self.assertEqual(node.photo.ref.title, 'ref title')
        self.assertEqual(couch_mock.get.call_count, 1)

        # Assign other reference to photo attribute.
        newref = Node()
        newref._id = 'new'
        newref.title = 'new ref'
        node.photo = newref

        self.assertEqual(node.photo._id, 'new')
        self.assertEqual(node.photo.ref.title, 'new ref')
        self.assertEqual(couch_mock.get.call_count, 1)

        # Check how comparison works.
        self.assertTrue(node.photo)
        node.photo = None
        self.assertFalse(node.photo)


class TestNodeForeignKey(unittest.TestCase):
    @patch('sboard.models.couch')
    def test_field(self, couch_mock):
        ref = Node()
        ref._id = '000123'
        ref.title = 'ref title'
        couch_mock.get.return_value = ref

        model = UniqueKey()
        model.key = ref
        model.save()

        model = UniqueKey.objects.get(key='000123')
        self.assertEqual(model.key._id, '000123')
        self.assertEqual(model.key.ref.title, 'ref title')
