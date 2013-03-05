# -*- coding: utf-8 -*-
# Copyright (c) 2013  Infrae. All rights reserved.
# See also LICENSE.txt

import unittest

from zope.component import getUtility
from Products.Silva.ftesting import smi_settings
from Products.Silva.testing import CatalogTransaction
from silva.app.subscriptions.interfaces import ISubscriptionService
from silva.app.subscriptions.testing import FunctionalLayer


class SettingsTestCase(unittest.TestCase):
    layer = FunctionalLayer
    user = 'manager'

    def setUp(self):
        self.root = self.layer.get_application()
        self.layer.login('manager')
        with CatalogTransaction():
            factory = self.root.manage_addProduct['silva.app.subscriptions']
            factory.manage_addSubscriptionService()
            factory = self.root.manage_addProduct['Silva']
            factory.manage_addMockupVersionedContent('document', 'Document')

            service = getUtility(ISubscriptionService)
            service.enable_subscriptions()

    def test_subscriptions_settings(self):
        browser = self.layer.get_web_browser(smi_settings)
        browser.login(self.user)

        self.assertEqual(browser.inspect.title, u"root")
        self.assertEqual(
            browser.inspect.tabs,
            ['Content', 'Add', 'Properties', 'Settings'])
        self.assertEqual(browser.inspect.tabs['Settings'].open.click(), 200)
        self.assertIn('Subscriptions', browser.inspect.tabs['Settings'].entries)
        self.assertEqual(
            browser.inspect.tabs['Settings'].entries['Subscriptions'].click(),
            200)
        self.assertIn('Manage subscriptions', browser.inspect.form)

        form = browser.inspect.form['Manage subscriptions']
        self.assertIn('subscribed email addresses', form.fields)
        form.fields['subscribed email addresses'].value = 'info@infrae.com'
        self.assertEqual(form.actions, ['Cancel', 'Save changes'])
        self.assertEqual(form.actions['Save changes'].click(), 200)
        browser.macros.assertFeedback('Changes saved.')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SettingsTestCase))
    return suite
