define([
    "dojo/_base/declare",
    "dgrid/OnDemandGrid",
    "dgrid/ColumnSet",
    "dgrid/Selection",
    "dgrid/Keyboard",
    "dgrid/tree",
    "dgrid/extensions/ColumnResizer",
    "stalker/GanttColumn"
], function (declare, OnDemandGrid, ColumnSet, Selection, Keyboard, tree,
             ColumnResizer, GanttColumn) {
    // module:
    //     GanttGrid
    // summary:
    //     A dgrid extension to create a gantt chart, with columns for tasks, resources, and timelines

    // Creates a new grid with one column set definition to display tasks & resources and a second
    // column set for the actual gantt chart
    "use strict";
    return declare([OnDemandGrid, ColumnSet, Selection, Keyboard, ColumnResizer], {
        columnSets: [
            // Column set to display task and resource
            [
                {
                    id: {
                        label: "ID",
                        sortable: false,
                        get: function (object) {
                            return object;
                        },
                        formatter: function (object) {
                            var bg_color = object.progress >= 100 ? 'rgb(153, 255, 51)' : 'red',
                                font_weight = 'normal';

                            return '<div ' +
                                'style="' +
                                'font-weight: ' + font_weight + ';' +
                                'background-color: ' + bg_color + '">' +
                                object.id + '</div>';
                        },
                        resizable: true
                    },
                    name: tree(
                        {
                            label: "Name",
                            sortable: false,
                            get: function (object) {
                                return object
                            },
                            formatter: function (object) {
                                var font_weight = object.hasChildren ? 'bold' : 'normal';
                                return '<div style="font-weight: ' + font_weight + '">' +
                                    object.name +
                                    '</div>';
                            }
                        }
                    ),
                    start: {
                        label: 'Start',
                        sortable: false,
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
                        get: function (object) {
                            return object;
                        },
                        formatter: function (object) {
                            var end_date = new Date(object.end);
                            return end_date.format("yyyy-mm-dd HH:MM");
                        }
                    },
                    resource: {
                        label: "Resource",
                        sortable: false
                    }
                }
            ],

            // Column set to display gantt chart; note that this is not associated with
            // any actual property of the data object because it uses the whole object to
            // render
            [
                {
                    chart: new GanttColumn({
                        scale: 8000000,
                        start: new Date(2013, 4, 1),
                        end: new Date(2015, 0, 1),
                        sortable: false
                    })
                }
            ]
        ]
    });
});
