define([
    "dojo/_base/declare",
    'dojo/_base/lang',
    "dgrid/OnDemandGrid",
    "dgrid/ColumnSet",
    "dgrid/Selection",
    "dgrid/Keyboard",
    "dgrid/tree",
    "stalker/GanttColumn"
], function (declare, lang, OnDemandGrid, ColumnSet, Selection, Keyboard, tree,
             GanttColumn) {
    // module:
    //     GanttGrid
    // summary:
    //     A dgrid extension to create a gantt chart, with columns for tasks, resources, and timelines

    // Creates a new grid with one column set definition to display tasks & resources and a second
    // column set for the actual gantt chart
    "use strict";
    return declare([OnDemandGrid, ColumnSet, Selection, Keyboard], {
        keyMap: lang.mixin({}, Keyboard.defaultKeyMap, {
            //    37 - left
            //    38 - up
            //    39 - right
            //    40 - down
            39: function () { // right arrow
                var obj;
                for (obj in this.selection) {
                    this.expand(obj, true);
                }
            },
            37: function () {  // left arrow
                var obj;
                for (obj in this.selection) {
                    this.expand(obj, false);
                }
            },
            65: function () { // "a"
                this.selectAll();
            },
            68: function () { // "d"
                this.clearSelection();
            }
        }),
        columnSets: [
            // Column set to display task and resource
            [
                {
                    id: {
                        label: "ID",
                        sortable: false,
                        get: function (object) {
                            return object;
                        },
                        formatter: function (object) {
                            var p_cmpl, p_cmpl_r, bg_color, font_weight;

                            p_cmpl = object.total_logged_seconds / object.schedule_seconds * 100;
                            p_cmpl_r = (Math.floor(p_cmpl / 10) * 10).toFixed(0);

                            font_weight = 'normal';

                            return '<div class="percentComplete' + p_cmpl_r + '">' +
                                object.id + '</div>';
                        },
                        resizable: true
                    },
                    name: tree(
                        {
                            label: "Name",
                            sortable: false,
                            get: function (object) {
                                return object;
                            },
                            formatter: function (object) {
                                
                                var template = templates.taskEditRow;
                                var template_var = {};
                                template_var.font_weight = object.hasChildren ? 'bold' : 'normal';
                                template_var.contextMenuClass = 'taskEditRow';
                                if (object.type === 'Project') {
                                    template = templates.projectEditRow;
                                    template_var.contextMenuClass = 'projectEditRow';
                                } else {
                                    if (object.hasChildren) {
                                        template = templates.parentTaskEditRow;
                                        template_var.contextMenuClass = 'parentTaskEditRow';
                                    } else {
                                        template_var.responsible = {
                                            id: object.responsible.id,
                                            name: object.responsible.name
                                        };
                                    }
                                }

                                template_var.hasChildren = object.hasChildren;
                                template_var.id = object.id;
                                template_var.name = object.name;
                                template_var.start = object.start;
                                template_var.end = object.end;
                                template_var.type = object.type;

                                return template(template_var);
                            }
                        }
                    ),
                    resource: {
                        label: "Resource",
                        sortable: false,
                        get: function (object) {
                            return object;
                        },
                        formatter: function (object) {
                            var ret = '', i, resource;
                            if (object.resources) {
                                for (i = 0; i < object.resources.length; i++) {
                                    resource = object.resources[i];
                                    ret = ret + (ret === "" ? "" : ", ") + templates.resourceLink(resource);
                                }
                            }
                            return ret;
                        }
                    },
                    timing: {
                        label: 'Timing',
                        sortable: false,
                        get: function (object) {
                            return object;
                        },
                        formatter: function (object) {

                            // map time unit names
                            var time_unit_names = {
                                'h': 'Hour',
                                'd': 'Day',
                                'w': 'Week',
                                'm': 'Month',
                                'y': 'Year'
                            },
                                timing = '';

                            if (!object.hasChildren) {
                                // do not add schedule model if it is the default (effort)
                                if (object.schedule_model !== 'effort') {
                                    timing += object.schedule_model.toUpperCase()[0] + ': ';
                                }
                                if (Math.floor(object.schedule_timing) === object.schedule_timing) {
                                    timing += object.schedule_timing;
                                } else {
                                    timing += (object.schedule_timing).toFixed(1);
                                }
                                
                                timing += ' ' + time_unit_names[object.schedule_unit];

                                // make it plural
                                if (object.schedule_timing > 1) {
                                    timing += 's';
                                }
                            }
                            return timing;
                        }
                    },
                    complete: {
                        label: '% Compl.',
                        sortable: false,
                        get: function (object) {
                            return object;
                        },
                        formatter: function (object) {
                            var p_complete = object.total_logged_seconds / object.schedule_seconds * 100;
                            // check if it has a floating part
                            if (Math.floor(p_complete) === p_complete) {
                                // it is an integer do not fix it
                                return p_complete + '%';
                            } else {
                                // it is a float fix it
                                return p_complete.toFixed(1) + '%';
                            }
                        }
                    },
                    start: {
                        label: 'Start',
                        sortable: false,
                        get: function (object) {
                            return object;
                        },
                        formatter: function (object) {
                            var start_date = new Date(object.start);
                            return start_date.format("yyyy-mm-dd HH:MM");
                        }
                    },
                    end: {
                        label: 'End',
                        sortable: false,
                        get: function (object) {
                            return object;
                        },
                        formatter: function (object) {
                            var end_date = new Date(object.end);
                            return end_date.format("yyyy-mm-dd HH:MM");
                        }
                    }
                }
            ],

            // Column set to display gantt chart; note that this is not associated with
            // any actual property of the data object because it uses the whole object to
            // render
            [
                {
                    chart: new GanttColumn({
                        scale: 4000000,
                        start: new Date().clearTime().getTime() - 15552000000,
                        end: new Date().clearTime().getTime() + 15552000000 + 86400000 - 1,
                        sortable: false
                    })
                }
            ]
        ]
    });
});
