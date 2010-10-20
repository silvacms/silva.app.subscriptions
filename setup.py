# -*- coding: utf-8 -*-
# Copyright (c) 2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

from setuptools import setup, find_packages
import os

version = '1.0'

tests_require = [
    'Products.Silva [test]',
    ]

setup(name='silva.app.subscriptions',
      version=version,
      description="Let people subscribe to content changes",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      classifiers=[
        "Framework :: Zope2",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='silva app redirect permanent http',
      author='Sylvain Viollon',
      author_email='info@infrae.com',
      url='http://infrae.com/products/silva',
      license='BSD',
      package_dir={'': 'src'},
      packages=find_packages('src', exclude=['ez_setup']),
      namespace_packages=['silva', 'silva.app'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
        'Products.Silva',
        'five.grok',
        'megrok.chameleon',
        'setuptools',
        'silva.captcha',
        'silva.core.conf',
        'silva.core.interfaces',
        'silva.core.references',
        'silva.core.services',
        'silva.core.views',
        'silva.translations',
        'z3c.schema',
        'zeam.form.silva',
        'zope.component',
        'zope.interface',
        'zope.lifecycleevent',
        ],
      tests_require = tests_require,
      extras_require = {'test': tests_require},
      )
