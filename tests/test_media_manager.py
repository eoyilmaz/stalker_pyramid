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
import os
from pyramid import testing

import unittest2
import shutil
import tempfile

from stalker import db, defaults, Link, Repository, Structure, FilenameTemplate, \
    Status, StatusList, Type, User, Project, Task, Version
from stalker_pyramid.views.link import MediaManager


here = os.path.abspath(os.path.dirname(__file__))


class MediaManagerTestCase(unittest2.TestCase):
    """tests the stalker_pyramid.views.link.MediaManager class
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

    def test_convert_file_link_to_full_path_link_path_is_not_a_string(self):
        """testing if a TypeError will be raised when the given link_path is
        not a string
        """
        with self.assertRaises(TypeError) as cm:
            self.test_media_manager.convert_file_link_to_full_path(1)

        self.assertEqual(
            '"link_path" argument in '
            'MediaManager.convert_file_link_to_full_path() method should be '
            'a str, not int',
            cm.exception.message
        )

    # def test_convert_file_link_to_full_path_link_path_is_not_starting_with_spl(self):
    #     """testing if a ValueError will be raised when the given link_path
    #     argument value is not starting with "SPL"
    #     """
    #     with self.assertRaises(ValueError) as cm:
    #         self.test_media_manager.convert_file_link_to_full_path(
    #             '/home/stalker/Not starting with spl/'
    #         )
    # 
    #     self.assertEqual(
    #         '"link_path" argument in '
    #         'MediaManager.convert_file_link_to_full_path() method should be '
    #         'a str starting with "SPL/"',
    #         cm.exception.message
    #     )

    def test_convert_file_link_to_full_path_is_working_properly(self):
        """testing if MediaManager.convert_file_link_to_full_path() method will
        generate correct absolute path from the given SPL relative path.
        """
        test_value = 'SPL/aa/bb/aabbccddee.ff'
        expected_value = '%s/aa/bb/aabbccddee.ff' % \
            defaults.server_side_storage_path
        self.assertEqual(
            expected_value,
            self.test_media_manager.convert_file_link_to_full_path(test_value)
        )

    def test_convert_full_path_to_file_link_full_path_is_not_a_string(self):
        """testing if a TypeError will be raised when the given full_path is
        not a string
        """
        with self.assertRaises(TypeError) as cm:
            self.test_media_manager.convert_full_path_to_file_link(1)

        self.assertEqual(
            '"full_path" argument in '
            'MediaManager.convert_full_path_to_file_link() method should be '
            'a str, not int',
            cm.exception.message
        )

    def test_convert_full_path_to_file_link_full_path_is_not_starting_with_spl(self):
        """testing if a ValueError will be raised when the given full_path
        argument value is not starting with "SPL"
        """
        with self.assertRaises(ValueError) as cm:
            self.test_media_manager.convert_full_path_to_file_link(
                '/home/stalker/Not starting with spl/'
            )

        self.assertEqual(
            '"full_path" argument in '
            'MediaManager.convert_full_path_to_file_link() method should be '
            'a str starting with "%s"' % defaults.server_side_storage_path,
            cm.exception.message
        )

    def test_convert_full_path_to_file_link_is_working_properly(self):
        """testing if MediaManager.convert_full_path_to_file_link() method will
        generate correct SPL relative path from the given absolute path.
        """
        test_value = '%s/aa/bb/aabbccddee.ff' % \
            defaults.server_side_storage_path
        expected_value = 'SPL/aa/bb/aabbccddee.ff'
        self.assertEqual(
            expected_value,
            self.test_media_manager.convert_full_path_to_file_link(test_value)
        )

    def test_get_video_info_is_working_properly(self):
        """testing if the MediaManager.get_video_info() method is working
        properly
        """
        result = self.test_media_manager.get_video_info(
            self.test_video_path_mp4
        )
        self.assertEqual(
            result,
            {
                'video_info': {
                    'TAG:encoder': 'Lavf55.19.104',
                    'nb_streams': '1',
                    'start_time': '0.000000',
                    'format_long_name':
                        'QuickTime/MPEG-4/Motion JPEG 2000 format',
                    'format_name': 'mov,mp4,m4a,3gp,3g2,mj2',
                    'filename': self.test_video_path_mp4,
                    'TAG:compatible_brands': 'isomiso2avc1mp41',
                    'bit_rate': '2163440.000000',
                    'TAG:major_brand': 'isom',
                    'duration': '0.400000',
                    'TAG:minor_version': '512',
                    'size': '108172.000000'
                },
                'stream_info': [
                    {
                        'pix_fmt': 'yuv444p',
                        'index': '0',
                        'codec_tag': '0x31637661',
                        'level': '30',
                        'r_frame_rate': '25/1',
                        'start_time': '0.000000',
                        'time_base': '1/12800',
                        'codec_tag_string': 'avc1',
                        'codec_type': 'video',
                        'has_b_frames': '2',
                        'width': '640',
                        'codec_name': 'h264',
                        'codec_long_name':
                            'H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10',
                        'display_aspect_ratio': '8:5',
                        'sample_aspect_ratio': '1:1',
                        'TAG:language': 'und',
                        'height': '400',
                        'nb_frames': '10',
                        'codec_time_base': '1/50',
                        'duration': '0.320000',
                        'avg_frame_rate': '125/4'
                    }
                ]
            }
        )

    def test_generate_thumbnail_with_image_files_is_working_properly(self):
        """testing if MediaManager.generate_thumbnail() is working properly for
        image files
        """
        thumbnail_path = \
            self.test_media_manager.generate_thumbnail(self.test_image_path)

        # check if thumbnail is properly generated
        self.assertTrue(os.path.exists(thumbnail_path))

        # check if the thumbnail format is the default thumbnail format
        self.assertEqual(
            os.path.splitext(thumbnail_path)[1],
            self.test_media_manager.thumbnail_format
        )

    def test_generate_thumbnail_with_video_files_is_working_properly(self):
        """testing if MediaManager.generate_thumbnail() is working properly for
        video files
        """
        thumbnail_path = \
            self.test_media_manager.generate_thumbnail(
                self.test_video_path_mp4
                # '/home/eoyilmaz/Videos/14078313.mp4'
                # '/home/eoyilmaz/Videos/omo_MMR_30sn_040812.mov'
                # '/home/eoyilmaz/Videos/CG/BreakDowns/Commercials/Adidas-Carry/Carry_adidas_carry_60.mov'
                # '/home/eoyilmaz/Videos/Photography/Nikon_D3_vs_D3s.flv'
            )

        # check if thumbnail is properly generated
        self.assertTrue(os.path.exists(thumbnail_path))

        # check if the thumbnail format is the default thumbnail format
        self.assertEqual(
            os.path.splitext(thumbnail_path)[1],
            self.test_media_manager.thumbnail_format
        )

    def test_generate_thumbnail_with_a_file_which_is_not_an_image_nor_a_video(self):
        """testing if None will be returned from
        MediaManager.generate_thumbnail() method if the file extension is not
        among supported image formats nor in supported video formats
        """
        test_path = '/tmp/not_an_image_nor_a_video.obj'
        with self.assertRaises(RuntimeError) as cm:
            self.test_media_manager.generate_thumbnail(
                test_path
            )

        self.assertEqual(
            '%s is not an image nor a video file, can not generate a '
            'thumbnail for it!' % test_path,
            cm.exception.message
        )

    def test_upload_file_will_return_uploaded_file_full_path(self):
        """testing if uploading a file with MediaManager.upload_file() will
        return the path of the file in SPL.
        """
        with open(self.test_image_path) as f:
            return_val = self.test_media_manager.upload_file(f)

        # check if it is a string
        self.assertIsInstance(return_val, basestring)
        # check if it is an absolute path
        self.assertTrue(os.path.isabs(return_val))
        # check if it exists
        self.assertTrue(os.path.exists(return_val))

    def test_upload_reference_is_working_properly_for_image_files(self):
        """testing if MediaManager.upload_reference() is working properly for
        image files
        """
        # upload an image file as a reference
        with open(self.test_image_path) as f:
            link = self.test_media_manager.upload_reference(
                self.test_task2, f, 'test_image.png'
            )

        # now expect the return_val to be a Link instance
        self.assertIsInstance(link, Link)

        # check if it is in the given tasks references
        self.assertIn(link, self.test_task2.references)

        # expect the Link full_path to be:
        #   Task.path/References/Stalker_Pyramid/
        self.assertEqual(
            os.path.dirname(link.full_path),
            os.path.join(
                self.test_task2.path,
                'References/Stalker_Pyramid'
            )
        )

        # and the file exists there
        self.assertTrue(
            os.path.exists(
                os.path.join(
                    self.test_repository.path,
                    link.full_path
                )
            )
        )

        # expect the Link.thumbnail.full_path to be in
        #  Task.path/References/Stalker_Pyramid/ForWeb/
        self.assertEqual(
            os.path.dirname(link.thumbnail.full_path),
            os.path.join(
                self.test_task2.path,
                'References/Stalker_Pyramid/ForWeb'
            )
        )

        # and the file exists there
        self.assertTrue(
            os.path.exists(
                os.path.join(
                    self.test_repository.path,
                    link.thumbnail.full_path
                )
            )
        )

        # and expect the Link.thumbnail.thumbnail.full_path to be in
        #  Task.path/References/Stalker_Pyramid/Thumbnail/
        self.assertEqual(
            os.path.dirname(link.thumbnail.thumbnail.full_path),
            os.path.join(
                self.test_task2.path,
                'References/Stalker_Pyramid/Thumbnail'
            )
        )

        # and the file exists there
        self.assertTrue(
            os.path.exists(
                os.path.join(
                    self.test_repository.path,
                    link.thumbnail.thumbnail.full_path
                )
            )
        )

    def test_upload_reference_is_working_properly_for_video_files(self):
        """testing if MediaManager.upload_reference() is working properly for
        video files
        """
        # upload an image file as a reference
        with open(self.test_video_path_mp4) as f:
            link = self.test_media_manager.upload_reference(
                self.test_task2, f, 'test_video.mp4'
            )

        # now expect the return_val to be a Link instance
        self.assertIsInstance(link, Link)

        # check if it is in the given tasks references
        self.assertIn(link, self.test_task2.references)

        # expect the Link full_path to be:
        #   Task.path/References/Stalker_Pyramid/
        self.assertEqual(
            os.path.dirname(link.full_path),
            os.path.join(
                self.test_task2.path,
                'References/Stalker_Pyramid'
            )
        )

        # and the file exists there
        self.assertTrue(
            os.path.exists(
                os.path.join(
                    self.test_repository.path,
                    link.full_path
                )
            )
        )

        # expect the Link.thumbnail.full_path to be in
        #  Task.path/References/Stalker_Pyramid/ForWeb/
        self.assertEqual(
            os.path.dirname(link.thumbnail.full_path),
            os.path.join(
                self.test_task2.path,
                'References/Stalker_Pyramid/ForWeb'
            )
        )

        # and the file exists there
        self.assertTrue(
            os.path.exists(
                os.path.join(
                    self.test_repository.path,
                    link.thumbnail.full_path
                )
            )
        )

        # check the extension
        self.assertEqual(
            '.webm',
            os.path.splitext(link.thumbnail.full_path)[-1]
        )

        # and expect the Link.thumbnail.thumbnail.full_path to be in
        #  Task.path/References/Stalker_Pyramid/Thumbnail/
        self.assertEqual(
            os.path.dirname(link.thumbnail.thumbnail.full_path),
            os.path.join(
                self.test_task2.path,
                'References/Stalker_Pyramid/Thumbnail'
            )
        )

        # and the file exists there
        self.assertTrue(
            os.path.exists(
                os.path.join(
                    self.test_repository.path,
                    link.thumbnail.thumbnail.full_path
                )
            )
        )

        # check the extension
        self.assertEqual(
            '.jpg',
            os.path.splitext(link.thumbnail.thumbnail.full_path)[-1]
        )

    def test_upload_reference_there_is_a_file_with_the_same_name(self):
        """testing if the filename will be renamed to a suitable one if there
        is a file with the same name in MediaManager.upload_reference()
        """
        # create a temp file and ask to save over it
        # upload an image file as a reference
        with open(self.test_video_path_mp4) as f:
            link1 = self.test_media_manager.upload_reference(
                self.test_task2, f, 'test_video.mp4'
            )

        # do it again
        with open(self.test_video_path_mp4) as f:
            link2 = self.test_media_manager.upload_reference(
                self.test_task2, f, 'test_video.mp4'
            )

        self.assertNotEqual(link1.full_path, link2.full_path)
        self.assertEqual(
            'tp1/Test_Task_1/Test_Task_2/References/Stalker_Pyramid/'
            'test_video.mp4',
            link1.full_path
        )

        random_part = \
            link2.full_path[
                len('tp1/Test_Task_1/Test_Task_2/References/Stalker_Pyramid/'
                    'test_video'):-len('.mp4')]

        # the filename should be the same
        self.assertEqual(
            'tp1/Test_Task_1/Test_Task_2/References/Stalker_Pyramid/'
            'test_video%(random_part)s.mp4' % {'random_part': random_part},
            link2.full_path
        )

        # but the original file name should be the same
        self.assertEqual('test_video.mp4', link1.original_filename)
        self.assertEqual('test_video.mp4', link2.original_filename)
        self.assertEqual(link1.original_filename, link2.original_filename)

    def test_randomize_filename_is_working_properly(self):
        """testing if MediaManager.randomize_filename() is working properly
        """
        test_value = 'some/path/to/a/file.mp4'
        expected_result = 'some/path/to/a/file%(random_part)s.mp4'
        result = self.test_media_manager.randomize_file_name(test_value)

        random_part = result[len('some/path/to/a/file'):-len('.mp4')]

        self.assertEqual(
            result,
            expected_result % {'random_part': random_part}
        )

    def test_upload_version_output_is_working_properly(self):
        """testing if MediaManager.upload_version_output() is working properly
        """
        v = Version(task=self.test_task2)
        db.DBSession.add(v)
        db.DBSession.commit()

        v.update_paths()
        db.DBSession.add(v)
        db.DBSession.commit()

        # upload an image file as an output to a version of test_task2
        with open(self.test_video_path_mp4) as f:
            link = self.test_media_manager.upload_version_output(
                v, f, 'test_video.mp4'
            )

        # now expect the return_val to be a Link instance
        self.assertIsInstance(link, Link)

        # expect the Link full_path to be:
        #   Version.path/Outputs/Stalker_Pyramid/
        self.assertEqual(
            os.path.dirname(link.full_path),
            os.path.join(
                v.path,
                'Outputs/Stalker_Pyramid'
            )
        )

        # expect the Link.thumbnail.full_path to be in
        #  Version.path/Outputs/Stalker_Pyramid/ForWeb/
        self.assertEqual(
            os.path.dirname(link.thumbnail.full_path),
            os.path.join(
                v.path,
                'Outputs/Stalker_Pyramid/ForWeb'
            )
        )

        # and expect the Link.thumbnail.thumbnail.full_path to be in
        #  Version.path/Outputs/Stalker_Pyramid/Thumbnail/
        self.assertEqual(
            os.path.dirname(link.thumbnail.thumbnail.full_path),
            os.path.join(
                self.test_task2.path,
                'Outputs/Stalker_Pyramid/Thumbnail'
            )
        )

    def test_upload_version_is_working_properly(self):
        """testing if MediaManager.upload_version() is working properly.
        """
        with open(self.test_video_path_mp4) as f:
            v = self.test_media_manager.upload_version(
                self.test_task2, f, extension='.mp4'
            )

        # should return version instance
        self.assertIsInstance(v, Version)

        # the version path should be properly updated
        self.assertEqual(
            v.full_path,
            'tp1/Test_Task_1/Test_Task_2/Test_Task_2_Main_v001.mp4'
        )

        # the file should be there
        self.assertTrue(os.path.exists(v.absolute_full_path))

        # created with should be Stalker Pyramid
        self.assertEqual(
            'Stalker Pyramid',
            v.created_with
        )
        db.DBSession.add(v)
        db.DBSession.commit()

        # upload another and expect the version number to be updated
        with open(self.test_video_path_mp4) as f:
            v2 = self.test_media_manager.upload_version(
                self.test_task2, f, extension='.mp4'
            )

        # should return version instance
        self.assertIsInstance(v, Version)

        # the version path should be properly updated
        self.assertEqual(
            v2.full_path,
            'tp1/Test_Task_1/Test_Task_2/Test_Task_2_Main_v002.mp4'
        )

        # the file should be there
        self.assertTrue(os.path.exists(v2.absolute_full_path))

        # created with should be Stalker Pyramid
        self.assertEqual(
            'Stalker Pyramid',
            v2.created_with
        )
