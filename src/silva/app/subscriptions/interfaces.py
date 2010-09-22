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


class ISubscriptionManager(Interface):
    """Subscribable interface
    """
    subscribability = Attribute(
        u"Mode indicating if the subscription is on")
    locally_subscribed_emails = Attribute(
        u"Set of locally subscribed email to this content")

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


    def getSubscriptions():
        """Return a list of ISubscription objects
        """

    def isValidSubscription(emailaddress, token):
        """Return True is the specified emailaddress and token depict a
        valid subscription request. False otherwise.
        """

    def isValidCancellation(emailaddress, token):
        """Return True is the specified emailaddress and token depict a
        valid cancellation request. False otherwise.
        """

    def isSubscribed(emailaddress):
        """Return True is the specified emailaddress is already subscribed
        for the adapted object. False otherwise.
        """

    def generateConfirmationToken(emailaddress):
        """Generate a token used for the subscription/cancellation cycle.
        """


class ISubscriptionService(ISilvaService, ISilvaLocalService):

    def sendNotificationEmail(content, template_id):
        """Render the given template using content information and
        send the result to the subscribed people.
        """
