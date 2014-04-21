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
import shutil

import tempfile
import mocker
import os
from pyramid import testing
from pyramid.testing import DummyRequest
import unittest2

from stalker import (db, defaults, Link, Status, StatusList, Type, Repository,
                     User, FilenameTemplate, Structure, Project, Task)
from stalker_pyramid.views import get_logged_in_user
from stalker_pyramid.views.link import (ImageData, ImgToLinkConverter,
                                        MediaManager, upload_files,
                                        assign_reference)

from tests import DummyMultiDict, DummyFileParam

here = os.path.abspath(os.path.dirname(__file__))


class ImageDataTestCase(unittest2.TestCase):
    """tests the ImageData class
    """

    def test_parse_is_working_properly(self):
        """testing if the parse method is working properly
        """
        data = "data:image/jpeg;base64,/9j/4QA6RXhpZgAA"
        img_data = ImageData(data)
        img_data.parse()
        self.assertEqual(img_data.raw_data, data)
        self.assertEqual(img_data.type, 'image/jpeg')
        self.assertEqual(img_data.extension, '.jpeg')
        self.assertEqual(img_data.base64_data, '/9j/4QA6RXhpZgAA')


class ImgToLinkConverterTestCase(unittest2.TestCase):
    """tests the ImgToLinkConverter class
    """

    def setUp(self):
        """set up the test
        """
        defaults.server_side_storage_path = tempfile.mkdtemp()

    def tearDown(self):
        """clean up the test
        """
        shutil.rmtree(defaults.server_side_storage_path)

    def test_img_to_link_converter_is_working_properly(self):
        """testing if the ImgToLinkConverterTestCase is working properly
        """
        raw_data = '<img src="%s" ' \
                   'class="" style="margin: 0px; resize: none; position: ' \
                   'relative; zoom: 1; display: block; height: 234px; ' \
                   'width: 266px; top: auto; left: auto;"><div>asfd</div>' \
                   '<div style="text-align: left;">asdfas</div><div><b>dfas' \
                   '</b></div><div><b>dfa</b></div><div><b>sa</b></div><div>' \
                   'fda</div>'

        base64_data = 'data:image/jpeg;base64,/9j/4QA6RXhpZgAA'

        parser = ImgToLinkConverter()
        parser.feed(raw_data % base64_data)
        parser.replace_urls()

        self.assertEqual(len(parser.links), 1)
        self.assertIsInstance(parser.links[0], Link)

        link_path = '/%s' % parser.links[0].full_path
        replaced_data = raw_data % link_path

        self.assertEqual(parser.raw_data, replaced_data)


