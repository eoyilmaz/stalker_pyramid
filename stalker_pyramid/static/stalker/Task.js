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
    "dojo/_base/declare"
], function (declare) {
    'use strict';
    return declare('Task', null, {
        id: null,

        name: '',
        hierarchy_name: '',
        description: '',

        priority: 500,

        type: 'Task',

        children: [],
        child_ids: [],
        hasChildren: false,

        parent: null,
        parent_id: null,

        depend_ids: [],
        depends: null,

        start: null,
        duration: null,
        end: null,

        schedule_model: 'effort',
        schedule_timing: 10,
        schedule_unit: 'h',
        schedule_constraint: 0,

        schedule_seconds: 0,
        total_logged_seconds: 0,

        remaining_seconds: null,

        progress: 0,

        bid_timing: null,
        bid_unit: null,

        is_milestone: false,
        startIsMilestone: false,
        endIsMilestone: false,

        clippedStart: false,
        clippedEnd: false,

        resources: [],
        resource_ids: [],

        responsible: [],
        responsible_ids: [],

        time_logs: [],
        time_log_ids: [],

        hasExternalDep: false,

        constructor: function (kwargs) {
            this.grid = kwargs.grid;

            this.id = kwargs.id || null;
            this.name = kwargs.name || null;
            this.hierarchy_name = kwargs.hierarchy_name || '';
            this.description = kwargs.description || null;

            this.priority = kwargs.priority || 500;

            this.type = kwargs.type || 'Task';

            this.parent_id = kwargs.parent_id || null;
            this.parent = kwargs.parent || null;

            this.hasChildren = kwargs.hasChildren || false;

            this.depend_ids = kwargs.depend_ids || [];

            this.start = kwargs.start || null;
            this.duration = kwargs.duration || null;
            this.end = kwargs.end || null;

            this.schedule_model = kwargs.schedule_model;
            this.schedule_timing = (kwargs.schedule_timing || 10).toFixed(1);
            this.schedule_unit = kwargs.schedule_unit || 'h';
            this.schedule_constraint = kwargs.schedule_constraint || 0;

            this.schedule_seconds = kwargs.schedule_seconds || 0;
            this.total_logged_seconds = kwargs.total_logged_seconds || 0;

            this.remaining_seconds = ((this.schedule_seconds - this.total_logged_seconds) / 3600 ).toFixed(1) + ' h';

            this.progress = this.schedule_seconds > 0 ? this.total_logged_seconds / this.schedule_seconds * 100 : 0;

            this.bid_timing = (kwargs.bid_timing).toFixed(1);
            this.bid_unit = kwargs.bid_unit;

            this.is_milestone = false;
            this.startIsMilestone = false;
            this.endIsMilestone = false;

            // some dynamic attributes
            this.resources = kwargs.resources || [];
            this.resource_ids = kwargs.resource_ids || [];

            this.responsible = kwargs.responsible;

            var i;
            if (this.resource_ids.length === 0) {
                // no problem if there are no resources
                for (i = 0; i < this.resources.length; i++) {
                    this.resource_ids.push(this.resources[i].id);
                }
            } else {
                if (this.grid !== null) {
                    for (i = 0; i < this.resource_ids.length; i++) {
                        this.resources.push(this.master.getResource(this.resource_ids[i]));
                    }
                }
            }

            this.time_logs = [];
            this.time_log_ids = [];

            this.hasExternalDep = kwargs.hasExternalDep || false;
        },

        link: function () {
            var rendered;
            if (this.type === 'Project') {
                rendered = templates.projectLink(this);
            } else {
                rendered = templates.taskLink(this);
            }
            return rendered;
        },

        getResourcesLinks: function () {
            var ret = '', i, resource;
            if (this.resources) {
                for (i = 0; i < this.resources.length; i++) {
                    resource = this.resources[i];
                    ret = ret + (ret === "" ? "" : ", ") + templates.resourceLink(resource);
                }
            }
            return ret;
        },

        getResourcesStr: function () {
            var ret = '', i, resource;
            if (this.resources) {
                for (i = 0; i < this.resources.length; i++) {
                    resource = this.resources[i];
                    ret = ret + (ret === "" ? "" : ", ") + resource.name;
                }
            }
            return ret;
        }

    });
});
