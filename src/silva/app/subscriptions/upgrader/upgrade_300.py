# -*- coding: utf-8 -*-
# Copyright (c) 2011-2012 Infrae. All rights reserved.
# See also LICENSE.txt

import logging

from Acquisition import aq_base

from silva.core.interfaces import IContent, IContainer
from silva.core.upgrade.upgrade import BaseUpgrader, AnyMetaType, content_path
from silva.app.subscriptions.subscribable import SubscribableData
from zope.annotation.interfaces import IAnnotations

VERSION_A0='3.0a0'
logger = logging.getLogger('silva.core.upgrade')


class SubscriptionUpgrader(BaseUpgrader):
    """We move subscriptions information from the content to the
    annotation.
    """

    def validate(self, content):
        return (hasattr(aq_base(content), '__subscribability__') and
                (IContent.providedBy(content) or
                 IContainer.providedBy(content)))

    def upgrade(self, content):
        logger.info(u'Update subscription in: %s.', content_path(content))
        annotations = IAnnotations(content)
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
