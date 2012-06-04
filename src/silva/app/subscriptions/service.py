# Copyright (c) 2002-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

# Python
from datetime import datetime
import time
import urllib
import logging

# Zope
from AccessControl import ClassSecurityInfo
from Acquisition import aq_base
from App.class_init import InitializeClass
from OFS import Folder

# Silva
from Products.Silva import SilvaPermissions
from Products.Silva import MAILDROPHOST_AVAILABLE, MAILHOST_ID
from Products.Silva.mail import sendmail
from Products.Silva.install import add_helper, pt_add_helper

from five import grok
from zope import interface, schema
from silva.app.subscriptions import errors
from silva.app.subscriptions.interfaces import (
    ISubscriptionService, ISubscriptionManager)
from silva.core import conf as silvaconf
from silva.core.interfaces import IHaunted, IVersion, IPublishable
from silva.core.interfaces.events import IContentPublishedEvent
from silva.core.layout.interfaces import IMetadata
from silva.core.references.reference import get_content_id, get_content_from_id
from silva.core.services.base import SilvaService
from silva.core.services.interfaces import ISecretService
from silva.translations import translate as _
from z3c.schema.email import isValidMailAddress
from zeam.form import silva as silvaforms
from zope.component import queryUtility, getUtility
from zope.lifecycleevent.interfaces import IObjectCreatedEvent

logger = logging.getLogger('silva.app.subscriptions')


