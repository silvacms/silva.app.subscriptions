# -*- coding: utf-8 -*-
# Copyright (c) 2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

from five import grok
from silva.app.subscriptions.interfaces import (
    ISubscriptionService, ISubscriptionManager)
from silva.app.subscriptions.interfaces import (
    ACQUIRE_SUBSCRIBABILITY, NOT_SUBSCRIBABLE, SUBSCRIBABLE)
from silva.core.interfaces import ISilvaObject, IContainer
from silva.core.views import views as silvaviews
from silva.core.smi.settings import SettingsMenu, Settings
from silva.ui.menu import MenuItem
from silva.translations import translate as _

from zeam.form import silva as silvaforms
from zope import schema
from zope.component import queryUtility
from zope.interface import Interface
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm


@grok.provider(IContextSourceBinder)
def subscribability_options(context):
    options = []
    settings = ISubscriptionManager(context)
    for value, title in [
        (ACQUIRE_SUBSCRIBABILITY, _(u"Acquire settings from above")),
        (NOT_SUBSCRIBABLE, _(u"Disable subscriptions")),
        (SUBSCRIBABLE, _(u"Enable subscriptions"))]:
        if value in settings.subscribability_possibilities:
            options.append(
                SimpleTerm(value=value, token=str(value), title=title))
    return SimpleVocabulary(options)


class ISubscribableSettings(Interface):
    subscribability = schema.Choice(
        title=_(u"subscribable"),
        description=_(
            u"Set the subscribability for this content, "
            u"or set it to acquire the subscribability from above "
            u"(the default)."),
        source=subscribability_options,
        required=True)
    locally_subscribed_emails = schema.Set(
        title=_(u"subscribed email addresses"),
        description=_(u"List of email addresses currently subscribed "
                      u"to this content at this level, one per line. "),
        value_type=schema.TextLine(required=True),
        required=False)


class SubscriptionForm(silvaforms.SMIForm):
    """Edit subscriptions.
    """
    grok.adapts(Settings, ISilvaObject)
    grok.name('subscriptions')
    grok.require('silva.ManageSilvaContent')

    label = _(u"Manage subscriptions")
    fields = silvaforms.Fields(ISubscribableSettings)
    fields['subscribability'].mode = 'radio'
    fields['locally_subscribed_emails'].mode = 'lines'
    fields['locally_subscribed_emails'].defaultValue = lambda f: set()
    ignoreContent = False
    dataManager = silvaforms.makeAdaptiveDataManager(ISubscriptionManager)
    actions = silvaforms.Actions(
        silvaforms.CancelAction(),
        silvaforms.EditAction())


class SubscriptionMenu(MenuItem):
    grok.adapts(SettingsMenu, IContainer)
    grok.order(110)
    grok.require('silva.ManageSilvaContent')

    name = _(u"Subscriptions")
    screen = SubscriptionForm
    description = _(u"manage subscriptions")

    def available(self):
        if ISubscriptionManager(self.content, None) is None:
            return False
        service = queryUtility(ISubscriptionService)
        return service is not None and service.are_subscriptions_enabled()


class SubscriptionPortlet(silvaviews.Viewlet):
    grok.order(0)
    grok.view(SubscriptionForm)
    grok.viewletmanager(silvaforms.SMIFormPortlets)

    def update(self):
        settings = ISubscriptionManager(self.context)
        self.is_enabled = settings.is_subscribable()
        self.all_subscribers = len(settings.subscriptions)
        self.locally_subscribers = len(settings.locally_subscribed_emails)
        self.above_subscribers = self.all_subscribers - self.locally_subscribers


