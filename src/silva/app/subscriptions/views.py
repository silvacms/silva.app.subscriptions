# -*- coding: utf-8 -*-
# Copyright (c) 2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

from zExceptions import NotFound

from five import grok
from megrok.chameleon.components import ChameleonPageTemplate
from silva.app.subscriptions import errors
from silva.app.subscriptions.interfaces import ISubscriptionService
from silva.captcha import Captcha
from silva.core.interfaces import ISilvaObject
from silva.core.views import views as silvaviews
from silva.translations import translate as _
from z3c.schema.email import RFC822MailAddress
from zeam.form import silva as silvaforms
from zope import interface
from zope.component import queryUtility, getUtility


class ISubscriptionFields(interface.Interface):
    email = RFC822MailAddress(
        title=_(u"Email address"),
        description=_(
            u"Enter your email on which you wish receive your notifications."),
        required=True)
    captcha = Captcha(
        title=_(u"Captcha"),
        description=_(
            u'Please retype the captcha below to verify that you are human.'),
        required=True)


class SubscriptionForm(silvaforms.PublicForm):
    grok.context(ISilvaObject)
    grok.name('subscriptions.html')
    grok.require('zope2.View')

    def update(self):
        service = queryUtility(ISubscriptionService)
        if service is None or not service.is_subscriptions_enabled():
            raise NotFound(u"Subscription are not enabled.")

    @property
    def label(self):
        return _(u'subscribe / unsubscribe to ${title}',
                 mapping={'title': self.context.get_title()})
    description =_(u'Fill in your email address if you want to receive an a '
                   u'email notifications whenever a new version of this page '
                   u'or its subpages becomes available.')
    fields = silvaforms.Fields(ISubscriptionFields)

    @silvaforms.action(_(u'Subscribe'))
    def action_subscribe(self):
        data, error = self.extractData()
        if error:
            return silvaforms.FAILURE
        service = getUtility(ISubscriptionService)
        try:
            service.requestSubscription(self.context, data['email'])
        except errors.NotSubscribableError:
            self.status = _(u"You cannot subscribe to this content.")
            return silvaforms.FAILURE
        except errors.AlreadySubscribedError:
            self.status = _(u"You are already subscribed to this content.")
            return silvaforms.FAILURE
        self.status = _(u'Confirmation request for subscription '
                        u'has been emailed to ${email}.',
                        mapping={'email': data['email']})
        return silvaforms.SUCCESS

    @silvaforms.action(_(u'Unsubscribe'))
    def action_unsubscribe(self):
        data, error = self.extractData()
        if error:
            return silvaforms.FAILURE
        service = getUtility(ISubscriptionService)
        try:
            service.requestCancellation(self.context, data['email'])
        except errors.NotSubscribableError:
            self.status = _(u"You cannot subscribe to this content.")
            return silvaforms.FAILURE
        except errors.NotSubscribedError:
            self.status = _(u"You are not subscribed to this content.")
            return silvaforms.FAILURE
        self.status = _(u'Confirmation request for cancellation '
                        u'has been emailed to ${email}.',
                        mapping={'email': data['email']})
        return silvaforms.SUCCESS

    @silvaforms.action(_(u'Cancel'))
    def action_cancel(self):
        self.redirect(self.url())
        return silvaforms.SUCCESS


class SubscriptionConfirmationPage(silvaviews.Page):
    grok.context(SubscriptionForm)
    grok.name('confirm_subscription')

    template = ChameleonPageTemplate(filename='templates/confirmationpage.cpt')

    def __init__(self, context, request):
        super(SubscriptionConfirmationPage, self).__init__(
            context.context, request)

    def update(self, content=None, email=None, token=None):
        if content is None or email is None or token is None:
            self.status = _(u"Invalid subscription confirmation.")
            return
        service = queryUtility(ISubscriptionService)
        if service is None or not service.is_subscriptions_enabled():
            self.status = _("Subscription no longer available.")
            return
        try:
            service.subscribe(content, email, token)
        except errors.SubscriptionError:
            self.status = _("Subscription failed.")
            return
        self.status = _(
            u'You have been successfully subscribed. '
            u'This means you will receive email notifications '
            u'whenever a new version of these pages becomes available.')


class SubscriptionCancellationConfirmationPage(SubscriptionConfirmationPage):
    grok.name('confirm_cancellation')

    def update(self, content=None, email=None, token=None):
        if content is None or email is None or token is None:
            self.status = _(u"Invalid confirmation.")
            return
        service = queryUtility(ISubscriptionService)
        if service is None or not service.is_subscriptions_enabled():
            self.status = _(u"Subscription no longer available.")
            return
        try:
            service.unsubscribe(content, email, token)
        except errors.SubscriptionError:
            self.status = _(
                u"Something went wrong in unsubscribing from this page. "
                u"It might be that the link you followed expired.")
            return
        self.status = _(u"You have been successfully unsubscribed.")
