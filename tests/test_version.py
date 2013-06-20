# -*- coding: utf-8 -*-
# Stalker Pyramid a Web Base Production Asset Management System
# Copyright (C) 2009-2013 Erkan Ozgur Yilmaz
#
# This file is part of Stalker Pyramid.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA

import unittest
import transaction

from pyramid import testing

from stalker import db
from stalker.db.session import DBSession
from zope.sqlalchemy import ZopeTransactionExtension


class VersionViewTestCase(unittest.TestCase):
    """tests version view
    """
    def setUp(self):
        """setup the test
        """
        self.config = testing.setUp()
        db.setup({'sqlalchemy.url': 'sqlite:///:memory:'})

        DBSession.configure(extension=ZopeTransactionExtension())
        # with transaction.manager:
        #     model = MyModel(name='one', value=55)
        #     DBSession.add(model)

    def tearDown(self):
        DBSession.remove()
        testing.tearDown()

    def test_create_version_dialog(self):
        from stalker_pyramid.views.version import create_version_dialog
        request = testing.DummyRequest()
        info = create_version_dialog(request)
        self.assertEqual(info['one'].name, 'one')
        self.assertEqual(info['project'], 'stalker')
