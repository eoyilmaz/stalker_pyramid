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


// extend the Date object to include getClock(), setClock()
/**
 * Returns the UTC clock as milliseconds
 * 
 * @returns {Number}
 */
Date.prototype.getClock = function () {
    return this.getTime() % 86400000;
};

/**
 * Sets the UTC clock of the Date object
 * 
 * @param {Number} clock
 *  The clock in milliseconds
 * 
 */
Date.prototype.setClock = function (clock) {
    'use strict';
    var temp_clock = +clock,
        time = this.getTime();
    this.setTime(time - time % 86400000 + temp_clock % 86400000);
    return this;
};

try {
    module.exports.Date = Date;
} catch (e) {
}
