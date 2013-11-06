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


function Studio() {
    'use strict';
    this.daily_working_hours = 9;
    this.weekly_working_hours = 51;
    this.working_hours = { // these should be in UTC time/hours
        1: [28800000, 61200000],  // monday    9 : 10:00 - 19:00 in Turkey 08:00 - 17:00 in UTC
        2: [28800000, 61200000],  // tuesday   9 : 10:00 - 19:00 in Turkey 08:00 - 17:00 in UTC
        3: [28800000, 61200000],  // wednesday 9 : 10:00 - 19:00 in Turkey 08:00 - 17:00 in UTC
        4: [28800000, 61200000],  // thursday  9 : 10:00 - 19:00 in Turkey 08:00 - 17:00 in UTC
        5: [28800000, 61200000],  // friday    9 : 10:00 - 19:00 in Turkey 08:00 - 17:00 in UTC
        6: [36000000, 57600000],  // saturday  6 : 12:00 - 18:00 in Turkey 10:00 - 16:00 in UTC
        7: [null, null]           // sunday    0 : day off
    };
    this.vacations = [];
}

/**
 * Returns the total working hours between the given dates
 * 
 * @param {Date, Number} start
 * @param {Date, Number} end
 */
Studio.prototype.get_working_hours_between_dates = function (start, end) {
    'use strict';
    // calculate the working hours between the given dates as milliseconds
    // don't consider vacations for now

    // so we need to start from start and iterate over to the end date
    // each time by setting our temp date to the start working hour and end
    // working hour of that day

    var temp_start = +start,
        temp_end = +start,
        end_date = +end,
        total_working_millies = 0;
    while (temp_start < end_date) {
        total_working_millies += temp_end - temp_start;
        temp_start = this.get_closest_working_hour_start(temp_end);
        temp_end = this.get_closest_working_hour_end(temp_start);
        temp_end = Math.min(temp_end, end_date);
        temp_start = Math.min(temp_start, temp_end);
    }
    return total_working_millies;
};

/**
 * Returns the next closest working hour start if the given date is not in a
 * working hour range. Otherwise returns the date itself.
 * 
 * @param {Date} date
 *      Integer or Date object
 */
Studio.prototype.get_closest_working_hour_start = function (date) {
    'use strict';
    // ensure it is a Date instance
    // because it is the start value, to prevent the last millisecond of the
    // working day to be counted as a working hour we add 1 milliseconds to the
    // start value to correctly get the next working days start value as the
    // return value
    var is_working_hour = this.is_working_hour(date + 1);

    var temp_date = +date;

    if (is_working_hour) {
        return temp_date;
    } else {
        // get the day and the working hours for that day, if no working hours
        // go to the next day
        temp_date = moment.utc(date);
        var day_of_week = temp_date.isoWeekday();
        // now get the working hours for that day
        var working_hours = this.working_hours[day_of_week];
        // if date.hour is lower than start return start
        // else check if the next day is a working day
        var clock = (temp_date.valueOf() % 86400000);
        if (working_hours[0] !== null && clock <= working_hours[0]) {
            return temp_date.startOf('day') + working_hours[0];
        } else {
            // we should check the next day
            // because of the time offsets there is very weird things going on
            // when daylight saving is active,
            // and as a shortcut directly set to the next days working hours start
            var next_day_of_week = temp_date.add(1, 'day').isoWeekday();
            var next_day_working_hour_start = this.working_hours[next_day_of_week][0] || 0;

            temp_date = temp_date.startOf('day') + next_day_working_hour_start;
            return +this.get_closest_working_hour_start(temp_date);
        }
    }
};

/**
 * Returns the next closest working hour end if the given date is not in a
 * working hour range. Otherwise returns the date itself.
 * 
 * @param {Date} date
 *      Integer or Date object
 */
Studio.prototype.get_closest_working_hour_end = function (date) {
    'use strict';
    // ensure it is a Date instance
    var is_working_hour = this.is_working_hour(date);

    // get the day and the working hours for that day, if no working hours
    // go to the next day
    var temp_date = moment.utc(date);
    var day_of_week = temp_date.isoWeekday();
    // now get the working hours for that day
    var working_hours = this.working_hours[day_of_week];
    // if date.hour is lower than end return end
    // else check if the next day is a working day
    var clock = (temp_date.valueOf() % 86400000);
    if (working_hours[1] !== null && clock <= working_hours[1]) {
        return temp_date.startOf('day') + working_hours[1];
    } else {
        // we should check the next day
        temp_date.add(1, 'day').startOf('day');
        return +this.get_closest_working_hour_end(+temp_date);
    }
};


/**
 * Returns true or false depending on if the given date is in a working
 * hour range
 *   
 * @param {Date} date
 * @returns {boolean}
 */
Studio.prototype.is_working_hour = function (date) {
    'use strict';
    // get the working hours of the week day
    var week_day, clock, working_hours_of_week_day, temp_date;
    // ensure that it is a Date object

    var temp_date = moment.utc(date);

    week_day = temp_date.isoWeekday();
    clock = temp_date - moment.utc(temp_date).startOf('day');

//    clock = temp_date.getClock();
    working_hours_of_week_day = this.working_hours[week_day];
    return working_hours_of_week_day[0] !== null &&
        working_hours_of_week_day[1] !== null &&
        clock >= working_hours_of_week_day[0] &&
        clock <= working_hours_of_week_day[1];
};

try {
    module.exports.Studio = Studio;
} catch (e) {
}
