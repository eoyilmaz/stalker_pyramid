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

try {
    var moment = require('../../moment/moment.min');
} catch (e) {};


/**
 * Renders header cells under the given parent
 * 
 * @param options
 * @returns {*|jQuery|HTMLElement}
 */
define([], function () {
    return function (options) {
        'use strict';
        var parent = options.parent;
        var start = options.start;
        var end = options.end;
        var scale = options.scale;
        var step_size = options.step_size;
        var step_unit = options.step_unit;
        var period_unit = options.period_unit;
        var height = options.height;
        var format = options.format;

        var original_start = moment(start).startOf('day');

        var start_date = moment(start).startOf(period_unit).startOf('day');
        var end_date = moment(end).endOf(period_unit).endOf('day');

        // find the start and end of the period
        var period_start = moment(start_date.startOf(period_unit));
        var period_end = moment(start_date.endOf(period_unit));

        if (step_size > 1) {
            end_date.add(step_size - 1, step_unit);
            period_end.add(step_size - 1, period_unit);
        }

        // create the first div elements using start_date and week_end
        var parent_div = jQuery(jQuery.parseHTML('<div class="headerCell"></div>'));
        parent_div.css({
            width: Math.floor((end_date - start_date) / scale),
            left: Math.floor((start_date - original_start) / scale),
            height: height,
            position: 'absolute'
        });
        jQuery(parent).append(parent_div);

        var header_div_element;
        // now wee need to iterate until the end_date is bigger than end

        var formatter = function(ps, pe) {
            return ps.format(format);
        };

        if (typeof format === 'function') {
            formatter = format;
        }

        while (period_start < end_date) {
            // create the first div elements using start_date and week_end
            header_div_element = jQuery(jQuery.parseHTML('<div class="headerCell center">' + formatter(period_start, period_end) + '</div>'));
            header_div_element.css({
                width: Math.floor((period_end - period_start) / scale),
                left: Math.floor((period_start - start_date) / scale)
            });
            parent_div.append(header_div_element);
            // go to next step
            period_start.add(step_size, step_unit).startOf(step_unit);
            period_end.add(step_size, step_unit).endOf(step_unit);
        }
        return parent_div;
    };
});
