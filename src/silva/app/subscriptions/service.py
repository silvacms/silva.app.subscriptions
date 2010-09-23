# Copyright (c) 2002-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

# Python
import urllib
import logging

# Zope
from AccessControl import ClassSecurityInfo
from App.class_init import InitializeClass
from OFS import Folder

# Silva
from Products.Silva import SilvaPermissions
from Products.Silva import MAILDROPHOST_AVAILABLE, MAILHOST_ID
from Products.Silva.mail import sendmail
from Products.Silva.install import add_helper, fileobject_add_helper

from five import grok
from zope import interface, schema
from silva.app.subscriptions import errors
from silva.app.subscriptions.interfaces import (
    ISubscriptionService, ISubscriptionManager)
from silva.core import conf as silvaconf
from silva.core.interfaces import IHaunted, IVersionedContent
from silva.core.interfaces.events import IContentPublishedEvent
from silva.core.references.reference import get_content_id, get_content_from_id
from silva.core.services.base import SilvaService
from silva.translations import translate as _
from z3c.schema.email import isValidMailAddress
from zeam.form import silva as silvaforms
from zope.component import queryUtility
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
    _fromaddress = 'Silva Subscription Service <subscription-service@example.com>'

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
        adapted = ISubscriptionManager(content, None)
        # see if content is subscribable
        if adapted is None or not adapted.is_subscribable():
            raise errors.NotSubscribableError()
        # validate address
        if not isValidMailAddress(email):
            raise errors.InvalidEmailaddressError()
        # generate confirmation token using adapter
        token = adapted.generate_token(email)
        # check if not yet subscribed
        subscription = adapted.get_subscription(email)
        if subscription is not None:
            # send an email informing about this situation
            self._sendSuperfluousSubscriptionRequestEmail(
                content, email, token, 'already_subscribed_template',
                'confirm_subscription', subscription.content)
            raise errors.AlreadySubscribedError()
        # send confirmation email to emailaddress
        self._send_confirmation(
            content, content, email, token,
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
            self._sendSuperfluousCancellationRequestEmail(
                content, email, 'not_subscribed_template')
            raise errors.NotSubscribedError()
        # generate confirmation token using adapter
        token = subscription.manager.generate_token(email)
        # send confirmation email to emailaddress
        self._send_confirmation(
            content, subscription.content, email, token,
            'cancellation_confirmation_template', 'confirm_cancellation')

    # Called from subscription confirmation UI

    security.declareProtected(SilvaPermissions.View, 'subscribe')
    def subscribe(self, ref, emailaddress, token):
        # Check and confirm subscription
        # NOTE: no doc string, so, not *publishable* TTW
        #
        context = get_content_from_id(ref)
        assert context is not None, u'Invalid content'
        manager = ISubscriptionManager(context, None)
        if manager is None:
            raise errors.NotSubscribableError()
        emailaddress = urllib.unquote(emailaddress)
        if not manager.validate_token(emailaddress, token):
            raise errors.SubscriptionError()
        manager.subscribe(emailaddress)

    security.declareProtected(SilvaPermissions.View, 'unsubscribe')
    def unsubscribe(self, ref, email, token):
        # Check and confirm cancellation
        # NOTE: no doc string, so, not *publishable* TTW
        #
        context = get_content_from_id(ref)
        assert context is not None, u'Invalid content'
        manager = ISubscriptionManager(context, None)
        if manager is None:
            raise errors.CancellationError()
        email = urllib.unquote(email)
        if not manager.validate_token(email, token):
            raise errors.CancellationError()
        manager.unsubscribe(email)

    # Helpers

    def _metadata(self, content, setname, fieldname):
        metadata_service = content.service_metadata
        version = content.get_viewable()
        value = metadata_service.getMetadataValue(version, setname, fieldname)
        if type(value) == type(u''):
            value = value.encode('utf-8')
        return value

    security.declarePrivate('sendNotificationEmail')
    def send_notification(
        self, content, template_id='publication_event_template'):
        if not self.are_subscriptions_enabled():
            return
        if not template_id in self.objectIds():
            logger.error("Missing template %s for notification on %s." % (
                    template_id, repr(content)))
            return
        data = {}
        data['contenturl'] = content.absolute_url()
        data['contenttitle'] = content.get_title().encode('utf-8')
        data['subject'] = self._metadata(content, 'silva-extra', 'subject')
        data['description'] = self._metadata(content, 'silva-extra', 'content_description')
        template = str(self[template_id])
        manager = ISubscriptionManager(content)
        for subscription in manager.get_subscriptions():
            content_url = subscription.content.absolute_url()
            data['subscribedcontenturl'] =  content_url
            data['serviceurlforsubscribedcontent'] = \
                content_url + '/subscriptions.html'
            data['toaddress'] = subscription.email
            self._send_email(template, data)

    def _get_default_data(self, content, email):
        data = {}
        data['fromaddress'] = self._fromaddress
        data['toaddress'] = email
        data['contenturl'] = content.absolute_url()
        data['contenttitle'] = content.get_title().encode('utf-8')
        return data

    def _sendSuperfluousCancellationRequestEmail(self, content, email, template_id):
        template = str(self[template_id])
        data = self._get_default_data(content, email)
        self._send_email(template, data)

    def _sendSuperfluousSubscriptionRequestEmail(
        self, content, email, token, template_id, action, subscribed_content):
        template = str(self[template_id])
        data = self._get_default_data(content, email)
        data['confirmationurl'] = '%s/subscriptions.html/@@%s?%s' % (
            content.absolute_url(), action, urllib.urlencode((
                ('content', get_content_id(content)),
                ('email', urllib.quote(email)),
                ('token', token)),))
        subscribed_url = subscribed_content.absolute_url()
        data['subscribedcontenturl'] = subscribed_url
        data['serviceurlforsubscribedcontent'] = subscribed_url + '/subscriptions.html'
        self._send_email(template, data)

    def _send_confirmation(
        self, content, subscribed_content, email, token, template_id, action):
        template = str(self[template_id])
        data = self._get_default_data(content, email)
        data['confirmationurl'] = '%s/subscriptions.html/@@%s?%s' % (
            subscribed_content.absolute_url(), action, urllib.urlencode((
                    ('content', get_content_id(subscribed_content)),
                    ('email', urllib.quote(email)),
                    ('token', token)),))
        self._send_email(template, data)

    def _send_email(self, template, data):
        message = template % data
        sendmail(self, message)


InitializeClass(SubscriptionService)


class ISubscriptionSettings(interface.Interface):
    _fromaddress = schema.TextLine(
        title=_(u"From address"),
        description=_(u"Address used to send notification emails"),
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
    description = _(u"Modify generic settings")
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
    for identifier in [
        'subscription_confirmation_template',
        'already_subscribed_template',
        'cancellation_confirmation_template',
        'not_subscribed_template',
        'publication_event_template']:
        add_helper(
            service, identifier, globals(), fileobject_add_helper, True)


@grok.subscribe(IVersionedContent, IContentPublishedEvent)
def content_published(content, event):
    """Content have been published. Send notifications.
    """
    service = queryUtility(ISubscriptionService)
    if service is not None:
        # first send notification for content
        service.send_notification(content)
        # now send email for potential haunting ghosts
        for haunting in IHaunted(content).getHauting():
            service.send_notification(haunting)
