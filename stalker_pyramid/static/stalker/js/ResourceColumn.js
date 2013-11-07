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
    'use strict';

    /**
     * Renders header cells under the given parent
     * 
     * @param options
     * @returns {*|jQuery|HTMLElement}
     */
    var draw_header_cell = function (options) {
        var parent = options.parent;
        var start = options.start;
        var end = options.end;
        var scale = options.scale;
        var step_size = options.step_size;
        var step_unit = options.step_unit;
        var period_unit = options.period_unit;
        var height = options.height;
        var format = options.format;

        var original_start = moment(start).startOf('day');

        var start_date = moment(start).startOf(period_unit).startOf('day');
        var end_date = moment(end).endOf(period_unit).endOf('day');

        // find the start and end of the period
        var period_start = moment(start_date.startOf(period_unit));
        var period_end = moment(start_date.endOf(period_unit));

        if (step_size > 1) {
            end_date.add(step_size - 1, step_unit);
            period_end.add(step_size - 1, period_unit);
        }
        
        console.log('Math.floor((start_date - original_start) / scale):', Math.floor((start_date - original_start) / scale));

        // create the first div elements using start_date and week_end
        var parent_div = $($.parseHTML('<div class="headerCell"></div>'));
        parent_div.css({
            width: Math.floor((end_date - start_date) / scale),
            left: Math.floor((start_date - original_start) / scale),
            height: height,
            position: 'absolute'
        });
        $(parent).append(parent_div);

        var header_div_element;
        // now wee need to iterate until the end_date is bigger than end

        var formatter = function(ps, pe) {
            return ps.format(format);
        };

        if (typeof (format) === 'function') {
            formatter = format;
        }

        while (period_start < end_date) {
            // create the first div elements using start_date and week_end
            header_div_element = $($.parseHTML('<div class="headerCell center">' + formatter(period_start, period_end) + '</div>'));
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
        var step_size = options.step_size;
        var step_unit = options.step_unit;
        var period_unit = options.period_unit;
        var height = options.height;
        var millies_possible_in_period = options.millies_possible_in_period;

        // create a TimeLog instance
        var resource = new Resource(data);

        var original_start = moment(start).startOf('day');

        var start_date = moment(start).startOf(period_unit).startOf('day');
        var end_date = moment(end).endOf(period_unit).endOf('day');

        // find the start and end of the period
        var period_start = moment(start_date.startOf(period_unit));
        var period_end = moment(start_date.endOf(period_unit));

        var total_logged_millies;
        var log_bar, data_bar;
        var log_bar_container;

        var parent_div = $($.parseHTML('<div class="logContainer"></div>'));
        parent_div.css({
            width: Math.floor((end_date - start_date) / scale),
            left: Math.floor((start_date - original_start) / scale), // offset as neccessary
            height: height,
            position: 'absolute'
        });
        $(parent).append(parent_div);

        var added_first_time_log = false;
        var resource_count = resource.resource_count;

        // calculate once
        var denominator = height / (millies_possible_in_period * resource_count);

        while (period_start < end_date) {
            total_logged_millies = resource.total_logged_milliseconds(+period_start, +period_end);
            // draw a div at that range with the height of total_logged_millies
//            if (total_logged_millies > 0 || added_first_time_log) {
                added_first_time_log = true;
                log_bar_container = $($.parseHTML('<div class="log_bar layout"></div>'));
                log_bar_container.css({
                    left: Math.floor((period_start - start_date) / scale),
                    width: Math.floor((period_end - period_start) / scale)
                });

                log_bar = $($.parseHTML('<div class="log_bar log"></div>'));
                log_bar.css({
                    height: Math.floor(total_logged_millies * denominator)
                });

                data_bar = $($.parseHTML('<div class="data_bar"></div>'));
                var total_hours = (total_logged_millies / 3600000).toFixed(0);
                data_bar.text(total_hours);
                log_bar_container.append(log_bar);
                log_bar_container.append(data_bar);
                parent_div.append(
                    log_bar_container
                );
//            }
            // get the new start and end values
            period_start.add(step_size, step_unit).startOf(step_unit);
            period_end.add(step_size, step_unit).endOf(step_unit);
        }
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
                'draw': function (parent, data, start, end) {
                    return draw_cell({
                        parent: parent,
                        data: data,
                        start: start,
                        end: end,
                        scale: 120000,
                        step_size: 1,
                        step_unit: 'hour',
                        period_unit: 'hour',
                        height: 24,
                        millies_possible_in_period: 3600000 // 1 hours for anima
                    });
                }
            }
        },
        "d": {
            scale: 120000, // 1 day is 30 px
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
                'draw': function (parent, data, start, end) {
                    return draw_cell({
                        parent: parent,
                        data: data,
                        start: start,
                        end: end,
                        scale: 2880000,
                        step_size: 1,
                        step_unit: 'day',
                        period_unit: 'day',
                        height: 24,
                        millies_possible_in_period: 9 * 3600000 // 9 hours for anima
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
                'draw': function (parent, data, start, end) {
                    return draw_cell({
                        parent: parent,
                        data: data,
                        start: start,
                        end: end,
                        scale: 21600000,
                        step_size: 7,
                        step_unit: 'day',
                        period_unit: 'isoweek',
                        height: 24,
                        millies_possible_in_period: 183600000 // 51 hours for anima
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
//                        console.log(+moment(start).startOf('year'));
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
                'draw': function (parent, data, start, end) {
                    return draw_cell({
                        parent: parent,
                        data: data,
                        start: start,
                        end: end,
                        scale: 86400000,
                        step_size: 1,
                        step_unit: 'month',
                        period_unit: 'month',
                        height: 24,
                        millies_possible_in_period: 183600000 * 4 // 204 hours for anima
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
                'draw': function (parent, data, start, end) {
                    return draw_cell({
                        parent: parent,
                        data: data,
                        start: start,
                        end: end,
                        scale: 315360000,
                        step_size: 1,
                        step_unit: 'year',
                        period_unit: 'year',
                        height: 24,
                        millies_possible_in_period: 9573418080 // 6 * 52.1428 * 51 * 3600000
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

            // render cells
            zoom_levels[column.scale].chart.draw(td, data, column.start, column.end);

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
            var parent_div;
            for (i = 0; i < header_count; i += 1) {
                parent_div = zoom_levels[column.scale].headers[i].draw(th, column.start, column.end);
                parent_div.css({
                    top: i * 27
                })
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
