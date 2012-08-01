# Copyright (c) 2002-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

import unittest

from zope.component import getUtility
from zope.interface.verify import verifyObject

from silva.app.subscriptions import errors
from silva.app.subscriptions.interfaces import ISubscriptionManager
from silva.app.subscriptions.interfaces import ISubscriptionService
from silva.app.subscriptions.interfaces import SUBSCRIBABLE
from silva.app.subscriptions.testing import FunctionalLayer
from silva.core.interfaces import IPublicationWorkflow


class SubscriptionServiceTestCase(unittest.TestCase):
    """Test the Subscription Service.
    """
    layer = FunctionalLayer

    def setUp(self):
        self.root = self.layer.get_application()
        self.layer.login('manager')
        factory = self.root.manage_addProduct['silva.app.subscriptions']
        factory.manage_addSubscriptionService()

        factory = self.root.manage_addProduct['Silva']
        factory.manage_addMockupVersionedContent('document', 'Document')
        factory.manage_addFolder('folder', u'Test Folder')
        factory.manage_addGhost('ghost', None, haunted=self.root.document)
        factory.manage_addFile('file', u'Downloable File')

    def test_service(self):
        """Test service settings.
        """
        service = getUtility(ISubscriptionService)
        self.assertTrue(verifyObject(ISubscriptionService, service))
        self.assertEqual(self.root.service_subscriptions, service)

        # By default subscription are off, but you can change it
        self.assertEqual(service.are_subscriptions_enabled(), False)

        service.enable_subscriptions()
        self.assertEqual(service.are_subscriptions_enabled(), True)

        # You can now if at one given context they are enabled
        self.assertEqual(service.are_subscriptions_enabled(self.root), False)
        manager = ISubscriptionManager(self.root)
        manager.subscribability = SUBSCRIBABLE
        self.assertEqual(service.are_subscriptions_enabled(self.root), True)

        # And we disable them globaly now
        service.disable_subscriptions()
        self.assertEqual(service.are_subscriptions_enabled(), False)
        self.assertEqual(service.are_subscriptions_enabled(self.root), False)

    def test_subscription_failures(self):
        """Test cases where you can't request subscription to a content.
        """
        service = getUtility(ISubscriptionService)
        service.enable_subscriptions()

        # first use something not subscribable at all
        self.assertRaises(
            errors.NotSubscribableError,
            service.request_subscription,
            self.root.file, "torvald@example.com")

        # even if all parameters are correct, content has to have its
        # subscribability set
        self.assertRaises(
            errors.NotSubscribableError,
            service.request_subscription,
            self.root.document, "torvald@example.com")

        # Set subscribability, invalid emailaddress though
        manager = ISubscriptionManager(self.root.document)
        manager.subscribability = SUBSCRIBABLE
        self.assertRaises(
            errors.InvalidEmailaddressError,
            service.request_subscription,
            self.root.document, "lekker zalm")

        # emailaddress already subscribed
        manager.subscribe("torvald@example.com")
        self.assertRaises(
            errors.AlreadySubscribedError,
            service.request_subscription,
            self.root.document, "torvald@example.com")

    def test_subscribe(self):
        """Test request_subscription sends a mail, and we can get
        subscribed with it.
        """
        browser = self.layer.get_browser()

        manager = ISubscriptionManager(self.root.document)
        manager.subscribability = SUBSCRIBABLE
        self.assertEqual(manager.is_subscribed('torvald@example.com'), False)
        self.assertEqual(self.root.service_mailhost.messages, [])

        service = getUtility(ISubscriptionService)
        service.enable_subscriptions()
        service.request_subscription(self.root.document, "torvald@example.com")

        message = self.root.service_mailhost.read_last_message()
        self.assertNotEqual(message, None)
        self.assertEqual(message.content_type, 'text/plain')
        self.assertEqual(message.charset, 'utf-8')
        self.assertEqual(message.mto, ['torvald@example.com'])
        self.assertEqual(
            message.mfrom,
            'Subscription Service <subscription-service@example.com>')
        self.assertEqual(
            message.subject,
            'Subscription confirmation to "document"')
        self.assertEqual(len(message.urls), 2)

        # XXX it is a bit hardcoded on the template, the confirmation
        # is the second like in the mail.
        confirmation_url = message.urls[-1]
        self.assertEqual(browser.open(confirmation_url), 200)
        self.assertEqual(
            browser.location,
            '/root/document/subscriptions.html/@@confirm_subscription')
        self.assertEqual(
            browser.html.xpath('//p[@class="subscription-result"]/text()'),
            ['You have been successfully subscribed. '
             'You will now receive email notifications.'])

        # Torvald is now subscribed
        self.assertEqual(manager.is_subscribed('torvald@example.com'), True)

    def test_unsubscription_failures(self):
        """Test unsubscription failures cases.
        """
        service = getUtility(ISubscriptionService)
        service.enable_subscriptions()

        # first use something not subscribable at all
        self.assertRaises(
            errors.NotSubscribableError,
            service.request_cancellation,
            self.root.file, "torvald@example.com")

        # invalid emailaddress
        self.assertRaises(
            errors.InvalidEmailaddressError,
            service.request_cancellation,
            self.root.document, "lekker zalm")

        # emailaddress was not subscribed
        self.assertRaises(
            errors.NotSubscribedError,
            service.request_cancellation,
            self.root.document, "torvald@example.com")

    def test_unsubscribe(self):
        """Test unsubscription feature.
        """
        browser = self.layer.get_browser()

        manager = ISubscriptionManager(self.root.document)
        manager.subscribability = SUBSCRIBABLE
        manager.subscribe('torvald@example.com')
        self.assertEqual(manager.is_subscribed('torvald@example.com'), True)
        self.assertEqual(self.root.service_mailhost.messages, [])

        service = getUtility(ISubscriptionService)
        service.enable_subscriptions()
        service.request_cancellation(self.root.document, "torvald@example.com")

        message = self.root.service_mailhost.read_last_message()
        self.assertNotEqual(message, None)
        self.assertEqual(message.content_type, 'text/plain')
        self.assertEqual(message.charset, 'utf-8')
        self.assertEqual(message.mto, ['torvald@example.com'])
        self.assertEqual(
            message.mfrom,
            'Subscription Service <subscription-service@example.com>')
        self.assertEqual(
            message.subject,
            'Confirm the cancellation of subscription to "document"')
        self.assertEqual(len(message.urls), 2)

        # XXX it is a bit hardcoded in the template, the confirmation
        # is the last link in the mail.
        confirmation_url = message.urls[-1]
        self.assertEqual(browser.open(confirmation_url), 200)
        self.assertEqual(
            browser.location,
            '/root/document/subscriptions.html/@@confirm_cancellation')
        self.assertEqual(
            browser.html.xpath('//p[@class="subscription-result"]/text()'),
            ['You have been successfully unsubscribed.'])

        # Torvald is now subscribed
        self.assertEqual(manager.is_subscribed('torvald@example.com'), False)

    def test_publication_notification(self):
        """We verify that if a document is publish, and the
        notification are enabled, a mail is sent to the susbcribed people.
        """
        service = getUtility(ISubscriptionService)
        service.enable_subscriptions()
        service._from = 'notification@example.com'

        manager = ISubscriptionManager(self.root)
        manager.subscribability = SUBSCRIBABLE
        manager.subscribe('torvald@example.com')
        self.assertEqual(len(self.root.service_mailhost.messages), 0)

        IPublicationWorkflow(self.root.document).publish()

        # We have two notification, one for the document, one for the ghost
        self.assertEqual(len(self.root.service_mailhost.messages), 2)
        message = self.root.service_mailhost.messages[0]
        self.assertEqual(message.content_type, 'text/plain')
        self.assertEqual(message.charset, 'utf-8')
        self.assertEqual(message.mto, ['torvald@example.com'])
        self.assertEqual(message.mfrom, 'notification@example.com')
        self.assertEqual(message.subject, 'Change notification for "Document"')

        message = self.root.service_mailhost.messages[1]
        self.assertEqual(message.content_type, 'text/plain')
        self.assertEqual(message.charset, 'utf-8')
        self.assertEqual(message.mto, ['torvald@example.com'])
        self.assertEqual(message.mfrom, 'notification@example.com')
        self.assertEqual(message.subject, 'Change notification for "ghost"')

        self.root.service_mailhost.reset()
        self.assertEqual(len(self.root.service_mailhost.messages), 0)

        # We now disable the subscription. And publish a new version.
        service.disable_subscriptions()
        self.root.document.create_copy()
        IPublicationWorkflow(self.root.document).publish()

        # No notification have been sent
        self.assertEqual(len(self.root.service_mailhost.messages), 0)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SubscriptionServiceTestCase))
    return suite
