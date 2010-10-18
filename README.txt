========================
silva.core.subscriptions
========================

``silva.core.subscriptions`` let visitors subscribe to content in
order to receive notification on change. You can only subscribe to a
part of a site or a page.

Subscription registration can done via a form that is rendered inside
the public layout and protected with a Captcha if the user is not logged
in. The registration requires a validation done by email.

Managers can administrate subscribed emails.

A local service contains some generic settings and all email templates
that can be customized.

The API is extensible, and the notification can be reused by other
extensions for other purposes, they can add more email templates and
trigger their own notifications themselves.
