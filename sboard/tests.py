from unittest import TestCase
from sboard.models import Node, couch, Comment


class SimpleTest(TestCase):
    def setUp(self):
        text = 'simple-test-case-1'
        t1 = Node(title=text, body=text)
        t1.save()
        t2 = Comment(body=text + '-comment-1', parents=[t1._id])
        t2.save()
        t3 = Comment(body=text + '-comment-2', parents=[t1._id])
        t3.save()
        t4 = Node(body=text + '-comment-2', parents=[t1._id])
        t4.save()
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
