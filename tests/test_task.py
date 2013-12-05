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
from tests import DummyMultiDict

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
        self.status_rts = Status(name='Ready To Start', code='RTS')
        self.status_wip = Status(name='Work In Progress', code='WIP')
        self.status_prev = Status(name='Pending Review', code='PREV')
        self.status_hrev = Status(name='Has Revision', code='HREV')
        self.status_cmpl = Status(name='Completed', code='CMPL')
        DBSession.add_all([
            self.status_new, self.status_rts, self.status_wip,
            self.status_prev, self.status_hrev, self.status_cmpl
        ])

        self.test_project_status_list = StatusList(
            name='Project Statuses',
            target_entity_type='Project',
            statuses=[self.status_new, self.status_wip,
                      self.status_cmpl]
        )
        DBSession.add(self.test_project_status_list)

        self.test_task_statuses = StatusList(
            name='Task Statuses',
            target_entity_type='Task',
            statuses=[self.status_new, self.status_rts, self.status_wip,
                      self.status_prev, self.status_hrev,
                      self.status_cmpl]
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
        self.test_project1 = Project(
            name='Test Project 1',
            code='TProj1',
            status_list=self.test_project_status_list,
            repository=self.test_repo,
            start=datetime.datetime(2013, 6, 20, 0, 0, 0),
            end=datetime.datetime(2013, 6, 30, 0, 0, 0),
            lead=self.test_user1
        )
        DBSession.add(self.test_project1)

        # root tasks
        self.test_task1 = Task(
            name='Test Task 1',
            project=self.test_project1,
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
            project=self.test_project1,
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
            project=self.test_project1,
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
                'status': 'new',
                'total_logged_seconds': 0,
                'type': 'Task',
            },
            {
                'bid_timing': 10,
                'bid_unit': 'd',
                'completed': 0.0,
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
                'schedule_seconds': 651600.0,
                'schedule_timing': 10,
                'start': milliseconds_since_epoch(self.test_task2.start),
                'status': 'new',
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
                'status': 'new',
                'type': 'Task',
            },
            {
                'bid_timing': 10,
                'bid_unit': 'd',
                'completed': 0,
                'dependencies': [{'id': 28, 'name': 'Test Task 3'}],
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
                'status': 'new',
                'total_logged_seconds': 0,
                'type': 'Task',
            },
            {
                'bid_timing': 10,
                'bid_unit': 'd',
                'completed': 0,
                'dependencies': [{'id': 29, 'name': 'Test Task 4'}],
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
                'status': 'new',
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
                'status': 'new',
                'type': 'Task',
                'total_logged_seconds': 0,
            },
            {
                'bid_timing': 10,
                'bid_unit': 'd',
                'completed': 0.0,
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
                'schedule_seconds': 324000.0,
                'schedule_timing': 10,
                'schedule_unit': 'd',
                'start': milliseconds_since_epoch(self.test_task7.start),
                'status': 'new',
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
                'status': 'new',
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
                'status': 'new',
                'total_logged_seconds': 0,
                'type': 'Task',
            },
            {
                'bid_timing': 1.0,
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
                'schedule_timing': 1.0,
                'schedule_unit': 'h',
                'start': milliseconds_since_epoch(self.test_asset1.start),
                'status': 'new',
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

    def test_request_review_returns_code_500_if_no_task_found(self):
        """testing if a response with code 500 is returned back when there is
        no such task
        """
        # request review for self.test_task4
        request = testing.DummyRequest()
        request.matchdict['id'] = 123123123
        request.params['send_email'] = 0

        # patch get_logged_in_user
        admin = User.query.filter(User.login == 'admin').first()
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(admin)
        m.replay()

        response = task.request_review(request)
        self.assertEqual(response.status_int, 500)
        self.assertEqual(response.body, 'There is no task with id: 123123123')

    def test_request_review_should_not_work_for_tasks_with_the_status_is_set_to_new(self):
        """testing if a server error will be returned if the task issued in
        request_review has a status of "new"
        """
        # request revision for self.test_task4
        self.test_task4.status = self.status_new
        request = testing.DummyRequest()
        request.matchdict['id'] = self.test_task4.id
        request.params['send_email'] = 0

        # patch get_logged_in_user
        admin = User.query.filter(User.login == 'admin').first()
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(admin)
        m.replay()

        response = task.request_review(request)
        self.assertEqual(response.status_int, 500)
        self.assertEqual(
            response.body,
            'You can not request a review for a task with status is set to '
            '"New"'
        )

    def test_request_review_should_not_work_for_tasks_with_the_status_is_set_to_ready_to_start(self):
        """testing if a server error will be returned if the task issued in
        request_review has a status of "rts"
        """
        # request revision for self.test_task4
        self.test_task4.status = self.status_rts
        request = testing.DummyRequest()
        request.matchdict['id'] = self.test_task4.id
        request.params['send_email'] = 0

        # patch get_logged_in_user
        admin = User.query.filter(User.login == 'admin').first()
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(admin)
        m.replay()

        response = task.request_review(request)
        self.assertEqual(response.status_int, 500)
        self.assertEqual(
            response.body,
            'You can not request a review for a task with status is set to '
            '"Ready To Start"'
        )

    def test_request_review_should_not_work_for_tasks_with_the_status_is_set_to_pending_review(self):
        """testing if a server error will be returned if the task issued in
        request_revision has a status of "prev"
        """
        # request revision for self.test_task4
        self.test_task4.status = self.status_prev
        request = testing.DummyRequest()
        request.matchdict['id'] = self.test_task4.id
        request.params['send_email'] = 0

        # patch get_logged_in_user
        admin = User.query.filter(User.login == 'admin').first()
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(admin)
        m.replay()

        response = task.request_review(request)
        self.assertEqual(response.status_int, 500)
        self.assertEqual(
            response.body,
            'You can not request a review for a task with status is set to '
            '"Pending Review"'
        )

    def test_request_review_should_not_work_for_tasks_with_the_status_is_set_to_has_revision(self):
        """testing if a server error will be returned if the task issued in
        request_review has a status of "has revision"
        """
        # request revision for self.test_task4
        self.test_task4.status = self.status_hrev
        request = testing.DummyRequest()
        request.matchdict['id'] = self.test_task4.id
        request.params['send_email'] = 0

        # patch get_logged_in_user
        admin = User.query.filter(User.login == 'admin').first()
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(admin)
        m.replay()

        response = task.request_review(request)
        self.assertEqual(response.status_int, 500)
        self.assertEqual(
            response.body,
            'You can not request a review for a task with status is set to '
            '"Has Revision"'
        )

    def test_request_review_should_not_work_for_tasks_with_the_status_is_set_to_completed(self):
        """testing if a server error will be returned if the task issued in
        request_review has a status of "completed"
        """
        # request revision for self.test_task4
        self.test_task4.status = self.status_cmpl
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

        response = task.request_review(request)
        self.assertEqual(response.status_int, 500)
        self.assertEqual(
            response.body,
            'You can not request a review for a task with status is set to '
            '"Completed"'
        )

    def test_request_review_will_work_only_for_leaf_tasks(self):
        """testing if the request_review will only work for leaf tasks
        """
        # create a time log before asking review
        time_log = TimeLog(
            resource=self.test_task4.resources[0],
            task=self.test_task4,
            start=datetime.datetime(2013, 6, 20, 10, 0),
            end=datetime.datetime(2013, 6, 20, 19, 0)
        )
        DBSession.add(time_log)
        self.test_task1.status = self.status_wip

        # request review for self.test_task1
        request = testing.DummyRequest()
        request.matchdict['id'] = self.test_task1.id
        request.params['send_email'] = 0

        # patch get_logged_in_user
        admin = User.query.filter(User.login == 'admin').first()
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(admin)
        m.replay()

        # also patch route_url of request
        request.route_url = lambda x, id: 'localhost:6453/tasks/23/view'

        response = task.request_review(request)
        self.assertEqual(response.status_int, 500)
        self.assertEqual(response.body, 'Can not request review for a '
                                        'container task')

    def test_request_review_should_not_work_for_users_who_are_not_a_resource_nor_responsible_of_the_task(self):
        """testing if request_review() will not work for users who are not a
        resource nor the responsible of the task
        """
        # create a time log before asking review
        time_log = TimeLog(
            resource=self.test_task4.resources[0],
            task=self.test_task4,
            start=datetime.datetime(2013, 6, 20, 10, 0),
            end=datetime.datetime(2013, 6, 20, 19, 0)
        )
        DBSession.add(time_log)
        self.test_task4.status = self.status_wip

        # request review for self.test_task4
        request = testing.DummyRequest()
        request.matchdict['id'] = self.test_task4.id
        request.params['send_email'] = 0

        # patch get_logged_in_user
        admin = User.query.filter(User.login == 'admin').first()
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(admin)
        m.replay()

        # also patch route_url of request
        request.route_url = lambda x, id: 'localhost:6453/tasks/23/view'

        response = task.request_review(request)
        self.assertEqual(response.status_int, 500)
        self.assertEqual(response.body,
                         'You are not one of the resources nor the '
                         'responsible of this task, so you can not request a '
                         'review for this task')

    def test_request_review_is_working_properly(self):
        """testing if the request_review function is working properly
        """
        # create a time log before asking review
        time_log = TimeLog(
            resource=self.test_task4.resources[0],
            task=self.test_task4,
            start=datetime.datetime(2013, 6, 20, 10, 0),
            end=datetime.datetime(2013, 6, 20, 19, 0)
        )
        DBSession.add(time_log)
        self.test_task4.status = self.status_wip

        # request review for self.test_task4
        request = testing.DummyRequest()
        request.matchdict['id'] = self.test_task4.id
        request.params['send_email'] = 0

        # patch get_logged_in_user
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(self.test_task4.resources[0])
        m.replay()

        # also patch route_url of request
        request.route_url = lambda x, id: 'localhost:6453/tasks/23/view'

        # also patch route_url of request
        request.route_path = lambda x, id: '/tasks/23/view'

        response = task.request_review(request)
        self.assertEqual(response.status_int, 200)

        # check if the status of the original task is set to Pending Revision
        #self.test_task4 = Task.query.get(self.test_task4.id)
        self.assertEqual(self.test_task4.status, self.status_prev)

        # check if the task percent_complete is 100
        self.assertEqual(self.test_task4.percent_complete, 100)

    def test_request_revision_returns_code_500_if_no_task_found(self):
        """testing if a response with code 500 is returned back when there is
        no such task
        """
        # request review for self.test_task4
        request = testing.DummyRequest()
        request.matchdict['id'] = 123123123
        request.params['send_email'] = 0

        # patch get_logged_in_user
        admin = User.query.filter(User.login == 'admin').first()
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(admin)
        m.replay()

        response = task.request_revision(request)
        self.assertEqual(response.status_int, 500)
        self.assertEqual(response.body, 'There is no task with id: 123123123')

    def test_request_revision_returns_code_500_if_no_schedule_timing_found(self):
        """testing if a response with code 500 is returned back when there is
        no schedule_timing parameter
        """
        # request review for self.test_task4
        request = testing.DummyRequest()
        request.matchdict['id'] = self.test_task4.id
        request.params['send_email'] = 0
        request.params['schedule_unit'] = 'h'
        request.params['schedule_model'] = 'effort'

        # patch get_logged_in_user
        admin = User.query.filter(User.login == 'admin').first()
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(admin)
        m.replay()

        response = task.request_revision(request)
        self.assertEqual(response.status_int, 500)
        self.assertEqual(response.body,
                         'There are missing parameters: schedule_timing')

    def test_request_revision_returns_code_500_if_schedule_timing_is_not_an_int_or_float(self):
        """testing if a response with code 500 is returned back when the
        schedule_timing is not an integer or float
        """
        # request review for self.test_task4
        request = testing.DummyRequest()
        request.matchdict['id'] = self.test_task4.id
        request.params['send_email'] = 0
        request.params['schedule_unit'] = 'h'
        request.params['schedule_timing'] = 'this is not an integer or float'
        request.params['schedule_model'] = 'effort'

        # patch get_logged_in_user
        admin = User.query.filter(User.login == 'admin').first()
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(admin)
        m.replay()

        response = task.request_revision(request)
        self.assertEqual(response.status_int, 500)
        self.assertEqual(response.body,
                         'Please supply a float or integer value for '
                         'schedule_timing parameter')

    def test_request_revision_returns_code_500_if_no_schedule_unit_found(self):
        """testing if a response with code 500 is returned back when there is
        no schedule_unit parameter
        """
        # request review for self.test_task4
        request = testing.DummyRequest()
        request.matchdict['id'] = self.test_task4.id
        request.params['send_email'] = 0
        request.params['schedule_timing'] = 1.0
        request.params['schedule_model'] = 'effort'

        # patch get_logged_in_user
        admin = User.query.filter(User.login == 'admin').first()
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(admin)
        m.replay()

        response = task.request_revision(request)
        self.assertEqual(response.status_int, 500)
        self.assertEqual(response.body,
                         'There are missing parameters: schedule_unit')

    def test_request_revision_returns_code_500_if_no_schedule_unit_value_is_wrong(self):
        """testing if a response with code 500 is returned back when the value
        of schedule_unit parameter is not one of ['h', 'd', 'w', 'm', 'y']
        """
        # request review for self.test_task4
        request = testing.DummyRequest()
        request.matchdict['id'] = self.test_task4.id
        request.params['send_email'] = 0
        request.params['schedule_timing'] = 1.0
        request.params['schedule_unit'] = 'min'
        request.params['schedule_model'] = 'effort'

        # patch get_logged_in_user
        admin = User.query.filter(User.login == 'admin').first()
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(admin)
        m.replay()

        response = task.request_revision(request)
        self.assertEqual(response.status_int, 500)
        self.assertEqual(response.body,
                         "schedule_unit parameter should be one of ['h', 'd', "
                         "'w', 'm', 'y']")

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
        request.params['schedule_model'] = 'effort'

        # patch get_logged_in_user
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(self.test_task4.resources[0])
        m.replay()

        response = task.request_revision(request)
        self.assertEqual(response.status_int, 500)
        self.assertEqual(
            response.body,
            'You can not request a revision for a task with status is set to '
            '"New"'
        )

    def test_request_revision_should_not_work_for_tasks_with_the_status_is_set_to_rts(self):
        """testing if a server error will be returned if the task issued in
        request_review has a status of "rts"
        """
        # request revision for self.test_task4
        self.test_task4.status = self.status_rts
        request = testing.DummyRequest()
        request.matchdict['id'] = self.test_task4.id
        request.params['send_email'] = 0
        request.params['schedule_timing'] = 5
        request.params['schedule_unit'] = 'h'
        request.params['schedule_model'] = 'effort'

        # patch get_logged_in_user
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(self.test_task4.resources[0])
        m.replay()

        response = task.request_revision(request)
        self.assertEqual(response.status_int, 500)
        self.assertEqual(
            response.body,
            'You can not request a revision for a task with status is set to '
            '"Ready To Start"'
        )

    def test_request_revision_should_not_work_for_tasks_with_the_status_is_set_to_wip(self):
        """testing if a server error will be returned if the task issued in
        request_revision has a status of "wip"
        """
        # request revision for self.test_task4
        self.test_task4.status = self.status_wip
        request = testing.DummyRequest()
        request.matchdict['id'] = self.test_task4.id
        request.params['send_email'] = 0
        request.params['schedule_timing'] = 5
        request.params['schedule_unit'] = 'h'
        request.params['schedule_model'] = 'effort'

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
            'You can not request a revision for a task with status is set to '
            '"Work In Progress"'
        )

    def test_request_revision_should_not_work_for_tasks_with_the_status_is_set_to_has_revision(self):
        """testing if a server error will be returned if the task issued in
        request_revision has a status of "has revision"
        """
        # request revision for self.test_task4
        self.test_task4.status = self.status_hrev
        request = testing.DummyRequest()
        request.matchdict['id'] = self.test_task4.id
        request.params['send_email'] = 0
        request.params['schedule_timing'] = 5
        request.params['schedule_unit'] = 'h'
        request.params['schedule_model'] = 'effort'

        # patch get_logged_in_user
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(self.test_task4.resources[0])
        m.replay()

        response = task.request_revision(request)
        self.assertEqual(response.status_int, 500)
        self.assertEqual(
            response.body,
            'You can not request a revision for a task with status is set to '
            '"Has Revision"'
        )

    def test_request_revision_should_not_work_for_tasks_with_the_status_is_set_to_completed(self):
        """testing if a server error will be returned if the task issued in
        request_revision has a status of "completed"
        """
        # request revision for self.test_task4
        self.test_task4.status = self.status_cmpl
        request = testing.DummyRequest()
        request.matchdict['id'] = self.test_task4.id
        request.params['send_email'] = 0
        request.params['schedule_timing'] = 5
        request.params['schedule_unit'] = 'h'
        request.params['schedule_model'] = 'effort'

        # patch get_logged_in_user
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(self.test_task4.resources[0])
        m.replay()

        response = task.request_revision(request)
        self.assertEqual(response.status_int, 500)
        self.assertEqual(
            response.body,
            'You can not request a revision for a task with status is set to '
            '"Completed"'
        )

    def test_request_revision_is_working_properly_for_tasks_with_status_pending_review(self):
        """testing if the request_revision function is working properly
        """
        # create a time log before asking review
        time_log = TimeLog(
            resource=self.test_task4.resources[0],
            task=self.test_task4,
            start=datetime.datetime(2013, 6, 20, 10, 0),
            end=datetime.datetime(2013, 6, 20, 19, 0)
        )
        DBSession.add(time_log)
        self.test_task4.status = self.status_prev

        # request revision for self.test_task4
        request = testing.DummyRequest()
        request.matchdict['id'] = self.test_task4.id
        request.params['send_email'] = 0
        request.params['schedule_timing'] = 5
        request.params['schedule_unit'] = 'h'
        request.params['schedule_model'] = 'effort'

        # patch get_logged_in_user
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(self.test_task4.resources[0])
        m.replay()

        # also patch route_url of request
        request.route_url = lambda x, id: 'localhost:6453/tasks/23/view'

        response = task.request_revision(request)
        logger.debug(response.body)
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

    def test_request_extra_time_works_only_for_leaf_tasks(self):
        """testing if task.request_extra_time works only for leaf tasks
        """
        # request extra time for self.test_task1
        request = testing.DummyRequest()
        request.matchdict['id'] = self.test_task1.id
        request.params['send_email'] = 0

        # patch get_logged_in_user
        admin = User.query.filter(User.login == 'admin').first()
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(admin)
        m.replay()

        # also patch route_url of request
        request.route_url = lambda x, id: 'localhost:6453/tasks/23/view'

        response = task.request_extra_time(request)
        self.assertEqual(response.status_int, 500)
        self.assertEqual(response.body,
                         'Can not request extra time for a container task')

    def test_create_task_leaf_task_with_no_dependency(self):
        """testing if create_task with no dependency will set the newly created
        task status to RTS
        """
        request = testing.DummyRequest()
        request.params = DummyMultiDict()
        request.POST = request.params
        request.params['project_id'] = self.test_project1.id
        request.params['name'] = 'New Task 1'
        request.params['entity_type'] = 'Task'
        request.params['schedule_timing'] = 1.0
        request.params['schedule_unit'] = 'h'
        request.params['schedule_model'] = 'effort'

        # patch get_logged_in_user
        admin = User.query.filter(User.login == 'admin').first()
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(admin)
        m.replay()

        # now create the task
        response = task.create_task(request)
        self.assertEqual(response.status_int, 200)

        # find the newly created task
        new_task = Task.query.filter(Task.name == 'New Task 1').first()
        self.assertIsNotNone(new_task)

        # now check the status
        self.assertEqual(
            self.status_rts,
            new_task.status
        )

    def test_create_task_leaf_task_with_dependency_with_status_not_complete(self):
        """testing if create_task with dependency will set the newly created
        task status to NEW if dependencies are not in Status:Complete
        """
        request = testing.DummyRequest()

        request.params = DummyMultiDict()
        request.POST = request.params
        request.params['project_id'] = self.test_project1.id
        request.params['name'] = 'New Task 1'
        request.params['entity_type'] = 'Task'
        request.params['schedule_timing'] = 1.0
        request.params['schedule_unit'] = 'h'
        request.params['schedule_model'] = 'effort'
        request.params['dependent_ids'] = [self.test_task1.id]
        self.assertNotEqual(
            self.status_cmpl,
            self.test_task1.status
        )

        # patch get_logged_in_user
        admin = User.query.filter(User.login == 'admin').first()
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(admin)
        m.replay()

        # now create the task
        response = task.create_task(request)
        self.assertEqual(response.status_int, 200)

        # find the newly created task
        new_task = Task.query.filter(Task.name == 'New Task 1').first()
        self.assertIsNotNone(new_task)

        # now check the status
        self.assertEqual(
            self.status_new,
            new_task.status
        )

    def test_create_task_leaf_task_with_dependency_with_status_complete(self):
        """testing if create_task with dependency will set the newly created
        task status to RTS if dependencies are all in Status:Complete
        """
        request = testing.DummyRequest()
        request.params = DummyMultiDict()
        request.POST = request.params
        request.params['project_id'] = self.test_project1.id
        request.params['name'] = 'New Task 1'
        request.params['entity_type'] = 'Task'
        request.params['schedule_timing'] = 1.0
        request.params['schedule_unit'] = 'h'
        request.params['schedule_model'] = 'effort'
        request.params['dependent_ids'] = [self.test_task1.id]
        self.test_task1.status = self.status_cmpl
        self.assertEqual(
            self.status_cmpl,
            self.test_task1.status
        )

        # patch get_logged_in_user
        admin = User.query.filter(User.login == 'admin').first()
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(admin)
        m.replay()

        # now create the task
        response = task.create_task(request)
        self.assertEqual(response.status_int, 200)

        # find the newly created task
        new_task = Task.query.filter(Task.name == 'New Task 1').first()
        self.assertIsNotNone(new_task)

        # now check the status
        self.assertEqual(
            self.status_rts,
            new_task.status
        )

    def test_create_task_leaf_task_with_dependency_with_mixed_statuses(self):
        """testing if create_task with dependency will set the newly created
        task status to RTS if dependencies are all in Status:Complete
        """
        request = testing.DummyRequest()
        request.params = DummyMultiDict()
        request.POST = request.params
        request.params['project_id'] = self.test_project1.id
        request.params['name'] = 'New Task 1'
        request.params['entity_type'] = 'Task'
        request.params['schedule_timing'] = 1.0
        request.params['schedule_unit'] = 'h'
        request.params['schedule_model'] = 'effort'
        request.params['dependent_ids'] = [self.test_task1.id,
                                           self.test_task2.id]
        self.test_task1.status = self.status_cmpl
        self.test_task2.status = self.status_wip
        self.assertEqual(
            self.status_cmpl,
            self.test_task1.status
        )
        self.assertEqual(
            self.status_wip,
            self.test_task2.status
        )

        # patch get_logged_in_user
        admin = User.query.filter(User.login == 'admin').first()
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(admin)
        m.replay()

        # now create the task
        response = task.create_task(request)
        self.assertEqual(response.status_int, 200)

        # find the newly created task
        new_task = Task.query.filter(Task.name == 'New Task 1').first()
        self.assertIsNotNone(new_task)

        # now check the status
        self.assertEqual(
            self.status_new,
            new_task.status
        )

    def test_review_task_changes_dependent_task_statuses_to_rts_if_completed(self):
        """testing if review_task() will change the dependent task statuses
        from new to rts if the current task is completed and there are no other
        dependencies for dependent tasks
        """
        self.fail('test is not implemented yet')

    def test_review_task_changes_dependent_task_statuses_to_new_if_has_revision(self):
        """testing if review_task() will change the dependent task statuses to
        new if the current task has revisions and there are no other
        dependencies for dependent tasks
        """
        self.fail('test is not implemented yet')

    def test_update_task_statuses_with_dependencies_for_a_task_with_no_dependencies(self):
        """testing if the task status is going to be updated to RTS if the task
        has not any dependencies for a leaf task
        """
        self.assertEqual(self.test_task8.status, self.status_new)
        task.update_task_statuses_with_dependencies(self.test_task8)
        self.assertEqual(self.test_task8.status, self.status_rts)

    def test_update_task_statuses_with_dependencies_for_a_container_task(self):
        """testing if container task statuses will not be changed if they do
        not have any dependencies and even if their statuses are NEW
        """
        self.assertEqual(self.test_task2.status, self.status_new)
        task.update_task_statuses_with_dependencies(self.test_task2)
        self.assertEqual(self.test_task2.status, self.status_new)

    def test_update_task_statuses_with_dependencies_with_completed_dependencies(self):
        """testing if the task status is going to be updated to RTS if all of
        the dependent tasks are in CMPL status for a task
        """
        # the hero task
        self.assertEqual(self.test_task5.status, self.status_new)

        # the dependencies
        self.test_task4.status = self.status_cmpl
        self.test_task6.status = self.status_cmpl
        self.test_task7.status = self.status_cmpl
        self.assertEqual(self.test_task4.status, self.status_cmpl)
        self.assertEqual(self.test_task6.status, self.status_cmpl)
        self.assertEqual(self.test_task7.status, self.status_cmpl)
        self.test_task5.depends.append(self.test_task4)
        self.test_task5.depends.append(self.test_task6)
        self.test_task5.depends.append(self.test_task7)

        task.update_task_statuses_with_dependencies(self.test_task5)
        self.assertEqual(self.test_task5.status, self.status_rts)

    def test_update_task_statuses_with_dependencies_with_half_completed_dependencies(self):
        """testing if the task status will be set to NEW if dependencies are
        still not all CMPL
        """
        # the hero task
        self.test_task5.status = self.status_new
        self.assertEqual(self.test_task5.status, self.status_new)

        # the dependencies
        self.test_task4.status = self.status_cmpl
        self.test_task6.status = self.status_cmpl
        self.test_task7.status = self.status_wip
        self.assertEqual(self.test_task4.status, self.status_cmpl)
        self.assertEqual(self.test_task6.status, self.status_cmpl)
        self.assertEqual(self.test_task7.status, self.status_wip)
        self.test_task5.depends.append(self.test_task4)
        self.test_task5.depends.append(self.test_task6)
        self.test_task5.depends.append(self.test_task7)

        task.update_task_statuses_with_dependencies(self.test_task5)
        self.assertEqual(self.test_task5.status, self.status_new)

    def test_update_task_statuses_with_dependencies_with_half_completed_dependencies_and_status_wip(self):
        """testing if the task status will be not changed if the task status is
        not NEW even if dependencies are still not all CMPL, this is for
        backward compatibility
        """
        # the hero task
        self.test_task5.status = self.status_wip
        self.assertEqual(self.test_task5.status, self.status_wip)

        # the dependencies
        self.test_task4.status = self.status_cmpl
        self.test_task6.status = self.status_cmpl
        self.test_task7.status = self.status_wip
        self.assertEqual(self.test_task4.status, self.status_cmpl)
        self.assertEqual(self.test_task6.status, self.status_cmpl)
        self.assertEqual(self.test_task7.status, self.status_wip)
        self.test_task5.depends.append(self.test_task4)
        self.test_task5.depends.append(self.test_task6)
        self.test_task5.depends.append(self.test_task7)

        task.update_task_statuses_with_dependencies(self.test_task5)
        self.assertEqual(self.test_task5.status, self.status_wip)

    def test_update_task_statuses_with_dependencies_with_half_completed_dependencies_and_status_prev(self):
        """testing if the task status will be not changed if the task status is
        not NEW even if dependencies are still not all CMPL, this is for
        backward compatibility
        """
        # the hero task
        self.test_task5.status = self.status_prev
        self.assertEqual(self.test_task5.status, self.status_prev)

        # the dependencies
        self.test_task4.status = self.status_cmpl
        self.test_task6.status = self.status_cmpl
        self.test_task7.status = self.status_wip
        self.assertEqual(self.test_task4.status, self.status_cmpl)
        self.assertEqual(self.test_task6.status, self.status_cmpl)
        self.assertEqual(self.test_task7.status, self.status_wip)
        self.test_task5.depends.append(self.test_task4)
        self.test_task5.depends.append(self.test_task6)
        self.test_task5.depends.append(self.test_task7)

        task.update_task_statuses_with_dependencies(self.test_task5)
        self.assertEqual(self.test_task5.status, self.status_prev)

    def test_update_task_statuses_with_dependencies_with_half_completed_dependencies_and_status_hrev(self):
        """testing if the task status will be not changed if the task status is
        not NEW even if dependencies are still not all CMPL, this is for
        backward compatibility
        """
        # the hero task
        self.test_task5.status = self.status_hrev
        self.assertEqual(self.test_task5.status, self.status_hrev)

        # the dependencies
        self.test_task4.status = self.status_cmpl
        self.test_task6.status = self.status_cmpl
        self.test_task7.status = self.status_wip
        self.assertEqual(self.test_task4.status, self.status_cmpl)
        self.assertEqual(self.test_task6.status, self.status_cmpl)
        self.assertEqual(self.test_task7.status, self.status_wip)
        self.test_task5.depends.append(self.test_task4)
        self.test_task5.depends.append(self.test_task6)
        self.test_task5.depends.append(self.test_task7)

        task.update_task_statuses_with_dependencies(self.test_task5)
        self.assertEqual(self.test_task5.status, self.status_hrev)

    def test_update_task_statuses_with_dependencies_with_half_completed_dependencies_and_status_cmpl(self):
        """testing if the task status will be not changed if the task status is
        not NEW even if dependencies are still not all CMPL, this is for
        backward compatibility
        """
        # the hero task
        self.test_task5.status = self.status_cmpl
        self.assertEqual(self.test_task5.status, self.status_cmpl)

        # the dependencies
        self.test_task4.status = self.status_cmpl
        self.test_task6.status = self.status_cmpl
        self.test_task7.status = self.status_wip
        self.assertEqual(self.test_task4.status, self.status_cmpl)
        self.assertEqual(self.test_task6.status, self.status_cmpl)
        self.assertEqual(self.test_task7.status, self.status_wip)
        self.test_task5.depends.append(self.test_task4)
        self.test_task5.depends.append(self.test_task6)
        self.test_task5.depends.append(self.test_task7)

        task.update_task_statuses_with_dependencies(self.test_task5)
        self.assertEqual(self.test_task5.status, self.status_cmpl)

