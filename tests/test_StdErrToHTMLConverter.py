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


import unittest
from stalker_pyramid.views import StdErrToHTMLConverter


class StdErrToHTMLConverterTestCase(unittest.TestCase):
    """tests the stalker_pyramid.views.StdErrToHTMLConverter class
    """

    def test_list_input(self):
        """testing if the class is working with lists as the error message
        """
        test_data = [
            '/tmp/Stalker_3coLKi.tjp:1909: \x1b[35mWarning: The total effort (1.0d or 9.0h) of the provided bookings for task Task_108.Task_1350.Task_1351.Task_1353.Asset_1359.Task_1356.Task_1357 exceeds the specified effort of 0.1111111111111111d or 1.0h.\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1949: \x1b[35mWarning: The total effort (1.0d or 9.0h) of the provided bookings for task Task_108.Task_1350.Task_1351.Task_1353.Asset_1367.Task_1370.Task_1371 exceeds the specified effort of 0.1111111111111111d or 1.0h.\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1989: \x1b[35mWarning: The total effort (1.0d or 9.0h) of the provided bookings for task Task_108.Task_1350.Task_1351.Task_1353.Asset_1368.Task_1369.Task_1375 exceeds the specified effort of 0.1111111111111111d or 1.0h.\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:2029: \x1b[35mWarning: The total effort (2.0d or 18.0h) of the provided bookings for task Task_108.Task_1350.Task_1351.Task_1353.Asset_1381.Task_1391.Task_1394 exceeds the specified effort of 0.1111111111111111d or 1.0h.\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:2070: \x1b[35mWarning: The total effort (1.0d or 9.0h) of the provided bookings for task Task_108.Task_1350.Task_1351.Task_1353.Asset_1382.Task_1392.Task_1393 exceeds the specified effort of 0.1111111111111111d or 1.0h.\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1320: \x1b[35mWarning: Due to a mix of ALAP and ASAP scheduled tasks or a dependency on a lower priority tasks the following tasks stole resources from Task_108.Task_109.Asset_130.Task_605 despite having a lower priority:\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1735: \x1b[34mInfo: Task Task_108.Task_109.Asset_581.Task_583\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1762: \x1b[34mInfo: Task Task_108.Task_109.Asset_585.Task_587\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1797: \x1b[34mInfo: Task Task_108.Task_109.Asset_589.Task_591\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1442: \x1b[35mWarning: Due to a mix of ALAP and ASAP scheduled tasks or a dependency on a lower priority tasks the following task stole resources from Task_108.Task_109.Asset_135.Task_552 despite having a lower priority:\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1398: \x1b[34mInfo: Task Task_108.Task_109.Asset_133.Task_545\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1450: \x1b[35mWarning: Due to a mix of ALAP and ASAP scheduled tasks or a dependency on a lower priority tasks the following tasks stole resources from Task_108.Task_109.Asset_135.Task_553 despite having a lower priority:\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1743: \x1b[34mInfo: Task Task_108.Task_109.Asset_581.Task_584\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1485: \x1b[34mInfo: Task Task_108.Task_109.Asset_136.Task_558\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1770: \x1b[34mInfo: Task Task_108.Task_109.Asset_585.Task_588\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1805: \x1b[34mInfo: Task Task_108.Task_109.Asset_589.Task_598\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1485: \x1b[35mWarning: Due to a mix of ALAP and ASAP scheduled tasks or a dependency on a lower priority tasks the following task stole resources from Task_108.Task_109.Asset_136.Task_558 despite having a lower priority:\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1743: \x1b[34mInfo: Task Task_108.Task_109.Asset_581.Task_584\x1b[0m\n'
        ]
        expected_result = \
            '<p>/tmp/Stalker_3coLKi.tjp:1909: <span class="alert alert-warning" style="overflow-wrap: break-word"><strong>Warning:</strong> The total effort (1.0d or 9.0h) of the provided bookings for task Task_108.Task_1350.Task_1351.Task_1353.Asset_1359.Task_1356.Task_1357 exceeds the specified effort of 0.1111111111111111d or 1.0h.</span><br>' \
            '/tmp/Stalker_3coLKi.tjp:1949: <span class="alert alert-warning" style="overflow-wrap: break-word"><strong>Warning:</strong> The total effort (1.0d or 9.0h) of the provided bookings for task Task_108.Task_1350.Task_1351.Task_1353.Asset_1367.Task_1370.Task_1371 exceeds the specified effort of 0.1111111111111111d or 1.0h.</span><br>' \
            '/tmp/Stalker_3coLKi.tjp:1989: <span class="alert alert-warning" style="overflow-wrap: break-word"><strong>Warning:</strong> The total effort (1.0d or 9.0h) of the provided bookings for task Task_108.Task_1350.Task_1351.Task_1353.Asset_1368.Task_1369.Task_1375 exceeds the specified effort of 0.1111111111111111d or 1.0h.</span><br>' \
            '/tmp/Stalker_3coLKi.tjp:2029: <span class="alert alert-warning" style="overflow-wrap: break-word"><strong>Warning:</strong> The total effort (2.0d or 18.0h) of the provided bookings for task Task_108.Task_1350.Task_1351.Task_1353.Asset_1381.Task_1391.Task_1394 exceeds the specified effort of 0.1111111111111111d or 1.0h.</span><br>' \
            '/tmp/Stalker_3coLKi.tjp:2070: <span class="alert alert-warning" style="overflow-wrap: break-word"><strong>Warning:</strong> The total effort (1.0d or 9.0h) of the provided bookings for task Task_108.Task_1350.Task_1351.Task_1353.Asset_1382.Task_1392.Task_1393 exceeds the specified effort of 0.1111111111111111d or 1.0h.</span><br>' \
            '/tmp/Stalker_3coLKi.tjp:1320: <span class="alert alert-warning" style="overflow-wrap: break-word"><strong>Warning:</strong> Due to a mix of ALAP and ASAP scheduled tasks or a dependency on a lower priority tasks the following tasks stole resources from Task_108.Task_109.Asset_130.Task_605 despite having a lower priority:</span><br>' \
            '/tmp/Stalker_3coLKi.tjp:1735: <span class="alert alert-info" style="overflow-wrap: break-word"><strong>Info:</strong> Task Task_108.Task_109.Asset_581.Task_583</span><br>' \
            '/tmp/Stalker_3coLKi.tjp:1762: <span class="alert alert-info" style="overflow-wrap: break-word"><strong>Info:</strong> Task Task_108.Task_109.Asset_585.Task_587</span><br>' \
            '/tmp/Stalker_3coLKi.tjp:1797: <span class="alert alert-info" style="overflow-wrap: break-word"><strong>Info:</strong> Task Task_108.Task_109.Asset_589.Task_591</span><br>' \
            '/tmp/Stalker_3coLKi.tjp:1442: <span class="alert alert-warning" style="overflow-wrap: break-word"><strong>Warning:</strong> Due to a mix of ALAP and ASAP scheduled tasks or a dependency on a lower priority tasks the following task stole resources from Task_108.Task_109.Asset_135.Task_552 despite having a lower priority:</span><br>' \
            '/tmp/Stalker_3coLKi.tjp:1398: <span class="alert alert-info" style="overflow-wrap: break-word"><strong>Info:</strong> Task Task_108.Task_109.Asset_133.Task_545</span><br>' \
            '/tmp/Stalker_3coLKi.tjp:1450: <span class="alert alert-warning" style="overflow-wrap: break-word"><strong>Warning:</strong> Due to a mix of ALAP and ASAP scheduled tasks or a dependency on a lower priority tasks the following tasks stole resources from Task_108.Task_109.Asset_135.Task_553 despite having a lower priority:</span><br>' \
            '/tmp/Stalker_3coLKi.tjp:1743: <span class="alert alert-info" style="overflow-wrap: break-word"><strong>Info:</strong> Task Task_108.Task_109.Asset_581.Task_584</span><br>' \
            '/tmp/Stalker_3coLKi.tjp:1485: <span class="alert alert-info" style="overflow-wrap: break-word"><strong>Info:</strong> Task Task_108.Task_109.Asset_136.Task_558</span><br>' \
            '/tmp/Stalker_3coLKi.tjp:1770: <span class="alert alert-info" style="overflow-wrap: break-word"><strong>Info:</strong> Task Task_108.Task_109.Asset_585.Task_588</span><br>' \
            '/tmp/Stalker_3coLKi.tjp:1805: <span class="alert alert-info" style="overflow-wrap: break-word"><strong>Info:</strong> Task Task_108.Task_109.Asset_589.Task_598</span><br>' \
            '/tmp/Stalker_3coLKi.tjp:1485: <span class="alert alert-warning" style="overflow-wrap: break-word"><strong>Warning:</strong> Due to a mix of ALAP and ASAP scheduled tasks or a dependency on a lower priority tasks the following task stole resources from Task_108.Task_109.Asset_136.Task_558 despite having a lower priority:</span><br>' \
            '/tmp/Stalker_3coLKi.tjp:1743: <span class="alert alert-info" style="overflow-wrap: break-word"><strong>Info:</strong> Task Task_108.Task_109.Asset_581.Task_584</span></p>'

        c = StdErrToHTMLConverter(test_data)
        self.assertEqual(
            expected_result,
            c.html()
        )

    def test_replace_links(self):
        """testing if the class is working with lists as the error message
        """

        test_data = [
            '/tmp/Stalker_3coLKi.tjp:1909: \x1b[35mWarning: The total effort (1.0d or 9.0h) of the provided bookings for task Task_108.Task_1350.Task_1351.Task_1353.Asset_1359.Task_1356.Task_1357 exceeds the specified effort of 0.1111111111111111d or 1.0h.\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1949: \x1b[35mWarning: The total effort (1.0d or 9.0h) of the provided bookings for task Task_108.Task_1350.Task_1351.Task_1353.Asset_1367.Task_1370.Task_1371 exceeds the specified effort of 0.1111111111111111d or 1.0h.\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1989: \x1b[35mWarning: The total effort (1.0d or 9.0h) of the provided bookings for task Task_108.Task_1350.Task_1351.Task_1353.Asset_1368.Task_1369.Task_1375 exceeds the specified effort of 0.1111111111111111d or 1.0h.\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:2029: \x1b[35mWarning: The total effort (2.0d or 18.0h) of the provided bookings for task Task_108.Task_1350.Task_1351.Task_1353.Asset_1381.Task_1391.Task_1394 exceeds the specified effort of 0.1111111111111111d or 1.0h.\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:2070: \x1b[35mWarning: The total effort (1.0d or 9.0h) of the provided bookings for task Task_108.Task_1350.Task_1351.Task_1353.Asset_1382.Task_1392.Task_1393 exceeds the specified effort of 0.1111111111111111d or 1.0h.\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1320: \x1b[35mWarning: Due to a mix of ALAP and ASAP scheduled tasks or a dependency on a lower priority tasks the following tasks stole resources from Task_108.Task_109.Asset_130.Task_605 despite having a lower priority:\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1735: \x1b[34mInfo: Task Task_108.Task_109.Asset_581.Task_583\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1762: \x1b[34mInfo: Task Task_108.Task_109.Asset_585.Task_587\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1797: \x1b[34mInfo: Task Task_108.Task_109.Asset_589.Task_591\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1442: \x1b[35mWarning: Due to a mix of ALAP and ASAP scheduled tasks or a dependency on a lower priority tasks the following task stole resources from Task_108.Task_109.Asset_135.Task_552 despite having a lower priority:\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1398: \x1b[34mInfo: Task Task_108.Task_109.Asset_133.Task_545\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1450: \x1b[35mWarning: Due to a mix of ALAP and ASAP scheduled tasks or a dependency on a lower priority tasks the following tasks stole resources from Task_108.Task_109.Asset_135.Task_553 despite having a lower priority:\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1743: \x1b[34mInfo: Task Task_108.Task_109.Asset_581.Task_584\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1485: \x1b[34mInfo: Task Task_108.Task_109.Asset_136.Task_558\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1770: \x1b[34mInfo: Task Task_108.Task_109.Asset_585.Task_588\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1805: \x1b[34mInfo: Task Task_108.Task_109.Asset_589.Task_598\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1485: \x1b[35mWarning: Due to a mix of ALAP and ASAP scheduled tasks or a dependency on a lower priority tasks the following task stole resources from Task_108.Task_109.Asset_136.Task_558 despite having a lower priority:\x1b[0m\n',
            '/tmp/Stalker_3coLKi.tjp:1743: \x1b[34mInfo: Task Task_108.Task_109.Asset_581.Task_584\x1b[0m\n'
        ]
        expected_result = \
            '<p>/tmp/Stalker_3coLKi.tjp:1909: <span class="alert alert-warning" ' \
            'style="overflow-wrap: break-word"><strong>Warning:</strong> ' \
            'The total effort (1.0d or 9.0h) of the provided bookings for ' \
            'task <a href="/tasks/1357/view">Task_1357</a> exceeds the ' \
            'specified effort of 0.1111111111111111d or 1.0h.</span><br>' \
            '/tmp/Stalker_3coLKi.tjp:1949: <span class="alert alert-warning" ' \
            'style="overflow-wrap: break-word"><strong>Warning:</strong> ' \
            'The total effort (1.0d or 9.0h) of the provided bookings for ' \
            'task <a href="/tasks/1371/view">Task_1371</a> exceeds the ' \
            'specified effort of 0.1111111111111111d or 1.0h.</span><br>' \
            '/tmp/Stalker_3coLKi.tjp:1989: <span class="alert alert-warning" ' \
            'style="overflow-wrap: break-word"><strong>Warning:</strong> ' \
            'The total effort (1.0d or 9.0h) of the provided bookings for ' \
            'task <a href="/tasks/1375/view">Task_1375</a> exceeds the ' \
            'specified effort of 0.1111111111111111d or 1.0h.</span><br>' \
            '/tmp/Stalker_3coLKi.tjp:2029: <span class="alert alert-warning" ' \
            'style="overflow-wrap: break-word"><strong>Warning:</strong> ' \
            'The total effort (2.0d or 18.0h) of the provided bookings for ' \
            'task <a href="/tasks/1394/view">Task_1394</a> exceeds the ' \
            'specified effort of 0.1111111111111111d or 1.0h.</span><br>' \
            '/tmp/Stalker_3coLKi.tjp:2070: <span class="alert alert-warning" ' \
            'style="overflow-wrap: break-word"><strong>Warning:</strong> ' \
            'The total effort (1.0d or 9.0h) of the provided bookings for ' \
            'task <a href="/tasks/1393/view">Task_1393</a> exceeds the ' \
            'specified effort of 0.1111111111111111d or 1.0h.</span><br>' \
            '/tmp/Stalker_3coLKi.tjp:1320: <span class="alert alert-warning" ' \
            'style="overflow-wrap: break-word"><strong>Warning:</strong> ' \
            'Due to a mix of ALAP and ASAP scheduled tasks or a dependency ' \
            'on a lower priority tasks the following tasks stole resources ' \
            'from <a href="/tasks/605/view">Task_605</a> despite having a ' \
            'lower priority:</span><br>/tmp/Stalker_3coLKi.tjp:1735: ' \
            '<span class="alert alert-info" style="overflow-wrap: ' \
            'break-word"><strong>Info:</strong> Task ' \
            '<a href="/tasks/583/view">Task_583</a></span><br>' \
            '/tmp/Stalker_3coLKi.tjp:1762: <span class="alert alert-info" ' \
            'style="overflow-wrap: break-word"><strong>Info:</strong> Task ' \
            '<a href="/tasks/587/view">Task_587</a></span><br>' \
            '/tmp/Stalker_3coLKi.tjp:1797: <span class="alert alert-info" ' \
            'style="overflow-wrap: break-word"><strong>Info:</strong> Task ' \
            '<a href="/tasks/591/view">Task_591</a></span><br>' \
            '/tmp/Stalker_3coLKi.tjp:1442: <span class="alert alert-warning" ' \
            'style="overflow-wrap: break-word"><strong>Warning:</strong> Due ' \
            'to a mix of ALAP and ASAP scheduled tasks or a dependency on a ' \
            'lower priority tasks the following task stole resources from ' \
            '<a href="/tasks/552/view">Task_552</a> despite having a lower ' \
            'priority:</span><br>/tmp/Stalker_3coLKi.tjp:1398: ' \
            '<span class="alert alert-info" style="overflow-wrap: ' \
            'break-word"><strong>Info:</strong> Task ' \
            '<a href="/tasks/545/view">Task_545</a></span><br>' \
            '/tmp/Stalker_3coLKi.tjp:1450: <span class="alert alert-warning" ' \
            'style="overflow-wrap: break-word"><strong>Warning:</strong> ' \
            'Due to a mix of ALAP and ASAP scheduled tasks or a dependency ' \
            'on a lower priority tasks the following tasks stole resources ' \
            'from <a href="/tasks/553/view">Task_553</a> despite having a ' \
            'lower priority:</span><br>/tmp/Stalker_3coLKi.tjp:1743: ' \
            '<span class="alert alert-info" style="overflow-wrap: ' \
            'break-word"><strong>Info:</strong> Task ' \
            '<a href="/tasks/584/view">Task_584</a></span><br>' \
            '/tmp/Stalker_3coLKi.tjp:1485: <span class="alert alert-info" ' \
            'style="overflow-wrap: break-word"><strong>Info:</strong> Task ' \
            '<a href="/tasks/558/view">Task_558</a></span><br>' \
            '/tmp/Stalker_3coLKi.tjp:1770: <span class="alert alert-info" ' \
            'style="overflow-wrap: break-word"><strong>Info:</strong> Task ' \
            '<a href="/tasks/588/view">Task_588</a></span><br>' \
            '/tmp/Stalker_3coLKi.tjp:1805: <span class="alert alert-info" ' \
            'style="overflow-wrap: break-word"><strong>Info:</strong> Task ' \
            '<a href="/tasks/598/view">Task_598</a></span><br>' \
            '/tmp/Stalker_3coLKi.tjp:1485: <span class="alert alert-warning" ' \
            'style="overflow-wrap: break-word"><strong>Warning:</strong> ' \
            'Due to a mix of ALAP and ASAP scheduled tasks or a dependency ' \
            'on a lower priority tasks the following task stole resources ' \
            'from <a href="/tasks/558/view">Task_558</a> despite having a ' \
            'lower priority:</span><br>/tmp/Stalker_3coLKi.tjp:1743: <span ' \
            'class="alert alert-info" style="overflow-wrap: break-word">' \
            '<strong>Info:</strong> Task ' \
            '<a href="/tasks/584/view">Task_584</a>' \
            '</span></p>'
        c = StdErrToHTMLConverter(test_data)

        self.maxDiff = None
        self.assertEqual(
            expected_result,
            c.html(replace_links=True)
        )
