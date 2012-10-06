from django_nose import NoseTestSuiteRunner

from django.conf import settings


class SboardTestSuiteRunner(NoseTestSuiteRunner):
    def setup_databases(self):
        self._setup_couchdb()
        return super(SboardTestSuiteRunner, self).setup_databases()

    # def teardown_databases(self, *args, **kwargs):
    #     self._teardown_couchdb()
    #     return super(SboardTestSuiteRunner, self).teardown_databases(
    #             *args, **kwargs)

    def _setup_couchdb(self):
        databases = []
        for app, url in getattr(settings, "COUCHDB_DATABASES", []):
            databases.append((app, url + '_unittestdb'))
        settings.COUCHDB_DATABASES = databases
