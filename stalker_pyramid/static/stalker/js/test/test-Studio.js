// Stalker Pyramid
// Copyright (C) 2013 Erkan Ozgur Yilmaz
//
// This file is part of Stalker Pyramid.
//
// This library is free software; you can redistribute it and/or
// modify it under the terms of the GNU Lesser General Public
// License as published by the Free Software Foundation;
// version 2.1 of the License.
//
// This library is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
// Lesser General Public License for more details.
//
// You should have received a copy of the GNU Lesser General Public
// License along with this library; if not, write to the Free Software
// Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA


var Studio = require('../Studio.js').Studio;

exports['test Date.getClock() is working properly'] = function (test) {
    var test_date = new Date(1383579474543);

    test.equal(
        test_date.getClock(),
        56274543
    );

    test.done();
};

exports['test Date.setClock() is working properly'] = function (test) {
    var test_date = new Date(2013, 10, 4, 10, 0);
    test_date.setClock(56274543);
    test.equal(test_date.getTime(), 1383579474543);
    test.done();
};

exports['test_is_working_hour'] = function (test) {
    var studio = new Studio();

    var test_values = [
        [new Date(2013, 10, 4, 16, 38), true],
        [new Date(2013, 10, 3, 10, 0), false],
        [new Date(2013, 10, 4, 20, 0), false]
    ];

    var test_value, expected_result;
    for (var i=0; i < test_values.length; i += 1){
        test_value = test_values[i][0];
        expected_result = test_values[i][1];

        test.equal(studio.is_working_hour(test_value), expected_result);
    }

    test.done();
};

exports['test_get_closest_working_hour_start'] = function (test) {
    var studio = new Studio();
    
    var test_values = [
        [new Date(2013, 10, 4, 16, 38), new Date(2013, 10, 4, 16, 38).getTime()],
        [new Date(2013, 10, 3, 10, 0), new Date(2013, 10, 4, 10, 0).getTime()],
        [new Date(2013, 10, 4, 20, 0), new Date(2013, 10, 5, 10, 0).getTime()],
        [new Date(2013, 10, 2, 20, 0), new Date(2013, 10, 4, 10, 0).getTime()]
    ];

    var test_value, expected_result;
    for (var i=0; i < test_values.length; i += 1){
        test_value = test_values[i][0];
        expected_result = test_values[i][1];

        test.equal(
            studio.get_closest_working_hour_start(test_value),
            expected_result
        );
    }
    test.done();
};

exports['test_get_closest_working_hour_end'] = function (test) {
    var studio = new Studio();

    var test_values = [
        [new Date(2013, 10, 4, 16, 38), new Date(2013, 10, 4, 19, 0).getTime()],
        [new Date(2013, 10, 3, 10, 0), new Date(2013, 10, 4, 19, 0).getTime()],
        [new Date(2013, 10, 4, 20, 0), new Date(2013, 10, 5, 19, 0).getTime()]
    ];

    var test_value, expected_result;
    for (var i=0; i < test_values.length; i += 1){
        test_value = test_values[i][0];
        expected_result = test_values[i][1];

        test.equal(
            studio.get_closest_working_hour_end(test_value),
            expected_result
        );
    }
    test.done();
};

exports['test_get_working_hours_between_dates'] = function (test) {
    var studio = new Studio();
    
    var test_values = [
        [
            new Date(2013, 10, 4, 10, 0), // start
            new Date(2013, 10, 4, 19, 0), // end
            32400000// expected result : 9 hours
        ],
        [
            new Date(2013, 10, 4, 16, 0), // start
            new Date(2013, 10, 4, 22, 0), // end
            10800000// expected result : 3 hours 16:00 - 19:00
        ],
        [
            new Date(2013, 10, 4, 5, 0), // start
            new Date(2013, 10, 4, 14, 0), // end
            14400000// expected result : 4 hours from 10:00
        ],
        [
            new Date(2013, 10, 3, 10, 0), // start
            new Date(2013, 10, 4, 19, 0), // end
            32400000// expected result : 9 hours from monday 10:00 - monday 19:00
        ],
        [
            new Date(2013, 10, 4, 15, 0), // start
            new Date(2013, 10, 6, 19, 0), // end
            79200000// expected result : 22 hours from monday 15:00 - wednesday 19:00
        ],
    ];

    var start, end, expected;
    for (var i=0; i < test_values.length; i += 1){
        start = test_values[i][0];
        end = test_values[i][1];
        expected = test_values[i][2];

        test.equal(
            studio.get_working_hours_between_dates(start, end),
            expected
        );
    }
    test.done();
};
