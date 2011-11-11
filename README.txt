========================
silva.core.subscriptions
========================

Introduction
============

``silva.core.subscriptions`` let visitors subscribe to Silva content
in order to receive notification emails on modification. You can only
subscribe to a part of the site or only to a page.

Subscription registration can be done by visitors via a form rendered
inside the public layout. If the visitor is not authenticated, the
form is protected with a Captcha. The registration requires a
validation done by email.

Site managers can directly administrate subscribed emails (add,
remove) without that validation step.

A local service contains some generic settings and all email templates
used. You can be customized them at will.

The service provides you with an API usable to develop extensions that
send notification for any wanted action or event using a custom email
template of your choice.

Code repository
===============

You can find the source code for this extension in Mercurial:
https://hg.infrae.com/silva.app.subscriptions/.
