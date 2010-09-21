# -*- coding: utf-8 -*-
# Copyright (c) 2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

from five import grok
from silva.app.subscriptions.interfaces import ISubscriptionService
from silva.core.interfaces import ISubscribable, ISilvaObject
from silva.core.smi import smi as silvasmi
from silva.core.smi.interfaces import IPropertiesTab
from silva.core.views import views as silvaviews
from silva.translations import translate as _
from zeam.form import silva as silvaforms
from zope import schema
from zope.component import queryUtility
from zope.interface import Interface
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from Products.Silva.adapters import subscribable


@grok.provider(IContextSourceBinder)
def subscribability_options(context):
    options = []
    settings = ISubscribable(context)
    for value, title in [
        (subscribable.ACQUIRE_SUBSCRIBABILITY, _(u"Acquire settings from above")),
        (subscribable.NOT_SUBSCRIBABLE, _(u"Disable subscriptions")),
        (subscribable.SUBSCRIBABLE, _(u"Enable subscriptions"))]:
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
                      u"to this content at this level. "),
        value_type=schema.TextLine(required=True),
        required=False)


class SubscriptionForm(silvaforms.SMIForm):
    """Edit subscriptions.
    """
    grok.context(ISilvaObject)
    grok.implements(IPropertiesTab)
    grok.name('tab_subscriptions')
    grok.require('silva.ManageSilvaContent')

    tab = 'properties'
    label = _(u"manage subscriptions")
    fields = silvaforms.Fields(ISubscribableSettings)
    fields['subscribability'].mode = 'radio'
    ignoreContent = False
    dataManager = silvaforms.makeAdaptiveDataManager(ISubscribable)
    actions = silvaforms.Actions(
        silvaforms.CancelAction(),
        silvaforms.EditAction())


class SubscriptionPortlet(silvaviews.Viewlet):
    grok.viewletmanager(silvasmi.SMIPortletManager)
    grok.order(0)
    grok.view(SubscriptionForm)

    def update(self):
        settings = ISubscribable(self.context)
        self.is_enabled = settings.is_subscribable()
        self.all_subscribers = len(settings.getSubscriptions())
        self.locally_subscribers = len(settings.locally_subscribed_emails)
        self.above_subscribers = self.all_subscribers - self.locally_subscribers


class SubscriptionButton(silvasmi.SMIMiddleGroundButton):
    grok.order(110)
    grok.require('silva.ManageSilvaContent')
    grok.view(IPropertiesTab)

    tab = 'tab_subscriptions'
    label = _(u"subscriptions")
    help = _(u"manage subscriptions: alt-u")
    accesskey = "u"

    def available(self):
        if ISubscribable(self.context, None) is None:
            return False
        service = queryUtility(ISubscriptionService)
        return service is not None and service.is_subscriptions_enabled()
