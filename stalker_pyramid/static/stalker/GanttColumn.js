define([
    "dojo/_base/array",
    "dojo/date/locale",
    "put-selector/put",
    'stalker/GanttTask'
], function (array, locale, put, GanttTask) {
    // module:
    //     ganttColumn
    // summary:
    //     A dgrid column plugin that generates gantt chart time lines in a
    //     column.

//    function getColumnSetElement(element) {
//        // summary:
//        //     Finds the column set parent element of a given cell.
//        // element:
//        //     DomNode
//        // returns:
//        //     DomNode?
//        console.debug('element: ', element);
//        if (element) {
//            element = element.parentNode;
//            while (element && element.className !== "dgrid-column-set") {
//                element = element.parentNode;
//            }
//        }
//        return element;
//    }

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

            // IE < 8 receive the inner padding node, not the td directly
            cell = td.tagName === "TD" ? td : td.parentNode;

            // Add empty content to the cell to avoid it collapsing in IE
            td.innerHTML = "&nbsp;";

            // create a GanttTask instance
            var task = new GanttTask(data);
            console.debug('task: ', task);

            // Ensure the start time is always milliseconds since epoch
            // and not a Date object
            var chartStartTime = +column.start,

            // This is the number of milliseconds per pixel rendered
                chartTimeScale = column.scale,
            
            // The start position of the task bar for this task, in pixels
                left = (task.start - column.start) / chartTimeScale,

            // The width of the task bar for this task, in pixels
                width = (task.end - task.start) / chartTimeScale;

            // Create the colored task bar representing the duration of a task

//            data.progress = data.completed * 100;
//            data.link = function () {
//                return this.name;
//            };

            console.debug('code is here 1');

            var taskBar;
            if (task.type === 'Project') {
                console.debug('code is here 1a');
                taskBar = $(templates.projectBar(task));
                console.debug('code is here 1b');
            } else if (task.type === 'Task' || task.type === 'Asset' ||
                       task.type === 'Shot' || task.type === 'Sequence') {
                console.debug('code is here 1c');
                if (task.hasChildren){
                    taskBar = $(templates.parentTaskBar(task));
                } else {
                    taskBar = $(templates.taskBar(task));
                }
                console.debug('code is here 1d');
            }
            taskBar.css({
                left: left,
                width: width
            });
            $(td).append(taskBar);

            console.debug('code is here 2');
            console.debug('taskBar: ', taskBar);
            console.debug('code is here 3a');
            console.debug('td : ', td);
            console.debug('code is here 3b');


            // Create the overlay for the amount of the task that has been completed
            //var completeBar = put(td, "span.completed-bar[style=left:" + left + "px;width:" + width * object.completed + "px]");

            // Save the location of the right-hand edge for drawing depedency lines later
            cell.finished = left + width;

            // This reference is stored
            firstCell = firstCell || td;

            var grid = column.grid;
//            console.debug('grid: ', grid);

            // TODO: enable this part later
//            // Create arrows for each dependency, but only after all other rows
//            // have been rendered so that they can be retrieved and measured
//            // properly
//            setTimeout(function () {
//                // First, create a special column set row (which contains
//                // elements that have synced horizontal scrolling) so that all
//                // the dependency lines can be grouped together and will be
//                // properly scrolled horizontally along with the rest of the
//                // rows
//                if (!dependencyRow) {
//                    // This intermediate element is necessary for the
//                    // dependency lines to render outside of the zero height
//                    // dependency row;
//                    //    the outer element has a height of zero, the inner
//                    //    element has height to accommodate all the lines
//                    dependencyRow = put(getColumnSetElement(firstCell), "-div.dependency-container");
//
//                    // Create the scrolling container for the gantt dependency
//                    // arrows
//                    dependencyRow = put(dependencyRow, "div.dgrid-column-set.dependency-row[data-dgrid-column-set-id=1]");
//
//                    // Create the actual container for the dependency arrows
//                    // inside the scrolling container this will scroll within
//                    // the .dependency-row
//                    dependencyRow = put(dependencyRow, "div.dependencies.dgrid-column-chart");
//                }
//
//                array.forEach(object.dependencies, function (dependency) {
//                    // This corresponds to the dependency DOM node, the
//                    // starting point of the dependency line
//                    var cell = grid.cell(dependency, column.id).element;
//
//                    // create the horizontal line part of the arrow
//                    var hline = put(dependencyRow, "span.dep-horizontal-line");
//
//                    // we find the location of the starting cell and use that
//                    // to place the horizontal line
//                    var top = getColumnSetElement(cell).offsetTop + 10;
//                    hline.style.top = top + "px";
//                    hline.style.left = cell.finished + 5 + "px";
//
//                    // the start variable is the starting point of the target
//                    // dependent cell
//                    hline.style.width = left - cell.finished - 4 + "px";
//
//                    // now we create the vertical line and position it
//                    var vline = put(dependencyRow, "span.dep-vertical-line");
//
//                    vline.style.top = top + 2 + "px";
//                    vline.style.left = left + "px";
//
//                    var tdTop = getColumnSetElement(td).offsetTop - 5;
//                    vline.style.height = tdTop - getColumnSetElement(cell).offsetTop + "px";
//                    // now we create the arrow at the end of the line, position
//                    // it correctly
//                    var arrow = put(dependencyRow, "span.ui-icon.down-arrow");
//                    arrow.style.top = tdTop + "px";
//                    arrow.style.left = left - 7 + "px";
//                });
//            }, 0);
        };

        column.renderHeaderCell = function (th) {
            // summary:
            //     Creates a header cell that contains the dates corresponding to the time lines that are being rendered in the main content
            // th: DomNode
            //
            // here we render the header for the gantt chart, this will be a row of dates
            // with days of the week in a row underneath
            var table = put(th, "table");
            // Create the date row
            var dateRow = put(table, "tr");
            // start at the time indicated by the column
            var date = new Date(column.start);
            var lastDay = 7;
            // now we iterate through the time span, incrementing by date
            while (date.getTime() < column.end) {
                // each time a new week is started, we write a new date for the week
                if (date.getDay() < lastDay) {
                    // create the cell
                    put(dateRow, "td[style=width:" + (lastDay - date.getDay()) * 86400000 / column.scale + "px]", {
                        innerHTML: lastDay - date.getDay() > 2 ? locale.format(date, {selector: "date"}) : "",
                        colSpan: lastDay - date.getDay()
                    });

                }
                // get the day of the week before incrementing
                lastDay = date.getDay() + 1;
                date = new Date(date.getTime() + 86400000); // increment a day
            }
            // now we create a row for the days of the week
            var dayRow = put(table, "tr");
            // restart the time iteration, and iterate again
            date = new Date(column.start);
            while (date.getTime() < column.end) {
                put(dayRow, "td[style=width:" + (86400000) / column.scale + "px]", {
                    innerHTML: locale.format(date, {selector: "date", datePattern: "EEE"}).substring(0, 1)
                });

                date = new Date(date.getTime() + 86400000); // increment a day
            }
        };

        return column;
    };
});
