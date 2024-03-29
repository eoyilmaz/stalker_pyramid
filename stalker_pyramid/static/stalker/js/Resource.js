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
            this.studio = new Studio();
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

        },

        link: function () {
            return templates.resourceLink(this);
        },

        /**
         * Returns the total logged seconds between the given dates
         * 
         * @param start
         *   the start date as milliseconds
         * @param end
         *   the end date as milliseconds
         * @returns {number}
         */
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
        },

        /**
         * Returns the tasks between given dates
         * 
         * @param start
         * @param end
         * @returns {Array}
         */
        tasks_in_between: function (start, end) {
            var tasks = this.tasks,
                tasks_count = tasks.length,
                tasks_in_between_list = [],
                task = null,
                i;

            // for dates after today consider only tasks
            for (i = 0; i < tasks_count; i += 1) {
                task = tasks[i];
                if (task.start <= end && task.end >= start) {
                    tasks_in_between_list.push(tasks[i]);
                }
            }
            return tasks_in_between_list;
        },

        /**
         * a synonym for total_logged_milliseconds
         * 
         * @param start
         *   the start date as milliseconds
         * @param end
         *   the end date as milliseconds
         * @returns {number}
         */
        data_in_between: function(start, end) {
            return this.total_logged_milliseconds(start, end);
        },

        /**
         * returns the labels of tasks between the given dates
         *
         * @param start
         * @param end
         */
        data_labels: function (start, end) {
            let tasks = this.tasks_in_between(start, end);
            let task, tasks_title, tasks_title_buffer = [];
            for (let i = 0; i < tasks.length; i += 1) {
                task = tasks[i];
                tasks_title_buffer.push('task_ids=' + task.id);
            }

            if (tasks_title_buffer.length === 0) {
                tasks_title = "<span>-- No Tasks --</span>";
            } else {
                tasks_title = '<a class="pull-right" data-target="#dialog_template" data-toggle="modal" data-keyboard="false" href="/tasks/change/properties/dialog?' + tasks_title_buffer.join("&") + '"> <i class="icon-edit bigger-130"></i> </a>';
            }
            return tasks_title;
        },

        /**
         * returns the efficiency of this resource, it is 1 by default but if
         * this resource is a department then the efficiency can be bigger than
         * 1
         * 
         */
        data_scale: function() {
            return this.resource_count;
        }

    });
});
