// Stalker a Production Asset Management System
// Copyright (C) 2009-2013 Erkan Ozgur Yilmaz
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

define([
    "dojo/_base/declare",
    "stalker/js/TimeLog",
    "stalker/js/Task"
], function (declare, TimeLog, Task) {
    'use strict';
    return declare('Resource', null, {
        id: null,
        name: '',
        tasks: [],
        time_logs: [],

        studio: null,

        constructor: function (settings) {
            //this.grid = settings.grid;
//            console.log('code is here 1');
            this.studio = new Studio();
//            console.log('code is here 2');
            this.id = settings.id || null;
            this.name = settings.name || null;
            this.type = settings.type || null;
            this.resource_count = settings.resource_count || 1;

            this.tasks = [];
            this.time_logs = [];

            var time_log_data = settings.time_logs || [],
                temp_time_log = null,
                i,
                task_data = settings.tasks || [],
                temp_task = null;

            // time logs
            for (i = 0; i < time_log_data.length; i += 1) {
                temp_time_log = new TimeLog(time_log_data[i]);
                temp_time_log.resource = this;
                this.time_logs.push(temp_time_log);
            }

            // tasks
            for (i = 0; i < task_data.length; i += 1) {
                temp_task = new Task(task_data[i]);
                temp_task.resource = this;
                this.tasks.push(temp_task);
            }

//            console.log('code is here 3');
        },

        link: function () {
            return templates.resourceLink(this);
        },

        total_logged_milliseconds: function (start, end) {
            // returns the amount of logged seconds between the given dates
            var time_logs = this.time_logs,
                tasks = this.tasks,
                time_logs_count = time_logs.length,
                tasks_count = tasks.length,
                total_millies = 0,
                range_start = null,
                range_end = null,
                tlog = null,
                task = null,
                today = new Date().getTime(),
                i;

            // return time logs until today
            // and tasks to the end date

            // compare the start and end range with today
            // if it is before today, only consider time logs
            // if it is after today, consider tasks
            // only consider end time

            if (end < today) {
                // for dates before today consider only time logs
                for (i = 0; i < time_logs_count; i += 1) {
                    tlog = time_logs[i];
                    if (tlog.start <= end && tlog.end >= start) {
                        // we have a candidate now get the millis
                        range_start = Math.max(tlog.start, start); // take the max of the start 
                        range_end   = Math.min(tlog.end,   end); // take the min of the end
                        total_millies += (range_end - range_start);
                    }
                }
            } else {
                // for dates after today consider only tasks
                for (i = 0; i < tasks_count; i += 1) {
                    // for tasks we should consider working days between the start and end dates
                    task = tasks[i];
                    if (task.start <= end && task.end >= start) {
                        range_start = Math.max(task.start, start);
                        range_end = Math.min(task.end, end);
                        total_millies += this.studio.get_working_hours_between_dates(range_start, range_end);
                    }
                }
            }
            return total_millies;
        }

    });
});
