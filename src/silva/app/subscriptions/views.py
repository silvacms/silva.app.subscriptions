# -*- coding: utf-8 -*-
# Copyright (c) 2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

from AccessControl import getSecurityManager
from zExceptions import NotFound

from five import grok
from megrok.chameleon.components import ChameleonPageTemplate
from silva.app.subscriptions import errors
from silva.app.subscriptions.interfaces import ISubscriptionService
from silva.app.subscriptions.interfaces import ISubscriptionManager
from silva.captcha import Captcha
from silva.core.services.interfaces import IMemberService
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

def captcha_available(form):
    return not form.user_id

def email_default(form):
    if form.default_email:
        return form.default_email
    return silvaforms.NO_VALUE


subscription_fields = silvaforms.Fields(ISubscriptionFields)
subscription_fields['captcha'].available = captcha_available
subscription_fields['email'].defaultValue = email_default


class SubscribeAction(silvaforms.Action):
    identifier = 'subscribe'
    title = _(u"Subscribe")

    def available(self, form):
        if form.default_email:
            return not form.manager.is_subscribed(form.default_email)
        return True

    def __call__(self, form):
        data, error = form.extractData()
        if error:
            return silvaforms.FAILURE
        service = getUtility(ISubscriptionService)
        try:
            service.request_subscription(form.context, data['email'])
        except errors.NotSubscribableError:
            form.status = _(u"You cannot subscribe to this content.")
            return silvaforms.FAILURE
        except errors.AlreadySubscribedError:
            form.status = _(u"You are already subscribed to this content.")
            return silvaforms.FAILURE
        form.status = _(u'Confirmation request for subscription '
                        u'has been emailed to ${email}.',
                        mapping={'email': data['email']})
        return silvaforms.SUCCESS


class UnsubscribeAction(silvaforms.Action):
    identifier = 'unsubscribe'
    title = _(u"Unsubscribe")

    def available(self, form):
        if form.default_email:
            return form.manager.is_subscribed(form.default_email)
        return True

    def __call__(self, form):
        data, error = form.extractData()
        if error:
            return silvaforms.FAILURE
        service = getUtility(ISubscriptionService)
        try:
            service.request_cancellation(form.context, data['email'])
        except errors.NotSubscribableError:
            form.status = _(u"You cannot subscribe to this content.")
            return silvaforms.FAILURE
        except errors.NotSubscribedError:
            form.status = _(u"You are not subscribed to this content.")
            return silvaforms.FAILURE
        form.status = _(u'Confirmation request for cancellation '
                        u'has been emailed to ${email}.',
                        mapping={'email': data['email']})
        return silvaforms.SUCCESS

subscription_actions = silvaforms.Actions(
    SubscribeAction(),
    UnsubscribeAction())


class SubscriptionForm(silvaforms.PublicForm):
    grok.context(ISilvaObject)
    grok.name('subscriptions.html')
    grok.require('zope2.View')

    @property
    def label(self):
        return _(u'subscribe / unsubscribe to ${title}',
                 mapping={'title': self.context.get_title()})
    description =_(
        u'Fill in your email address if you want to receive an a '
        u'email notifications whenever a change happen at this URL. '
        u'You can cancel notification if already subscribed as well.')
    fields = subscription_fields.copy()
    actions = subscription_actions.copy()

    @silvaforms.action(_(u'Cancel'))
    def action_cancel(self):
        self.redirect(self.url())
        return silvaforms.SUCCESS

    def update(self):
        service = queryUtility(ISubscriptionService)
        if service is None or not service.are_subscriptions_enabled():
            raise NotFound(u"Subscription are not enabled.")
        self.manager = ISubscriptionManager(self.context, None)
        if self.manager is None:
            raise NotFound(u"Subscription not available on this content")
        self.default_email = None
        self.user_id = getSecurityManager().getUser().getId()
        if self.user_id:
            member = getUtility(IMemberService).get_member(self.user_id)
            if member is not None:
                self.default_email = member.email()


class SubscriptionConfirmationPage(silvaviews.Page):
    grok.context(SubscriptionForm)
    grok.name('confirm_subscription')

    template = ChameleonPageTemplate(
        filename='templates/confirmationpage.cpt')

    def __init__(self, context, request):
        super(SubscriptionConfirmationPage, self).__init__(
            context.context, request)

    def update(self, content=None, email=None, token=None):
        if content is None or email is None or token is None:
            self.status = _(u"Invalid subscription confirmation.")
            return
        service = queryUtility(ISubscriptionService)
        if service is None or not service.are_subscriptions_enabled():
            self.status = _("Subscription no longer available.")
            return
        try:
            service.subscribe(content, email, token)
        except errors.SubscriptionError:
            self.status = _("Subscription failed.")
            return
        self.status = _(
            u'You have been successfully subscribed. '
            u'You will now receive email notifications.')


class SubscriptionCancellationConfirmationPage(SubscriptionConfirmationPage):
    grok.name('confirm_cancellation')

    def update(self, content=None, email=None, token=None):
        if content is None or email is None or token is None:
            self.status = _(u"Invalid confirmation.")
            return
        service = queryUtility(ISubscriptionService)
        if service is None or not service.are_subscriptions_enabled():
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


class SubscriptionContentProvider(silvaforms.PublicContentProviderForm):
    grok.context(ISilvaObject)
    grok.name('subscriptions')

    label = _(u'Subscribe / Unsubscribe')
    description =_(
        u'Fill in your email address if you want to receive an a '
        u'email notifications whenever a new version of this page '
        u'or its subpages becomes available.')
    fields = subscription_fields.copy()
    actions = subscription_actions.copy()

    def update(self):
        self.manager = ISubscriptionManager(self.context)
        self.default_email = None
        self.user_id = getSecurityManager().getUser().getId()
        if self.user_id:
            member = getUtility(IMemberService).get_member(self.user_id)
            if member is not None:
                self.default_email = member.email()
        super(SubscriptionContentProvider, self).update()
