import unidecode
import uuid

from django.template.defaultfilters import slugify


def get_node_id(title=None, allow_uuid=True):
    if title and len(title) <= 72:
        return slugify(unidecode.unidecode(title))
    elif allow_uuid:
        return str(uuid.uuid4())
    else:
        return None
