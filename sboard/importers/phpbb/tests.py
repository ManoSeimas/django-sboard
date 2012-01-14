# coding: utf-8

import unittest

from .importers import PhpbbParser


class ParserTests(unittest.TestCase):
    def test_smilies(self):
        parser = PhpbbParser(None, None)
        parser.parse(u'<!-- s:) -->'
                     u'<img src="{SMILIES_PATH}/icon_e_smile.gif" '
                     u'alt=":)" title="Išsišiepęs" />'
                     u'<!-- s:) -->')
        self.assertEqual(parser.get_rst(), u'☺')

    def test_links(self):
        # TODO: fix this test
        # this test should recongnize local links and replace url to correct
        # local url...
        parser = PhpbbParser(None, None)
        parser.parse(u'<!-- l -->'
                     u'<a class="postlink-local" '
                     u'href="http://www.ubuntu.lt/forum/viewtopic.php?f=3&amp;t=1710&amp;start=110">'
                     u'viewtopic.php?f=3&amp;t=1710&amp;start=110'
                     u'</a>'
                     u'<!-- l -->')
        self.assertEqual(parser.get_rst(), u'some-slug_')
