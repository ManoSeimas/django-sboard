from unittest import TestCase
from sboard.models import Node, couch, Comment


class SimpleTest(TestCase):
    def setUp(self):
        text = 'simple-test-case-1'
        t1 = Node(title=text)
        t1.save()
        t1.set_body(text)

        t2 = Comment(parents=[t1._id])
        t2.save()
        t2.set_body(text + '-comment-1')

        t3 = Comment(parents=[t1._id])
        t3.save()
        t3.set_bodytext + '-comment-2'()

        t4 = Node(parents=[t1._id])
        t4.save()
        t4.set_body(text + '-comment-2')

        self.comments = [t2._id, t3._id]
        self.nodes = [t1._id, t4._id]
        self.parent_id = t1._id

    def testChildrenCount(self):
        topic = couch.topics(key=self.parent_id, include_docs=True).all()[0]
        self.assertEqual(topic.get_children_count(), 3)

    def testPolymorphism(self):
        parent = couch.topics(key=self.parent_id, include_docs=True).all()[0]
        self.assertEqual(parent.__class__, Node)
        for child in parent.get_children():
            if child._id in self.comments:
                self.assertEqual(child.__class__, Comment)
            elif child._id in self.nodes:
                self.assertEqual(child.__class__, Node)
            else:
                assert False, "Unknown item: %s" % child._id

    def tearDown(self):
        parent = couch.topics(key=self.parent_id, include_docs=True).all()[0]
        for child in parent.get_children():
            child.delete()
        parent.delete()
