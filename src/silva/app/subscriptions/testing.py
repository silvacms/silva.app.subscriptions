# -*- coding: utf-8 -*-
# Copyright (c) 2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

from Products.Silva.testing import SilvaLayer
import silva.app.subscriptions


class SilvaSubscriptionLayer(SilvaLayer):
    default_packages = SilvaLayer.default_packages + [
        'silva.app.subscription',
        ]


FunctionalLayer = SilvaSubscriptionLayer(
    silva.app.subscriptions, zcml_file="configure.zcml")
