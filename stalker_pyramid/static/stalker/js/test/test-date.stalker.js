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


var Date = require('../date.stalker').Date;

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
