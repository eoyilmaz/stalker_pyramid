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
    "stalker/js/Task",
    "dgrid/extensions/ColumnResizer"
], function (declare, lang, OnDemandGrid, ColumnSet, Selection, Keyboard, tree,
             DijitRegistry, put, GanttColumn, Task, ColumnResizer) {
    // module:
    //     GanttGrid
    // summary:
    //     A dgrid extension to create a gantt chart, with columns for tasks,
    //     resources, and time lines

    // Creates a new grid with one column set definition to display tasks & resources and a second
    // column set for the actual gantt chart
    "use strict";
    return declare([OnDemandGrid, ColumnSet, Selection, Keyboard, DijitRegistry], {
        keyMap: lang.mixin({}, Keyboard.defaultKeyMap, {
            38: function (event) { // up arrow
                event.preventDefault();
                event.stopPropagation();
                var id, selection = [];
                for (id in this.selection) {
                    selection.push(id);
                }
                var selected_count = selection.length;
                if (selected_count) {
                    var last_selected_row = selection[selected_count - 1];
                    var upper_row = this.up(last_selected_row, 1, true);
                    if (upper_row) {
                        var grid = this;
                        setTimeout(function () {
                            grid.clearSelection();
                        }, 0);
                        setTimeout(function () {
                            grid.focus(upper_row);
                        }, 0);
                        setTimeout(function () {
                            grid.select(upper_row);
                        }, 0);
                    }
                }
            },
            40: function (event) { // down arrow
                event.preventDefault();
                event.stopPropagation();
                var id, selection = [];
                for (id in this.selection) {
                    selection.push(id);
                }
                var selected_count = selection.length;
                if (selected_count) {
                    var last_selected_row = selection[selected_count - 1];
                    var down_row = this.down(last_selected_row, 1, true);
                    if (down_row) {
                        var grid = this;
                        setTimeout(function () {
                            grid.clearSelection();
                        }, 0);
                        setTimeout(function () {
                            grid.focus(down_row);
                        }, 0);
                        setTimeout(function () {
                            grid.select(down_row);
                        }, 0);
                    }
                }
            },
            39: function (event) { // right arrow
                event.preventDefault();
                event.stopPropagation();
                var obj;
                for (obj in this.selection) {
                    this.expand(obj, true);
                }
            },
            /**
             * collapses an expanded row or goes to a parent row if it is
             * already collapsed or is not expandable
             * 
             * @param event
             */
            37: function (event) {  // left arrow
                event.preventDefault();
                event.stopPropagation();
                var row_id, row, expanded, parent_id;

                var grid = this;
                var jump_to_row = function (row) {
                    setTimeout(function () {
                        grid.clearSelection();
                    }, 0);
                    setTimeout(function () {
                        grid.focus(row);
                    }, 0);
                    setTimeout(function () {
                        grid.select(row);
                    }, 0);
                };

                var selected_row_ids = [];
                for (row_id in this.selection) {
                    selected_row_ids.push(row_id);
                }
                var num_of_selection = selected_row_ids.length;

                for (var i = 0; i < num_of_selection ; i += 1) {
                    row_id = selected_row_ids[i];
                    row = this.row(row_id);
                    // if it is an expanded column just collapse it
                    expanded = this._expanded[row_id];
                    if (expanded) {
                        this.expand(row_id, false);
                    } else {
                        // do a special thing just for the last row
                        if ( i === num_of_selection - 1) {
                            // it is not expanded so go to parent
                            parent_id = row.data.parent_id;
                            if (parent_id) {
                                var parent_row = grid.row(parent_id);
                                jump_to_row(parent_row);
                            }
                        }
                    }
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

        /**
         * Storage for hidden column ids
         */
        hidden_columns: [],

        /**
         * Returns true or false according to the display state of the column
         * with the given column_id
         * 
         * @param {string} column_id
         * @returns {boolean}
         */
        is_hidden_column: function (column_id) {
            return this.hidden_columns.indexOf(column_id) !== -1;
        },

        /**
         * Toggles column visibility
         * @param {string} column_id
         */
        toggle_column: function (column_id) {
            if (this.is_hidden_column(column_id)) {
                this.show_column(column_id);
            } else {
                this.hide_column(column_id);
            }
        },

        /**
         * Displays the given column
         * 
         * @param {string} column_id
         *   The column id
         */
        show_column: function (column_id) {
            var full_id = '.dgrid-column-' + column_id;
            $(full_id).filter(function () {
                return $(this).css('display') === 'none';
            }).css({'display': ''});
            // remove from hidden_columns
            var index = this.hidden_columns.indexOf(column_id);
            if (index !== -1) {
                this.hidden_columns.splice(index, 1);
            }
        },

        /**
         * Hides the given column
         * 
         * @param {string} column_id
         *   The column id
         */
        hide_column: function (column_id) {
            setTimeout( // wait until dom actions finished, especially needed for chart
                function () {
                    var full_id = '.dgrid-column-' + column_id;
                    var data = $(full_id).filter(function () {
                        return $(this).css('display') !== 'none';
                    });
                    data.css({'display': 'none'});

                }, 0
            );

            // add to hidden_columns
            if (this.hidden_columns.indexOf(column_id) === -1) {
                this.hidden_columns.push(column_id);
            }

        },

        /**
         * Returns the cookie name that stores the column visibility settings
         */
        cookie_name: function () {
        },

        /**
         * Stores the column visibility states in a cookie
         */
        load_column_visibility_state: function () {
        },

        /**
         * Stores the column visibility states in a cookie
         */
        save_column_visibility_state: function () {
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
                        renderCell: function (object, value, node, options) {
                            var entity_type = object.entity_type;
                            var id_template_str = '<div class="action-buttons">' +
                                '<a onclick="javascript:scrollToTaskItem(' + object.start + ')" title="Scroll To"><i class="icon-exchange"></i></a>' +
                                '<a href="' + object.link + '" title="View"><i class="icon-info-sign"></i></a>' +
                                '</div>';

                            var id_template = doT.template(id_template_str);
                            var node_js = $(node);
                            node_js.addClass(object.status).append(
                                $.parseHTML(id_template(object))
                            );
                            // check if hidden
                            var column_id = 'action';
                            var grid = this.grid;
                            if (grid.is_hidden_column(column_id)) {
                                // also hide this one by default
                                node_js.css({'display': 'none'});
                            }
                        },
                        resizable: false
                    },
                    id: {
                        label: "ID",
                        sortable: false,
                        get: function (object) {
                            return object;
                        },
                        renderCell: function (object, value, node, options) {
                            $(node).addClass(object.status).append(
                                $.parseHTML('<a href="' + object.link + '">' + object.id + '</a>')
                            );
                            // check if hidden
                            var column_id = 'id';
                            var grid = this.grid;
                            if (grid.is_hidden_column(column_id)) {
                                // also hide this one by default
                                $(node).css({'display': 'none'});
                            }
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
                            renderCell: function (object, value, node, options) {
                                var template = templates.taskEditRow;
                                var template_var = {};

                                template_var.font_weight = object.hasChildren ? 'bold' : 'normal';
                                template_var.contextMenuClass = 'taskEditRow';

                                if (object.entity_type === 'Project') {
                                    template_var.contextMenuClass = 'projectEditRow';
                                } else {
                                    if (object.hasChildren) {
                                        template_var.contextMenuClass = 'parentTaskEditRow';
                                    }
                                }

                                template_var.hasChildren = object.hasChildren;
                                template_var.link = object.link;
                                template_var.id = object.id;
                                template_var.name = object.name;
                                template_var.start = object.start;
                                template_var.end = object.end;
                                template_var.entity_type = object.entity_type;

                                $(node).addClass(object.status).append(
                                    $.parseHTML(template(template_var))
                                );
                                // check if hidden
                                var column_id = 'name';
                                var grid = this.grid;
                                if (grid.is_hidden_column(column_id)) {
                                    // also hide this one by default
                                    $(node).css({'display': 'none'});
                                }
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
                        renderCell: function (object, value, node, options) {
                            var p_complete, p_complete_str;
                            p_complete = object.schedule_seconds > 0 ? object.total_logged_seconds / object.schedule_seconds * 100 : 0;
                            // check if it has a floating part
                            p_complete_str = p_complete.toFixed(0);

                            $(node).addClass(object.status).append(
                                $.parseHTML('<div class="' + object.status + '">' + p_complete_str + '</div>')
                            );
                            // check if hidden
                            var column_id = 'complete';
                            var grid = this.grid;
                            if (grid.is_hidden_column(column_id)) {
                                // also hide this one by default
                                $(node).css({'display': 'none'});
                            }
                        }
                    },
                    resource: {
                        label: "Resource",
                        sortable: false,
                        resizable: true,
                        get: function (object) {
                            return object;
                        },
                        renderCell: function (object, value, node, options) {
                            var ret = '', i, resource;
                            if (object.resources) {
                                for (i = 0; i < object.resources.length; i++) {
                                    resource = object.resources[i];
                                    ret = ret + (ret === "" ? "" : ", ") + templates.resourceLink(resource);
                                }
                            }
                            $(node).addClass(object.status).append(
                                $.parseHTML(ret)
                            );
                            // check if hidden
                            var column_id = 'resource';
                            var grid = this.grid;
                            if (grid.is_hidden_column(column_id)) {
                                // also hide this one by default
                                $(node).css({'display': 'none'});
                            }
                        }
                    },
                    timing: {
                        label: 'Timing',
                        sortable: false,
                        resizable: true,
                        get: function (object) {
                            return object;
                        },
                        renderCell: function (object, value, node, options) {
                            // map time unit names
                            var time_unit_names = {
                                'min': 'Minute',
                                'h': 'Hour',
                                'd': 'Day',
                                'w': 'Week',
                                'm': 'Month',
                                'y': 'Year'
                            }, timing = '';

                            if (object.entity_type !== 'Project') {
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
                            $(node).addClass(object.status).text(timing);
                            // check if hidden
                            var column_id = 'timing';
                            var grid = this.grid;
                            if (grid.is_hidden_column(column_id)) {
                                // also hide this one by default
                                $(node).css({'display': 'none'});
                            }
                        }
                    },
                    start: {
                        label: 'Start',
                        sortable: false,
                        resizable: true,
                        get: function (object) {
                            return object;
                        },
                        renderCell: function (object, value, node, options) {
                            var start_date = moment(object.start);
                            $(node).addClass(object.status);
                            $(node).text(
                                start_date.format("YYYY-MM-DD HH:mm")
                            );
                            // check if hidden
                            var column_id = 'start';
                            var grid = this.grid;
                            if (grid.is_hidden_column(column_id)) {
                                // also hide this one by default
                                $(node).css({'display': 'none'});
                            }
                        }
                    },
                    end: {
                        label: 'End',
                        sortable: false,
                        resizable: true,
                        get: function (object) {
                            return object;
                        },
                        renderCell: function (object, value, node, options) {
                            var end_date = moment(object.end);
                            $(node).addClass(object.status);
                            $(node).text(
                                end_date.format("YYYY-MM-DD HH:mm")
                            );
                            // check if hidden
                            var column_id = 'end';
                            var grid = this.grid;
                            if (grid.is_hidden_column(column_id)) {
                                // also hide this one by default
                                $(node).css({'display': 'none'});
                            }
                        }
                    },
                    status: {
                        label: 'Status',
                        sortable: false,
                        resizable: true,
                        get: function (object) {
                            return object;
                        },
                        renderCell: function (object, value, node, options) {
                            $(node).addClass(object.status);
                            $(node).append(
                                $.parseHTML('<span class="' + object.status + '">' + object.status + '</span>')
                            );
                            // check if hidden
                            var column_id = 'status';
                            var grid = this.grid;
                            if (grid.is_hidden_column(column_id)) {
                                // also hide this one by default
                                $(node).css({'display': 'none'});
                            }
                        }
                    },
                    dependencies: {
                        label: 'Dependencies',
                        sortable: false,
                        get: function(object) {
                            return object;
                        },
                        renderCell: function(object, value, node, options) {
                            $(node).addClass(object.status);

                            if (object.entity_type !== 'Project') {
                                var link_template = doT.template('<a href="/tasks/{{= it.id}}/view">{{= it.name}}</a>');
                                var link_string = '';
                                for (var i = 0; i < object.dependencies.length; i += 1) {
                                    link_string += i > 0 ? ', ' : '';
                                    link_string += link_template(object.dependencies[i]);
                                }
    
                                $(node).append($.parseHTML(link_string));
                            }
                            // check if hidden
                            var column_id = 'dependencies';
                            var grid = this.grid;
                            if (grid.is_hidden_column(column_id)) {
                                // also hide this one by default
                                $(node).css({'display': 'none'});
                            }
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
