# -*- coding: utf-8 -*-
# Copyright (c) 2011 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

from Acquisition import aq_base

from silva.core.interfaces import IContent
from silva.core.upgrade.upgrade import BaseUpgrader, AnyMetaType
from silva.app.subscriptions.subscribable import SubscribableData
from zope.annotation.interfaces import IAnnotations

VERSION_A0='3.0a0'


class SubscriptionUpgrader(BaseUpgrader):
    """We move subscriptions information from the content to the
    annotation.
    """

    def upgrade(self, content):
        if IContent.providedBy(content):
            if hasattr(aq_base(content), '__subscribability__'):
                annotations = IAnnotations(content)
                if 'silva.app.subscriptions' not in annotations:
                    data = SubscribableData(content.__subscribability__)
                    annotations['silva.app.subscriptions'] = data
                    if hasattr(aq_base(content), '__subscriptions__'):
                        data.subscriptions = set(content.__subscriptions__.keys())
                        delattr(content, '__subscriptions__')
                    if hasattr(aq_base(content), '__pending_subscription_tokens__'):
                        delattr(content, '__pending_subscription_tokens__')
                    delattr(content, '__subscribability__')
        return content


subscription_upgrader = SubscriptionUpgrader(VERSION_A0, AnyMetaType, -500)
