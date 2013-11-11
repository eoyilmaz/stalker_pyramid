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

import mocker

import datetime

import unittest2
import transaction

from pyramid import testing
from pyramid.httpexceptions import HTTPServerError

from stalker import (db, Project, Status, StatusList, Repository, Task, User,
                     Asset, Type, TimeLog)
from stalker.db.session import DBSession

from stalker_pyramid.views import task, milliseconds_since_epoch

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
        db.init()

        DBSession.remove()
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
        self.status_new = Status(name='New', code='NEW')
        self.status_wip = Status(name='Work In Progress', code='WIP')
        self.status_prev = Status(name='Pending Review', code='PREV')
        self.status_hrev = Status(name='Has Revision', code='HREV')
        self.status_completed = Status(name='Completed', code='CMPL')
        DBSession.add_all([
            self.status_new, self.status_wip, self.status_prev,
            self.status_hrev, self.status_completed
        ])

        self.test_project_status_list = StatusList(
            name='Project Statuses',
            target_entity_type='Project',
            statuses=[self.status_new, self.status_wip,
                      self.status_completed]
        )
        DBSession.add(self.test_project_status_list)

        self.test_task_statuses = StatusList(
            name='Task Statuses',
            target_entity_type='Task',
            statuses=[self.status_new, self.status_wip,
                      self.status_prev, self.status_hrev,
                      self.status_completed]
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
            end=datetime.datetime(2013, 6, 30, 0, 0, 0),
            lead=self.test_user1
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
            status=self.status_new,
            status_list=self.test_task_statuses,
            resources=[self.test_user1],
            depends=[self.test_task3],
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
            depends=[self.test_task4],
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
            statuses=[self.status_new, self.status_wip,
                      self.status_prev],
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
        DBSession.flush()
        transaction.commit()

        # no children for self.test_task3
        self.all_tasks = [
            self.test_task1, self.test_task2, self.test_task3,
            self.test_task4, self.test_task5, self.test_task6,
            self.test_task7, self.test_task8, self.test_task9,
            self.test_asset1
        ]

    def tearDown(self):
        DBSession.remove()
        testing.tearDown()

    def test_convert_to_dgrid_gantt_task_format_tasks_is_empty(self):
        """testing if convert_to_dgrid_gantt_task_format function will return
        gracefully if tasks argument is None
        """
        return_value = task.convert_to_dgrid_gantt_task_format([])
        self.assertEqual(return_value, [])

    def test_convert_to_dgrid_gantt_task_format_tasks_is_not_a_list(self):
        """testing if an HTTPServerError will be raised when the tasks argument
        is not a list in convert_to_dgrid_gantt_task_format function
        """
        self.assertRaises(
            HTTPServerError,
            task.convert_to_dgrid_gantt_task_format,
            'not a list of task'
        )

    def test_convert_to_dgrid_gantt_task_format_tasks_is_not_a_list_of_tasks(self):
        """testing if an HTTPServerError will be raised when the tasks argument
        is not a list of tasks in convert_to_dgrid_gantt_task_format function
        """
        self.assertRaises(
            AttributeError,
            task.convert_to_dgrid_gantt_task_format,
            ['not', 'a', 'list', 'of', 'tasks']
        )

    def test_convert_to_dgrid_gantt_task_format_tasks_is_working_properly(self):
        """testing if task.convert_to_dgrid_gantt_task_format function is
        working properly
        """

        expected_data = [
            {
                'bid_unit': 'd',
                'bid_timing': 10,
                'completed': 0,
                'dependencies': [],
                'description': '',
                'end': milliseconds_since_epoch(self.test_task1.end),
                'hasChildren': True,
                'hierarchy_name': '',
                'id': self.test_task1.id,
                'link': '/tasks/%s/view' % self.test_task1.id,
                'name': 'Test Task 1',
                'parent': self.test_task1.project.id,
                'priority': 500,
                'resources': [],
                'responsible': {
                    'id': 12,
                    'name': 'Test User 1'
                },
                'schedule_constraint': 0,
                'schedule_model': 'effort',
                'schedule_seconds': 972000,
                'schedule_timing': 10,
                'schedule_unit': 'd',
                'start': milliseconds_since_epoch(self.test_task1.start),
                'total_logged_seconds': 0,
                'type': 'Task',
            },
            {
                'bid_timing': 10,
                'bid_unit': 'd',
                'completed': 0,
                'dependencies': [],
                'description': '',
                'end': milliseconds_since_epoch(self.test_task2.end),
                'hierarchy_name': '',
                'id': self.test_task2.id,
                'hasChildren': True,
                'link': '/tasks/%s/view' % self.test_task2.id,
                'name': 'Test Task 2',
                'parent': self.test_task2.project.id,
                'priority': 500,
                'resources': [],
                'responsible': {
                    'id': 12,
                    'name': 'Test User 1'
                },
                'schedule_constraint': 0,
                'schedule_model': 'effort',
                'schedule_unit': 'd',
                'schedule_seconds': 651600,
                'schedule_timing': 10,
                'start': milliseconds_since_epoch(self.test_task2.start),
                'total_logged_seconds': 0,
                'type': 'Task',
            },
            {
                'bid_timing': 10,
                'bid_unit': 'd',
                'completed': 0,
                'dependencies': [],
                'description': '',
                'end': milliseconds_since_epoch(self.test_task3.end),
                'hasChildren': False,
                'hierarchy_name': '',
                'id': self.test_task3.id,
                'link': '/tasks/%s/view' % self.test_task3.id,
                'name': 'Test Task 3', 'total_logged_seconds': 0,
                'parent': self.test_task3.project.id,
                'priority': 500,
                'resources': [
                    {'id': 12, 'name': 'Test User 1'},
                    {'id': 13, 'name': 'Test User 2'}
                ],
                'responsible': {'id': 12, 'name': 'Test User 1'},
                'schedule_constraint': 0,
                'schedule_model': 'effort',
                'schedule_seconds': 324000,
                'schedule_timing': 10,
                'schedule_unit': 'd',
                'start': milliseconds_since_epoch(self.test_task3.start),
                'type': 'Task',
            },
            {
                'bid_timing': 10,
                'bid_unit': 'd',
                'completed': 0,
                'dependencies': [{'id': 27, 'name': 'Test Task 3'}],
                'description': '',
                'end': milliseconds_since_epoch(self.test_task4.end),
                'hasChildren': False,
                'hierarchy_name': 'Test Task 1',
                'id': self.test_task4.id,
                'link': '/tasks/%s/view' % self.test_task4.id,
                'name': 'Test Task 4',
                'priority': 500,
                'resources': [{'id': 12, 'name': 'Test User 1'}],
                'responsible': {'id': 12, 'name': 'Test User 1'},
                'parent': self.test_task4.parent.id,
                'schedule_model': 'effort',
                'schedule_constraint': 0,
                'schedule_seconds': 324000,
                'schedule_timing': 10,
                'schedule_unit': 'd',
                'start': milliseconds_since_epoch(self.test_task4.start),
                'total_logged_seconds': 0,
                'type': 'Task',
            },
            {
                'bid_timing': 10,
                'bid_unit': 'd',
                'completed': 0,
                'dependencies': [{'id': 28, 'name': 'Test Task 4'}],
                'description': '',
                'end': milliseconds_since_epoch(self.test_task5.end),
                'id': self.test_task5.id,
                'hasChildren': False,
                'hierarchy_name': 'Test Task 1',
                'link': '/tasks/%s/view' % self.test_task5.id,
                'name': 'Test Task 5',
                'parent': self.test_task5.parent.id,
                'priority': 500,
                'resources': [{'id': 12, 'name': 'Test User 1'}],
                'responsible': {
                    'id': 12, 'name': 'Test User 1'
                },
                'schedule_constraint': 0,
                'schedule_model': 'effort',
                'schedule_seconds': 324000,
                'schedule_timing': 10,
                'schedule_unit': 'd',
                'start': milliseconds_since_epoch(self.test_task5.start),
                'total_logged_seconds': 0,
                'type': 'Task',
            },
            {
                'bid_timing': 10,
                'bid_unit': 'd',
                'completed': 0,
                'dependencies': [],
                'description': '',
                'end': milliseconds_since_epoch(self.test_task6.end),
                'hasChildren': False,
                'hierarchy_name': 'Test Task 1',
                'id': self.test_task6.id,
                'link': '/tasks/%s/view' % self.test_task6.id,
                'name': 'Test Task 6',
                'parent': self.test_task6.parent.id,
                'priority': 500,
                'resources': [{'id': 12, 'name': 'Test User 1'}],
                'responsible': {'id': 12, 'name': 'Test User 1'},
                'schedule_constraint': 0,
                'schedule_model': 'effort',
                'schedule_seconds': 324000,
                'schedule_timing': 10,
                'schedule_unit': 'd',
                'start': milliseconds_since_epoch(self.test_task6.start),
                'type': 'Task',
                'total_logged_seconds': 0,
            },
            {
                'bid_timing': 10,
                'bid_unit': 'd',
                'completed': 0,
                'dependencies': [],
                'description': '',
                'end': milliseconds_since_epoch(self.test_task7.end),
                'id': self.test_task7.id,
                'hasChildren': True,
                'hierarchy_name': 'Test Task 2',
                'link': '/tasks/%s/view' % self.test_task7.id,
                'name': 'Test Task 7',
                'resources': [],
                'responsible': {'id': 12, 'name': 'Test User 1'},
                'parent': self.test_task7.parent.id,
                'priority': 500,
                'schedule_constraint': 0,
                'schedule_model': 'effort',
                'schedule_seconds': 324000,
                'schedule_timing': 10,
                'schedule_unit': 'd',
                'start': milliseconds_since_epoch(self.test_task7.start),
                'total_logged_seconds': 0,
                'type': 'Task',
            },
            {
                'bid_timing': 10,
                'bid_unit': 'd',
                'completed': 0,
                'dependencies': [],
                'hierarchy_name': 'Test Task 2',
                'id': self.test_task8.id,
                'description': '',
                'end': milliseconds_since_epoch(self.test_task8.end),
                'hasChildren': False,
                'link': '/tasks/%s/view' % self.test_task8.id,
                'name': 'Test Task 8',
                'parent': self.test_task8.parent.id,
                'priority': 500,
                'resources': [{'id': 13, 'name': 'Test User 2'}],
                'responsible': {'id': 12, 'name': 'Test User 1'},
                'schedule_constraint': 0,
                'schedule_model': 'effort',
                'schedule_seconds': 324000,
                'schedule_timing': 10,
                'schedule_unit': 'd',
                'start': milliseconds_since_epoch(self.test_task8.start),
                'total_logged_seconds': 0,
                'type': 'Task',
            },
            {
                'bid_timing': 10,
                'bid_unit': 'd',
                'completed': 0,
                'dependencies': [],
                'description': '',
                'end': milliseconds_since_epoch(self.test_task9.end),
                'hasChildren': False,
                'hierarchy_name': 'Test Task 2 | Test Task 7 | Test Asset 1',
                'id': self.test_task9.id,
                'link': '/tasks/%s/view' % self.test_task9.id,
                'name': 'Test Task 9',
                'parent': self.test_task9.parent.id,
                'priority': 500,
                'resources': [],
                'responsible': {'id': 12, 'name': 'Test User 1'},
                'schedule_constraint': 0,
                'schedule_model': 'effort',
                'schedule_seconds': 324000,
                'schedule_timing': 10,
                'schedule_unit': 'd',
                'start': milliseconds_since_epoch(self.test_task9.start),
                'total_logged_seconds': 0,
                'type': 'Task',
            },
            {
                'bid_timing': 1,
                'bid_unit': 'h',
                'completed': 0,
                'dependencies': [],
                'description': '',
                'end': milliseconds_since_epoch(self.test_asset1.end),
                'hasChildren': True,
                'hierarchy_name': 'Test Task 2 | Test Task 7',
                'id': self.test_asset1.id,
                'link': '/assets/%s/view' % self.test_asset1.id,
                'name': 'Test Asset 1',
                'parent': self.test_asset1.parent.id,
                'priority': 500,
                'resources': [],
                'responsible': {'id': 12, 'name': 'Test User 1'},
                'schedule_constraint': 0,
                'schedule_model': 'effort',
                'schedule_seconds': 324000,
                'schedule_timing': 1,
                'schedule_unit': 'h',
                'start': milliseconds_since_epoch(self.test_asset1.start),
                'total_logged_seconds': 0,
                'type': 'Asset',
            }
        ]
        data = task.convert_to_dgrid_gantt_task_format(self.all_tasks)
        self.maxDiff = None

        print data,
        print '#########################'
        print expected_data

        self.assertItemsEqual(
            data,
            expected_data
        )

    def test_duplicate_task_hierarchy_task_is_not_existing(self):
        """testing if None will be returned if the task is not existing
        """
        dummyRequest = testing.DummyRequest()
        response = task.duplicate_task_hierarchy(dummyRequest)
        self.assertEqual(response.status_int, 500)

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

        DBSession.flush()
        transaction.commit()

        dummyRequest = testing.DummyRequest()
        dummyRequest.matchdict['id'] = self.test_task2.id
        print 'self.test_task2.id: %s' % self.test_task2.id

        response = task.duplicate_task_hierarchy(dummyRequest)
        print ('response.text : %s' % response.text)
        self.assertEqual(response.status_int, 200)
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

        # task8
        self.assertEqual(dup_task8.schedule_timing,
                         self.test_task8.schedule_timing)
        self.assertEqual(dup_task8.schedule_model,
                         self.test_task8.schedule_model)
        self.assertEqual(dup_task8.schedule_constraint,
                         self.test_task8.schedule_constraint)

    def test_request_revision_should_not_work_for_tasks_with_the_status_is_set_to_new(self):
        """testing if a server error will be returned if the task issued in
        request_review has a status of "new"
        """
        # request revision for self.test_task4
        self.test_task4.status = self.status_new
        request = testing.DummyRequest()
        request.matchdict['id'] = self.test_task4.id
        request.params['send_email'] = 0
        request.params['schedule_timing'] = 5
        request.params['schedule_unit'] = 'h'

        # patch get_logged_in_user
        admin = User.query.filter(User.login == 'admin').first()
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(admin)
        m.replay()

        response = task.request_revision(request)
        self.assertEqual(response.status_int, 500)
        self.assertEqual(
            response.body,
            'You can not request a review for a task with status is set to "New"'
        )

    def test_request_revision_should_not_work_for_tasks_with_the_status_is_set_to_has_revision(self):
        """testing if a server error will be returned if the task issued in
        request_review has a status of "has revision"
        """
        # request revision for self.test_task4
        self.test_task4.status = self.status_hrev
        request = testing.DummyRequest()
        request.matchdict['id'] = self.test_task4.id
        request.params['send_email'] = 0
        request.params['schedule_timing'] = 5
        request.params['schedule_unit'] = 'h'

        # patch get_logged_in_user
        admin = User.query.filter(User.login == 'admin').first()
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(admin)
        m.replay()

        response = task.request_revision(request)
        self.assertEqual(response.status_int, 500)
        self.assertEqual(
            response.body,
            'You can not request a review for a task with status is set to "Has Revision"'
        )

    def test_request_revision_should_not_work_for_tasks_with_the_status_is_set_to_completed(self):
        """testing if a server error will be returned if the task issued in
        request_review has a status of "completed"
        """
        # request revision for self.test_task4
        self.test_task4.status = self.status_completed
        request = testing.DummyRequest()
        request.matchdict['id'] = self.test_task4.id
        request.params['send_email'] = 0
        request.params['schedule_timing'] = 5
        request.params['schedule_unit'] = 'h'

        # patch get_logged_in_user
        admin = User.query.filter(User.login == 'admin').first()
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(admin)
        m.replay()

        response = task.request_revision(request)
        self.assertEqual(response.status_int, 500)
        self.assertEqual(
            response.body,
            'You can not request a review for a task with status is set to "Completed"'
        )

    def test_request_revision_is_working_properly(self):
        """testing if the request_revision function is working
        properly
        """
        admin = User.query.filter(User.login == 'admin').first()

        # create a time log before asking review
        time_log = TimeLog(
            resource=self.test_task4.resources[0],
            task=self.test_task4,
            start=datetime.datetime(2013, 6, 20, 10, 0),
            end=datetime.datetime(2013, 6, 20, 19, 0)
        )
        DBSession.add(time_log)
        self.test_task4.status = self.status_wip

        # request revision for self.test_task4
        request = testing.DummyRequest()
        request.matchdict['id'] = self.test_task4.id
        request.params['send_email'] = 0
        request.params['schedule_timing'] = 5
        request.params['schedule_unit'] = 'h'

        # patch get_logged_in_user
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(admin)
        m.replay()

        # also patch route_url of request
        request.route_url = lambda x, id: 'localhost:6453/tasks/23/view'

        response = task.request_revision(request)
        self.assertEqual(response.status_int, 200)

        # check if the status of the original task is set to Has Revision
        #self.test_task4 = Task.query.get(self.test_task4.id)
        self.assertEqual(self.test_task4.status, self.status_hrev)

        # check if the task percent_complete is 100
        assert isinstance(self.test_task4, Task)
        self.assertEqual(self.test_task4.percent_complete, 100)

        # check if a new task with the same name but has a postfix of
        # " - Rev 1" is created
        rev_task = Task.query.filter(
            Task.name == self.test_task4.name + ' - Rev 1').first()
        self.assertIsNotNone(rev_task)

        # check if the rev task has the same dependencies plus the original
        # task in its depends list
        self.assertItemsEqual(
            rev_task.depends,
            [self.test_task3, self.test_task4]
        )

        # check if the dependent tasks to original task are now depending to
        # the revision task
        self.assertItemsEqual(
            rev_task.dependent_of, [self.test_task5]
        )

        # and the original tasks dependency links are broken
        self.assertItemsEqual(
            self.test_task4.dependent_of, [rev_task]
        )

