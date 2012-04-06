import os

from optparse import make_option

from django.core.management.base import BaseCommand

from sboard import es
from sboard.esmanagement import ESManagement


class Command(BaseCommand):
    help = "ElasticSearch management tool."

    option_list = BaseCommand.option_list + (
        make_option('--path', action='store', dest='path',
                    default='parts/elasticsearch',
                    help='ElasticSearch root directory.'),
        make_option('--wait', type=int, dest='wait', default=30,
                    help='Seconds to wait for ElasticSearch to start.'),
    )

    def start(self, esm, options):
        if esm.check() or esm.is_just_started():
            print("ElasticSearch is already started.")
        else:
            print("Starting ElasticSearch...")
            esm.stop()
            esm.start()
            print(" ... waiting while server starts...")
            if esm.wait(options['wait']):
                print(" ... done.")
            else:
                esm.stop()
                print(" ... failed. Timeout is reached.")

    def stop(self, esm, options):
        print("Stopping ElasticSearch...")
        esm.stop()
        print(" ... done.")

    def install(self, esm, options):
        print("Installing CouchDB river index...")
        esm.start()
        if esm.wait(options['wait']):
            esm.install()
            print(" ... done.")
        else:
            print(" ... failed. Can't start ElasticSearch server, timeout "
                  "is reached.")

    def uninstall(self, esm, options):
        print("Uninstalling CouchDB river index...")
        esm.start()
        if esm.wait(options['wait']):
            esm.uninstall()
            print(" ... done.")
        else:
            print(" ... failed. Can't start ElasticSearch server, timeout "
                  "is reached.")

    def indices(self, esm, options):
        for name, index in es.conn.get_indices().items():
            print('%s: %s' % (name, index['num_docs']))

    def handle(self, *args, **options):
        path = options['path'] or os.getcwd()
        if args:
            action = args[0]
        else:
            action = 'start'

        esm = ESManagement(path)

        if action == 'install':
            self.install(esm, options)

        elif action == 'uninstall':
            self.uninstall(esm, options)

        elif action == 'reinstall':
            self.uninstall(esm, options)
            self.install(esm, options)

        elif action == 'stop':
            self.stop(esm, options)

        elif action == 'start':
            self.start(esm, options)

        elif action == 'restart':
            self.stop(esm, options)
            self.start(esm, options)

        elif action == 'indices':
            self.indices(esm, options)

        else:
            print("Unknown command.")