class SubscriptionService(Folder.Folder, SilvaService):
    """Subscription Service
    """
    grok.implements(ISubscriptionService)
    default_service_identifier = 'service_subscriptions'

    meta_type = "Silva Subscription Service"
    silvaconf.icon('service.png')

    manage_options = (
        {'label':'Settings', 'action':'manage_settings'},
        ) + Folder.Folder.manage_options

    security = ClassSecurityInfo()

    # subscriptions are disabled by default
    _enabled = False
    _from = 'Subscription Service <subscription-service@example.com>'
    _sitename = 'Silva'
    _maximum_delay = 3

    # ZMI methods

    security.declareProtected(
        SilvaPermissions.ViewManagementScreens, 'enable_subscriptions')
    def enable_subscriptions(self):
        self._enabled = True

    security.declareProtected(
        SilvaPermissions.ViewManagementScreens, 'disable_subscriptions')
    def disable_subscriptions(self):
        self._enabled = False

    security.declareProtected(SilvaPermissions.View, 'are_subscriptions_enabled')
    def are_subscriptions_enabled(self, context=None):
        if not self._enabled:
            return False
        if context is not None:
            manager = ISubscriptionManager(context, None)
            if manager is None:
                return False
            return manager.is_subscribable()
        return True

    # Called from subscription UI

    security.declareProtected(SilvaPermissions.View, 'request_subscription')
    def request_subscription(self, content, email):
        # Send out request for subscription
        # NOTE: no doc string, so, not *publishable* TTW
        #
        if not self.are_subscriptions_enabled():
            raise errors.NotSubscribableError()

        manager = ISubscriptionManager(content, None)
        # see if content is subscribable
        if manager is None or not manager.is_subscribable():
            raise errors.NotSubscribableError()

        # validate address
        if not isValidMailAddress(email):
            raise errors.InvalidEmailaddressError()

        # check if not yet subscribed
        subscription = manager.get_subscription(email)
        if subscription is not None:
            # send an email informing about this situation
            self._send_confirmation(
                content, subscription.content, email,
                'already_subscribed_template', 'confirm_subscription')
            raise errors.AlreadySubscribedError()

        # send confirmation email to emailaddress
        self._send_confirmation(
            content, content, email,
            'subscription_confirmation_template', 'confirm_subscription')

    security.declareProtected(SilvaPermissions.View, 'request_cancellation')
    def request_cancellation(self, content, email):
        # Send out request for cancellation of the subscription
        # NOTE: no doc string, so, not *publishable* TTW
        #
        manager = ISubscriptionManager(content, None)
        if manager is None:
            raise errors.NotSubscribableError()
        # validate address
        if not isValidMailAddress(email):
            raise errors.InvalidEmailaddressError()

        # check if indeed subscribed
        subscription = manager.get_subscription(email)
        if subscription is None:
            # send an email informing about this situation
            self._send_information(content, email, 'not_subscribed_template')
            raise errors.NotSubscribedError()

        self._send_confirmation(
            content, subscription.content, email,
            'cancellation_confirmation_template', 'confirm_cancellation')

    # Called from subscription confirmation UI

    security.declareProtected(SilvaPermissions.View, 'subscribe')
    def subscribe(self, content_id, email, token):
        # Check and confirm subscription
        # NOTE: no doc string, so, not *publishable* TTW
        #
        content = get_content_from_id(content_id)
        assert content is not None, u'Invalid content'
        manager = ISubscriptionManager(content, None)
        if manager is None:
            raise errors.NotSubscribableError()
        email = urllib.unquote(email)
        if not self._validate_token(
            content_id, email, 'confirm_subscription', token):
            raise errors.SubscriptionError()
        manager.subscribe(email)

    security.declareProtected(SilvaPermissions.View, 'unsubscribe')
    def unsubscribe(self, content_id, email, token):
        # Check and confirm cancellation
        # NOTE: no doc string, so, not *publishable* TTW
        #
        content = get_content_from_id(content_id)
        assert content is not None, u'Invalid content'
        manager = ISubscriptionManager(content, None)
        if manager is None:
            raise errors.CancellationError()
        email = urllib.unquote(email)
        if not self._validate_token(
            content_id, email, 'confirm_cancellation', token):
            raise errors.CancellationError()
        manager.unsubscribe(email)

    security.declarePrivate('send_notification')
    def send_notification(
        self, content, template_id='publication_event_template'):
        if not self.are_subscriptions_enabled():
            return
        template = self._get_template(content, template_id)
        data = self._get_default_data(content)
        manager = ISubscriptionManager(content)
        for subscription in manager.get_subscriptions():
            content_url = subscription.content.absolute_url()
            data['subscribed_content'] = subscription.content
            data['service_url'] = content_url + '/subscriptions.html'
            data['to'] = subscription.email
            self._send_email(template, data)

    def _generate_token(self, content_id, email, action):
        secret = getUtility(ISecretService)
        now = str(int(time.time()))
        key = secret.digest(content_id, email, now, action)
        return ':'.join((now, key)).encode('base64').strip()

    def _validate_token(self, content_id, email, action, token):
        try:
            token = token.decode('base64')
            if ':' not in token:
                return False
            query_date, query_key = token.split(':')
            delay = datetime.now() - datetime.fromtimestamp(int(query_date))
            if delay.days > self._maximum_delay:
                return False
            secret = getUtility(ISecretService)
            key = secret.digest(content_id, email, query_date, action)
            return query_key == key
        except:
            return False

    def _get_template(self, content, template_id):
        if not template_id in self.objectIds():
            logger.error("Missing template %s for notification on %s." % (
                    template_id, repr(content)))
            raise KeyError(template_id)
        return aq_base(self[template_id]).__of__(content)

    def _get_default_data(self, content, email=None):
        data = {}
        data['from'] = self._from
        data['to'] = email
        data['metadata'] = IMetadata(content)
        data['sitename'] = self._sitename
        data['confirmation_delay'] = self._maximum_delay
        return data

    def _send_information(self, content, email, template_id):
        template = self._get_template(content, template_id)
        data = self._get_default_data(content, email)
        self._send_email(template, data)

    def _send_confirmation(
        self, content, subscribed_content, email, template_id, action):
        template = self._get_template(content, template_id)
        data = self._get_default_data(content, email)
        subscribed_content_url = subscribed_content.absolute_url()
        subscribed_content_id = get_content_id(subscribed_content)
        token = self._generate_token(subscribed_content_id, email, action)
        data['confirmation_url'] = '%s/subscriptions.html/@@%s?%s' % (
            subscribed_content_url, action, urllib.urlencode((
                    ('content', subscribed_content_id),
                    ('email', urllib.quote(email)),
                    ('token', token)),))
        data['subscribed_content'] = subscribed_content
        data['service_url'] = subscribed_content_url + '/subscriptions.html'
        self._send_email(template, data)

    def _send_email(self, template, data):
        message = template(**data)
        sendmail(self, message)


InitializeClass(SubscriptionService)


