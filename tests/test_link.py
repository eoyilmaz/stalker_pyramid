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

import os
import tempfile
import unittest2

from stalker import defaults, Link
from stalker_pyramid.views.link import ImageData, ImgToLinkConverter


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
