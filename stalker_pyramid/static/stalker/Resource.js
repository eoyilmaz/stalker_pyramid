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
    "stalker/TimeLog"
], function (declare, TimeLog) {
    'use strict';
    return declare('Resource', null, {
        id: null,
        name: '',
        tasks: [],
        time_logs: [],

        constructor: function (settings) {
            //this.grid = kwargs.grid;

            this.id = settings.id || null;
            this.name = settings.name || null;
            this.type = settings.type || null;

//            this.tasks = kwargs.tasks || [];
            this.tasks = null; // do not manage tasks for now

            this.time_logs = [];

            var time_log_data = settings.time_logs || [];
            var temp_time_log = null;
            for (var i=0; i < time_log_data.length; i++ ){
                temp_time_log = new TimeLog(time_log_data[i]);
                temp_time_log.resource = this;
                this.time_logs.push(temp_time_log);
            }
        },

        link: function () {
            return templates.resourceLink(this);
        }

    });
});