class LinkTestCase(unittest2.TestCase):
    """tests Link functions
    """

    def setUp(self):
        """setup the test
        """
        # setup test database
        self.config = testing.setUp()
        db.setup({'sqlalchemy.url': 'sqlite:///:memory:'})
        db.init()

        defaults.server_side_storage_path = tempfile.mkdtemp()
        self.temp_test_data_folder = tempfile.mkdtemp()
        self.test_repo_path = tempfile.mkdtemp()

        self.status_wfd = Status.query.filter_by(code="WFD").first()
        self.status_rts = Status.query.filter_by(code="RTS").first()
        self.status_wip = Status.query.filter_by(code="WIP").first()
        self.status_prev = Status.query.filter_by(code="PREV").first()
        self.status_hrev = Status.query.filter_by(code="HREV").first()
        self.status_drev = Status.query.filter_by(code="DREV").first()
        self.status_oh = Status.query.filter_by(code="OH").first()
        self.status_stop = Status.query.filter_by(code="STOP").first()
        self.status_cmpl = Status.query.filter_by(code="CMPL").first()

        self.task_status_list = StatusList.query\
            .filter_by(target_entity_type='Task').first()

        self.test_project_status_list = StatusList(
            name="Project Statuses",
            statuses=[self.status_wip,
                      self.status_prev,
                      self.status_cmpl],
            target_entity_type='Project',
        )
        db.DBSession.add(self.test_project_status_list)

        self.test_movie_project_type = Type(
            name="Movie Project",
            code='movie',
            target_entity_type='Project',
        )
        db.DBSession.add(self.test_movie_project_type)

        self.test_repository_type = Type(
            name="Test Repository Type",
            code='test',
            target_entity_type='Repository',
        )
        db.DBSession.add(self.test_repository_type)

        self.test_repository = Repository(
            name="Test Repository",
            type=self.test_repository_type,
            linux_path=self.test_repo_path,
            windows_path=self.test_repo_path,
            osx_path=self.test_repo_path
        )
        db.DBSession.add(self.test_repository)

        self.test_user1 = User(
            name="User1",
            login="user1",
            email="user1@user1.com",
            password="1234"
        )
        db.DBSession.add(self.test_user1)

        self.test_ft = FilenameTemplate(
            name='Task Filename Template',
            target_entity_type='Task',
            path='{{project.code}}/{%- for parent_task in parent_tasks -%}'
                 '{{parent_task.nice_name}}/{%- endfor -%}',
            filename='{{task.nice_name}}_{{version.take_name}}'
                     '_v{{"%03d"|format(version.version_number)}}{{extension}}'
        )
        db.DBSession.add(self.test_ft)

        self.test_structure = Structure(
            name='Movie Project Structure',
            templates=[self.test_ft]
        )
        db.DBSession.add(self.test_structure)

        self.test_project1 = Project(
            name="Test Project1",
            code='tp1',
            type=self.test_movie_project_type,
            status_list=self.test_project_status_list,
            repository=self.test_repository,
            structure=self.test_structure,
            lead=self.test_user1
        )
        db.DBSession.add(self.test_project1)

        self.test_task1 = Task(
            name='Test Task 1',
            project=self.test_project1
        )
        db.DBSession.add(self.test_task1)

        self.test_task2 = Task(
            name='Test Task 2',
            parent=self.test_task1
        )
        db.DBSession.add(self.test_task2)

        # create test data
        self.test_base_image_path = os.path.join(
            here,
            'test_data/test_image.png'
        )

        # create test image
        self.test_image_path = os.path.join(
            self.temp_test_data_folder,
            'test_image.png'
        )
        shutil.copy(self.test_base_image_path, self.test_image_path)

        # create image sequence
        self.test_image_sequence_path = []
        for i in range(10):
            image_path = os.path.join(
                self.temp_test_data_folder,
                'test_image_%03d.png' % i
            )
            shutil.copy(self.test_base_image_path, image_path)
            self.test_image_sequence_path.append(image_path)

        self.test_media_manager = MediaManager()

        # create mp4 video
        self.test_video_path_mp4 = os.path.join(
            self.temp_test_data_folder,
            'test_image.mp4'
        )

        self.test_media_manager.ffmpeg(**{
            'i': os.path.join(
                self.temp_test_data_folder,
                'test_image_%03d.png'
            ),
            'vcodec': 'libx264',
            'b:v': '1024k',
            'o': self.test_video_path_mp4
        })

        # create mov video
        self.test_video_path_mov = os.path.join(
            self.temp_test_data_folder,
            'test_image.mov'
        )

        self.test_media_manager.ffmpeg(**{
            'i': os.path.join(
                self.temp_test_data_folder,
                'test_image_%03d.png'
            ),
            'vcodec': 'libx264',
            'b:v': '1024k',
            'o': self.test_video_path_mov
        })

        # create mpg video
        self.test_video_path_mpg = os.path.join(
            self.temp_test_data_folder,
            'test_image.mpg'
        )

        self.test_media_manager.ffmpeg(**{
            'i': os.path.join(
                self.temp_test_data_folder,
                'test_image_%03d.png'
            ),
            'b:v': '1024k',
            'o': self.test_video_path_mpg
        })
        db.DBSession.flush()
        db.DBSession.commit()
        # transaction.commit()

    def tearDown(self):
        """clean up the test
        """
        shutil.rmtree(defaults.server_side_storage_path)

        # remove generic_temp_folder
        shutil.rmtree(self.temp_test_data_folder, ignore_errors=True)

        # remove repository
        shutil.rmtree(self.test_repo_path, ignore_errors=True)

        # clean up test database
        # from stalker.db.declarative import Base
        # Base.metadata.drop_all(db.DBSession.connection())
        # db.DBSession.commit()
        db.DBSession.remove()
        testing.tearDown()

    def test_upload_files_is_working_properly_for_single_file(self):
        """testing if views.link.upload_files() will just accept files and save
        them to a temp place and return file info as JSON data
        """
        request = DummyRequest()
        request.params = DummyMultiDict()
        request.POST = request.params
        original_filename = os.path.basename(self.test_image_path)
        request.params['file'] = [
            DummyFileParam(
                filename=original_filename,
                file=open(self.test_image_path)
            )
        ]

        # patch get_logged_in_user
        admin = User.query.filter(User.login == 'admin').first()
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(admin)
        m.replay()

        response = upload_files(request)
        self.assertEqual(
            response,
            {
                'files': [{
                    'original_filename': original_filename,
                    'full_path': response['files'][0]['full_path']  # not a
                }]                                                  # good way
            }                                                       # to test
        )

    def test_assign_reference_is_working_properly_for_single_file(self):
        """testing if views.link.assign_reference() is working properly for a
        single file setup
        """
        request = DummyRequest()
        request.params = DummyMultiDict()
        request.POST = request.params
        original_filename = os.path.basename(self.test_image_path)
        request.params['files[]'] = [
            DummyFileParam(
                filename=original_filename,
                file=open(self.test_image_path)
            )
        ]

        # patch get_logged_in_user
        admin = User.query.filter(User.login == 'admin').first()
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(admin)
        m.replay()

        response = assign_reference(request)
        self.assertEqual(
            response,
            {
                'files': [{
                    'original_filename': original_filename,
                    'full_path': response['files'][0]['full_path']  # not a
                }]                                                  # good way
            }                                                       # to test
        )
