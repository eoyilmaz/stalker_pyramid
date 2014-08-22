# -*- coding: utf-8 -*-
# Stalker Pyramid a Web Base Production Asset Management System
# Copyright (C) 2009-2014 Erkan Ozgur Yilmaz
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

import unittest
import transaction

from pyramid import testing
from pyramid.httpexceptions import HTTPServerError

from stalker import (db, Project, Status, StatusList, Repository, Task, User,
                     Asset, Type, TimeLog, Ticket)
from stalker.db.session import DBSession

from stalker_pyramid.views import task, milliseconds_since_epoch, local_to_utc

import logging
from stalker_pyramid.testing import DummyMultiDict

logger = logging.getLogger(__name__)


class TaskViewTestCase(unittest.TestCase):
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
        self.status_new = Status.query.filter_by(code='NEW').first()
        self.status_wts = Status.query.filter_by(code='WTS').first()
        self.status_rts = Status.query.filter_by(code='RTS').first()
        self.status_wip = Status.query.filter_by(code='WIP').first()
        self.status_prev = Status.query.filter_by(code='PREV').first()
        self.status_hrev = Status.query.filter_by(code='HREV').first()
        self.status_drev = Status.query.filter_by(code='DREV').first()
        self.status_cmpl = Status.query.filter_by(code='CMPL').first()

        self.test_project_status_list = StatusList(
            name='Project Statuses',
            target_entity_type='Project',
            statuses=[self.status_new, self.status_wip,
                      self.status_cmpl]
        )
        DBSession.add(self.test_project_status_list)

        self.test_task_statuses = \
            StatusList.query.filter_by(target_entity_type='Task').first()

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
            resources=[self.test_user2],
            start=datetime.datetime(2013, 6, 20, 0, 0),
            end=datetime.datetime(2013, 6, 30, 0, 0),
            schedule_model='effort',
            schedule_timing=10,
            schedule_unit='d'
        )
        DBSession.add(self.test_task8)

        self.test_asset_status_list = \
            StatusList.query.filter_by(target_entity_type='Asset').first()

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

        # --------------
        # Task Hierarchy
        # --------------
        #
        # +-> Test Task 1
        # |   |
        # |   +-> Test Task 4
        # |   |
        # |   +-> Test Task 5
        # |   |
        # |   +-> Test Task 6
        # |
        # +-> Test Task 2
        # |   |
        # |   +-> Test Task 7
        # |   |   |
        # |   |   +-> Test Asset 1
        # |   |       |
        # |   |       +-> Test Task 9
        # |   |
        # |   +-> Test Task 8
        # |
        # +-> Test Task 3

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

    def test_find_leafs_in_hierarchy_is_working_properly(self):
        """testing if the find_leafs_in_hierarchy() is working properly
        """
        expected = [self.test_task7]
        result = task.find_leafs_in_hierarchy(self.test_task2)
        self.assertItemsEqual(expected, result)

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
        # self.assertEqual(dup_task2.timing_resolution,
        #                  self.test_task2.timing_resolution)
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

    def test_request_review_updates_previous_ticket(self):
        """testing if the request_review() will find and update the previous
        ticket
        """
        # create a time log before asking review
        time_log = TimeLog(
            resource=self.test_task4.resources[0],
            task=self.test_task4,
            start=datetime.datetime(2013, 6, 20, 10, 0),
            end=datetime.datetime(2013, 6, 20, 19, 0)
        )
        utc_now = local_to_utc(datetime.datetime.now())
        time_log.date_created = utc_now
        self.test_task4.date_created = utc_now

        DBSession.add(time_log)
        self.test_task4.status = self.status_wip

        # create a Ticket to check if the Ticket is going to be updated with
        # the revision
        review_type = Type(target_entity_type='Ticket', name='Review',
                           code='Review')
        db.DBSession.add(review_type)

        ticket = Ticket(
            project=self.test_task4.project,
            type=review_type,
            description='Test Ticket',
            date_created=utc_now
        )
        ticket.links.append(self.test_task4)
        # also resolve the ticket
        ticket.resolve(self.test_task4.resources[0], 'fixed')
        db.DBSession.add(ticket)
        db.DBSession.commit()

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

        # check if the ticket is reopened
        self.assertEqual(
            ticket.status, Status.query.filter_by(name='Reopened').first()
        )

        # and check if there is a new comment on the ticket with the supplied
        # text
        comment = ticket.comments[0]
        # assert isinstance(comment, Note)
        self.assertEqual(
            comment.content,
            '%(description)s' % {
                'description': u'<a href="/tasks/23/view">Test User 1</a> '
                               u'has requested you to do a review for '
                               u'<a href="/tasks/23/view">Test Task 4 (Task) '
                               u'- (Test Task 1)</a>'
            }
        )

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
        utc_now = local_to_utc(datetime.datetime.now())
        time_log.date_created = utc_now
        self.test_task4.date_created = utc_now

        DBSession.add(time_log)
        self.test_task4.status = self.status_prev

        # request revision for self.test_task4
        request = testing.DummyRequest()
        request.matchdict['id'] = self.test_task4.id
        description = 'This is the test description'
        request.params['description'] = description
        request.params['send_email'] = 0
        request.params['schedule_timing'] = 5
        request.params['schedule_unit'] = 'd'
        request.params['schedule_model'] = 'effort'

        # patch get_logged_in_user
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(self.test_task4.resources[0])
        m.replay()

        # create a Ticket to check if the Ticket is going to be updated with
        # the revision
        review_type = Type(target_entity_type='Ticket', name='Review',
                           code='Review')
        db.DBSession.add(review_type)

        ticket = Ticket(
            project=self.test_task4.project,
            type=review_type,
            description='Test Ticket',
            date_created=utc_now
        )
        ticket.links.append(self.test_task4)
        # also resolve the ticket
        ticket.resolve(self.test_task4.resources[0], 'fixed')
        db.DBSession.add(ticket)
        db.DBSession.commit()

        # also patch route_url of request
        request.route_url = lambda x, id: 'localhost:6453/tasks/23/view'

        response = task.request_revision(request)
        logger.debug(response.body)
        self.assertEqual(response.status_int, 200)

        # check if the status of the original task is set to Has Revision
        self.assertEqual(self.test_task4.status, self.status_hrev)

        # # check if the task percent_complete is 100
        # assert isinstance(self.test_task4, Task)
        # self.assertEqual(self.test_task4.percent_complete, 100)
        # check if the task is extended with the given revision timing
        self.assertEqual(
            self.test_task4.schedule_timing,
            54
        )
        # and the unit is converted to hours
        self.assertEqual(
            self.test_task4.schedule_unit,
            'h'
        )

        # check if the task dependency list is intact
        self.assertItemsEqual(
            self.test_task4.depends,
            [self.test_task3]
        )

        # check if the dependent tasks are intact
        self.assertItemsEqual(
            self.test_task4.dependent_of, [self.test_task5]
        )

        # and check if there is a new comment on the ticket with the supplied
        # text
        comment = ticket.comments[0]
        # assert isinstance(comment, Note)
        self.assertEqual(
            comment.content,
            '%(description)s' % {
                'description': description
            }
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

    def test_create_task_updates_the_status_correctly(self):
        """testing if create_task() will create new tasks with correct status
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
        request.params['dependent_ids'] = []

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


class TaskViewSimpleFunctionsTestCase(unittest.TestCase):
    """tests the simple functions that doesn't need a request
    """

    def test_generate_where_clause_case1(self):
        """testing if the view.tasks.generate_where_clause() is working
        properly
        """
        test_value = {
            'id': [23],
            'name': ['Lighting'],
            'entity_type': ['Task'],
            'task_type': ['Lighting'],
            'resource_name': ['Ozgur']
        }

        result = task.generate_where_clause(test_value)

        self.assertEqual("""where (
    tasks.id = 23
    and (tasks.name ilike '%Lighting%' or tasks.full_path ilike '%Lighting%')
    and tasks.entity_type = 'Task'
    and task_types.name ilike '%Lighting%'
    and exists (
        select * from (
            select unnest(resource_info.resource_name)
        ) x(resource_name)
        where x.resource_name like '%Ozgur%'
    )
)""", result)

    def test_generate_where_clause_case2(self):
        """testing if the view.tasks.generate_where_clause() is working
        properly
        """
        test_value = {
            'id': [23],
            'task_type': ['Lighting'],
            'resource_name': ['Ozgur']
        }

        result = task.generate_where_clause(test_value)

        self.assertEqual("""where (
    tasks.id = 23
    and task_types.name ilike '%Lighting%'
    and exists (
        select * from (
            select unnest(resource_info.resource_name)
        ) x(resource_name)
        where x.resource_name like '%Ozgur%'
    )
)""", result)

    def test_generate_where_clause_case3(self):
        """testing if the view.tasks.generate_where_clause() is working
        properly
        """
        test_value = {
            'resource_name': ['Ozgur']
        }

        result = task.generate_where_clause(test_value)

        self.assertEqual("""where (
    exists (
        select * from (
            select unnest(resource_info.resource_name)
        ) x(resource_name)
        where x.resource_name like '%Ozgur%'
    )
)""", result)

    def test_generate_where_clause_case4(self):
        """testing if the view.tasks.generate_where_clause() is working
        properly
        """
        test_value = {
            'resource_id': [26]
        }

        result = task.generate_where_clause(test_value)

        self.assertEqual("""where (
    exists (
        select * from (
            select unnest(resource_info.resource_id)
        ) x(resource_id)
        where x.resource_id = 26
    )
)""", result)

    def test_generate_where_clause_case5(self):
        """testing if the view.tasks.generate_where_clause() is working
        properly
        """
        test_value = {
            'task_type': ['Lighting', 'Comp'],
        }

        result = task.generate_where_clause(test_value)

        self.assertEqual("""where (
    task_types.name = '%Lighting%'
    and task_types.name = '%Comp%'
)""", result)

    def test_generate_where_clause_case6(self):
        """testing if the view.tasks.generate_where_clause() is working
        properly
        """
        test_value = {
            'project_id': [23],
        }

        result = task.generate_where_clause(test_value)

        self.assertEqual("""where (
    "Tasks".project_id = 23
)""", result)

    def test_generate_where_clause_case7(self):
        """testing if the view.tasks.generate_where_clause() is working
        properly
        """
        test_value = {
            'status': ['WIP', 'DREV'],
        }

        result = task.generate_where_clause(test_value)

        self.assertEqual("""where (
    "Statuses".code ilike '%WIP%'
    and "Statuses".code ilike '%DREV%'
)""", result)

    def test_generate_where_clause_case8(self):
        """testing if the view.tasks.generate_where_clause() is working
        properly
        """
        test_value = {
            'status': ['WIP', 'DREV'],
            'leaf_only': 1
        }

        result = task.generate_where_clause(test_value)

        self.assertEqual("""where (
    "Statuses".code ilike '%WIP%'
    and "Statuses".code ilike '%DREV%'
    and not exists (
        select 1 from "Tasks"
        where "Tasks".parent_id = tasks.id
    )
)""", result)

    def test_generate_where_clause_case9(self):
        """testing if the view.tasks.generate_where_clause() is working
        properly
        """
        test_value = {
            'leaf_only': 1
        }

        result = task.generate_where_clause(test_value)

        self.assertEqual("""where (
    not exists (
        select 1 from "Tasks"
        where "Tasks".parent_id = tasks.id
    )
)""", result)

    def test_generate_where_clause_case10(self):
        """testing if the view.tasks.generate_where_clause() is working
        properly
        """
        test_value = {
            'responsible_id': [25, 26]
        }

        result = task.generate_where_clause(test_value)

        self.assertEqual("""where (
    25 = any (tasks.responsible_id)
    and 26 = any (tasks.responsible_id)
)""", result)

    def test_generate_where_clause_case11(self):
        """testing if the view.tasks.generate_where_clause() is working
        properly
        """
        test_value = {
            'has_resource': 1
        }

        result = task.generate_where_clause(test_value)

        self.assertEqual("""where (
    resource_info.info is not NULL
)""", result)

    def test_generate_where_clause_case12(self):
        """testing if the view.tasks.generate_where_clause() is working
        properly
        """
        test_value = {
            'has_no_resource': 1
        }

        result = task.generate_where_clause(test_value)

        self.assertEqual("""where (
    resource_info.info is NULL
)""", result)

    def test_generate_where_clause_case13(self):
        """testing if the view.tasks.generate_where_clause() is working
        properly
        """
        test_value = {
            'watcher_id': [26]
        }

        result = task.generate_where_clause(test_value)

        self.assertEqual("""where (
    26 = any (tasks.watcher_id)
)""", result)

    def test_generate_order_by_clause_case_1(self):
        """testing if the view.tasks.generate_order_by_clause() is working
        properly
        """
        test_value = [
            'id', 'name', 'full_path', 'parent_id',
            'resource', 'status', 'project_id',
            'task_type', 'entity_type', 'percent_complete'
        ]

        result = task.generate_order_by_clause(test_value)
        self.assertEqual(
            """order by tasks.id, tasks.name, tasks.full_path, """
            """tasks.parent_id, resource_info.info, "Statuses".code, """
            """"Tasks".project_id, task_types.name, tasks.entity_type, """
            """percent_complete""", result
        )


class TaskForceStatusTestCase(unittest.TestCase):
    """tests views.task.force_task_status function
    """

    def setUp(self):
        """set the test up
        """

        db.setup()
        db.init()

        self.status_new = Status.query.filter_by(code='NEW').first()
        self.status_wfd = Status.query.filter_by(code='WFD').first()
        self.status_rts = Status.query.filter_by(code='RTS').first()
        self.status_wip = Status.query.filter_by(code='WIP').first()
        self.status_prev = Status.query.filter_by(code='PREV').first()
        self.status_hrev = Status.query.filter_by(code='HREV').first()
        self.status_drev = Status.query.filter_by(code='DREV').first()
        self.status_stop = Status.query.filter_by(code='STOP').first()
        self.status_oh = Status.query.filter_by(code='OH').first()
        self.status_cmpl = Status.query.filter_by(code='CMPL').first()

        self.test_project_statuses = StatusList(
            name='Project Statuses',
            target_entity_type='Project',
            statuses=[self.status_new, self.status_wip, self.status_cmpl]
        )

        self.test_repo = Repository(
            name='Test Repository'
        )

        self.test_project = Project(
            name='Test Project',
            code='TP',
            status_list=self.test_project_statuses,
            repository=self.test_repo
        )

        self.test_task1 = Task(name='Task1', project=self.test_project)

        DBSession.add_all([self.test_project])
        DBSession.commit()

    def test_force_status_in_WFD_task(self):
        """testing if a force_status() will return a response with code 500 if
        the task is an WFD task
        """
        self.test_task1.status = self.status_wfd

        request = testing.DummyRequest()
        request.matchdict = {
            'id': self.test_task1.id,
            'status_code':'CMPL'
        }
        response = task.force_task_status(request)

        self.assertEqual(response.status_code, 500)

        self.assertEqual(response.text, 'Cannot force WFD tasks')

    def test_force_status_in_RTS_task(self):
        """testing if a force_status() will return a response with code 500 if
        the task is an RTS task
        """
        self.test_task1.status = self.status_rts

        request = testing.DummyRequest()
        request.matchdict = {
            'id': self.test_task1.id,
            'status_code':'CMPL'
        }
        response = task.force_task_status(request)

        self.assertEqual(response.status_code, 500)

        self.assertEqual(response.text, 'Cannot force RTS tasks')

    def test_force_status_in_DREV_task(self):
        """testing if a force_status() will return a response with code 500 if
        the task is an DREV task
        """
        self.test_task1.status = self.status_drev

        request = testing.DummyRequest()
        request.matchdict = {
            'id': self.test_task1.id,
            'status_code':'CMPL'
        }
        response = task.force_task_status(request)

        self.assertEqual(response.status_code, 500)

        self.assertEqual(response.text, 'Cannot force DREV tasks')

    def test_force_status_in_PREV_task(self):
        """testing if a force_status() will return a response with code 500 if
        the task is an PREV task
        """
        self.test_task1.status = self.status_prev

        request = testing.DummyRequest()
        request.matchdict = {
            'id': self.test_task1.id,
            'status_code':'CMPL'
        }
        response = task.force_task_status(request)

        self.assertEqual(response.status_code, 500)

        self.assertEqual(response.text, 'Cannot force PREV tasks')

    def test_force_status_task_to_WFD(self):
        """testing if a force_status() will return a response with code 500 if
        new status code is WFD
        """
        self.test_task1.status = self.status_wip

        request = testing.DummyRequest()
        request.matchdict = {
            'id': self.test_task1.id,
            'status_code':'WFD'
        }
        response = task.force_task_status(request)

        self.assertEqual(response.status_code, 500)

        self.assertEqual(response.text, 'Can not set status to: WFD')

    def test_force_status_task_to_RTS(self):
        """testing if a force_status() will return a response with code 500 if
        new status code is RTS
        """
        self.test_task1.status = self.status_wip

        request = testing.DummyRequest()
        request.matchdict = {
            'id': self.test_task1.id,
            'status_code':'RTS'
        }
        response = task.force_task_status(request)

        self.assertEqual(response.status_code, 500)

        self.assertEqual(response.text, 'Can not set status to: RTS')

    def test_force_status_task_to_WIP(self):
        """testing if a force_status() will return a response with code 500 if
        new status code is WIP
        """
        self.test_task1.status = self.status_wip

        request = testing.DummyRequest()
        request.matchdict = {
            'id': self.test_task1.id,
            'status_code':'WIP'
        }
        response = task.force_task_status(request)

        self.assertEqual(response.status_code, 500)

        self.assertEqual(response.text, 'Can not set status to: WIP')

    def test_force_status_task_to_HREV(self):
        """testing if a force_status() will return a response with code 500 if
        new status code is HREV
        """
        self.test_task1.status = self.status_wip

        request = testing.DummyRequest()
        request.matchdict = {
            'id': self.test_task1.id,
            'status_code':'HREV'
        }
        response = task.force_task_status(request)

        self.assertEqual(response.status_code, 500)

        self.assertEqual(response.text, 'Can not set status to: HREV')

    def test_force_status_task_to_PREV(self):
        """testing if a force_status() will return a response with code 500 if
        new status code is PREV
        """
        self.test_task1.status = self.status_wip

        request = testing.DummyRequest()
        request.matchdict = {
            'id': self.test_task1.id,
            'status_code':'PREV'
        }
        response = task.force_task_status(request)

        self.assertEqual(response.status_code, 500)

        self.assertEqual(response.text, 'Can not set status to: PREV')

    def test_force_status_task_to_DREV(self):
        """testing if a force_status() will return a response with code 500 if
        new status code is DREV
        """
        self.test_task1.status = self.status_wip

        request = testing.DummyRequest()
        request.matchdict = {
            'id': self.test_task1.id,
            'status_code':'DREV'
        }
        response = task.force_task_status(request)

        self.assertEqual(response.status_code, 500)

        self.assertEqual(response.text, 'Can not set status to: DREV')

    def test_task_schedule_timing_values_are_trimmed(self):
        """testing if the task.schedule_timing value is trimmed to the total
        logged seconds value
        """
        self.fail('test is not implemented yet')