class ISubscriptionSettings(interface.Interface):
    _from = schema.TextLine(
        title=_(u"From address"),
        description=_(u"Email address used to send notification emails"),
        required=True)
    _sitename = schema.TextLine(
        title=_(u"Service name"),
        description=_(u"Service name to report in notification emails"),
        required=True)
    _maximum_delay = schema.Int(
        title=_(u"Maximum confirmation delay in days"),
        description=_(u"When a confirmation email is sent, "
                      u"it must be validated within that number of days"),
        required=True)


class SubscriptionServiceManagementView(silvaforms.ZMIComposedForm):
    """Edit File Serivce.
    """
    grok.require('zope2.ViewManagementScreens')
    grok.name('manage_settings')
    grok.context(SubscriptionService)

    label = _(u"Service Subscriptions Configuration")


class SubscriptionServiceActivateForm(silvaforms.ZMISubForm):
    grok.context(SubscriptionService)
    silvaforms.view(SubscriptionServiceManagementView)
    silvaforms.order(20)

    label = _(u"Activate subscriptions")
    description = _(u"Activate sending emails notifications")

    def available(self):
        return not self.context.are_subscriptions_enabled()

    @silvaforms.action(_(u'Activate'))
    def action_activate(self):
        self.context.enable_subscriptions()
        self.status = _(u"Subscriptions activated.")
        return silvaforms.SUCCESS


class SubscriptionServiceOptionForm(silvaforms.ZMISubForm):
    grok.context(SubscriptionService)
    silvaforms.view(SubscriptionServiceManagementView)
    silvaforms.order(30)

    label = _(u"Configure subscriptions")
    description = _(u"Modify email notification settings")
    ignoreContent = False
    fields = silvaforms.Fields(ISubscriptionSettings)
    actions = silvaforms.Actions(silvaforms.EditAction())


class SubscriptionServiceDisableForm(silvaforms.ZMISubForm):
    grok.context(SubscriptionService)
    silvaforms.view(SubscriptionServiceManagementView)
    silvaforms.order(20)

    label = _(u"Disable subscriptions")
    description = _(u"Disable sending emails notifications")

    def available(self):
        return self.context.are_subscriptions_enabled()

    @silvaforms.action(_(u'Disable'))
    def action_disable(self):
        self.context.disable_subscriptions()
        self.status = _(u"Subscriptions disabled.")
        return silvaforms.SUCCESS


class SubscriptionServiceInstallMaildropHostForm(silvaforms.ZMISubForm):
    grok.context(SubscriptionService)
    silvaforms.view(SubscriptionServiceManagementView)
    silvaforms.order(40)

    label = _(u"Install MaildropHost")
    description = _(u"Install a MaildropHost service to send emails")

    def is_installable(self):
        if not MAILDROPHOST_AVAILABLE:
            return False
        root = self.context.get_root()
        mailhost =  getattr(root, MAILHOST_ID, None)
        return mailhost is None or mailhost.meta_type != 'Maildrop Host'

    def available(self):
        return self.status or self.is_installable()

    @silvaforms.action(
        _(u'Install'),
        available=lambda form:form.is_installable())
    def action_install(self):
        root = self.context.get_root()
        if hasattr(root, MAILHOST_ID):
            root.manage_delObjects([MAILHOST_ID,])
        factory = root.manage_addProduct['MaildropHost']
        factory.manage_addMaildropHost(
            MAILHOST_ID, 'Spool based mail delivery')
        self.status = (
            u'New mailhost object installed. '
            u'The system adminstator should take care of '
            u'starting the mail delivery process.')


@grok.subscribe(ISubscriptionService, IObjectCreatedEvent)
def service_created(service, event):
    """Add all default templates to the service.
    """
    service._sitename = service.get_root().get_title_or_id()
    for identifier in [
        'subscription_confirmation_template.pt',
        'already_subscribed_template.pt',
        'cancellation_confirmation_template.pt',
        'not_subscribed_template.pt',
        'publication_event_template.pt']:
        add_helper(service, identifier, globals(), pt_add_helper, True)


@grok.subscribe(IVersion, IContentPublishedEvent)
def version_published(version, event):
    """Content have been published. Send notifications.
    """
    service = queryUtility(ISubscriptionService)
    if service is not None:
        content = version.get_silva_object()
        if IPublishable.providedBy(content):
            # first send notification for content
            service.send_notification(content)
            # now send email for potential haunting ghosts
            for haunting in IHaunted(content).getHaunting():
                service.send_notification(haunting)
