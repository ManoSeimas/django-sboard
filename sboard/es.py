from django.conf import settings

import pyes

conn = pyes.ES(list(settings.ELASTICSEARCH_SERVERS))
