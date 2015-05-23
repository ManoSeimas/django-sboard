from django.conf import settings
from django.utils.encoding import smart_str, force_unicode
from django.utils.safestring import mark_safe


def restructuredtext(value):
    docutils_settings = getattr(settings, "RESTRUCTUREDTEXT_FILTER_SETTINGS", {})
    parts = publish_parts(source=smart_str(value), writer_name="html4css1", settings_overrides=docutils_settings)
    return mark_safe(force_unicode(parts["fragment"]))
