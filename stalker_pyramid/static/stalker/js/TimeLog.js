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
