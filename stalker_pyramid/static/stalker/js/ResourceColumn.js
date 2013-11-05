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
    'stalker/js/Resource',
    'stalker/js/TimeLog'
], function (domConstruct, array, lang, locale, put, Resource, TimeLog) {
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
//            console.debug('ResourceColumn.column.renderCell start');

            // IE < 8 receive the inner padding node, not the td directly
            cell = td.tagName === "TD" ? td : td.parentNode;

            // Add empty content to the cell to avoid it collapsing in IE
            //td.innerHTML = "&nbsp;";

            // create a TimeLog instance
            var resource = new Resource(data);

            // Ensure the start time is always milliseconds since epoch
            // and not a Date object
            column.start = +column.start;
            column.end = +column.end;

            // This is the number of milliseconds per pixel rendered
            var chartTimeScale = column.scale,

            // The start position of the task bar for this task, in pixels
                left = (resource.start - column.start) / chartTimeScale,

            // The width of the task bar for this task, in pixels
                width = (resource.end - resource.start) / chartTimeScale;

            // Create the colored task bar representing the duration of a task
//            var resourceBar;
//            resourceBar = $($.parseHTML(templates.resourceBar(resource)));

            // iterate the weeks from start to end, choose the week start and
            // dates correctly
            var temp_end = new Date(column.end);
            column.end = temp_end.setClock(0).getTime() + 86399999;
            var range_start = new Date(column.start).setClock(0);
            var dow = range_start.getDay();
            range_start = range_start.getTime();
            // one_day =  86400000
            // one_day - 1 milliseconds = 86399999
            // one_week = 604800000;
            // one_week - 1 milliseconds = 604799999;
            var range_end = range_start + (7 - dow) * 86400000 - 1;

            var total_logged_millies;
            var weekly_millies_possible = 183600000; // 51 hours for anima
            var weekly_log_bar;
            var weekly_log_bar_layout_div;
            var td_jq = $(td);
            var td_jq_append = td_jq.append;
            var Math_floor = Math.floor;
            var parseHTML = $.parseHTML;

            var added_first_time_log = false;
            var today = new Date().setClock(0);
            var this_weekend = ((7 - today.getDay()) % 7) * 86400000 + today.getTime() + 86400000 - 1;

//            var end_date = Math.min(this_weekend, column.end);
            var end_date = column.end;

            var resource_count = resource.resource_count;

            while (range_start < end_date) {
                range_end = Math.min(range_end, column.end);
                total_logged_millies = resource.total_logged_milliseconds(range_start, range_end);
                // draw a div at that range with the height of total_logged_millies

                if (total_logged_millies > 0 || added_first_time_log) {
                    added_first_time_log = true;
                    weekly_log_bar_layout_div = $($.parseHTML('<div class="log_bar layout"></div>'));
                    weekly_log_bar_layout_div.css({
                        left: Math_floor((range_start - column.start) / chartTimeScale),
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
                // get the new start and end values
                range_start = range_end + 1;
                range_end += 604800000;
            }

//            resourceBar.css({
//                left: left,
//                width: width
//            });
//            $(td).append(resourceBar);


            // Save the location of the right-hand edge for drawing depedency lines later
            cell.finished = left + width;

            // This reference is stored
            firstCell = firstCell || td;

            var grid = column.grid;

            // render today
            var today_as_millis = (new Date()).getTime();
            put(td, "div.today[style=left:" + Math.floor((today_as_millis - column.start) / column.scale) + "px;]");

//            console.debug('ResourceColumn.column.renderCell end');
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
            date_x = (date_as_millis - column.start) / column.scale;

            scroller = $('.dgrid-column-set-scroller-1');
            scroller_width = scroller.width();
            scroller.scrollLeft(date_x - scroller_width * 0.5);
        };


        column.centerOnToday = function () {
            // scrolls to today
            column.scrollToDate(new Date());
        };

        column.renderHeaderCell = function (th) {
            // summary:
            //     Creates a header cell that contains the dates corresponding to the time lines that are being rendered in the main content
            // th: DomNode
            //
            // here we render the header for the gantt chart, this will be a row of dates
            // with days of the week in a row underneath
//            console.debug('ResourceColum.column.renderHeaderCell start');

            // normalize table scale
//            var one_day_width = 86400000 / column.scale;
            var one_day_width = 3;
            var number_of_days = (column.end - column.start) / 86400000;

//            // floor one_day_width
//            one_day_width = Math.floor(one_day_width);

            var one_week_width = 7 * one_day_width;

            // recalculate scale
            var table_width = number_of_days * (one_day_width + 1); // add 1px per day for border (ugly!)
            column.scale = (column.end - column.start) / table_width;

//            console.debug('column.start           : ', column.start);
//            console.debug('column.end             : ', column.end);
//            console.debug('column.scale (norm)    : ', column.scale);
//            console.debug('number of days         : ', number_of_days);
//            console.debug('one week width         : ', one_week_width);
//            console.debug('one day width          : ', one_day_width);
//            console.debug('table_width            : ', table_width);

            // fix scrolling
            column.grid.addCssRule(".dgrid-column-chart", "width: " + table_width + "px");

            // calculate table width
//            var table_width = (column.end - column.start) / column.scale;
            var table = put(th, "table[style=width:" + table_width + "px]");

            // Create the date row
            var dateRow = put(table, "tr[style=table-layout:fixed].resourceHead1");

            // start at the time indicated by the column
            var date = new Date(column.start);
            var lastDay = 7;

            var lastDay_minus_day;
            // now we iterate through the time span, incrementing by date
            while (date.getTime() < column.end) {
                // each time a new week is started, we write a new date for the week
                lastDay_minus_day = lastDay - date.getDay();
                if (date.getDay() < lastDay) {
                    put(
                        dateRow,
                        "td",
                        {
                            innerHTML: lastDay_minus_day > 2 ? date.format('dd-mm-yyyy') : "",
                            colSpan: lastDay_minus_day
                        }
                    );
                }
                // get the day of the week before incrementing
                lastDay = date.getDay() + 1;
                date = new Date(date.getTime() + 86400000); // increment a day
            }
            // now we create a row for the days of the week
            var dayRow = put(table, "tr.resourceHead2");
            // restart the time iteration, and iterate again
            date = new Date(column.start);
            while (date.getTime() < column.end) {
                put(dayRow, "td", {
                    innerHTML: locale.format(date, {selector: "date", datePattern: "EEE"}).substring(0, 1)
                });
                date = new Date(date.getTime() + 86400000); // increment a day
            }

            // render today
            var today_as_millis = (new Date()).getTime();
            put(th, "div.today[style=left:" + Math.floor((today_as_millis - column.start) / column.scale) + "px;]");
//            console.debug('ResourceColum.column.renderHeaderCell end');
        };

        return column;
    };
});
