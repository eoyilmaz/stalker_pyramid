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
    "dojo/_base/declare",
    'dojo/_base/lang',
    "dgrid/OnDemandGrid",
    "dgrid/ColumnSet",
    "dgrid/Selection",
    "dgrid/Keyboard",
    "dgrid/tree",
    "dgrid/extensions/DijitRegistry",
    "put-selector/put",
    "stalker/js/DiscreetDataColumn"
], function (declare, lang, OnDemandGrid, ColumnSet, Selection, Keyboard, tree,
             DijitRegistry, put, DiscreetDataColumn) {
    // module:
    //     GanttGrid
    // summary:
    //     A dgrid extension to create a chart that represents data between
    //     discreet dates.

    // Creates a new grid with one column set definition to display data name
    // and a second column set for the actual discreet data
    "use strict";

    return declare([OnDemandGrid, ColumnSet, Selection, Keyboard, DijitRegistry], {
        /**
         *  customize this to add functionality to the data
         *  
         *  so pass your own object as the wrapper, it will be used as follows:
         *  
         *  data = new Wrapper(data);
         *  
         *  essentially allowing one to customize the displayed data
         */
        data_wrapper: Object,
        start: null,
        end: null,
        keyMap: lang.mixin({}, Keyboard.defaultKeyMap, {
            //    37 - left
            //    38 - up
            //    39 - right
            //    40 - down
            39: function () { // right arrow
                var obj;
                for (obj in this.selection) {
                    this.expand(obj, true);
                }
            },
            37: function () {  // left arrow
                var obj;
                for (obj in this.selection) {
                    this.expand(obj, false);
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
        columnSets: [
            // Column set to display discreet data
            [
                {
                    id: {
                        label: "ID",
                        sortable: false,
                        get: function (object) {
                            return object;
                        },
                        formatter: function (object) {
                            return object.id;
                        },
                        resizable: true
                    },
                    name: tree(
                        {
                            label: "Name",
                            sortable: false,
                            get: function (object) {
                                return object;
                            },
                            formatter: function (object) {
                                var return_val;
                                if (object.type === 'Department') {
                                    return_val = '<div><i class="icon-group"></i>&nbsp<a href="/departments/'+ object.id + '/view">' + object.name + '</a></div>';
                                } else {
                                    return_val = '<div><i class="icon-user"></i>&nbsp<a href="/users/'+ object.id + '/view">' + object.name + '</a></div>';
                                }
                                return return_val;
                            },
                            renderExpando: function (level, hasChildren, expanded, object) {
                                // summary:
                                //     Provides default implementation for column.renderExpando.

                                var dir = this.grid.isRTL ? "right" : "left",
                                    cls = ".dgrid-expando-icon",
                                    node;
                                if (hasChildren) {
                                    cls += ".ui-icon.ui-icon-triangle-1-" + (expanded ? "se" : "e");
                                }
                                node = put("div" + cls + "[style=margin-" + dir + ": " +
                                    (level * (this.indentWidth || 9)) + "px; float: " + dir + "; position: inherit]");
                                node.innerHTML = "&nbsp;"; // for opera to space things properly
                                return node;
                            }
                        }
                    )

                }
            ],

            // Column set to discreet data in separate boxes;
            // note that this is not associated with
            // any actual property of the data object because it uses the whole
            // object to render
            [
                {
                    chart: new DiscreetDataColumn({
                        sortable: false
                    })
                }
            ]
        ]
    });
});
