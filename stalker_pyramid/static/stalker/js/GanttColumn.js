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
    'dojo/dom-construct',
    "dojo/_base/array",
    'dojo/_base/lang',
    "dojo/date/locale",
    "put-selector/put",
    'stalker/js/Task',
    'stalker/js/HeaderCell'
], function (domConstruct, array, lang, locale, put, Task, draw_header_cell) {
    // module:
    //     ganttColumn
    // summary:
    //     A dgrid column plugin that generates gantt chart time lines in a
    //     column.

    function getColumnSetElement(element) {
        // summary:
        //     Finds the column set parent element of a given cell.
        // element:
        //     DomNode
        // returns:
        //     DomNode?
//        console.debug('element: ', element);
        if (element) {
            element = element.parentNode;
            while (element && element.className !== "dgrid-column-set") {
                element = element.parentNode;
            }
        }
        return element;
    }

    /**
     * Render the given time log data under to the given parent
     * 
     * @param options
     * @returns {*|jQuery|HTMLElement}
     */
    var draw_cell = function (options) {
        var parent = options.parent;
        var data = options.data;
        var start = options.start;
        var end = options.end;
        var scale = options.scale;

        // create a Task instance
        var task = new Task(data);

        var start_date = moment(start).startOf('day');
        var end_date = moment(end).endOf('day');

        // The start position of the task bar for this task, in pixels
        var task_bar;

        var parent_div = $($.parseHTML('<div class="taskContainer"></div>'));
        parent_div.css({
            width: Math.floor((end_date - start_date) / scale)
        });
        $(parent).append(parent_div);

        if (task.type === 'Project') {
            task_bar = $($.parseHTML(templates.projectBar(task)));
        } else if (task.type === 'Task' || task.type === 'Asset' ||
                   task.type === 'Shot' || task.type === 'Sequence') {
            if (task.hasChildren) {
                task_bar = $($.parseHTML(templates.parentTaskBar(task)));
            } else {
                task_bar = $($.parseHTML(templates.taskBar(task)));
            }
        }

        task_bar.css({
            width: Math.floor((task.end - task.start) / scale),
            left: Math.floor((task.start - start_date) / scale)
        });

        parent_div.append(task_bar);
        return parent_div;
    };

    var zoom_levels = {
        "h": {
            scale: 120000, // 1 hour is 30 px
            table_width: function (start, end) {
                var start_date = moment(start).startOf('day');
                var end_date = moment(end).endOf('day');
                return Math.floor((end_date - start_date) / this.scale);
            },
            headers: [
                {
                    draw: function (parent, start, end) {
                        return draw_header_cell({
                            parent: parent,
                            start: start,
                            end: end,
                            scale: 120000,
                            step_size: 7,
                            step_unit: 'day',
                            period_unit: 'isoweek',
                            height: 26,
                            format: '[Week] w'
                        });
                    }
                },
                {
                    draw: function (parent, start, end) {
                        return draw_header_cell({
                            parent: parent,
                            start: start,
                            end: end,
                            scale: 120000,
                            step_size: 1,
                            step_unit: 'day',
                            period_unit: 'day',
                            height: 26,
                            format: 'ddd, DD-MMM-YYYY'
                        });
                    }
                },
                {
                    draw: function (parent, start, end) {
                        return draw_header_cell({
                            parent: parent,
                            start: start,
                            end: end,
                            scale: 120000,
                            step_size: 1,
                            step_unit: 'hour',
                            period_unit: 'hour',
                            height: 26,
                            format: 'H'
                        });
                    }
                }

            ],
            'chart': {
                'element_width': 30, // in px
                'draw': function (parent, data, start, end) {
                    return draw_cell({
                        parent: parent,
                        data: data,
                        start: start,
                        end: end,
                        scale: 120000
                    });
                }
            }
        },
        "d": {
            scale: 2880000, // 1 day is 30 px
            table_width: function (start, end) {
                var start_date = moment(start).startOf('day');
                var end_date = moment(end).endOf('day');
                return Math.floor((end_date - start_date) / this.scale);
            },
            headers: [
                {
                    draw: function (parent, start, end) {
                        return draw_header_cell({
                            parent: parent,
                            start: start,
                            end: end,
                            scale: 2880000,
                            step_size: 1,
                            step_unit: 'month',
                            period_unit: 'month',
                            height: 26,
                            format: 'MMM YYYY'
                        });
                    }
                },
                {
                    draw: function (parent, start, end) {
                        return draw_header_cell({
                            parent: parent,
                            start: start,
                            end: end,
                            scale: 2880000,
                            step_size: 7,
                            step_unit: 'day',
                            period_unit: 'isoweek',
                            height: 26,
                            format: '[Week] w'
                        });
                    }
                },
                {
                    draw: function (parent, start, end) {
                        return draw_header_cell({
                            parent: parent,
                            start: start,
                            end: end,
                            scale: 2880000,
                            step_size: 1,
                            step_unit: 'day',
                            period_unit: 'day',
                            height: 26,
                            format: 'D'
                        });
                    }
                },
                {
                    draw: function (parent, start, end) {
                       return draw_header_cell({
                            parent: parent,
                            start: start,
                            end: end,
                            scale: 2880000,
                            step_size: 1,
                            step_unit: 'day',
                            period_unit: 'day',
                            height: 26,
                            format: 'dd'
                        });
                    }
                }
            ],
            'chart': {
                'element_width': 30, // in px
                'draw': function (parent, data, start, end) {
                    return draw_cell({
                        parent: parent,
                        data: data,
                        start: start,
                        end: end,
                        scale: 2880000
                    });
                }
            }
        },
        "w": {
            scale: 21600000, // 1 week is 28 px
            table_width: function (start, end) {
                var start_date = moment(start).startOf('day');
                var end_date = moment(end).endOf('day');
                return Math.floor((end_date - start_date) / this.scale);
            },
            headers: [
                {
                    draw: function (parent, start, end) {
                        return draw_header_cell({
                            parent: parent,
                            start: start,
                            end: end,
                            scale: 21600000,
                            step_size: 1,
                            step_unit: 'year',
                            period_unit: 'year',
                            height: 26,
                            format: 'YYYY'
                        });
                    }
                },
                {
                    draw: function (parent, start, end) {
                        return draw_header_cell({
                            parent: parent,
                            start: start,
                            end: end,
                            scale: 21600000,
                            step_size: 1,
                            step_unit: 'month',
                            period_unit: 'month',
                            height: 26,
                            format: 'MMM'
                        });
                    }
                },
                {
                    draw: function (parent, start, end) {
                        return draw_header_cell({
                            parent: parent,
                            start: start,
                            end: end,
                            scale: 21600000,
                            step_size: 7,
                            step_unit: 'day',
                            period_unit: 'isoweek',
                            height: 26,
                            format: 'w'
                        });
                    }
                }
            ],
            'chart': {
                'element_width': 28, // in px
                'draw': function (parent, data, start, end) {
                    return draw_cell({
                        parent: parent,
                        data: data,
                        start: start,
                        end: end,
                        scale: 21600000
                    });
                }
            }
        },
        "m": { // 
            scale: 86400000, // 1 month is 30 px
            table_width: function (start, end) {
                var start_date = moment(start).startOf('day');
                var end_date = moment(end).endOf('day');
                return Math.floor((end_date - start_date) / this.scale);
            },
            headers: [
                { // years
                    draw: function (parent, start, end) {
                        return draw_header_cell({
                            parent: parent,
                            start: start,
                            end: end,
                            scale: 86400000,
                            step_size: 1,
                            step_unit: 'year',
                            period_unit: 'year',
                            height: 26,
                            format: 'YYYY'
                        });
                    }
                },
//                { // quarters
//                    draw: function (parent, start, end) {
//                        return draw_header_cell({
//                            parent: parent,
//                            start: +moment(start).startOf('year'),
//                            end: end,
//                            scale: 86400000,
//                            step_size: 3,
//                            step_unit: 'month',
//                            period_unit: 'month',
//                            height: 26,
//                            format: function (region_start, region_end) {
//                                return 'Q' + Math.floor(moment(region_start).month() / 4);
//                            }
//                        });
//                    }
//                },
                { // months
                    draw: function (parent, start, end) {
                        return draw_header_cell({
                            parent: parent,
                            start: start,
                            end: end,
                            scale: 86400000,
                            step_size: 1,
                            step_unit: 'month',
                            period_unit: 'month',
                            height: 26,
                            format: 'M'
                        });
                    }
                }
            ],
            'chart': {
                'element_width': 30, // in px
                'draw': function (parent, data, start, end) {
                    return draw_cell({
                        parent: parent,
                        data: data,
                        start: start,
                        end: end,
                        scale: 86400000
                    });
                }
            }
        },
        "y": { // 
            scale: 315360000, // 1 year is 100 px 31536000000/100
            table_width: function (start, end) {
                var start_date = moment(start).startOf('day');
                var end_date = moment(end).endOf('day');
                return Math.floor((end_date - start_date) / this.scale);
            },
            headers: [
                { // years
                    draw: function (parent, start, end) {
                        return draw_header_cell({
                            parent: parent,
                            start: start,
                            end: end,
                            scale: 315360000,
                            step_size: 1,
                            step_unit: 'year',
                            period_unit: 'year',
                            height: 26,
                            format: 'YYYY'
                        });
                    }
                }
            ],
            'chart': {
                'element_width': 100, // in px
                'draw': function (parent, data, start, end) {
                    return draw_cell({
                        parent: parent,
                        data: data,
                        start: start,
                        end: end,
                        scale: 315360000
                    });
                }
            }
        }
    };


    return function (column) {
        // summary:
        //     Updates a column definition with special rendering methods that
        //     generate a gantt style chart.
        // column: Object
        //     A column definition with the following special keys:
        //     - start: Date|number
        //         The start date of the gantt chart's viewport, either as a
        //         Date object or in milliseconds since the Unix epoch.
        //     - end: Date|number
        //         The end date of the gantt chart's viewport, either as a Date
        //         object or in milliseconds since the Unix epoch.
        //     - scale: number
        //         The number of milliseconds that one pixel represents.

        if (typeof(column.start) === 'function') {
            column.start = +column.start();
        } else {
            column.start = +column.start;
        }

        if (typeof(column.end) === 'function') {
            column.end = +column.end();
        } else {
            column.end = +column.end;
        }

        var dependencyRow,
            firstCell;

        /**
         * Renders the today line under to the given parent
         * 
         * @param {object} parent
         * @param {number} start
         * @param {number} scale
         */
        var render_today = function (parent, start, scale) {
            var today = moment();
            var start_date = moment(start).startOf('day');
            var today_element = $($.parseHTML('<div></div>'));
            today_element.addClass('today').css({
                left: Math.floor((today - start_date) / scale)
            });
            $(parent).append(today_element);
        };

        /**
         * Calculates the number of div element going to be rendered for one
         * row when the start and end dates and zoom level is set to given
         * parameters. So one can use it to calculate how much is it going to
         * take.
         * 
         * @param start
         * @param end
         * @param zoom_level
         * @returns {number}
         */
        column.guess_element_count = function(start, end, zoom_level) {
            var table_width = zoom_levels[zoom_level].table_width(start, end);
            var element_width = zoom_levels[zoom_level].chart.element_width;
            return Math.floor(table_width / element_width);
        };

        /**
         * Converts the given start and end pixel values to start and end dates
         * in millies
         * 
         * @param start
         * @param end
         */
        column.convert_pixel_to_millies = function (start, end) {
            var scale = zoom_levels[column.scale].scale;
            var start_date = moment(column.start).startOf('day');
            return {
                start: start * scale + start_date,
                end: end * scale + start_date
            };
        };

        /**
         * Returns the best zoom level for the given start and end range
         * @param start
         * @param end
         */
        column.guess_zoom_level = function(start, end) {
            // get the zoom level with the desired scale so the range will have
            // around 100 boxes
            var range = end - start;
            var desired_element_count = 100;
            var min_ratio = 1e10;
            var current_ratio;
            var current_element_count;
            var desired_level = null;
            for (var level in zoom_levels) {
                if (level !== null) {
                    current_element_count = this.guess_element_count(start, end, level);
                    current_ratio = desired_element_count / current_element_count + current_element_count / desired_element_count - 2;
//                    console.log('level:', level,'ratio:', current_ratio);
                    if (current_ratio < min_ratio) {
                        min_ratio = current_ratio;
                        desired_level = level;
                    }
                }
            }
            return desired_level;
        };

        /**
         * Renders one row
         * 
         * @param data
         * @param value
         * @param td
         */
        column.renderCell = function (data, value, td) {
            // summary:
            //     Renders a task.
            // object: Object
            //     An object representing a task with the following special
            //     keys:
            //     - start: Date|number
            //         The start time for the task, either as a Date object or
            //         in milliseconds since the Unix epoch.
            //     - end: Date|number
            //         The end time for the task, either as a Date object or in
            //         milliseconds since the Unix epoch.
            //     - completed: number
            //         The amount of the task that has been completed, between
            //         0 and 1.
            //     - dependencies: any[]
            //         An array of data objects or data object identifiers that
            //         this task depends on.
            // value: unused
            // td: DomNode

            // render cells
            zoom_levels[column.scale].chart.draw(td, data, column.start, column.end);

            // render today
            render_today(td, column.start, zoom_levels[column.scale].scale);
        };

        column.refresh = function (options) {
            // summary:
            //     Refreshes the header cell
            // remove the header contents

            // set some defaults
            options = lang.mixin(
                { // default values
                    'start': column.start,
                    'end': column.end,
                    'scale': column.scale
                },
                options
            );

            domConstruct.empty(column.headerNode);
            column.renderHeaderCell(column.headerNode);

            column.start = options.start;
            column.end = options.end;
            column.scale = options.scale;

            // let it adjust the scrollbars
            column.grid.resize();
        };

        column.reload = function () {
            // summary:
            //      reloads the grid data
            column.grid.refresh();
        };

        column.scrollToDate = function (date) {
            // scrolls to the given date
            var date_as_millis, date_x, scroller, scroller_width;

            header = $(column.headerNode);

            date_as_millis = +date;
            var start_date = moment(column.start).startOf('day');
            date_x = (date_as_millis - start_date) / zoom_levels[column.scale].scale;

            scroller = $('.dgrid-column-set-scroller-1');
            scroller_width = scroller.width();
            scroller.scrollLeft(date_x - scroller_width * 0.5);
        };


        column.centerOnToday = function () {
            // scrolls to today
            column.scrollToDate(new Date());
        };

        column.renderHeaderCell = function (th) {
            // fix scrolling
            var table_width = zoom_levels[column.scale].table_width(column.start, column.end);
            column.grid.addCssRule(".dgrid-column-chart", "width: " + table_width + "px");

            $(th).css({
                width: table_width
            });

            // get element width
            // render headers
            var i;
            var header_count = zoom_levels[column.scale].headers.length;
            var parent_div;
            for (i = 0; i < header_count; i += 1) {
                parent_div = zoom_levels[column.scale].headers[i].draw(th, column.start, column.end);
                parent_div.css({
                    top: i * 27
                });
            }
            // extend the height of the table header
            $(th).css({
                height: header_count * 27 // 27 px each
            });

            // render today
            render_today(th, column.start, zoom_levels[column.scale].scale);
        };

        return column;
    };
});
