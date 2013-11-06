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
        if (element) {
            element = element.parentNode;
            while (element && element.className !== "dgrid-column-set") {
                element = element.parentNode;
            }
        }
        return element;
    }


    /**
     * 
     * 
     * 
     * Returns a formatted string
     * 
     * @param {number} start
     *     the start of the range of a particular time box in
     *     milliseconds
     * @param {number} end
     *     the end of the range of a particular time box in
     *     milliseconds
     * @returns {string}
     * 
     */
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
                return Math.floor((end - start) / this.scale);
            },
            headers: [
                {
                    draw: function (parent, start, end) {
                        // draw itself

                        // iterate from start to end day
                        var scale = 21600000;

                        var start_date = moment(start).startOf('day');
                        var end_date = moment(end).endOf('day');

                        // find the end of the first week
                        var week_start = moment(start_date.startOf('isoweek'));
                        var week_end = moment(start_date.endOf('isoweek'));
                        // create the first div elements using start_date and week_end

                        var parent_div = $($.parseHTML('<div class="headerCell"></div>'));
                        // fix scroll
                        parent_div.css({
                            width: (end_date - start_date) / scale
                        })
                        $(parent).append(parent_div);

                        var header_div_element;
                        // now wee need to iterate until the end_date is bigger than end
                        while (week_start < end_date) {
                            // create the first div elements using start_date and week_end
                            header_div_element = $($.parseHTML('<div class="headerCell center">' + week_start.format('w') + '</div>'));
                            header_div_element.css({
                                width: Math.floor((week_end - week_start) / scale),
                                left: Math.floor((week_start - start_date) / scale)
                            });
//                            console.log('(week_end - week_start) :', (week_end - week_start));
//                            console.log('width :', Math.floor((week_end - week_start) / scale));
                            parent_div.append(header_div_element);
                            // go to next week
                            week_start.add(7, 'day');
                            week_end.add(7, 'day');
                        }

                    }
                },
                { // weeks from monday to sunday
                    title: function (start, end) {
                        // return the start day in DD-MM-YYYY format
                        var start_date = moment(start);
                        return start_date.format('DD-MM-YYYY');
                    },
                    time_step: 864000000 * 7 // 7 days
                },
                {
                    title: function (start, end) {
                        // return the start day in DD-MM-YYYY format
                        var start_date = moment(start);
                        return start_date.format('H');
                    },
                    time_step: 21600000 // 6 hours
                }
            ]
        },
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


        var dependencyRow,
            firstCell;

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
            console.log('ResourceColumn.column.renderCell start');
            // IE < 8 receive the inner padding node, not the td directly
            var cell = td.tagName === "TD" ? td : td.parentNode;

            // Add empty content to the cell to avoid it collapsing in IE
            //td.innerHTML = "&nbsp;";

            // create a TimeLog instance
            var resource = new Resource(data);

            // Ensure the start time is always milliseconds since epoch
            // and not a Date object

            var start_date = moment(column.start).startOf('day');
            var end_date = moment(column.end).endOf('day');
//            console.log('start_date :', start_date);
//            console.log('end_date   :', end_date);

            // This is the number of milliseconds per pixel rendered
            var chartTimeScale = zoom_levels[column.scale].scale;
//            console.log('chartTimeScale :', chartTimeScale);

            // iterate the weeks from start to end, choose the week start and
            // dates correctly
            var range_start = moment(start_date).startOf('isoweek');
            var range_end = moment(end_date).endOf('isoweek');

            var total_logged_millies;
            var weekly_millies_possible = 183600000; // 51 hours for anima
            var weekly_log_bar;
            var weekly_log_bar_layout_div;
            var td_jq = $(td);
            var Math_floor = Math.floor;

            var added_first_time_log = false;
            var today = moment(new Date()).startOf('day');

            var resource_count = resource.resource_count;

