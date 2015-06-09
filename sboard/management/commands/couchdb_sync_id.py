from django.db import connection
from django.core.management.base import BaseCommand

from sboard.models import couch, UniqueKey


class Command(BaseCommand):
    help = "import all content from database and convert from phpBB."

    def get_last_id(self):
        last_id_node = couch.view('sboard/max_id', reduce=True, group=False,
                                  include_docs=False,
                                  startkey='000000', endkey='ffffff').one()
        if last_id_node:
            return int(last_id_node['value'], 36)

    def reset_autoincrement(self, table, value):
        with connection.cursor() as cursor:
            cursor.execute('ALTER TABLE {} AUTO_INCREMENT = %s'.format(table),
                           [value])

    def handle(self, *args, **options):
        last_id = self.get_last_id()
        if last_id:
            next_id = last_id + 1
            table_name = UniqueKey._meta.db_table
            self.reset_autoincrement(table_name, next_id)
            print('Synced table "{}" auto_increment id to {}'.format(
                table_name, next_id))
