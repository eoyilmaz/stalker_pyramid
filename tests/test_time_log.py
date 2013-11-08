# -*- coding: utf-8 -*-
#
# Stalker Pyramid Copyright (C) 2013 Erkan Ozgur Yilmaz
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
import datetime

import unittest2
import transaction

from pyramid import testing
from stalker import db, User, Status, StatusList, Repository, Project, Task
from stalker.db import DBSession
from stalker_pyramid.views import time_log, milliseconds_since_epoch


class TimeLogViewTestCase(unittest2.TestCase):
    """tests the time log view
    """

    def setUp(self):
        """setup the test
        """
        self.config = testing.setUp()
        db.setup({'sqlalchemy.url': 'sqlite:///:memory:'})
        db.init()

        DBSession.remove()
        # test users
        self.user1 = User(
            name='Test User 1',
            login='tuser1',
            email='tuser1@test.com',
            password='secret'
        )
        DBSession.add(self.user1)

        # create a couple of tasks
        self.status1 = Status(name='New', code='NEW')
        self.status2 = Status(name='Work In Progress', code='WIP')
        self.status3 = Status(name='Pending Review', code='PREV')
        self.status4 = Status(name='Has Revisions', code='HREV')
        self.status5 = Status(name='Complete', code='CMPL')

        self.project_status_list = StatusList(
            name='Project Statuses',
            target_entity_type='Project',
            statuses=[self.status1, self.status2, self.status5]
        )
        DBSession.add(self.project_status_list)

        self.task_status_list = StatusList(
            name='Task Statuses',
            target_entity_type='Task',
            statuses=[self.status1, self.status2, self.status3,
                      self.status4, self.status5]
        )
        DBSession.add(self.task_status_list)

        # repo
        self.repo = Repository(
            name='Test Repository'
        )
        DBSession.add(self.repo)

        # proj1
        self.proj1 = Project(
            name='Test Project',
            code='TProj1',
            status_list=self.project_status_list,
            repository=self.repo,
            lead=self.user1
        )
        DBSession.add(self.proj1)

        # tasks
        self.task1 = Task(
            name='Test Task 1',
            project=self.proj1,
            status_list=self.task_status_list,
            status=self.status1,
            resources=[self.user1],
            schedule_timing=5,
            schedule_unit='d',
            schedule_model='effort'
        )
        DBSession.add(self.task1)
        transaction.commit()

    def tearDown(self):
        DBSession.remove()
        testing.tearDown()

    def test_creating_a_time_log_for_a_new_task(self):
        """testing if the status of the time log will be set to WIP if a time
        log has been created to that task for that task
        """
        request = testing.DummyRequest()
        self.task1 = Task.query.filter(Task.name == self.task1.name).first()
        request.params['task_id'] = self.task1.id
        request.params['resource_id'] = self.task1.resources[0].id
        request.params['start'] = "Fri, 01 Nov 2013 08:00:00 GMT"
        request.params['end'] = "Fri, 01 Nov 2013 17:00:00 GMT"

        self.assertEqual(self.task1.status, self.status1)
        time_log.create_time_log(request)
        self.assertEqual(self.task1.status, self.status2)

    def test_creating_a_time_log_for_a_task_whose_dependending_tasks_already_has_time_logs(self):
        """testing if a HTTPServer error will be raised when a time log tried
        to be for a task whose depending tasks already has time logs created
        (This test should be in Stalker)
        """
        # create a new task
        task2 = Task(
            name='Test Task 2',
            project=self.proj1,
            depends=[self.task1],
            resources=[self.user1],
            schedule_timing=4,
            schedule_unit= 'd',
            schedule_model='effort',
            status_list=self.task_status_list
        )
        DBSession.add(task2)
        DBSession.flush()
        transaction.commit()

        # set the status of task1 to complete
        self.task1.status = self.status5
        DBSession.flush()
        transaction.commit()

        # and now create time logs for task2
        request = testing.DummyRequest()
        request.params['task_id'] = task2.id
        request.params['resource_id'] = self.user1.id
        request.params['start'] = "Fri, 01 Nov 2013 08:00:00 GMT"
        request.params['end'] = "Fri, 01 Nov 2013 17:00:00 GMT"
        response = time_log.create_time_log(request)
        self.assertEqual(response.status_int, 200)
        DBSession.add(task2)
        DBSession.flush()
        transaction.commit()

        # now because task2 is depending on to the task1
        # and task2 has now started, entering any new time logs to task1
        # is forbidden
        request = testing.DummyRequest()
        request.params['task_id'] = self.task1.id
        request.params['resource_id'] = self.user1.id
        request.params['start'] = "Fri, 02 Nov 2013 08:00:00 GMT"
        request.params['end'] = "Fri, 02 Nov 2013 17:00:00 GMT"

        response = time_log.create_time_log(request)
        self.assertEqual(
            response.status_int, 500
        )

    def test_creating_a_time_log_for_a_task_whose_dependent_tasks_has_not_finished_yet(self):
        """testing if a HTTPServer error will be raised when a time log tried
        to be created for a Task whose dependent tasks has not finished yet
        """
        # create a new task
        task2 = Task(
            name='Test Task 2',
            project=self.proj1,
            depends=[self.task1],
            resources=[self.user1],
            schedule_timing=4,
            schedule_unit='d',
            schedule_model='effort',
            status_list=self.task_status_list
        )
        DBSession.add(task2)
        DBSession.flush()
        transaction.commit()

        # now because task2 is depending on to the task1
        # and task1 is not finished yet (where the status is not
        # set to Complete, we should expect an HTTPServerError()
        # to be raised
        request = testing.DummyRequest()
        request.params['task_id'] = task2.id
        request.params['resource_id'] = self.user1.id
        request.params['start'] = "Fri, 01 Nov 2013 08:00:00 GMT"
        request.params['end'] = "Fri, 01 Nov 2013 17:00:00 GMT"

        response = time_log.create_time_log(request)
        self.assertEqual(
            response.status_int, 500
        )
