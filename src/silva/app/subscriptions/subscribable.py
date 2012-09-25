# -*- coding: utf-8 -*-
# Copyright (c) 2002-2012 Infrae. All rights reserved.
# See also LICENSE.txt

from Acquisition import aq_parent
from persistent import Persistent

from five import grok
from silva.core import interfaces
from silva.app.subscriptions.interfaces import ISubscriptionManager
from silva.app.subscriptions.interfaces import ISubscription
from silva.app.subscriptions.interfaces import (
    ACQUIRE_SUBSCRIBABILITY, NOT_SUBSCRIBABLE, SUBSCRIBABLE)

from zope.annotation.interfaces import IAnnotations


class Subscription(object):
    grok.implements(ISubscription)

    def __init__(self, email, manager):
        self.email = email
        self.content = manager.context
        self.manager = manager


class SubscribableData(Persistent):

    def __init__(self, default_subscribability):
        self.subscribability = default_subscribability
        self.subscriptions = set([])


class Subscribable(grok.Adapter):
    """Subscribable adapters potentially subscribable content and container
    Silva objects and encapsulates the necessary API for
    handling subscriptions.
    """
    grok.context(interfaces.IContent)
    grok.implements(ISubscriptionManager)
    grok.provides(ISubscriptionManager)

    default_subscribability = ACQUIRE_SUBSCRIBABILITY
    subscribability_possibilities = [
        NOT_SUBSCRIBABLE, SUBSCRIBABLE, ACQUIRE_SUBSCRIBABILITY]

    def __init__(self, context):
        super(Subscribable, self).__init__(context)
        annotations = IAnnotations(self.context)
        data = annotations.get('silva.app.subscriptions')
        if data is None:
            data = SubscribableData(self.default_subscribability)
            annotations['silva.app.subscriptions'] = data
        self.data =  data

    # ACCESSORS

    def is_subscribable(self):
        if self.data.subscribability == NOT_SUBSCRIBABLE:
            return False
        if self.data.subscribability == SUBSCRIBABLE:
            return True
        parent = ISubscriptionManager(aq_parent(self.context))
        return parent.is_subscribable()

    @apply
    def subscribability():
        def getter(self):
            return self.data.subscribability
        def setter(self, flag):
            assert flag in self.subscribability_possibilities
            self.data.subscribability = flag
        return property(getter, setter)

    @apply
    def locally_subscribed_emails():
        def getter(self):
            return set(self.data.subscriptions)
        def setter(self, emails):
            self.data.subscriptions = set(emails)
        return property(getter, setter)

    # ACCESSORS

    @property
    def subscriptions(self):
        subscriptions = {}
        for parent in self._get_subscribable_parents():
            for email in parent.locally_subscribed_emails:
                if email not in subscriptions:
                    subscriptions[email] = Subscription(email, parent)
        return subscriptions

    def _get_subscribable_parents(self, subscribables=None, last_explicit=0):
        # The purpose of last_explicit is to prevent to collect
        # subscribables where the non-subscribabiliy is acquired.
        if subscribables is None:
            subscribables = []
        if self.data.subscribability == NOT_SUBSCRIBABLE:
            # Empty list from the point without explicit
            # subscribability onwards.
            del subscribables[last_explicit:]
            return subscribables
        subscribables.append(self)
        if self.data.subscribability == SUBSCRIBABLE:
            # Keep a last_explicit for the object with explicit
            # subscribability set.
            last_explicit = len(subscribables)
        parent = ISubscriptionManager(aq_parent(self.context))
        return parent._get_subscribable_parents(subscribables, last_explicit)

    def get_subscriptions(self):
        return self.subscriptions.values()

    def get_subscription(self, email):
        try:
            return self.subscriptions[email]
        except KeyError:
            return None

    def is_subscribed(self, email):
        return email in self.subscriptions

    # MODIFIERS

    def subscribe(self, email):
        self.data.subscriptions.add(email)
        self.data._p_changed = True

    def unsubscribe(self, emailaddress):
        if emailaddress in self.data.subscriptions:
            self.data.subscriptions.remove(emailaddress)
            self.data._p_changed = True



class SubscribableContainer(Subscribable):
    grok.context(interfaces.IContainer)


class SubscribableRoot(Subscribable):
    grok.context(interfaces.IRoot)

    default_subscribability = NOT_SUBSCRIBABLE
    subscribability_possibilities = [NOT_SUBSCRIBABLE, SUBSCRIBABLE]

    def _get_subscribable_parents(self, subscribables=None, last_explicit=0):
        # The purpose of last_explicit is to prevent to collect subscribables
        # where the non-subscribabiliy is acquired.
        if subscribables is None:
            subscribables = []
        if self.data.subscribability == NOT_SUBSCRIBABLE:
            # Empty list from the point without explicit
            # subscribability onwards.
            del subscribables[last_explicit:]
            return subscribables
        subscribables.append(self)
        return subscribables
