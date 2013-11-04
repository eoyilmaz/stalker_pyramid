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
    "stalker/js/ResourceColumn"
], function (declare, lang, OnDemandGrid, ColumnSet, Selection, Keyboard, tree,
             DijitRegistry, put, ResourceColumn) {
    // module:
    //     GanttGrid
    // summary:
    //     A dgrid extension to create a gantt chart, with columns for tasks, resources, and timelines

    // Creates a new grid with one column set definition to display tasks & resources and a second
    // column set for the actual gantt chart
    "use strict";
    return declare([OnDemandGrid, ColumnSet, Selection, Keyboard, DijitRegistry], {
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
//                    action: {
//                        label: "Action",
//                        sortable: false,
//                        get: function (object) {
//                            return object;
//                        },
//                        formatter: function (object) {
//                            console.debug('action formatter start');
//                            var object_type, id_template_str, id_template;
//                            object_type = object.type;
//                            id_template_str = '<div class="action-buttons">' +
//                                '<a onclick="javascript:scrollToTaskItem(' + object.start + ')" class="blue" title="Scroll To"><i class="icon-exchange"></i></a>' +
//                                '<a href="' + object.link + '" class="green" title="View"><i class="icon-info-sign"></i></a>' +
//                                '</div>';
//
//                            id_template = doT.template(id_template_str);
//
//                            var return_val = id_template(object);
//                            console.debug('action formatter end');
//                            return return_val;
//                        },
//                        resizable: true
//                    },
                    id: {
                        label: "ID",
                        sortable: false,
                        get: function (object) {
                            return object;
                        },
                        formatter: function (object) {
//                            console.debug('id formatter start');
//                            var return_val = '<a href="' + object.link + '">' + object.id + '</a>';
//                            console.debug('id formatter stop');
//                            return return_val;
                            return object.id;
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
//                                console.debug('tree formatter start');
//                                var template = templates.taskEditRow;
//                                var template_var = {};
//                                template_var.font_weight = object.hasChildren ? 'bold' : 'normal';
//                                template_var.contextMenuClass = 'taskEditRow';
//                                if (object.type === 'Project') {
//                                    template = templates.projectEditRow;
//                                    template_var.contextMenuClass = 'projectEditRow';
//                                } else {
//                                    if (object.hasChildren) {
//                                        template = templates.parentTaskEditRow;
//                                        template_var.contextMenuClass = 'parentTaskEditRow';
//                                    } else {
//                                        template_var.responsible = {
//                                            id: object.responsible.id,
//                                            name: object.responsible.name
//                                        };
//                                    }
//                                }
//
//                                template_var.hasChildren = object.hasChildren;
//                                template_var.link = object.link;
//                                template_var.id = object.id;
//                                template_var.name = object.name;
//                                template_var.start = object.start;
//                                template_var.end = object.end;
//                                template_var.type = object.type;
//
//                                var return_val = template(template_var);
                                var return_val = object.name;

//                                console.debug('tree formatter end');
                                return return_val;
                            },
                            renderExpando: function (level, hasChildren, expanded, object) {
                                // summary:
                                //     Provides default implementation for column.renderExpando.

                                var dir = this.grid.isRTL ? "right" : "left",
                                    cls = ".dgrid-expando-icon",
                                    node;
                                if (hasChildren) {
                                    cls += ".ui-icon.ui-icon-triangle-1-" + (expanded ? "se" : "e");
                                }
                                node = put("div" + cls + "[style=margin-" + dir + ": " +
                                    (level * (this.indentWidth || 9)) + "px; float: " + dir + "; position: inherit]");
                                node.innerHTML = "&nbsp;"; // for opera to space things properly
                                return node;
                            }
                        }
                    )

                }
            ],

            // Column set to display gantt chart; note that this is not associated with
            // any actual property of the data object because it uses the whole object to
            // render
            [
                {
                    chart: new ResourceColumn({
                        scale: 4000000,
                        start: function () {
                            var today = new Date();
                            // clear the time and set the day to the closest sunday
                            var day = today.getDay();
                            var closest_sunday = today.getTime() - ((7 - day) % 7) * 8640000;
                            // go back 1 and a half years
                            return closest_sunday - 52 * 86400000 * 7 * 1.5;
                        },
                        end: function () {
                            var today = new Date();
                            // clear the time and set the day to the closest sunday
                            var day = today.getDay();
                            var closest_sunday = today.getTime() - ((7 - day) % 7) * 8640000;
                            // go back 1 and a half years
                            return closest_sunday + 52 * 86400000 * 7 * 3 - 1;
                        },
                        sortable: false
                    })
                }
            ]
        ]
    });
});
