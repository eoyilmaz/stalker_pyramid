define([
    "dojo/_base/declare",
    'dojo/_base/lang',
    "dgrid/OnDemandGrid",
    "dgrid/ColumnSet",
    "dgrid/Selection",
    "dgrid/Keyboard",
    "dgrid/tree",
    "dgrid/extensions/DijitRegistry",
    "put-selector/put",
    "stalker/js/GanttColumn",
    "dgrid/extensions/ColumnResizer"
], function (declare, lang, OnDemandGrid, ColumnSet, Selection, Keyboard, tree,
             DijitRegistry, put, GanttColumn, ColumnResizer) {
    // module:
    //     GanttGrid
    // summary:
    //     A dgrid extension to create a gantt chart, with columns for tasks,
    //     resources, and time lines

    // Creates a new grid with one column set definition to display tasks & resources and a second
    // column set for the actual gantt chart
    "use strict";
    return declare([OnDemandGrid, ColumnSet, Selection, Keyboard, DijitRegistry, ColumnResizer], {
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
        selected_ids: function () {
            var selection, selected_ids, obj;
            selection = this.selection;
            selected_ids = [];
            for (obj in selection) {
                selected_ids.push(obj);
            }
            return selected_ids;
        },
        columnSets: [
            // Column set to display task and resource
            [
                {
                    action: {
                        label: "Action",
                        sortable: false,
                        get: function (object) {
                            return object;
                        },
                        formatter: function (object) {
                            var object_type = object.type;
                            var id_template_str = '<div class="action-buttons">' +
                                '<a onclick="javascript:scrollToTaskItem(' + object.start + ')" class="blue" title="Scroll To"><i class="icon-exchange"></i></a>' +
                                '<a href="' + object.link + '" class="green" title="View"><i class="icon-info-sign"></i></a>' +
                                '</div>';

                            var id_template = doT.template(id_template_str);
                            return id_template(object);
                        },
                        resizable: false
                    },
                    id: {
                        label: "ID",
                        sortable: false,
                        get: function (object) {
                            return object;
                        },
                        formatter: function (object) {
                            return '<a href="' + object.link + '">' + object.id + '</a>';
                        },
                        resizable: true
                    },
                    name: tree(
                        {
                            label: "Name",
                            sortable: false,
                            resizable: true,
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
                                template_var.link = object.link;
                                template_var.id = object.id;
                                template_var.name = object.name;
                                template_var.start = object.start;
                                template_var.end = object.end;
                                template_var.type = object.type;

                                return template(template_var);
                            },
                            renderExpando: function (level, hasChildren, expanded, object) {
                                // summary:
                                //     Provides default implementation for column.renderExpando.

                                var dir = this.grid.isRTL ? "right" : "left",
                                    cls = ".dgrid-expando-icon",
                                    node;
                                if (hasChildren){
                                    cls += ".ui-icon.ui-icon-triangle-1-" + (expanded ? "se" : "e");
                                }
                                node = put("div" + cls + "[style=margin-" + dir + ": " +
                                    (level * (this.indentWidth || 9)) + "px; float: " + dir + "; position: inherit]");
                                node.innerHTML = "&nbsp;"; // for opera to space things properly
                                return node;
                            }
                        }
                    ),
                    complete: {
                        label: '%',
                        sortable: false,
                        resizable: true,
                        get: function (object) {
                            return object;
                        },
                        formatter: function (object) {
                            var p_complete, p_complete_str, p_complete_rounded, bg_color, font_weight;
                            p_complete = object.schedule_seconds > 0 ? object.total_logged_seconds / object.schedule_seconds * 100 : 0;

                            font_weight = 'normal';

                            // check if it has a floating part

                            p_complete_str = p_complete.toFixed(0);
                            p_complete_rounded = (Math.floor(p_complete / 10) * 10).toFixed(0);

                            return '<div class="percentComplete' + p_complete_rounded + '">' + p_complete_str + '</div>';
                        }
                    },
                    resource: {
                        label: "Resource",
                        sortable: false,
                        resizable: true,
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
                        resizable: true,
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
                            }, timing = '';

                            if (object.type !== 'Project') {
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
                            }
                            return timing;
                        }
                    },
                    start: {
                        label: 'Start',
                        sortable: false,
                        resizable: true,
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
                        resizable: true,
                        get: function (object) {
                            return object;
                        },
                        formatter: function (object) {
                            var end_date = new Date(object.end);
                            return end_date.format("yyyy-mm-dd HH:MM");
                        }
                    },
//                    dependencies: {
//                        label: 'Dependencies',
//                        sortable: false,
//                        get: function(object) {
//                            return object;
//                        },
//                        formatter: function(object) {
//                            return object;
//                        }
//                    }
                }
            ],

            // Column set to display gantt chart; note that this is not associated with
            // any actual property of the data object because it uses the whole object to
            // render
            [
                {
                    chart: new GanttColumn({
                        scale: 'w',
                        resizable: true,
                        start: function () {
                            var today = moment();
                            return today.subtract(6, 'month').startOf('isoweek');
                        },
                        end: function () {
                            var today = moment();
                            return today.add(6, 'month').endOf('isoweek');
                        },
                        sortable: false
                    })
                }
            ]
        ]
    });
});