//            console.log('code is here 1');
            while (range_start < end_date) {
//                console.log('code is here 2');
//                range_end = moment(Math.min(range_end, column.end));
                total_logged_millies = resource.total_logged_milliseconds(range_start, range_end);
                // draw a div at that range with the height of total_logged_millies

                if (total_logged_millies > 0 || added_first_time_log) {
                    added_first_time_log = true;
                    weekly_log_bar_layout_div = $($.parseHTML('<div class="log_bar layout"></div>'));
                    weekly_log_bar_layout_div.css({
                        left: Math_floor((range_start - start_date) / chartTimeScale),
                        width: Math_floor((range_end - range_start) / chartTimeScale)
                    });

                    weekly_log_bar = $($.parseHTML('<div class="log_bar timeLog"></div>'));
                    weekly_log_bar.css({
                        height: Math_floor(total_logged_millies / weekly_millies_possible * 22 / resource_count)// weekly millies possible
                    });
                    weekly_log_bar_layout_div.append(weekly_log_bar);
                    td_jq.append(
                        weekly_log_bar_layout_div
                    );
                }
//                console.log('code is here 3');
                // get the new start and end values
                //range_start = range_end + 1;
                //range_end += 604800000;
                range_start.add(7, 'day');
//                console.log('code is here 3a');
                range_end.add(7, 'day');
//                console.log('code is here 4');
            }
//            console.log('code is here 5');

            // Save the location of the right-hand edge for drawing depedency lines later
//            cell.finished = left + width;

            // This reference is stored
            firstCell = firstCell || td;

            var grid = column.grid;

            // render today
            var today_as_millis = (new Date()).getTime();
            put(td, "div.today[style=left:" + Math.floor((today_as_millis - column.start) / chartTimeScale) + "px;]");

            console.debug('ResourceColumn.column.renderCell end');
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
            console.log('renderHeaderCell start');

            // here we render the header for the gantt chart, this will be a
            // row of dates with days of the week in a row underneath

            // normalize table scale
//            var one_day_width = 3;
//            var number_of_days = (column.end - column.start) / 86400000;
//
//            // recalculate scale
//            var table_width = number_of_days * (one_day_width + 1); // add 1px per day for border (ugly!)
//
//            // fix scrolling
            var table_width = zoom_levels[column.scale].table_width(column.start, column.end);
            column.grid.addCssRule(".dgrid-column-chart", "width: " + table_width + "px");

//            // calculate table width
//            var table = put(th, "table[style=width:" + table_width + "px]");
//
//            // Create the date row
//            var dateRow = put(table, "tr[style=table-layout:fixed].resourceHead1");
//
//            // start at the time indicated by the column
//            var date = new Date(column.start);
//            var lastDay = 7;
//
//            var lastDay_minus_day;
//            // now we iterate through the time span, incrementing by date
//            while (date.getTime() < column.end) {
//                // each time a new week is started, we write a new date for the week
//                lastDay_minus_day = lastDay - date.getDay();
//                if (date.getDay() < lastDay) {
//                    put(
//                        dateRow,
//                        "td",
//                        {
//                            innerHTML: lastDay_minus_day > 2 ? date.format('dd-mm-yyyy') : "",
//                            colSpan: lastDay_minus_day
//                        }
//                    );
//                }
//                // get the day of the week before incrementing
//                lastDay = date.getDay() + 1;
//                date = new Date(date.getTime() + 86400000); // increment a day
//            }
//            // now we create a row for the days of the week
//            var dayRow = put(table, "tr.resourceHead2");
//            // restart the time iteration, and iterate again
//            date = new Date(column.start);
//            while (date.getTime() < column.end) {
//                put(dayRow, "td", {
//                    innerHTML: locale.format(date, {selector: "date", datePattern: "EEE"}).substring(0, 1)
//                });
//                date = new Date(date.getTime() + 86400000); // increment a day
//            }

            // get element width
            var zoom = 'w';
            var width = zoom_levels[zoom].table_width(column.start, column.end);

            // render headers
            zoom_levels[zoom].headers[0].draw(th, column.start, column.end);

            // render today
            var today_as_millis = (new Date()).getTime();

            var today = $($.parseHTML('<div></div>'));
            today.addClass('today').css({
                left: Math.floor((today_as_millis - column.start) / zoom_levels[column.scale].scale)
            });

            $(th).append(today);

            console.log('renderHeaderCell end');
        };

        return column;
    };
});
