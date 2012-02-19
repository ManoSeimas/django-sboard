import urlparse

from django.core.management.base import BaseCommand

from pyes.rivers import CouchDBRiver

from sboard import es
from sboard.models import Node


class Command(BaseCommand):
    help = "Sync ElasticSearch indexes and settings."

    def handle(self, *args, **options):
        uri = Node.get_db().uri
        uri = urlparse.urlparse(uri)
        params = {
            'index_name': 'sboard',
            'index_type': 'allnodes',
            'host': uri.hostname,
            'port': uri.port,
            'db': uri.path.split('/')[1],
        }

        if uri.username:
            params['user'] = uri.username
        if uri.password:
            params['password'] = uri.password

        river = CouchDBRiver(**params)
        es.conn.create_river(river, river_name='sboard')
