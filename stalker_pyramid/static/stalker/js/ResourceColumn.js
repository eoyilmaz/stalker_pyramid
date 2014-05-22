// Stalker Pyramid
// Copyright (C) 2013 Erkan Ozgur Yilmaz
//
// This file is part of Stalker Pyramid.
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
    'stalker/js/Resource',
    'stalker/js/HeaderCell'
], function (domConstruct, array, lang, locale, Resource, draw_header_cell) {
    // module:
    //     ResourceColumn
    // summary:
    //     A dgrid column plugin that generates box charts in a column.
    'use strict';

    /**
     * Render the given data under to the given parent
     *
     * The options.data should have the following methods:
     *
     *   data_in_between(start, end)
     *     showing the amount of data supplied
     *     in between the start and end dates.
     *
     *   data_labels(start, end)
     *     showing the data labels
     *
     *   data_scale()
     *     showing the scale of the data
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

        var original_start = moment(start).startOf('day');

        var start_date = moment(start).startOf(period_unit).startOf('day');
        var end_date = moment(end).endOf(period_unit).endOf('day');

        // find the start and end of the period
        var period_start = moment(start_date.startOf(period_unit));
        var period_end = moment(start_date.endOf(period_unit));

        var data_in_between;
        var log_bar, data_bar, data_labels;
        var log_bar_container;

        var parent_div = $($.parseHTML('<div class="logContainer"></div>'));
        parent_div.css({
            width: Math.floor((end_date - start_date) / scale),
            left: Math.floor((start_date - original_start) / scale), // offset as neccessary
            height: height,
            position: 'absolute'
        });
        $(parent).append(parent_div);

        var added_first_data = false;
        var data_scale = data.data_scale();

        // calculate once
        var denominator = height / (millies_possible_in_period * data_scale);

        while (period_start < end_date) {
            data_in_between = data.data_in_between(+period_start, +period_end);
            data_labels = data.data_labels(period_start, period_end);

            // draw a div at that range with the height of data_in_between
            added_first_data = true;
            log_bar_container = $($.parseHTML('<div class="log_bar layout"></div>'));
            log_bar_container.css({
                left: Math.floor((period_start - start_date) / scale),
                width: Math.floor((period_end - period_start) / scale)
            });

            log_bar = $($.parseHTML('<div class="log_bar log"></div>'));
            log_bar.css({
                height: Math.floor(data_in_between * denominator)
            });

            var total_hours = (data_in_between / 3600000).toFixed(0);
            data_bar = $($.parseHTML(
                '<div class="data_bar" >' + total_hours + '</div>'
            ));
            data_bar.text(total_hours);
            data_bar.attr('data-content', data_labels).attr('data-rel', 'popover');
            log_bar_container.append(log_bar);
            log_bar_container.append(data_bar);

            parent_div.append(
                log_bar_container
            );
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
                'element_width': 30, // in px
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
                'element_width': 28, // in px
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
                'element_width': 100, // in px
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
                    if (current_ratio < min_ratio) {
                        min_ratio = current_ratio;
                        desired_level = level;
                    }
                }
            }
            return desired_level;
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
            // wrap the data with the grid.wrapper
            var wrapped_data = new this.grid.data_wrapper(data);
            // render cells
            zoom_levels[column.scale].chart.draw(td, wrapped_data, column.start, column.end);

            // render today
            render_today(td, column.start, zoom_levels[column.scale].scale);

            
            // draw popover
            $(td).find('[data-rel=popover]').popover({
                html:true,
                container: 'body'
            }).on('show.bs.popover', function () {
                // remove all the other popovers
                var self = this;
                $('[data-rel=popover]').each(function(){
                    if (this !== self) {
                        $(this).popover('hide');
                    } else {
                        $(this).popover({
                            trigger: 'hover'
                        })
                    }
                });
            });
            
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

            // let it adjust the scroll bars
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
