# -*- coding: utf-8 -*-
# Copyright (c) 2012  Infrae. All rights reserved.
# See also LICENSE.txt


import unittest

from Acquisition import aq_base

from ..interfaces import ISubscriptionManager
from ..testing import FunctionalLayer
from ..upgrader.upgrade_300 import subscription_upgrader


class UpgraderTestCase(unittest.TestCase):
    layer = FunctionalLayer

    def setUp(self):
        self.root = self.layer.get_application()
        self.layer.login('editor')

    def test_upgrade_content(self):
        """Test upgrade on a document.
        """
        content = self.root.item
        content.__subscribability__ = 1
        content.__subscriptions__ = {'wim@example.com': 'wim@example.com'}
        self.assertEqual(
            ISubscriptionManager(content).is_subscribable(),
            False)
        self.assertEqual(
            ISubscriptionManager(content).is_subscribed('wim@example.com'),
            False)
        self.assertEqual(
            subscription_upgrader.validate(content),
            True)
        self.assertEqual(
            subscription_upgrader.upgrade(content),
            content)
        self.assertEqual(
            ISubscriptionManager(content).is_subscribable(),
            True)
        self.assertEqual(
            ISubscriptionManager(content).is_subscribed('wim@example.com'),
            True)
        self.assertEqual(
            subscription_upgrader.validate(content),
            False)
        self.assertFalse(hasattr(aq_base(content), '__subscribability__'))
        self.assertFalse(hasattr(aq_base(content), '__subscriptions__'))


class DocumentUpgraderTestCase(UpgraderTestCase):

    def setUp(self):
        super(DocumentUpgraderTestCase, self).setUp()
        factory = self.root.manage_addProduct['Silva']
        factory.manage_addMockupVersionedContent('item', 'Document')


class ContainerUpgraderTestCase(UpgraderTestCase):

    def setUp(self):
        super(ContainerUpgraderTestCase, self).setUp()
        factory = self.root.manage_addProduct['Silva']
        factory.manage_addFolder('item', 'Folder')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(DocumentUpgraderTestCase))
    suite.addTest(unittest.makeSuite(ContainerUpgraderTestCase))
    return suite
