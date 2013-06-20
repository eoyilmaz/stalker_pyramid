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
import datetime

import unittest2
import transaction

from pyramid import testing
from pyramid.httpexceptions import HTTPServerError

from stalker import db, Project, Status, StatusList, Repository, Task, User
from stalker.db.session import DBSession
from zope.sqlalchemy import ZopeTransactionExtension

from stalker_pyramid.views import task, milliseconds_since_epoch


class TaskViewTestCase(unittest2.TestCase):
    """tests task view
    """

    def setUp(self):
        """setup the test
        """
        self.config = testing.setUp()
        db.setup({'sqlalchemy.url': 'sqlite:///:memory:'})

        DBSession.configure(extension=ZopeTransactionExtension)
        # with transaction.manager:
        #     model = MyModel(name='one', value=55)
        #     DBSession.add(model)

        with transaction.manager:
            # test users
            self.test_user1 = User(
                name='Test User 1',
                login='tuser1',
                email='tuser1@test.com',
                password='secret'
            )
            DBSession.add(self.test_user1)

            self.test_user2 = User(
                name='Test User 2',
                login='tuser2',
                email='tuser2@test.com',
                password='secret'
            )
            DBSession.add(self.test_user2)

            # create a couple of tasks
            self.test_status1 = Status(name='Status1', code='STS1')
            self.test_status2 = Status(name='Status2', code='STS1')
            self.test_status3 = Status(name='Status3', code='STS1')
            DBSession.add_all([
                self.test_status1, self.test_status2, self.test_status3
            ])

            self.test_project_status_list = StatusList(
                name='Project Statuses',
                target_entity_type='Project',
                statuses=[self.test_status1, self.test_status2,
                          self.test_status3]
            )
            DBSession.add(self.test_project_status_list)

            self.test_task_statuses = StatusList(
                name='Task Statuses',
                target_entity_type='Task',
                statuses=[self.test_status1, self.test_status2,
                          self.test_status3]
            )
            DBSession.add(self.test_task_statuses)

            # repository
            self.test_repo = Repository(
                name='Test Repository',
                linux_path='/mnt/T/',
                windows_path='T:/',
                osx_path='/Volumes/T/'
            )
            DBSession.add(self.test_repo)

            # proj1
            self.test_proj1 = Project(
                name='Test Project 1',
                code='TProj1',
                status_list=self.test_project_status_list,
                repository=self.test_repo,
                start=datetime.datetime(2013, 6, 20, 0, 0, 0),
                end=datetime.datetime(2013, 6, 30, 0, 0, 0)
            )
            DBSession.add(self.test_proj1)

            # root tasks
            self.test_task1 = Task(
                name='Test Task 1',
                project=self.test_proj1,
                status_list=self.test_task_statuses,
                start=datetime.datetime(2013, 6, 20, 0, 0),
                end=datetime.datetime(2013, 6, 30, 0, 0),
                schedule_model='effort',
                schedule_timing=10,
                schedule_unit='d'
            )
            DBSession.add(self.test_task1)

            self.test_task2 = Task(
                name='Test Task 2',
                project=self.test_proj1,
                status_list=self.test_task_statuses,
                start=datetime.datetime(2013, 6, 20, 0, 0),
                end=datetime.datetime(2013, 6, 30, 0, 0),
                schedule_model='effort',
                schedule_timing=10,
                schedule_unit='d'
            )
            DBSession.add(self.test_task2)

            self.test_task3 = Task(
                name='Test Task 3',
                project=self.test_proj1,
                status_list=self.test_task_statuses,
                resources=[self.test_user1, self.test_user2],
                start=datetime.datetime(2013, 6, 20, 0, 0),
                end=datetime.datetime(2013, 6, 30, 0, 0),
                schedule_model='effort',
                schedule_timing=10,
                schedule_unit='d'
            )
            DBSession.add(self.test_task3)

            # children tasks

            # children of self.test_task1
            self.test_task4 = Task(
                name='Test Task 4',
                parent=self.test_task1,
                status_list=self.test_task_statuses,
                resources=[self.test_user1],
                start=datetime.datetime(2013, 6, 20, 0, 0),
                end=datetime.datetime(2013, 6, 30, 0, 0),
                schedule_model='effort',
                schedule_timing=10,
                schedule_unit='d'
            )
            DBSession.add(self.test_task4)

            self.test_task5 = Task(
                name='Test Task 5',
                parent=self.test_task1,
                status_list=self.test_task_statuses,
                resources=[self.test_user1],
                start=datetime.datetime(2013, 6, 20, 0, 0),
                end=datetime.datetime(2013, 6, 30, 0, 0),
                schedule_model='effort',
                schedule_timing=10,
                schedule_unit='d'
            )
            DBSession.add(self.test_task5)

            self.test_task6 = Task(
                name='Test Task 6',
                parent=self.test_task1,
                status_list=self.test_task_statuses,
                resources=[self.test_user1],
                start=datetime.datetime(2013, 6, 20, 0, 0),
                end=datetime.datetime(2013, 6, 30, 0, 0),
                schedule_model='effort',
                schedule_timing=10,
                schedule_unit='d'
            )
            DBSession.add(self.test_task6)

            # children of self.test_task2
            self.test_task7 = Task(
                name='Test Task 7',
                parent=self.test_task2,
                status_list=self.test_task_statuses,
                resources=[self.test_user2],
                start=datetime.datetime(2013, 6, 20, 0, 0),
                end=datetime.datetime(2013, 6, 30, 0, 0),
                schedule_model='effort',
                schedule_timing=10,
                schedule_unit='d'
            )
            DBSession.add(self.test_task7)

            self.test_task8 = Task(
                name='Test Task 8',
                parent=self.test_task2,
                status_list=self.test_task_statuses,
                resources=[self.test_user2],
                start=datetime.datetime(2013, 6, 20, 0, 0),
                end=datetime.datetime(2013, 6, 30, 0, 0),
                schedule_model='effort',
                schedule_timing=10,
                schedule_unit='d'
            )
            DBSession.add(self.test_task8)

            # no children for self.test_task3
            self.all_tasks = [
                self.test_task1, self.test_task2, self.test_task3,
                self.test_task4, self.test_task5, self.test_task6,
                self.test_task7, self.test_task8
            ]
            new_session = DBSession()
            new_session.add_all([
                self.test_user1, self.test_user2,
                self.test_proj1
            ])

    def tearDown(self):
        DBSession.remove()
        testing.tearDown()

    def test_convert_to_jquery_gantt_task_format_tasks_is_empty(self):
        """testing if convert_to_jquery_gantt_task_format function will return
        gracefully if tasks argument is None
        """
        return_value = task.convert_to_jquery_gantt_task_format(None)
        self.assertEqual(return_value, {})

    def test_convert_to_jquery_gantt_task_format_tasks_is_not_a_list(self):
        """testing if an HTTPServerError will be raised when the tasks argument
        is not a list in convert_to_jquery_gantt_task_format function
        """
        self.assertRaises(
            HTTPServerError,
            task.convert_to_jquery_gantt_task_format,
            'not a list of task'
        )

    def test_convert_to_jquery_gantt_task_format_tasks_is_not_a_list_of_tasks(
            self):
        """testing if an HTTPServerError will be raised when the tasks argument
        is not a list of tasks in convert_to_jquery_gantt_task_format function
        """
        self.assertRaises(
            HTTPServerError,
            task.convert_to_jquery_gantt_task_format,
            ['not', 'a', 'list', 'of', 'tasks']
        )

    def test_convert_to_jquery_gantt_task_format_tasks_is_working_properly(
            self):
        """testing if task.convert_to_jquery_gantt_task_format function is
        working properly
        """
        expected_data = {
            'tasks': [
                # project 1
                {
                    'type': 'Project',
                    'id': None,
                    'code': 'TProj1',
                    'name': 'Test Project 1',
                    'start': 1371686400000,
                    'end': 1372550400000,
                    'computed_start': None,
                    'computed_end': None,
                    'schedule_model': 'duration',
                    'schedule_timing': 10,
                    'schedule_unit': 'd',
                    'parent_id': None,
                    'depend_id': [],
                    'resources': []
                },
                # task 1
                {
                    'type': 'Task',
                    'id': self.test_task1.id,
                    'name': 'Test Task 1',
                    'code': self.test_task1.id,
                    'description': '',
                    'priority': 500,
                    'status': 'STATUS_UNDEFINED',
                    'project_id': self.test_proj1.id,
                    'parent_id': self.test_proj1.id,
                    'depend_ids': [],
                    'resource_ids': [],
                    'time_log_ids': [],
                    'start': 1371686400000,
                    'end': 1372550400000,
                    'is_scheduled': False,
                    'schedule_timing': 10,
                    'schedule_unit': 'd',
                    'bid_timing': 10,
                    'bid_unit': 'd',
                    'schedule_model': 'effort',
                    'schedule_constraint': 0,
                    'schedule_seconds': 0,
                    'total_logged_seconds': 0,
                    'computed_start': None,
                    'computed_end': None,
                },
                # task 2
                {
                    'type': 'Task',
                    'id': self.test_task2.id,
                    'name': 'Test Task 2',
                    'code': self.test_task2.id,
                    'description': '',
                    'priority': 500,
                    'status': 'STATUS_UNDEFINED',
                    'project_id': self.test_proj1.id,
                    'parent_id': self.test_proj1.id,
                    'depend_ids': [],
                    'resource_ids': [],
                    'time_log_ids': [],
                    'start': 1371686400000,
                    'end': 1372550400000,
                    'is_scheduled': False,
                    'schedule_timing': 10,
                    'schedule_unit': 'd',
                    'bid_timing': 10,
                    'bid_unit': 'd',
                    'schedule_model': 'effort',
                    'schedule_constraint': 0,
                    'schedule_seconds': 0,
                    'total_logged_seconds': 0,
                    'computed_start': None,
                    'computed_end': None,
                },
                # task 3
                {
                    'type': 'Task',
                    'id': self.test_task3.id,
                    'name': 'Test Task 3',
                    'code': self.test_task3.id,
                    'description': '',
                    'priority': 500,
                    'status': 'STATUS_UNDEFINED',
                    'project_id': self.test_proj1.id,
                    'parent_id': self.test_proj1.id,
                    'depend_ids': [],
                    'resource_ids': [],
                    'time_log_ids': [],
                    'start': 1371686400000,
                    'end': 1372550400000,
                    'is_scheduled': False,
                    'schedule_timing': 10,
                    'schedule_unit': 'd',
                    'bid_timing': 10,
                    'bid_unit': 'd',
                    'schedule_model': 'effort',
                    'schedule_constraint': 0,
                    'schedule_seconds': 0,
                    'total_logged_seconds': 0,
                    'computed_start': None,
                    'computed_end': None,
                },
                # task 4
                {
                    'type': 'Task',
                    'id': self.test_task4.id,
                    'name': 'Test Task 2',
                    'code': self.test_task4.id,
                    'description': '',
                    'priority': 500,
                    'status': 'STATUS_UNDEFINED',
                    'project_id': self.test_proj1.id,
                    'parent_id': self.test_task1.id,
                    'depend_ids': [],
                    'resource_ids': [],
                    'time_log_ids': [],
                    'start': 1371686400000,
                    'end': 1372550400000,
                    'is_scheduled': False,
                    'schedule_timing': 10,
                    'schedule_unit': 'd',
                    'bid_timing': 10,
                    'bid_unit': 'd',
                    'schedule_model': 'effort',
                    'schedule_constraint': 0,
                    'schedule_seconds': 0,
                    'total_logged_seconds': 0,
                    'computed_start': None,
                    'computed_end': None,
                },
                # task 5
                {
                    'type': 'Task',
                    'id': self.test_task5.id,
                    'name': 'Test Task 5',
                    'code': self.test_task5.id,
                    'description': '',
                    'priority': 500,
                    'status': 'STATUS_UNDEFINED',
                    'project_id': self.test_proj1.id,
                    'parent_id': self.test_task1.id,
                    'depend_ids': [],
                    'resource_ids': [],
                    'time_log_ids': [],
                    'start': 1371686400000,
                    'end': 1372550400000,
                    'is_scheduled': False,
                    'schedule_timing': 10,
                    'schedule_unit': 'd',
                    'bid_timing': 10,
                    'bid_unit': 'd',
                    'schedule_model': 'effort',
                    'schedule_constraint': 0,
                    'schedule_seconds': 0,
                    'total_logged_seconds': 0,
                    'computed_start': None,
                    'computed_end': None,
                },
                # task 6
                {
                    'type': 'Task',
                    'id': self.test_task6.id,
                    'name': 'Test Task 6',
                    'code': self.test_task6.id,
                    'description': '',
                    'priority': 500,
                    'status': 'STATUS_UNDEFINED',
                    'project_id': self.test_proj1.id,
                    'parent_id': self.test_task1.id,
                    'depend_ids': [],
                    'resource_ids': [],
                    'time_log_ids': [],
                    'start': 1371686400000,
                    'end': 1372550400000,
                    'is_scheduled': False,
                    'schedule_timing': 10,
                    'schedule_unit': 'd',
                    'bid_timing': 10,
                    'bid_unit': 'd',
                    'schedule_model': 'effort',
                    'schedule_constraint': 0,
                    'schedule_seconds': 0,
                    'total_logged_seconds': 0,
                    'computed_start': None,
                    'computed_end': None,
                },
                # task 7
                {
                    'type': 'Task',
                    'id': self.test_task7.id,
                    'name': 'Test Task 7',
                    'code': self.test_task7.id,
                    'description': '',
                    'priority': 500,
                    'status': 'STATUS_UNDEFINED',
                    'project_id': self.test_proj1.id,
                    'parent_id': self.test_task2.id,
                    'depend_ids': [],
                    'resource_ids': [],
                    'time_log_ids': [],
                    'start': 1371686400000,
                    'end': 1372550400000,
                    'is_scheduled': False,
                    'schedule_timing': 10,
                    'schedule_unit': 'd',
                    'bid_timing': 10,
                    'bid_unit': 'd',
                    'schedule_model': 'effort',
                    'schedule_constraint': 0,
                    'schedule_seconds': 0,
                    'total_logged_seconds': 0,
                    'computed_start': None,
                    'computed_end': None,
                },
                # task 8
                {
                    'type': 'Task',
                    'id': self.test_task8.id,
                    'name': 'Test Task 8',
                    'code': self.test_task8.id,
                    'description': '',
                    'priority': 500,
                    'status': 'STATUS_UNDEFINED',
                    'project_id': self.test_proj1.id,
                    'parent_id': self.test_task1.id,
                    'depend_ids': [],
                    'resource_ids': [],
                    'time_log_ids': [],
                    'start': 1371686400000,
                    'end': 1372550400000,
                    'is_scheduled': False,
                    'schedule_timing': 10,
                    'schedule_unit': 'd',
                    'bid_timing': 10,
                    'bid_unit': 'd',
                    'schedule_model': 'effort',
                    'schedule_constraint': 0,
                    'schedule_seconds': 0,
                    'total_logged_seconds': 0,
                    'computed_start': None,
                    'computed_end': None,
                }
            ],
            'resources': [
                {'id': self.test_user1.id,
                 'name': self.test_user1.name},
                {'id': self.test_user2.id,
                 'name': self.test_user2.name},
            ],
            'time_logs': [],
            'timing_resolution': 60000,
            'working_hours': {
                'mon': [[540, 1080]],
                'tue': [[540, 1080]],
                'wed': [[540, 1080]],
                'thu': [[540, 1080]],
                'fri': [[540, 1080]],
                'sat': [],
                'sun': []
            },
            'daily_working_hours': 9,
            'weekly_working_hours': 45,
            'weekly_working_days': 5,
            'yearly_working_days': 260.714
        }

        data = task.convert_to_jquery_gantt_task_format(self.all_tasks)
        self.maxDiff = None
        self.assertEqual(
            data,
            expected_data
        )

        def test_create_task_dialog(self):
            """testing if the create_task_dialog view is working properly
            """
            request = testing.DummyRequest()
            request.params['']
            info = task.create_task_dialog(request)
            self.assertEqual(info['one'].name, 'one')
            self.assertEqual(info['project'], 'stalker')
