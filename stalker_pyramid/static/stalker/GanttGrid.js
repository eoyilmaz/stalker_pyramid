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
                // do something with key right
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
                            var progress = 0, bg_color, font_weight;

                            // TODO: Fix this, and use the total_logged_seconds also for parent tasks
                            if (!object.hasChildren) {
                                progress = object.schedule_seconds > 0 ? object.total_logged_seconds / object.schedule_seconds * 100 : 0;
                            }

                            bg_color = progress >= 100 ? 'rgb(153, 255, 51)' : 'red';
                            font_weight = 'normal';

                            return '<div ' +
                                'style="' +
                                'font-weight: ' + font_weight + ';' +
                                'background-color: ' + bg_color + '">' +
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
                                var template_var = {};

                                template_var.font_weight = object.hasChildren ? 'bold' : 'normal';
                                template_var.contextMenuClass = 'taskEditRow';
                                if (object.type === 'Project') {
                                    template_var.contextMenuClass = '';
                                } else {
                                    if (object.hasChildren) {
                                        template_var.contextMenuClass = 'parentTaskEditRow';
                                    }
                                }

                                template_var.hasChildren = object.hasChildren;
                                template_var.id = object.id;
                                template_var.name = object.name;
                                template_var.start = object.start;
                                template_var.end = object.end;
                                template_var.type = object.type;

                                return templates.taskEditNameRow(template_var);
                            }
                        }
                    ),
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
                    },
                    timing: {
                        label: 'Timing',
                        sortable: false,
                        get: function (object) {
                            return object;
                        },
                        formatter: function (object) {
                            var timing = '';
                            if (!object.hasChildren) {
                                timing = object.schedule_model.toUpperCase()[0] + ': ' + object.schedule_timing + object.schedule_unit;
                            }
                            return timing;
                        }
                    },
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
                        start: new Date().getTime() - 15552000000,
                        end: new Date().getTime() + 15552000000,
                        sortable: false
                    })
                }
            ]
        ]
    });
});
