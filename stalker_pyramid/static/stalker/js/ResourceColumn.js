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
    'stalker/js/Resource'
], function (domConstruct, array, lang, locale, put, Resource) {
    // module:
    //     ResourceColumn
    // summary:
    //     A dgrid column plugin that generates resource charts in a column.

    var draw_header_cell = function (options) {
        var parent = options.parent;
        var start = options.start;
        var end = options.end;
        var scale = options.scale;
        var step_size = options.step_size;
        var step_unit = options.step_unit;
        var period_unit = options.preiod_unit;
        var height = options.height;
        var top = options.top;
        var format = options.format;

        var original_start = moment(start).startOf('day');

        var start_date = moment(start).startOf(period_unit).startOf('day');
        var end_date = moment(end).endOf(period_unit).endOf('day');

        // find the end of the first week
        var period_start = moment(start_date.startOf(period_unit));
        var period_end = moment(start_date.endOf(period_unit));
        // create the first div elements using start_date and week_end

        var parent_div = $($.parseHTML('<div class="headerCell"></div>'));
        // fix scroll
        parent_div.css({
            width: Math.floor((end_date - start_date) / scale),
            left: Math.floor((start_date - original_start) / scale),
            height: height,
            top: top,
            position: 'absolute'
        });
        $(parent).append(parent_div);

        var header_div_element;
        // now wee need to iterate until the end_date is bigger than end
        while (period_start < end_date) {
            // create the first div elements using start_date and week_end
            header_div_element = $($.parseHTML('<div class="headerCell center">' + period_start.format(format) + '</div>'));
            header_div_element.css({
                width: Math.floor((period_end - period_start) / scale),
                left: Math.floor((period_start - start_date) / scale)
            });
            parent_div.append(header_div_element);
            // go to next step
            period_start.add(step_size, step_unit).startOf(step_unit);
            period_end.add(step_size, step_unit).endOf(step_unit);
        }
        return parent_div;
    };

    var zoom_levels = {
//        "h": {
//            table_width: function (start, end) {
//                // 1 hour = 40 px
//                return Math.floor((end - start) / 3600000 * 40);
//            },
//            headers: [
//                {
//                    title: function (start, end) {
//                        // return the start day in DD-MM-YYYY format
//                        var start_date = moment(start);
//                        return start_date.format('DD-MM-YYYY');
//                    },
//                    time_step: 864000000 // 24 hours
//                },
//                {
//                    title: function (start, end) {
//                        // return the start day in DD-MM-YYYY format
//                        var start_date = moment(start);
//                        return start_date.format('HH:00');
//                    },
//                    time_step: 3600000 // 1 hour
//                }
//            ]
//        },
//        "d": {
//            table_width: function (start, end) {
//                return Math.floor((end - start) / 21600000 * 50);
//            },
//            headers: [
//                {
//                    title: function (start, end) {
//                        // return the start day in DD-MM-YYYY format
//                        var start_date = moment(start);
//                        return start_date.format('DD-MM-YYYY');
//                    },
//                    time_step: 864000000 // 24 hours
//                },
//                {
//                    title: function (start, end) {
//                        // return the start day in DD-MM-YYYY format
//                        var start_date = moment(start);
//                        return start_date.format('H');
//                    },
//                    time_step: 21600000 // 6 hours
//                }
//            ]
//        },
        "w": {
            scale: 21600000, // 1 day is 4 px
            table_width: function (start, end) {
                var start_date = moment(start).startOf('day');
                var end_date = moment(end).endOf('day');
                return Math.floor((end_date - start_date) / this.scale);
            },
            headers: [
                {
                    draw: function (parent, start, end) {
                        draw_header_cell({
                            parent: parent,
                            start: start,
                            end: end,
                            scale: 21600000,
                            step_size: 1,
                            step_unit: 'month',
                            period_unit: 'month',
                            height: 26,
                            top: 0,
                            format: 'MMM YYYY'
                        });
                    }
                },
                {
                    draw: function (parent, start, end) {
                        draw_header_cell({
                            parent: parent,
                            start: start,
                            end: end,
                            scale: 21600000,
                            step_size: 7,
                            step_unit: 'day',
                            period_unit: 'isoweek',
                            height: 26,
                            top: 27,
                            format: 'w'
                        });
                    }
                }
            ],
            'chart': {
                'draw': function(parent, data, start, end, scale) {
                    // create a TimeLog instance
                    var resource = new Resource(data);
                    var original_start = moment(start).startOf('day');
                    var original_end = moment(end).endOf('day');

                    var start_date = moment(start).startOf('isoweek').startOf('day');
                    var end_date = moment(end).endOf('isoweek').endOf('day');

                    // iterate the weeks from start to end, choose the week start and
                    // dates correctly
                    var range_start = moment(start_date).startOf('isoweek');
                    var range_end = moment(range_start).add(7, 'days');

                    var total_logged_millies;
                    var weekly_millies_possible = 183600000; // 51 hours for anima
                    var weekly_log_bar;
                    var weekly_log_bar_layout_div;

                    var parent_div = $($.parseHTML('<div class="headerCell"></div>'));
                    parent_div.css({
                        width: Math.floor((end_date - start_date) / scale),
                        left: Math.floor((start_date - original_start) / scale), // offset as neccessary
                        height: 24,
                        position: 'absolute'
                    });
                    $(parent).append(parent_div);

                    var Math_floor = Math.floor;
                    var added_first_time_log = false;
                    var resource_count = resource.resource_count;

                    while (range_start < end_date) {
                        total_logged_millies = resource.total_logged_milliseconds(+range_start, +range_end);
                        // draw a div at that range with the height of total_logged_millies
                        if (total_logged_millies > 0 || added_first_time_log) {
                            added_first_time_log = true;
                            weekly_log_bar_layout_div = $($.parseHTML('<div class="log_bar layout"></div>'));
                            weekly_log_bar_layout_div.css({
                                left: Math_floor((range_start - start_date) / scale),
                                width: Math_floor((range_end - range_start) / scale) - 1 // just to give a feeling of border
                            });

                            weekly_log_bar = $($.parseHTML('<div class="log_bar timeLog"></div>'));
                            weekly_log_bar.css({
                                height: Math_floor(total_logged_millies / weekly_millies_possible * 22 / resource_count)// weekly millies possible
                            });
                            weekly_log_bar_layout_div.append(weekly_log_bar);
                            parent_div.append(
                                weekly_log_bar_layout_div
                            );
                        }
                        // get the new start and end values
                        range_start.add(7, 'day');
                        range_end.add(7, 'day');
                    }
                }
            }
        }
//        "m": { // every week in a box
//        },
//        "q": {},
//        "s": {},
//        "y": {}
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

        /**
         * Renders the today line under to the given parent
         * 
         * @param {object} parent
         * @param {number} start
         * @param {number} scale
         */
        var render_today = function (parent, start, scale) {
            var today = moment(new Date());
            var start_date = moment(start).startOf('day');
            var today_element = $($.parseHTML('<div></div>'));
            today_element.addClass('today').css({
                left: Math.floor((today - start_date) / scale)
            });
            $(parent).append(today_element);
        };


        /**
         * summary:
         *     Renders a task.
         * object: Object
         *     An object representing a task with the following special
         *     keys:
         *     - start: Date|number
         *         The start time for the task, either as a Date object or
         *         in milliseconds since the Unix epoch. 
         *     - end: Date|number
         *         The end time for the task, either as a Date object or in
         *         milliseconds since the Unix epoch.
         *     - completed: number
         *         The amount of the task that has been completed, between
         *         0 and 1.
         *     - dependencies: any[]
         *         An array of data objects or data object identifiers that
         *         this task depends on.
         *
         * @param data
         *     Resource Data
         * @param value
         *     unused
         * @param {Object} td
         *     DomNode
         */
        column.renderCell = function (data, value, td) {
            // IE < 8 receive the inner padding node, not the td directly
            var cell = td.tagName === "TD" ? td : td.parentNode;

            var scale = zoom_levels[column.scale].scale;
            // render cells
            zoom_levels[column.scale].chart.draw(td, data, column.start, column.end, scale);

            // render today
            render_today(td, column.start, zoom_levels[column.scale].scale);

        };

        column.refresh = function (kwargs) {
            // summary:
            //     Refreshes the header cell
            // remove the header contents

            // set some defaults
            kwargs = lang.mixin(
                { // default values
                    'start': column.start,
                    'end': column.end
                },
                kwargs
            );

            domConstruct.empty(column.headerNode);
            column.renderHeaderCell(column.headerNode);

            column.start = kwargs.start;
            column.end = kwargs.end;

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
            var header, position, date_as_millis, date_x, scroller,
                scroller_width;

            header = $(column.headerNode);
            position = header.position();

            date_as_millis = +date;
            date_x = (date_as_millis - column.start) / zoom_levels[column.scale].scale;

            scroller = $('.dgrid-column-set-scroller-1');
            scroller_width = scroller.width();
            scroller.scrollLeft(date_x - scroller_width * 0.5);
        };


        column.centerOnToday = function () {
            // scrolls to today
            column.scrollToDate(new Date());
        };

        /**
         * Creates a header cell that contains the dates corresponding to the
         * time lines that are being rendered in the main content
         * 
         * @param {Object} th
         *     DomNode
         */
        column.renderHeaderCell = function (th) {
            // fix scrolling
            var table_width = zoom_levels[column.scale].table_width(column.start, column.end);
            column.grid.addCssRule(".dgrid-column-chart", "width: " + table_width + "px");

            // get element width
            // render headers
            var i;
            var header_count = zoom_levels[column.scale].headers.length;
            for (i = 0; i < header_count; i += 1) {
                zoom_levels[column.scale].headers[i].draw(th, column.start, column.end);
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
