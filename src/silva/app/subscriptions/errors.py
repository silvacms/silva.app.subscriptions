# -*- coding: utf-8 -*-
# Copyright (c) 2002-2012 Infrae. All rights reserved.
# See also LICENSE.txt


class SubscriptionError(Exception):
    pass


class CancellationError(Exception):
    pass


class InvalidEmailaddressError(Exception):
    pass


class NotSubscribableError(Exception):
    pass


class AlreadySubscribedError(Exception):
    # NOTE: Please make sure in the UI code not to expose any information
    # about the validity of the email address!
    pass


class NotSubscribedError(Exception):
    # NOTE: Please make sure in the UI code not to expose any information
    # about the validity of the email address!
    pass
