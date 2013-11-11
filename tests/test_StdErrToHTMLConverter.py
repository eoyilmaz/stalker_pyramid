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


import unittest2
from stalker_pyramid.views import StdErrToHTMLConverter


class StdErrToHTMLConverterTestCase(unittest2.TestCase):
    """tests the stalker_pyramid.views.StdErrToHTMLConverter class
    """

    def test_list_input(self):
        """testing if the class is working with lists as the error message
        """
        test_data = [
            '/tmp/Stalker_3coLKi.tjp:1909: \x1b[35mWarning: The total effort (1.0d or 9.0h) of the provided bookings for task Project_23.Task_108.Task_1350.Task_1351.Task_1353.Asset_1359.Task_1356.Task_1357 exceeds the specified effort of 0.1111111111111111d or 1.0h.\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1949: \x1b[35mWarning: The total effort (1.0d or 9.0h) of the provided bookings for task Project_23.Task_108.Task_1350.Task_1351.Task_1353.Asset_1367.Task_1370.Task_1371 exceeds the specified effort of 0.1111111111111111d or 1.0h.\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1989: \x1b[35mWarning: The total effort (1.0d or 9.0h) of the provided bookings for task Project_23.Task_108.Task_1350.Task_1351.Task_1353.Asset_1368.Task_1369.Task_1375 exceeds the specified effort of 0.1111111111111111d or 1.0h.\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:2029: \x1b[35mWarning: The total effort (2.0d or 18.0h) of the provided bookings for task Project_23.Task_108.Task_1350.Task_1351.Task_1353.Asset_1381.Task_1391.Task_1394 exceeds the specified effort of 0.1111111111111111d or 1.0h.\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:2070: \x1b[35mWarning: The total effort (1.0d or 9.0h) of the provided bookings for task Project_23.Task_108.Task_1350.Task_1351.Task_1353.Asset_1382.Task_1392.Task_1393 exceeds the specified effort of 0.1111111111111111d or 1.0h.\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1320: \x1b[35mWarning: Due to a mix of ALAP and ASAP scheduled tasks or a dependency on a lower priority tasks the following tasks stole resources from Project_23.Task_108.Task_109.Asset_130.Task_605 despite having a lower priority:\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1735: \x1b[34mInfo: Task Project_23.Task_108.Task_109.Asset_581.Task_583\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1762: \x1b[34mInfo: Task Project_23.Task_108.Task_109.Asset_585.Task_587\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1797: \x1b[34mInfo: Task Project_23.Task_108.Task_109.Asset_589.Task_591\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1442: \x1b[35mWarning: Due to a mix of ALAP and ASAP scheduled tasks or a dependency on a lower priority tasks the following task stole resources from Project_23.Task_108.Task_109.Asset_135.Task_552 despite having a lower priority:\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1398: \x1b[34mInfo: Task Project_23.Task_108.Task_109.Asset_133.Task_545\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1450: \x1b[35mWarning: Due to a mix of ALAP and ASAP scheduled tasks or a dependency on a lower priority tasks the following tasks stole resources from Project_23.Task_108.Task_109.Asset_135.Task_553 despite having a lower priority:\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1743: \x1b[34mInfo: Task Project_23.Task_108.Task_109.Asset_581.Task_584\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1485: \x1b[34mInfo: Task Project_23.Task_108.Task_109.Asset_136.Task_558\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1770: \x1b[34mInfo: Task Project_23.Task_108.Task_109.Asset_585.Task_588\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1805: \x1b[34mInfo: Task Project_23.Task_108.Task_109.Asset_589.Task_598\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1485: \x1b[35mWarning: Due to a mix of ALAP and ASAP scheduled tasks or a dependency on a lower priority tasks the following task stole resources from Project_23.Task_108.Task_109.Asset_136.Task_558 despite having a lower priority:\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1743: \x1b[34mInfo: Task Project_23.Task_108.Task_109.Asset_581.Task_584\x1b[0m\n'
        ]
        expected_result = '/tmp/Stalker_3coLKi.tjp:1909: <div class="alert alert-warning" style="overflow-wrap: break-word"><strong>Warning:</strong> The total effort (1.0d or 9.0h) of the provided bookings for task Project_23.Task_108.Task_1350.Task_1351.Task_1353.Asset_1359.Task_1356.Task_1357 exceeds the specified effort of 0.1111111111111111d or 1.0h.</div>/tmp/Stalker_3coLKi.tjp:1949: <div class="alert alert-warning" style="overflow-wrap: break-word"><strong>Warning:</strong> The total effort (1.0d or 9.0h) of the provided bookings for task Project_23.Task_108.Task_1350.Task_1351.Task_1353.Asset_1367.Task_1370.Task_1371 exceeds the specified effort of 0.1111111111111111d or 1.0h.</div>/tmp/Stalker_3coLKi.tjp:1989: <div class="alert alert-warning" style="overflow-wrap: break-word"><strong>Warning:</strong> The total effort (1.0d or 9.0h) of the provided bookings for task Project_23.Task_108.Task_1350.Task_1351.Task_1353.Asset_1368.Task_1369.Task_1375 exceeds the specified effort of 0.1111111111111111d or 1.0h.</div>/tmp/Stalker_3coLKi.tjp:2029: <div class="alert alert-warning" style="overflow-wrap: break-word"><strong>Warning:</strong> The total effort (2.0d or 18.0h) of the provided bookings for task Project_23.Task_108.Task_1350.Task_1351.Task_1353.Asset_1381.Task_1391.Task_1394 exceeds the specified effort of 0.1111111111111111d or 1.0h.</div>/tmp/Stalker_3coLKi.tjp:2070: <div class="alert alert-warning" style="overflow-wrap: break-word"><strong>Warning:</strong> The total effort (1.0d or 9.0h) of the provided bookings for task Project_23.Task_108.Task_1350.Task_1351.Task_1353.Asset_1382.Task_1392.Task_1393 exceeds the specified effort of 0.1111111111111111d or 1.0h.</div>/tmp/Stalker_3coLKi.tjp:1320: <div class="alert alert-warning" style="overflow-wrap: break-word"><strong>Warning:</strong> Due to a mix of ALAP and ASAP scheduled tasks or a dependency on a lower priority tasks the following tasks stole resources from Project_23.Task_108.Task_109.Asset_130.Task_605 despite having a lower priority:</div>/tmp/Stalker_3coLKi.tjp:1735: <div class="alert alert-info" style="overflow-wrap: break-word"><strong>Info:</strong> Task Project_23.Task_108.Task_109.Asset_581.Task_583</div>/tmp/Stalker_3coLKi.tjp:1762: <div class="alert alert-info" style="overflow-wrap: break-word"><strong>Info:</strong> Task Project_23.Task_108.Task_109.Asset_585.Task_587</div>/tmp/Stalker_3coLKi.tjp:1797: <div class="alert alert-info" style="overflow-wrap: break-word"><strong>Info:</strong> Task Project_23.Task_108.Task_109.Asset_589.Task_591</div>/tmp/Stalker_3coLKi.tjp:1442: <div class="alert alert-warning" style="overflow-wrap: break-word"><strong>Warning:</strong> Due to a mix of ALAP and ASAP scheduled tasks or a dependency on a lower priority tasks the following task stole resources from Project_23.Task_108.Task_109.Asset_135.Task_552 despite having a lower priority:</div>/tmp/Stalker_3coLKi.tjp:1398: <div class="alert alert-info" style="overflow-wrap: break-word"><strong>Info:</strong> Task Project_23.Task_108.Task_109.Asset_133.Task_545</div>/tmp/Stalker_3coLKi.tjp:1450: <div class="alert alert-warning" style="overflow-wrap: break-word"><strong>Warning:</strong> Due to a mix of ALAP and ASAP scheduled tasks or a dependency on a lower priority tasks the following tasks stole resources from Project_23.Task_108.Task_109.Asset_135.Task_553 despite having a lower priority:</div>/tmp/Stalker_3coLKi.tjp:1743: <div class="alert alert-info" style="overflow-wrap: break-word"><strong>Info:</strong> Task Project_23.Task_108.Task_109.Asset_581.Task_584</div>/tmp/Stalker_3coLKi.tjp:1485: <div class="alert alert-info" style="overflow-wrap: break-word"><strong>Info:</strong> Task Project_23.Task_108.Task_109.Asset_136.Task_558</div>/tmp/Stalker_3coLKi.tjp:1770: <div class="alert alert-info" style="overflow-wrap: break-word"><strong>Info:</strong> Task Project_23.Task_108.Task_109.Asset_585.Task_588</div>/tmp/Stalker_3coLKi.tjp:1805: <div class="alert alert-info" style="overflow-wrap: break-word"><strong>Info:</strong> Task Project_23.Task_108.Task_109.Asset_589.Task_598</div>/tmp/Stalker_3coLKi.tjp:1485: <div class="alert alert-warning" style="overflow-wrap: break-word"><strong>Warning:</strong> Due to a mix of ALAP and ASAP scheduled tasks or a dependency on a lower priority tasks the following task stole resources from Project_23.Task_108.Task_109.Asset_136.Task_558 despite having a lower priority:</div>/tmp/Stalker_3coLKi.tjp:1743: <div class="alert alert-info" style="overflow-wrap: break-word"><strong>Info:</strong> Task Project_23.Task_108.Task_109.Asset_581.Task_584</div>'
        c = StdErrToHTMLConverter(test_data)
        self.assertEqual(
            expected_result,
            c.html()
        )
