# -*- coding: utf-8 -*-
# Copyright (c) 2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

import unittest

from zope.interface.verify import verifyObject
from silva.app.subscriptions.interfaces import ISubscriptionManager
from silva.app.subscriptions.testing import FunctionalLayer
from silva.app.subscriptions.interfaces import (
    ACQUIRE_SUBSCRIBABILITY, NOT_SUBSCRIBABLE, SUBSCRIBABLE)


class SubscriptionManagerTestCase(unittest.TestCase):
    """Test the Subscription Manager adapter.
    """
    layer = FunctionalLayer

    def setUp(self):
        self.root = self.layer.get_application()
        self.layer.login('manager')
        factory = self.root.manage_addProduct['silva.app.subscriptions']
        factory.manage_addSubscriptionService()

        factory = self.root.manage_addProduct['SilvaDocument']
        factory.manage_addDocument('document', 'Document')
        factory = self.root.manage_addProduct['Silva']
        factory.manage_addFolder('folder', u'Test Folder')
        factory.manage_addFile('file', u'Downloable File')

    def test_manager(self):
        """Check that we can get the adapter.
        """
        manager = ISubscriptionManager(self.root.document, None)
        self.assertNotEqual(manager, None)
        self.assertTrue(verifyObject(ISubscriptionManager, manager),)

        manager = ISubscriptionManager(self.root, None)
        self.assertNotEqual(manager, None)
        self.assertTrue(verifyObject(ISubscriptionManager, manager),)

        # They are not available on asset
        manager = ISubscriptionManager(self.root.file, None)
        self.assertEqual(manager, None)

    def test_subscribability(self):
        """Test the subscribability setting.
        """
        manager = ISubscriptionManager(self.root.document, None)
        self.assertEqual(manager.is_subscribable(), False)
        self.assertEqual(manager.subscribability, ACQUIRE_SUBSCRIBABILITY)

        # You can enable or disable that setting
        manager.subscribability = SUBSCRIBABLE
        self.assertEqual(manager.is_subscribable(), True)
        self.assertEqual(manager.subscribability, SUBSCRIBABLE)

        manager.subscribability = NOT_SUBSCRIBABLE
        self.assertEqual(manager.is_subscribable(), False)
        self.assertEqual(manager.subscribability, NOT_SUBSCRIBABLE)

        # You can set the setting on the parent root
        manager_root = ISubscriptionManager(self.root, None)
        self.assertEqual(manager_root.is_subscribable(), False)
        self.assertEqual(manager_root.subscribability, NOT_SUBSCRIBABLE)

        # You can change the setting. Not to acquired.
        manager_root.subscribability = SUBSCRIBABLE
        self.assertEqual(manager_root.is_subscribable(), True)
        self.assertEqual(manager_root.subscribability, SUBSCRIBABLE)

        self.assertRaises(
            AssertionError,
            setattr, manager_root, 'subscribability', ACQUIRE_SUBSCRIBABILITY)
        self.assertEqual(manager_root.is_subscribable(), True)
        self.assertEqual(manager_root.subscribability, SUBSCRIBABLE)

        # The setting was disabled on the document, it is still is.
        # However if we set it to acquired it will be enabled (since root is)
        self.assertEqual(manager.is_subscribable(), False)
        self.assertEqual(manager.subscribability, NOT_SUBSCRIBABLE)

        manager.subscribability = ACQUIRE_SUBSCRIBABILITY
        self.assertEqual(manager.is_subscribable(), True)
        self.assertEqual(manager.subscribability, ACQUIRE_SUBSCRIBABILITY)

    def test_subscribe_unsubscribe(self):
        manager = ISubscriptionManager(self.root.document, None)
        manager.subscribability = SUBSCRIBABLE
        self.assertEqual(manager.locally_subscribed_emails, set([]))
        self.assertEqual(manager.is_subscribed('sylvain@infrae.com'), False)

        # we can subscribe some emails
        manager.subscribe('wim@infrae.com')
        manager.subscribe('sylvain@infrae.com')
        manager.subscribe('sylvain@infrae.com')
        self.assertEqual(
            manager.locally_subscribed_emails,
            set(['wim@infrae.com', 'sylvain@infrae.com']))
        self.assertEqual(manager.is_subscribed('sylvain@infrae.com'), True)

        # and unscribe others
        manager.unsubscribe('arthur@accroc.org')
        manager.unsubscribe('sylvain@infrae.com')
        self.assertEqual(
            manager.locally_subscribed_emails,
            set(['wim@infrae.com']))
        self.assertEqual(manager.is_subscribed('sylvain@infrae.com'), False)

    def test_is_subscribed(self):
        """is_subscribed returns True if you are subscribed on of the
        parents.
        """
        manager_root = ISubscriptionManager(self.root, None)
        manager_root.subscribability = SUBSCRIBABLE
        manager_root.subscribe('wim@infrae.com')
        self.assertEqual(manager_root.is_subscribed('wim@infrae.com'), True)
        self.assertEqual(manager_root.is_subscribed('unknown@u.com'), False)

        manager = ISubscriptionManager(self.root.folder, None)
        self.assertEqual(manager.is_subscribed('wim@infrae.com'), True)
        self.assertEqual(manager.is_subscribed('unknown@u.com'), False)

        # If you turn off subscription off at the folder level, you
        # are no longer subscribed
        manager.subscribability = NOT_SUBSCRIBABLE
        self.assertEqual(manager.is_subscribed('wim@infrae.com'), False)

        # That didn't changed anything on the parent
        self.assertEqual(manager_root.is_subscribed('wim@infrae.com'), True)

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SubscriptionManagerTestCase))
    return suite
