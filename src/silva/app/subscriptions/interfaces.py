# -*- coding: utf-8 -*-
# Copyright (c) 2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$


from silva.core.interfaces import ISilvaService, ISilvaLocalService

# Subscription modes
NOT_SUBSCRIBABLE = 0
SUBSCRIBABLE = 1
ACQUIRE_SUBSCRIBABILITY = 2


class ISubscriptionService(ISilvaService, ISilvaLocalService):

    def sendNotificationEmail(content, template_id):
        """Render the given template using content information and
        send the result to the subscribed people.
        """
