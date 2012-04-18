# coding: utf-8

import string
import unidecode

from django.core.urlresolvers import reverse
from django.template.defaultfilters import slugify as django_slugify
from django.utils.functional import lazy

alphabet = string.digits + string.lowercase

reverse_lazy = lazy(reverse, str)


def slugify(title=None, length=60):
    u"""Smart slugify.

        >>> slugify(u'KOMITETO IŠVADA Įstatymo dėl Belgijos Karalystės, '
        ...         u'Bulgarijos Respublikos, Čekijos Respublikos, Danijos '
        ...         u'Karalystės, Vokietijos Federacinės Respublikos, Estijos '
        ...         u'Respublikos, Airijos, Graikijos Respublikos, Ispanijos '
        ...         u'Karalystės, Prancūzijos Respublikos, Italijos '
        ...         u'Respublikos, Kipro Respublikos, Latvijos Respublikos, '
        ...         u'Lietuvos Respublikos, Liuksemburgo Didžiosios'
        ...         u'Hercogystės, Vengrijos Respublikos, Maltos Respublikos, '
        ...         u'Nyderlandų Karalystės, Austrijos Respublikos, Lenkijos '
        ...         u'Respublikos, Portugalijos Respublikos, Rumunijos, '
        ...         u'Slovėnijos Respublikos, Slovakijos Respublikos, '
        ...         u'Suomijos Respublikos, Švedijos Karalystės, Jungtinės'
        ...         u'Didžiosios Britanijos ir Šiaurės Airijos Karalystės '
        ...         u'(Europos Sąjungos valstybių narių) ir Kroatijos '
        ...         u'Respublikos sutarties dėl Kroatijos Respublikos stojimo '
        ...         u'į Europos Sąjungą ratifikavimo projektui')
        u'komiteto-isvada-istatymo-del-belgijos---ratifikavimo-projektui'

        >>> slugify(u'KOMITETO IŠVADA Įstatymo dėl Belgijos Karalystės')
        u'komiteto-isvada-istatymo-del-belgijos-karalystes'

        >>> slugify(u'IŠVADA')
        u'isvada'

    """
    if not title:
        return ''

    begining_chars = length / 5
    slug = django_slugify(unidecode.unidecode(title))
    if len(slug) > length:
        words = slug.split('-')
        a, b = [], []
        while words and len('-'.join(a + b)) < length:
            if len('-'.join(a)) <= (len('-'.join(b)) + begining_chars):
                a.append(words.pop(0))
            else:
                b.insert(0, words.pop())
        if b:
            slug = '-'.join(a) + '---' + '-'.join(b)
        else:
            slug = '-'.join(a)
    return slug[:length + begining_chars]


def base36(number):
    """
        >>> base36(0)
        '0'
        >>> base36(10)
        'a'
        >>> base36(1000)
        'rs'
        >>> int('rs', 36)
        1000
        >>> base36(1000000)
        'lfls'
        >>> int('zzzzzz', 36)
        2176782335
        >>> base36(2176782335)
        'zzzzzz'
        >>> base36(1000000000)
        'gjdgxs'
        >>> base36(-42)
        '-16'

    """
    global alphabet

    if number == 0:
        return alphabet[0]

    base36 = ''
    sign = ''
    if number < 0:
        sign = '-'
        number = - number

    while number != 0:
        number, i = divmod(number, len(alphabet))
        base36 = alphabet[i] + base36

    return sign + base36
