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
import os
import tempfile

import unittest2

from pyramid import testing
from pyramid.security import remember

from stalker import (defaults, db, Project, Repository, Status, StatusList,
                     Task, User, Version)
from stalker.db.session import DBSession
import transaction
from zope.sqlalchemy import ZopeTransactionExtension
from stalker_pyramid.views import PermissionChecker


class VersionViewTestCase(unittest2.TestCase):
    """tests version view
    """

    def setUp(self):
        """setup the test
        """
        self.config = testing.setUp()
        db.setup({'sqlalchemy.url': 'sqlite:///:memory:'})

        DBSession.configure(extension=ZopeTransactionExtension())

        with transaction.manager:
            self.test_repo = Repository(
                name='Test Repository',
                linux_path=tempfile.mkdtemp(),
                windows_path=tempfile.mkdtemp(),
                osx_path=tempfile.mkdtemp()
            )
            DBSession.add(self.test_repo)

            self.status1 = Status(name='Status1', code='STS1')
            self.status2 = Status(name='Status2', code='STS2')
            self.status3 = Status(name='Status3', code='STS3')
            self.status4 = Status(name='Status4', code='STS4')
            self.status5 = Status(name='Status5', code='STS5')
            DBSession.add_all([self.status1, self.status2, self.status3,
                               self.status4, self.status5])

            self.test_project_status_list = StatusList(
                name='Project Statuses',
                statuses=[self.status1, self.status2, self.status3, self.status4,
                          self.status5],
                target_entity_type='Project'
            )
            DBSession.add(self.test_project_status_list)

            self.test_task_status_list = StatusList(
                name='Task Statuses',
                statuses=[self.status1, self.status2, self.status3, self.status4,
                          self.status5],
                target_entity_type='Task'
            )
            DBSession.add(self.test_task_status_list)

            self.test_version_status_list = StatusList(
                name='Version Statuses',
                statuses=[self.status1, self.status2, self.status3, self.status4,
                          self.status5],
                target_entity_type='Version'
            )
            DBSession.add(self.test_task_status_list)

            # create a project
            self.test_project = Project(
                name='Test Project',
                code='TP',
                repository=self.test_repo,
                status_list=self.test_project_status_list
            )
            DBSession.add(self.test_project)

            # create a task
            self.test_task = Task(
                project=self.test_project,
                name='Test Task',
                status_list=self.test_task_status_list
            )
            DBSession.add(self.test_task)

            # create a test version
            self.test_version = Version(
                task=self.test_task,
                status_list=self.test_version_status_list
            )
            DBSession.add(self.test_version)

        DBSession.add_all([
            self.test_project, self.test_project_status_list,
            self.test_repo, self.test_task, self.test_task_status_list,
            self.test_version
        ])

    def tearDown(self):
        os.rmdir(self.test_repo.linux_path)
        os.rmdir(self.test_repo.windows_path)
        os.rmdir(self.test_repo.osx_path)

        DBSession.remove()
        testing.tearDown()
        # remove the temp dirs

    def test_create_version_dialog(self):
        """testing if update_version_dialog returns the correct parameters
        """
        from stalker_pyramid.views.version import create_version_dialog
        request = testing.DummyRequest()
        # login
        remember(request, defaults.admin_login)
        request.matchdict['id'] = self.test_task.id

        info = create_version_dialog(request)
        self.assertEqual(info['mode'], 'CREATE')
        self.assertIsInstance(info['has_permission'], PermissionChecker)
        self.assertEqual(info['default_take_name'], defaults.version_take_name)
        self.assertEqual(info['take_names'], [defaults.version_take_name])
        # self.assertIsInstance(info['logged_in_user'], User)
        self.assertEqual(info['task'], self.test_task)

    def test_update_version_dialog(self):
        """testing if update_version_dialog returns the correct parameters
        """
        from stalker_pyramid.views.version import update_version_dialog
        request = testing.DummyRequest()

        # versions/{id}/update/dialog
        request.matchdict['id'] = self.test_version.id

        info = update_version_dialog(request)
        self.assertEqual(info['mode'], 'UPDATE')
        self.assertEqual(info['version'], self.test_version)
        self.assertIsInstance(info['has_permission'], PermissionChecker)

    def test_create_version(self):
        """testing if create_version creates a version properly
        """
        self.fail('test is not implemented yet')

    def test_update_version(self):
        """testing if update_version updates the version properly
        """
        self.fail('test is not implemented yet')

