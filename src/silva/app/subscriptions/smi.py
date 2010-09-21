# -*- coding: utf-8 -*-
# Copyright (c) 2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

from five import grok
from silva.core.smi import smi as silvasmi
from silva.translations import translate as _
from silva.core.interfaces import ISubscribable
from silva.app.subscriptions.interfaces import ISubscriptionService
from zope.component import queryUtility


class SubscriptionButton(silvasmi.SMIMiddleGroundButton):
    grok.order(110)
    grok.require('silva.ManageSilvaContent')

    tab = 'tab_subscriptions'
    label = _(u"subscriptions")
    help = _(u"manage subscriptions: alt-u")
    accesskey = "u"

    def available(self):
        if ISubscribable(self.context, None) is None:
            return False
        service = queryUtility(ISubscriptionService)
        return service is not None and service.is_subscriptions_enabled()
