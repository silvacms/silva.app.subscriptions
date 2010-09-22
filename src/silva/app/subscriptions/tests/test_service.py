# Copyright (c) 2002-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

import unittest

from zope.component import getUtility
from zope.interface.verify import verifyObject
from silva.app.subscriptions import errors
from silva.app.subscriptions.interfaces import (
    ISubscriptionService, ISubscriptionManager, SUBSCRIBABLE)
from silva.app.subscriptions.service import get_content_id
from silva.app.subscriptions.testing import FunctionalLayer


class SubscriptionServiceTestCase(unittest.TestCase):
    """Test the Subscription Service.
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
        factory.manage_addGhost('ghost', None, haunted=self.root.document)
        factory.manage_addFile('file', u'Downloable File')

    def test_service(self):
        service = getUtility(ISubscriptionService)
        self.assertTrue(verifyObject(ISubscriptionService, service))
        self.assertEqual(self.root.service_subscriptions, service)

    def test_request_subscription_failures(self):
        """Test cases where you can't request subscription to a content.
        """
        service = getUtility(ISubscriptionService)
        # first use something not subscribable at all
        self.assertRaises(
            errors.NotSubscribableError,
            service.request_subscription, self.root.file, "foo@foo.com")

        # even if all parameters are correct, content has to have its
        # subscribability set
        self.assertRaises(
            errors.NotSubscribableError,
            service.request_subscription, self.root.document, "foo@foo.com")

        # Set subscribability, invalid emailaddress though
        manager = ISubscriptionManager(self.root.document)
        manager.subscribability = SUBSCRIBABLE
        self.assertRaises(
            errors.InvalidEmailaddressError,
            service.request_subscription, self.root.document, "foo bar baz")

        # emailaddress already subscribed
        manager.subscribe("foo@foo.com")
        self.assertRaises(
            errors.AlreadySubscribedError,
            service.request_subscription, self.root.document, "foo@foo.com")

    def test_request_subscription(self):
        """Test request_subscription sends a mail.
        """
        manager = ISubscriptionManager(self.root.document)
        manager.subscribability = SUBSCRIBABLE

        service = getUtility(ISubscriptionService)
        service.request_subscription(self.root.document, "foo@foo.com")

        message = self.root.service_mailhost.read_last_message()
        self.assertNotEqual(message, None)
        self.assertEqual(message.mto, ['foo@foo.com'])

    def test_request_cancellation_failures(self):
        """Test request_cancellation failures cases.
        """
        service = getUtility(ISubscriptionService)

        # first use something not subscribable at all
        self.assertRaises(
            errors.NotSubscribableError,
            service.request_cancellation, self.root.file, "foo@foo.com")

        # invalid emailaddress
        self.assertRaises(
            errors.InvalidEmailaddressError,
            service.request_cancellation, self.root.document, "foo bar baz")

        # emailaddress was not subscribed
        self.assertRaises(
            errors.NotSubscribedError,
            service.request_cancellation, self.root.document, "foo@foo.com")

    def test_subscribe(self):
        ref = self.service._create_ref(self.doc)
        emailaddress = "foo1@bar.com"
        subscr = subscribable.getSubscribable(self.doc)
        subscr.setSubscribability(subscribable.SUBSCRIBABLE)
        token = subscr.generateConfirmationToken(emailaddress)
        self.service.subscribe(ref, emailaddress, token)
        self.assertEquals(True, subscr.isSubscribed(emailaddress))
        # and again, should raise an exception
        self.assertRaises(
            errors.SubscriptionError,
            self.service.subscribe, ref, emailaddress, token)
        # for an invalid content ref an exception should be raised too
        ref = self.service._create_ref(self.service) # use something not subscribable
        emailaddress = "foo2@bar.com"
        token = subscr.generateConfirmationToken(emailaddress)
        self.assertRaises(
            errors.SubscriptionError,
            self.service.subscribe, ref, emailaddress, token)

    def test_unsubscribe(self):
        ref = self.service._create_ref(self.doc)
        emailaddress = "foo1@bar.com"
        subscr = subscribable.getSubscribable(self.doc)
        subscr.setSubscribability(subscribable.SUBSCRIBABLE)
        token = subscr.generateConfirmationToken(emailaddress)
        self.service.subscribe(ref, emailaddress, token)
        token = subscr.generateConfirmationToken(emailaddress)
        self.service.unsubscribe(ref, emailaddress, token)
        # and again, should raise an exception
        self.assertRaises(
            errors.CancellationError,
            self.service.unsubscribe, ref, emailaddress, token)
        # for an invalid content ref an exception should be raised too
        emailaddress = "foo2@bar.com"
        token = subscr.generateConfirmationToken(emailaddress)
        self.service.subscribe(ref, emailaddress, token)
        token = subscr.generateConfirmationToken(emailaddress)
        ref = self.service._create_ref(self.service) # use something not subscribable
        self.assertRaises(
            errors.CancellationError,
            self.service.unsubscribe, ref, emailaddress, token)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SubscriptionServiceTestCase))
    return suite
