# -*- coding: utf-8 -*-
# Copyright (c) 2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

from zope.interface import Interface, Attribute
from silva.core.interfaces import ISilvaService, ISilvaLocalService

# Subscription modes for subscribability flag in ISubsriptionManager
NOT_SUBSCRIBABLE = 0
SUBSCRIBABLE = 1
ACQUIRE_SUBSCRIBABILITY = 2


class ISubscription(Interface):
    """Subscription interface.
    """
    email = Attribute(u"Subscribed email")
    content = Attribute(u"Content from which this email is subscribed")
    manager = Attribute(u"SubscriptionManager who is responsible")


class ISubscriptionManager(Interface):
    """Subscribable interface
    """
    subscribability = Attribute(
        u"Mode indicating if the subscription is on")
    locally_subscribed_emails = Attribute(
        u"Set of locally subscribed email to this content")
    subscriptions = Attribute(
        u"Dictionnay of subscribed emails to contents "
        u"for all subscriptions for this content and its parents")

    def is_subscribable():
        """Return True if the adapted object is actually subscribable,
        False otherwise.
        """

    def subscribe(email):
        """Subscribe email for the content.
        """

    def unsubscribe(email):
        """Unsubscribe emailaddress for the content.
        """

    def is_subscribed(email):
        """Return true if the given email is suscribed at this level.
        """

    def generate_token(email):
        """Generate a token used for the subscription/cancellation cycle.
        """

    def validate_token(email, token):
        """Return True is the specified email and token validate a
        previously call to generate_token.
        """


class ISubscriptionService(ISilvaService, ISilvaLocalService):

    def enable_subscriptions():
        """Enable subscriptions in that part of the site.
        """

    def disable_subscriptions():
        """Disable susbcriptions in that part of the site.
        """

    def is_subscriptions_enabled():
        """Return true if subscriptions are enabled in that part of
        the site.
        """

    def request_subscription(content, email):
        """Request a subscription to the given content by the given
        email.
        """

    def request_cancellation(content, email):
        """Request to cancel a subscription to the given content by
        the given email.
        """

    def send_notification(content, template_id):
        """Render the given template using content information and
        send the result to the subscribed people.
        """
