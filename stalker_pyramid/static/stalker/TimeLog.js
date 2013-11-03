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
    return declare('TimeLog', null, {
        id: null,

        resource: null,
        task: null,

        start: null,
        end: null,

        constructor: function (settings) {
            //this.grid = kwargs.grid;

            this.id = settings.id || null;
            this.start = settings.start || null;
            this.end = settings.end || null;

            // some dynamic attributes
            this.resource_id = settings.resource_id || null;
            this.resource = null; // will be filled by the resource itself
            this.task_id = settings.task_id || null;
            this.task = null; // do not manage tasks for now
        },

        link: function () {
            return templates.taskLink(this);
        },

        getResourceLinks: function () {
            var ret = '';
            if (this.resource) {
                ret = ret + (ret === "" ? "" : ", ") + templates.resourceLink(this.resource);
            }
            return ret;
        },

        getResourcesStr: function () {
            var ret = '';
            if (this.resource) {
                ret = ret + (ret === "" ? "" : ", ") + this.resource.name;
            }
            return ret;
        }

    });
});
