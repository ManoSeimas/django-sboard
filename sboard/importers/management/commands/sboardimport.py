from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.importlib import import_module

#from sboard.utils import get_class


def get_class(path):
    module_name, class_name = path.rsplit('.', 1)
    module = import_module(module_name)
    return getattr(module, class_name)


class Command(BaseCommand):
    help = "import all content from database and convert from phpBB."

    def handle(self, *args, **options):
        if len(args) > 0:
            handlers = [args.pop()]
        else:
            handlers = settings.SBOARD_MIGRATION_SCRIPTS.keys()

        for name in handlers:
            params = settings.SBOARD_MIGRATION_SCRIPTS[name]
            handler_class = get_class(params.pop('handler'))
            dbi = params.pop('dbi')
            handler = handler_class(dbi, params)
            handler.migrate()
