define([
    "dojo/_base/declare"
], function (declare) {
    'use strict';
    return declare('Task', null, {
        id: null,

        name: '',
        full_path: '',
        description: '',

        priority: 500,

        entity_type: 'Task',
        task_type: '',

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
//        schedule_constraint: 0,

        schedule_seconds: 0,
        total_logged_seconds: 0,

        remaining_seconds: null,

        progress: 0,

        status: 'new',

        bid_timing: 10,
        bid_unit: 'h',

        is_milestone: false,

        clippedStart: false,
        clippedEnd: false,

        resources: [],
        resource_ids: [],

        responsible: [],
        responsible_ids: [],

        time_logs: [],
        time_log_ids: [],

        constructor: function (settings) {
            this.grid = settings.grid || null;

            this.id = settings.id || null;
            this.name = settings.name || null;
            this.full_path = settings.full_path || '';
            this.description = settings.description || null;

            this.priority = settings.priority || 500;

            this.entity_type = settings.entity_type || 'Task';
            this.task_type = settings.task_type || '';

            this.parent_id = settings.parent_id || null;
            this.parent = settings.parent || null;

            this.hasChildren = settings.hasChildren || false;

            this.depend_ids = settings.depend_ids || [];

            this.start = settings.start || null;
            this.duration = settings.duration || null;
            this.end = settings.end || null;

            this.schedule_model = settings.schedule_model || this.schedule_model;
            this.schedule_timing = (settings.schedule_timing || 10).toFixed(1) || this.schedule_timing;
            this.schedule_unit = settings.schedule_unit || this.schedule_unit;
//            this.schedule_constraint = settings.schedule_constraint || 0;

            this.schedule_seconds = settings.schedule_seconds || 0;
            this.total_logged_seconds = settings.total_logged_seconds || 0;

            this.remaining_seconds = ((this.schedule_seconds - this.total_logged_seconds) / 3600).toFixed(1) + ' h';

            this.progress = this.schedule_seconds > 0 ? this.total_logged_seconds / this.schedule_seconds * 100 : 0;

            this.bid_timing = settings.bid_timing ? (settings.bid_timing).toFixed(1) : this.bid_timing;
            this.bid_unit = settings.bid_unit || this.bid_unit;

            this.is_milestone = false;

            // some dynamic attributes
            this.resources = settings.resources || [];
            this.resource_ids = settings.resource_ids || [];

//            this.responsible = settings.responsible || null;

            let i;
            if (this.resource_ids.length === 0) {
                // no problem if there are no resources
                for (i = 0; i < this.resources.length; i += 1) {
                    this.resource_ids.push(this.resources[i].id);
                }
            } else {
                if (this.grid !== null) {
                    for (i = 0; i < this.resource_ids.length; i += 1) {
                        this.resources.push(this.master.getResource(this.resource_ids[i]));
                    }
                }
            }

            this.time_logs = [];
            this.time_log_ids = [];

            this.status = settings.status || 'new';
        },

        link: function () {
            let rendered;
            if (this.entity_type === 'Project') {
                rendered = templates.projectLink(this);
            } else {
                rendered = templates.taskLink(this);
            }
            return rendered;
        },

        getResourcesLinks: function () {
            let ret = '', i, resource;
            if (this.resources) {
                for (i = 0; i < this.resources.length; i += 1) {
                    resource = this.resources[i];
                    ret = ret + (ret === "" ? "" : ", ") + templates.resourceLink(resource);
                }
            }
            return ret;
        },

        getResourcesStr: function () {
            let ret = '', i, resource;
            if (this.resources) {
                for (i = 0; i < this.resources.length; i += 1) {
                    resource = this.resources[i];
                    ret = ret + (ret === "" ? "" : ", ") + resource.name;
                }
            }
            return ret;
        }

    });
});
