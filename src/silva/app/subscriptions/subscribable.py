# Copyright (c) 2002-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

import itertools
import hashlib
import time
import datetime

from Acquisition import aq_parent
from BTrees.OOBTree import OOBTree

from five import grok
from silva.core import interfaces
from silva.app.subscriptions.interfaces import (
    ISubscriptionManager, ISubscription)
from silva.app.subscriptions.interfaces import (
    ACQUIRE_SUBSCRIBABILITY, NOT_SUBSCRIBABLE, SUBSCRIBABLE)


TIMEOUTINDAYS =  3

def generate_token(*args):
    hash = hashlib.md5()
    for arg in args:
        hash.update(str(args))
    return hash.hexdigest()


class Subscription(object):
    grok.implements(ISubscription)

    def __init__(self, email, manager):
        self.email = email
        self.content = manager.context
        self.manager = manager


class Subscribable(grok.Adapter):
    """Subscribable adapters potentially subscribable content and container
    Silva objects and encapsulates the necessary API for
    handling subscriptions.
    """
    grok.context(interfaces.IContent)
    grok.implements(ISubscriptionManager)
    grok.provides(ISubscriptionManager)

    subscribability_possibilities = [
        NOT_SUBSCRIBABLE, SUBSCRIBABLE, ACQUIRE_SUBSCRIBABILITY]

    def __init__(self, context):
        super(Subscribable, self).__init__(context)
        if not hasattr(context, '__subscribability__'):
            context.__subscribability__ = ACQUIRE_SUBSCRIBABILITY
        if not hasattr(context, '__subscriptions__'):
            context.__subscriptions__ = OOBTree()
        if not hasattr(context, '__pending_subscription_tokens__'):
            context.__pending_subscription_tokens__ = OOBTree()

    # ACCESSORS

    def is_subscribable(self):
        subscribability = self.context.__subscribability__
        if subscribability == NOT_SUBSCRIBABLE:
            return False
        if subscribability == SUBSCRIBABLE:
            return True
        parent = ISubscriptionManager(aq_parent(self.context))
        return parent.is_subscribable()

    @apply
    def subscribability():
        def getter(self):
            return self.context.__subscribability__
        def setter(self, flag):
            assert flag in self.subscribability_possibilities
            self.context.__subscribability__ = flag
        return property(getter, setter)

    @apply
    def locally_subscribed_emails():
        def getter(self):
            return set(self.context.__subscriptions__.keys())
        def setter(self, emails):
            # XXX Should not this be a set ??? (Need an upgrader)
            subscriptions = self.context.__subscriptions__
            subscriptions.clear()
            subscriptions.update(
                zip(emails, itertools.repeat(None, len(emails))))
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
        if self.context.__subscribability__ == NOT_SUBSCRIBABLE:
            # Empty list from the point without explicit
            # subscribability onwards.
            del subscribables[last_explicit:]
            return subscribables
        subscribables.append(self)
        if self.context.__subscribability__ == SUBSCRIBABLE:
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
        subscriptions = self.context.__subscriptions__
        subscriptions[email] = None

    def unsubscribe(self, emailaddress):
        subscriptions = self.context.__subscriptions__
        if subscriptions.has_key(emailaddress):
            del subscriptions[emailaddress]

    # Manager local subscription/unscription token

    def generate_token(self, email):
        tokens = self.context.__pending_subscription_tokens__
        timestamp = '%f' % time.time()
        token = generate_token(email, timestamp)
        tokens[email] = (timestamp, token)
        return token

    def validate_token(self, email, token):
        # The current implementation will keep items in the
        # pending list indefinitly if _validate is not called (end user
        # doesn't follow up on confirmantion email), or _validate is called,
        # but the supplied token is not valid.
        tokens = self.context.__pending_subscription_tokens__
        request_timestamp, expected_token = tokens.get(email, (None, None))
        if request_timestamp is None or expected_token is None:
            return False
        now = datetime.datetime.now()
        then = datetime.datetime.fromtimestamp(float(request_timestamp))
        delta = now - then
        if delta.days > TIMEOUTINDAYS:
            del tokens[email]
            return False
        if token == expected_token:
            del tokens[email]
            return True
        return False


class SubscribableContainer(Subscribable):
    grok.context(interfaces.IContainer)


class SubscribableRoot(Subscribable):
    grok.context(interfaces.IRoot)

    subscribability_possibilities = [NOT_SUBSCRIBABLE, SUBSCRIBABLE]

    def __init__(self, context):
        if not hasattr(context, '__subscribability__'):
            context.__subscribability__ = NOT_SUBSCRIBABLE
        super(SubscribableRoot, self).__init__(context)

    def _get_subscribable_parents(self, subscribables=None, last_explicit=0):
        # The purpose of last_explicit is to prevent to collect subscribables
        # where the non-subscribabiliy is acquired.
        if subscribables is None:
            subscribables = []
        if self.context.__subscribability__ == NOT_SUBSCRIBABLE:
            # Empty list from the point without explicit
            # subscribability onwards.
            del subscribables[last_explicit:]
            return subscribables
        subscribables.append(self)
        return subscribables
