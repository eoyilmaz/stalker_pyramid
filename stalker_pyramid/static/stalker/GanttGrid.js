define([
    "dojo/_base/declare",
    "dgrid/OnDemandGrid",
    "dgrid/ColumnSet",
    "dgrid/Selection",
    "dgrid/Keyboard",
    "dgrid/tree",
    "stalker/GanttColumn"
], function (declare, OnDemandGrid, ColumnSet, Selection, Keyboard, tree,
             GanttColumn) {
    // module:
    //     GanttGrid
    // summary:
    //     A dgrid extension to create a gantt chart, with columns for tasks, resources, and timelines

    // Creates a new grid with one column set definition to display tasks & resources and a second
    // column set for the actual gantt chart

    return declare([ OnDemandGrid, ColumnSet, Selection, Keyboard ], {
        columnSets: [
            // Column set to display task and resource
            [
                {
                    name: tree({ label: "Task", sortable: false }),
                    resource: { label: "Resource", sortable: false }
                }
            ],

            // Column set to display gantt chart; note that this is not associated with
            // any actual property of the data object because it uses the whole object to
            // render
            [
                {
                    chart: GanttColumn({
                        scale: 4000000,
                        start: new Date(2012, 0, 29, 1, 20, 0, 0),
                        end: new Date(2012, 1, 23, 12, 26, 40, 0),
                        sortable: false
                    })
                }
            ]
        ]
    });
});
