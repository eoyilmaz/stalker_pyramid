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

from stalker import db, Project, Status, StatusList, Repository, Task, User, Asset, Type, defaults
from stalker.db.session import DBSession
from zope.sqlalchemy import ZopeTransactionExtension

from stalker_pyramid.views import task, PermissionChecker, milliseconds_since_epoch

import logging
logger = logging.getLogger(__name__)


class TaskViewTestCase(unittest2.TestCase):
    """tests task view
    """

    def setUp(self):
        """setup the test
        """
        self.config = testing.setUp()
        db.setup({'sqlalchemy.url': 'sqlite:///:memory:'})

        DBSession.remove()
        DBSession.configure(extension=ZopeTransactionExtension())
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

            self.test_asset_status_list = StatusList(
                statuses=[self.test_status1, self.test_status2,
                          self.test_status3],
                target_entity_type='Asset'
            )
            DBSession.add(self.test_asset_status_list)

            # create an asset in between
            self.test_asset1 = Asset(
                name='Test Asset 1',
                code='TA1',
                parent=self.test_task7,
                type=Type(
                    name='Character',
                    code='Char',
                    target_entity_type='Asset',
                ),
                status_list=self.test_asset_status_list
            )
            DBSession.add(self.test_asset1)

            # new task under asset
            self.test_task9 = Task(
                name='Test Task 9',
                parent=self.test_asset1,
                status_list=self.test_task_statuses,
                start=datetime.datetime(2013, 6, 20, 0, 0),
                end=datetime.datetime(2013, 6, 30, 0, 0),
                schedule_model='effort',
                schedule_timing=10,
                schedule_unit='d'
            )
            DBSession.add(self.test_task9)

        # no children for self.test_task3
        self.all_tasks = [
            self.test_task1, self.test_task2, self.test_task3,
            self.test_task4, self.test_task5, self.test_task6,
            self.test_task7, self.test_task8, self.test_task9,
            self.test_asset1
        ]
        new_session = DBSession()
        new_session.add_all([
            self.test_user1, self.test_user2,
            self.test_proj1
        ])
        new_session.add_all(self.all_tasks)

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

    def test_convert_to_jquery_gantt_task_format_tasks_is_not_a_list_of_tasks(self):
        """testing if an HTTPServerError will be raised when the tasks argument
        is not a list of tasks in convert_to_jquery_gantt_task_format function
        """
        self.assertRaises(
            HTTPServerError,
            task.convert_to_jquery_gantt_task_format,
            ['not', 'a', 'list', 'of', 'tasks']
        )

    def test_convert_to_jquery_gantt_task_format_tasks_is_working_properly(self):
        """testing if task.convert_to_jquery_gantt_task_format function is
        working properly
        """
        expected_data = {
            'tasks': [
                # project 1
                {
                    'type': u'Project',
                    'id': 22,
                    'code': u'TProj1',
                    'name': u'Test Project 1',
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
                    'type': u'Task',
                    'id': self.test_task1.id,
                    'hierarchy_name': '',
                    'name': u'Test Task 1',
                    'code': self.test_task1.id,
                    'description': u'',
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
                    'schedule_timing': 10.0,
                    'schedule_unit': u'd',
                    'bid_timing': 10.0,
                    'bid_unit': u'd',
                    'schedule_model': u'effort',
                    'schedule_constraint': 0,
                    'schedule_seconds': 324000.0,
                    'total_logged_seconds': 0,
                    'computed_start': None,
                    'computed_end': None,
                },
                # task 2
                {
                    'type': u'Task',
                    'id': self.test_task2.id,
                    'hierarchy_name': '',
                    'name': u'Test Task 2',
                    'code': self.test_task2.id,
                    'description': u'',
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
                    'schedule_timing': 10.0,
                    'schedule_unit': u'd',
                    'bid_timing': 10.0,
                    'bid_unit': u'd',
                    'schedule_model': u'effort',
                    'schedule_constraint': 0,
                    'schedule_seconds': 324000.0,
                    'total_logged_seconds': 0,
                    'computed_start': None,
                    'computed_end': None,
                },
                # task 3
                {
                    'type': u'Task',
                    'id': self.test_task3.id,
                    'hierarchy_name': '',
                    'name': u'Test Task 3',
                    'code': self.test_task3.id,
                    'description': u'',
                    'priority': 500,
                    'status': 'STATUS_UNDEFINED',
                    'project_id': self.test_proj1.id,
                    'parent_id': self.test_proj1.id,
                    'depend_ids': [],
                    'resource_ids': [12, 13],
                    'time_log_ids': [],
                    'start': 1371686400000,
                    'end': 1372550400000,
                    'is_scheduled': False,
                    'schedule_timing': 10.0,
                    'schedule_unit': u'd',
                    'bid_timing': 10.0,
                    'bid_unit': u'd',
                    'schedule_model': u'effort',
                    'schedule_constraint': 0,
                    'schedule_seconds': 324000.0,
                    'total_logged_seconds': 0,
                    'computed_start': None,
                    'computed_end': None,
                },
                # task 4
                {
                    'type': u'Task',
                    'id': self.test_task4.id,
                    'hierarchy_name': u'Test Task 1',
                    'name': u'Test Task 4',
                    'code': self.test_task4.id,
                    'description': u'',
                    'priority': 500,
                    'status': 'STATUS_UNDEFINED',
                    'project_id': self.test_proj1.id,
                    'parent_id': self.test_task1.id,
                    'depend_ids': [],
                    'resource_ids': [12],
                    'time_log_ids': [],
                    'start': 1371686400000,
                    'end': 1372550400000,
                    'is_scheduled': False,
                    'schedule_timing': 10.0,
                    'schedule_unit': u'd',
                    'bid_timing': 10.0,
                    'bid_unit': u'd',
                    'schedule_model': u'effort',
                    'schedule_constraint': 0,
                    'schedule_seconds': 324000.0,
                    'total_logged_seconds': 0,
                    'computed_start': None,
                    'computed_end': None,
                },
                # task 5
                {
                    'type': u'Task',
                    'id': self.test_task5.id,
                    'hierarchy_name': u'Test Task 1',
                    'name': u'Test Task 5',
                    'code': self.test_task5.id,
                    'description': u'',
                    'priority': 500,
                    'status': 'STATUS_UNDEFINED',
                    'project_id': self.test_proj1.id,
                    'parent_id': self.test_task1.id,
                    'depend_ids': [],
                    'resource_ids': [12],
                    'time_log_ids': [],
                    'start': 1371686400000,
                    'end': 1372550400000,
                    'is_scheduled': False,
                    'schedule_timing': 10.0,
                    'schedule_unit': u'd',
                    'bid_timing': 10.0,
                    'bid_unit': u'd',
                    'schedule_model': u'effort',
                    'schedule_constraint': 0,
                    'schedule_seconds': 324000.0,
                    'total_logged_seconds': 0,
                    'computed_start': None,
                    'computed_end': None,
                },
                # task 6
                {
                    'type': u'Task',
                    'id': self.test_task6.id,
                    'hierarchy_name': u'Test Task 1',
                    'name': u'Test Task 6',
                    'code': self.test_task6.id,
                    'description': u'',
                    'priority': 500,
                    'status': 'STATUS_UNDEFINED',
                    'project_id': self.test_proj1.id,
                    'parent_id': self.test_task1.id,
                    'depend_ids': [],
                    'resource_ids': [12],
                    'time_log_ids': [],
                    'start': 1371686400000,
                    'end': 1372550400000,
                    'is_scheduled': False,
                    'schedule_timing': 10.0,
                    'schedule_unit': u'd',
                    'bid_timing': 10.0,
                    'bid_unit': u'd',
                    'schedule_model': u'effort',
                    'schedule_constraint': 0,
                    'schedule_seconds': 324000.0,
                    'total_logged_seconds': 0,
                    'computed_start': None,
                    'computed_end': None,
                },
                # task 7
                {
                    'type': u'Task',
                    'id': self.test_task7.id,
                    'hierarchy_name': u'Test Task 2',
                    'name': u'Test Task 7',
                    'code': self.test_task7.id,
                    'description': u'',
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
                    'schedule_timing': 10.0,
                    'schedule_unit': u'd',
                    'bid_timing': 10.0,
                    'bid_unit': u'd',
                    'schedule_model': u'effort',
                    'schedule_constraint': 0,
                    'schedule_seconds': 324000.0,
                    'total_logged_seconds': 0,
                    'computed_start': None,
                    'computed_end': None,
                },
                # task 8
                {
                    'type': u'Task',
                    'id': self.test_task8.id,
                    'hierarchy_name': u'Test Task 2',
                    'name': u'Test Task 8',
                    'code': self.test_task8.id,
                    'description': u'',
                    'priority': 500,
                    'status': 'STATUS_UNDEFINED',
                    'project_id': self.test_proj1.id,
                    'parent_id': self.test_task2.id,
                    'depend_ids': [],
                    'resource_ids': [13],
                    'time_log_ids': [],
                    'start': 1371686400000,
                    'end': 1372550400000,
                    'is_scheduled': False,
                    'schedule_timing': 10.0,
                    'schedule_unit': u'd',
                    'bid_timing': 10.0,
                    'bid_unit': u'd',
                    'schedule_model': u'effort',
                    'schedule_constraint': 0,
                    'schedule_seconds': 324000.0,
                    'total_logged_seconds': 0,
                    'computed_start': None,
                    'computed_end': None,
                },
                # task 9
                {
                    'type': u'Task',
                    'id': self.test_task9.id,
                    'hierarchy_name': u'Test Task 2 | Test Task 7 | Test Asset 1',
                    'name': u'Test Task 9',
                    'code': self.test_task9.id,
                    'description': u'',
                    'priority': 500,
                    'status': 'STATUS_UNDEFINED',
                    'project_id': self.test_proj1.id,
                    'parent_id': self.test_asset1.id,
                    'depend_ids': [],
                    'resource_ids': [],
                    'time_log_ids': [],
                    'start': 1371686400000,
                    'end': 1372550400000,
                    'is_scheduled': False,
                    'schedule_timing': 10.0,
                    'schedule_unit': u'd',
                    'bid_timing': 10.0,
                    'bid_unit': u'd',
                    'schedule_model': u'effort',
                    'schedule_constraint': 0,
                    'schedule_seconds': 324000.0,
                    'total_logged_seconds': 0,
                    'computed_start': None,
                    'computed_end': None,
                },
                # test asset 1
                {
                    'type': u'Asset',
                    'id': self.test_asset1.id,
                    'hierarchy_name': u'Test Task 2 | Test Task 7',
                    'name': u'Test Asset 1',
                    'code': self.test_asset1.id,
                    'description': u'',
                    'priority': 500,
                    'status': 'STATUS_UNDEFINED',
                    'project_id': self.test_proj1.id,
                    'parent_id': self.test_task7.id,
                    'depend_ids': [],
                    'resource_ids': [],
                    'time_log_ids': [],
                    'start': 1371686400000,
                    'end': 1372550400000,
                    'is_scheduled': False,
                    'schedule_timing': 1.0,
                    'schedule_unit': u'h',
                    'bid_timing': 1.0,
                    'bid_unit': u'h',
                    'schedule_model': u'effort',
                    'schedule_constraint': 0,
                    'schedule_seconds': 3600.0,
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
            'timing_resolution': 3600000,
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

    def test_duplicate_task_hierarchy_task_is_not_existing(self):
        """testing if None will be returned if the task is not existing
        """
        dummyRequest = testing.DummyRequest()
        self.assertRaises(HTTPServerError,
                          task.duplicate_task_hierarchy,
                          dummyRequest)

    def test_duplicate_task_is_working_properly(self):
        """testing if duplicate task is working properly
        """
        # duplicate a task
        dup_task2 = task.duplicate_task(self.test_task2)

        # and compare if it is working properly
        self.assertIsInstance(dup_task2, Task)

        assert isinstance(dup_task2, Task)
        self.assertEqual(dup_task2.bid_timing, self.test_task2.bid_timing)
        self.assertEqual(dup_task2.bid_unit, self.test_task2.bid_unit)
        self.assertEqual(dup_task2.computed_end, self.test_task2.computed_end)
        self.assertEqual(dup_task2.computed_start,
                         self.test_task2.computed_start)
        self.assertEqual(dup_task2.created_by, self.test_task2.created_by)
        self.assertEqual(dup_task2.depends, self.test_task2.depends)
        self.assertEqual(dup_task2.description, self.test_task2.description)
        self.assertEqual(dup_task2.entity_type, self.test_task2.entity_type)
        self.assertEqual(dup_task2.generic_data, self.test_task2.generic_data)
        self.assertEqual(dup_task2.is_complete, self.test_task2.is_complete)
        self.assertEqual(dup_task2.is_milestone, self.test_task2.is_milestone)
        self.assertEqual(dup_task2.name, self.test_task2.name)
        self.assertEqual(dup_task2.notes, self.test_task2.notes)
        self.assertEqual(dup_task2.parent, self.test_task2.parent)
        self.assertEqual(dup_task2.priority, self.test_task2.priority)
        self.assertEqual(dup_task2.project, self.test_task2.project)
        self.assertEqual(dup_task2.references, self.test_task2.references)
        self.assertEqual(dup_task2.resources, self.test_task2.resources)
        self.assertEqual(dup_task2.schedule_constraint,
                         self.test_task2.schedule_constraint)
        self.assertEqual(dup_task2.schedule_model,
                         self.test_task2.schedule_model)
        self.assertEqual(dup_task2.schedule_timing,
                         self.test_task2.schedule_timing)
        self.assertEqual(dup_task2.schedule_unit,
                         self.test_task2.schedule_unit)
        self.assertEqual(dup_task2.status, self.test_task2.status)
        self.assertEqual(dup_task2.status_list, self.test_task2.status_list)
        self.assertEqual(dup_task2.tags, self.test_task2.tags)
        self.assertEqual(dup_task2.thumbnail, self.test_task2.thumbnail)
        if self.test_task2.time_logs:
            self.assertNotEqual(dup_task2.time_logs, self.test_task2.time_logs)
        self.assertEqual(dup_task2.timing_resolution,
                         self.test_task2.timing_resolution)
        self.assertEqual(dup_task2.type, self.test_task2.type)
        self.assertEqual(dup_task2.updated_by,
                         self.test_task2.updated_by)
        if self.test_task2.versions:
            self.assertNotEqual(dup_task2.versions, self.test_task2.versions)
        self.assertEqual(dup_task2.versions, [])
        self.assertEqual(dup_task2.watchers, self.test_task2.watchers)

    def test_duplicate_task_hierarchy_is_working_properly(self):
        """testing if duplicate_task_hierarchy is working properly
        """
        # task1
        #   task4
        #   task5
        #   task6
        # task2
        #   task7
        #   task8
        # task3
        # make it complex
        self.test_task8.depends = [self.test_task7]
        # external dependency should be preserved
        self.test_task7.depends = [self.test_task6]
        self.test_task3.parent = self.test_task8
        self.test_task3.resources = [self.test_user2]

        # current state
        # task1
        #   task4
        #   task5
        #   task6
        # task2
        #   task7
        #     Test Asset1
        #       task9
        #   task8 (depends task7)
        #     task3
        # now duplicate it

        dummyRequest = testing.DummyRequest()
        dummyRequest.params['task_id'] = self.test_task2.id

        task.duplicate_task_hierarchy(dummyRequest)
        dup_task = Task.query.filter_by(name='Test Task 2 - Duplicate').first()
        self.assertIsInstance(dup_task, Task)

        self.assertEqual(len(dup_task.children), 2)
        self.assertTrue(
            dup_task.children[0].name in ['Test Task 7', 'Test Task 8']
        )

        dup_task7 = None
        dup_task8 = None
        if dup_task.children[0].name == 'Test Task 7':
            dup_task7 = dup_task.children[0]
            dup_task8 = dup_task.children[1]
        elif dup_task.children[1].name == 'Test Task 7':
            dup_task7 = dup_task.children[1]
            dup_task8 = dup_task.children[0]

        for dep_task in dup_task8.depends:
            logger.debug('%s of %s : ' % (dep_task, dep_task.parents))
            logger.debug('%s' % dep_task.id)

        # check dependencies
        self.assertEqual(dup_task8.depends, [dup_task7])

        self.assertEqual(dup_task7.depends, [self.test_task6])

        # check children
        self.assertEqual(len(dup_task7.children), 1)
        self.assertEqual(len(dup_task8.children), 1)

        dup_asset1 = dup_task7.children[0]
        self.assertIsInstance(dup_asset1, Asset)
        self.assertEqual(len(dup_asset1.children), 1)
        dup_task9 = dup_asset1.children[0]
        self.assertEqual(dup_task9.name, 'Test Task 9')

        dup_task3 = dup_task8.children[0]
        self.assertEqual(dup_task3.name, 'Test Task 3')

        # check resources
        self.assertEqual(dup_task7.resources, self.test_task7.resources)
        self.assertEqual(dup_task3.resources, self.test_task3.resources)

        # check timing
        # task3
        self.assertEqual(dup_task3.schedule_timing,
                         self.test_task3.schedule_timing)
        self.assertEqual(dup_task3.schedule_model,
                         self.test_task3.schedule_model)
        self.assertEqual(dup_task3.schedule_constraint,
                         self.test_task3.schedule_constraint)
        self.assertEqual(dup_task3.start, self.test_task3.start)
        self.assertEqual(dup_task3.end, self.test_task3.end)

        # task7
        self.assertEqual(dup_task7.schedule_timing,
                         self.test_task7.schedule_timing)
        self.assertEqual(dup_task7.schedule_model,
                         self.test_task7.schedule_model)
        self.assertEqual(dup_task7.schedule_constraint,
                         self.test_task7.schedule_constraint)
        self.assertEqual(dup_task7.start, self.test_task7.start)
        self.assertEqual(dup_task7.end, self.test_task7.end)

        # task8
        self.assertEqual(dup_task8.schedule_timing,
                         self.test_task8.schedule_timing)
        self.assertEqual(dup_task8.schedule_model,
                         self.test_task8.schedule_model)
        self.assertEqual(dup_task8.schedule_constraint,
                         self.test_task8.schedule_constraint)
        self.assertEqual(dup_task8.start, self.test_task8.start)
        self.assertEqual(dup_task8.end, self.test_task8.end)

    def test_walk_hierarchy_is_working_properly(self):
        """testing if walk_hierarchy is working properly
        """
        # Before:
        # task1
        #   task4
        #   task5
        #   task6
        # task2
        #   task7
        #   task8
        # task3

        # make it complex
        self.test_task3.parent = self.test_task8
        self.test_task1.parent = self.test_task2
        # After:
        # task2
        #   task7
        #   task8
        #     task3
        #   task1
        #     task4
        #     task5
        #     task6

        for t in task.walk_hierarchy(self.test_task2):
            logger.debug(t)
        self.fail('test and implementation is not finished yet')

    def test_create_task_dialog(self):
        """testing if the create_task_dialog view is working properly
        """
        request = testing.DummyRequest()
        request.matchdict['entity_id'] = self.test_proj1.id
        response = task.create_task_dialog(request)
        self.assertEqual(response['mode'], 'CREATE')
        self.assertIsInstance(response['has_permission'], PermissionChecker)
        self.assertEqual(response['project'], self.test_proj1)
        self.assertIsNone(response['parent'])
        self.assertEqual(response['schedule_models'],
                         defaults.task_schedule_models)
        self.assertEqual(response['milliseconds_since_epoch'],
                         milliseconds_since_epoch)
