# coding: utf-8

from anytorst.bbcode import BBCodeParser

import hashlib
import htmlentitydefs
import os
import re
import urllib
import uuid

import unidecode
from docutils import nodes
from docutils.core import publish_parts

from django.template.defaultfilters import slugify
from django.utils.html import strip_tags

from couchdbkit.exceptions import ResourceNotFound

from sqlalchemy import (Table, Column, Integer, text, Unicode, UnicodeText)

from sboard.importers.base import MigrationBase, metadata
from sboard.models import Node, Comment, Media

# Database schema generated using http://pypi.python.org/pypi/sqlautocode

Topic =  Table('phpbb_topics', metadata,
    Column(u'topic_id', Integer(), primary_key=True, nullable=False),
    Column(u'forum_id', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'icon_id', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'topic_attachment', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'topic_approved', Integer(), primary_key=False, nullable=False, default=text(u"'1'")),
    Column(u'topic_reported', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'topic_title', Unicode(255), primary_key=False, nullable=False, default=text(u"''")),
    Column(u'topic_poster', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'topic_time', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'topic_time_limit', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'topic_views', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'topic_replies', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'topic_replies_real', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'topic_status', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'topic_type', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'topic_first_post_id', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'topic_first_poster_name', Unicode(255), primary_key=False, nullable=False, default=text(u"''")),
    Column(u'topic_first_poster_colour', Unicode(6), primary_key=False, nullable=False, default=text(u"''")),
    Column(u'topic_last_post_id', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'topic_last_poster_id', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'topic_last_poster_name', Unicode(255), primary_key=False, nullable=False, default=text(u"''")),
    Column(u'topic_last_poster_colour', Unicode(6), primary_key=False, nullable=False, default=text(u"''")),
    Column(u'topic_last_post_subject', Unicode(255), primary_key=False, nullable=False, default=text(u"''")),
    Column(u'topic_last_post_time', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'topic_last_view_time', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'topic_moved_id', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'topic_bumped', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'topic_bumper', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'poll_title', Unicode(255), primary_key=False, nullable=False, default=text(u"''")),
    Column(u'poll_start', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'poll_length', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'poll_max_options', Integer(), primary_key=False, nullable=False, default=text(u"'1'")),
    Column(u'poll_last_vote', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'poll_vote_change', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
)


Post =  Table('phpbb_posts', metadata,
    Column(u'post_id', Integer(), primary_key=True, nullable=False),
    Column(u'topic_id', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'forum_id', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'poster_id', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'icon_id', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'poster_ip', Unicode(40), primary_key=False, nullable=False, default=text(u"''")),
    Column(u'post_time', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'post_approved', Integer(), primary_key=False, nullable=False, default=text(u"'1'")),
    Column(u'post_reported', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'enable_bbcode', Integer(), primary_key=False, nullable=False, default=text(u"'1'")),
    Column(u'enable_smilies', Integer(), primary_key=False, nullable=False, default=text(u"'1'")),
    Column(u'enable_magic_url', Integer(), primary_key=False, nullable=False, default=text(u"'1'")),
    Column(u'enable_sig', Integer(), primary_key=False, nullable=False, default=text(u"'1'")),
    Column(u'post_username', Unicode(255), primary_key=False, nullable=False, default=text(u"''")),
    Column(u'post_subject', Unicode(255), primary_key=False, nullable=False, default=text(u"''")),
    Column(u'post_text', UnicodeText(), primary_key=False, nullable=False),
    Column(u'post_checksum', Unicode(32), primary_key=False, nullable=False, default=text(u"''")),
    Column(u'post_attachment', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'bbcode_bitfield', Unicode(255), primary_key=False, nullable=False, default=text(u"''")),
    Column(u'bbcode_uid', Unicode(8), primary_key=False, nullable=False, default=text(u"''")),
    Column(u'post_postcount', Integer(), primary_key=False, nullable=False, default=text(u"'1'")),
    Column(u'post_edit_time', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'post_edit_reason', Unicode(255), primary_key=False, nullable=False, default=text(u"''")),
    Column(u'post_edit_user', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'post_edit_count', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'post_edit_locked', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
)


Attachment =  Table('phpbb_attachments', metadata,
    Column(u'attach_id', Integer(), primary_key=True, nullable=False),
    Column(u'post_msg_id', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'topic_id', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'in_message', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'poster_id', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'is_orphan', Integer(), primary_key=False, nullable=False, default=text(u"'1'")),
    Column(u'physical_filename', Unicode(255), primary_key=False, nullable=False, default=text(u"''")),
    Column(u'real_filename', Unicode(255), primary_key=False, nullable=False, default=text(u"''")),
    Column(u'download_count', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'attach_comment', UnicodeText(), primary_key=False, nullable=False),
    Column(u'extension', Unicode(100), primary_key=False, nullable=False, default=text(u"''")),
    Column(u'mimetype', Unicode(100), primary_key=False, nullable=False, default=text(u"''")),
    Column(u'filesize', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'filetime', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
    Column(u'thumbnail', Integer(), primary_key=False, nullable=False, default=text(u"'0'")),
)


def get_object_id(name):
    name = name.replace('_', '-')
    return slugify(unidecode.unidecode(name))


def get_object(model, object_id):
    try:
        obj = model.get(object_id)
    except ResourceNotFound:
        obj = model()
        obj._id = object_id

    return obj


def get_md5_sum(f, size=128):
    md5 = hashlib.md5()
    while True:
        data = f.read(size)
        if not data:
            break
        md5.update(data)
    return md5.hexdigest()


##
# Removes HTML or XML character references and entities from a text string.
#
# @param text The HTML (or XML) source text.
# @return The plain text, as a Unicode string, if necessary.
# @see http://effbot.org/zone/re-sub.htm#unescape-html
def unescape(text):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)


class PhpbbParser(BBCodeParser):
    SMILIES = {
        ':)': u'☺',
        ':(': u'☹',
        ':D': u'☻',
        ';)': u'ツ',
        ':*': u'⍣',
        ':o': u'⍤',
        ':|': u'⍨',
    }
    RE_SMILIES = re.compile(r'<!-- s([^ ]+) -->'
                            r'<img src="{SMILIES_PATH}/[^"]+" '
                            r'alt="[^"]+" title="[^"]+" />'
                            r'<!-- s\1 -->')

    RE_POSTLINK = re.compile(r'<!-- m -->'
                             r'<a class="postlink" href="([^"]+)">[^<]+</a>'
                             r'<!-- m -->')

    def __init__(self, session, obj):
        super(PhpbbParser, self).__init__()
        self.session = session
        self.obj = obj

    def download_attachment(self, uri, filename=None):
        filepath, hdr = urllib.urlretrieve(uri)
        if filename is None:
            slug, ext = os.path.splitext(uri)
            f = open(filepath)
            slug = get_md5_sum(f)
            f.close()
        else:
            slug, ext = os.path.splitext(filename)
        ext = ext.lower()
        slug = get_object_id(slug)
        media = get_object(Media, slug)
        media.ext = ext.lstrip('.')
        media.save()
        f = open(filepath)
        media.put_attachment(f, 'orig' + ext)
        f.close()
        return slug

    def check_image_hosting_services(self, uri):
        if 'ikelk.lt' in uri:
            return uri.replace('thumb_img', 'original_img')
        else:
            return uri

    def handle_img(self):
        if self.is_close_tag():
            uri = self.node_astext(self.node).strip()
            uri = self.check_image_hosting_services(uri)
            slug = self.download_attachment(uri)
            self.node['uri'] = slug
            self.node.clear()
            self.close_element()
        else:
            attrs = self.parse_attrs()
            self.open_element(nodes.image(**attrs))



    def handle_attachment(self):
        if self.is_close_tag():
            filename = strip_tags(self.node_astext(self.node)).strip()
            attachment = (self.session.query(Attachment).
                          filter(Attachment.columns.post_msg_id == self.obj.post_id).
                          filter(Attachment.columns.real_filename == filename).
                          one())
            uri = ('http://www.ubuntu.lt/forum/download/'
                   'file.php?id=%d') % attachment.attach_id
            slug = self.download_attachment(uri, filename)
            self.node['uri'] = slug
            self.node.clear()
            self.close_element()
        else:
            self.open_element(nodes.image())

    def replace_smilies(self, m):
        smile = m.group(1)
        if smile in self.SMILIES:
            return self.SMILIES[smile]
        else:
            return self.SMILIES[':)']

    def replace_postlink(self, m):
        link = m.group(1)
        return link

    def _handle_text(self, text):
        text = self.RE_SMILIES.sub(self.replace_smilies, text)
        text = self.RE_POSTLINK.sub(self.replace_postlink, text)
        return super(PhpbbParser, self)._handle_text(text)


class PhpbbMigration(MigrationBase):
    def migrate_posts(self, topic, node):
        for obj in (self.session.query(Post).
                    filter(Post.columns.post_id != topic.topic_first_post_id).
                    #filter(Post.columns.post_id == 7579).
                    order_by(Post.columns.post_time.desc())):
            slug = str(uuid.uuid4())
            comment = get_object(Comment, slug)
            print('  %s' % comment._id)

            post_text = unescape(obj.post_text)

            parser = PhpbbParser(self.session, obj)
            try:
                parser.parse(post_text)
            except Exception as e:
                print(e)
                print('----------------------')
                print(post_text)
                print('----------------------')
                raise e
            body = parser.get_rst()

            try:
                publish_parts(source=body, writer_name='html4css1',
                              settings_overrides={'halt_level': 2})
            except Exception as e:
                print(obj.post_text)
                print('----------------------')
                print(e)
                print('----------------------')
                print(body)
                print('----------------------')
                raise e

            comment.body = body
            comment.parents = [node._id]
            comment.migrate = {
                'type': 'phpbb',
                'post_id': obj.post_id,
                'topic_id': obj.topic_id,
                'forum_id': obj.forum_id,
              }
            comment.save()



    def migrate(self):
        for obj in (self.session.query(Topic, Post).
                    join(Post, Topic.columns.topic_first_post_id == Post.columns.post_id).
                    #filter(Topic.columns.topic_id == 7579).
                    order_by(Topic.columns.topic_time.desc()))[:3]:
            slug = get_object_id(obj.topic_title)
            node = get_object(Node, slug)
            node.title = obj.topic_title
            print(node._id)

            post_text = unescape(obj.post_text)

            parser = PhpbbParser(self.session, obj)
            try:
                parser.parse(post_text)
            except Exception as e:
                print(e)
                print('----------------------')
                print(post_text)
                print('----------------------')
                raise e
            body = parser.get_rst()

            try:
                publish_parts(source=body, writer_name='html4css1',
                              settings_overrides={'halt_level': 2})
            except Exception as e:
                print(e)
                print('--')
                print(body)
                print('--')
                raise e

            node.body = body

            node.migrate = {
                'type': 'phpbb',
                'post_id': obj.post_id,
                'topic_id': obj.topic_id,
                'forum_id': obj.forum_id,
              }
            node.save()

            self.migrate_posts(obj, node)
