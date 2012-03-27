import os

from optparse import make_option

from django.core.management.base import BaseCommand

from sboard.esmanagement import ESManagement


class Command(BaseCommand):
    help = "ElasticSearch management tool."

    option_list = BaseCommand.option_list + (
        make_option('--path', action='store', dest='path',
                    help='ElasticSearch root directory.'),
        make_option('--wait', type=int, dest='wait', default=30,
                    help='Seconds to wait for ElasticSearch to start.'),
    )

    def handle(self, *args, **options):
        path = options['path'] or os.getcwd()
        if args:
            action = args[0]
        else:
            action = 'start'

        esm = ESManagement(path)

        if action == 'install':
            print("Installing CouchDB river index...")
            esm.start()
            if esm.wait(options['wait']):
                if esm.is_installed():
                    print(" ... already installed.")
                else:
                    esm.install()
                    print(" ... done.")
            else:
                print(" ... failed. Can't start ElasticSearch server, timeout "
                      "is reached.")

        elif action == 'stop':
            print("Stopping ElasticSearch...")
            esm.stop()
            print(" ... done.")

        elif action == 'start':
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

        else:
            print("Unknown command.")
