define([
    'dojo/dom-construct',
    'dojo/query',
    'dojo/store/Memory',
    'dojo/_base/fx',
    'dojo/_base/lang'
], function (domConstruct, dojoQuery, Memory, fx, lang) {
    // ************************************************************************
    // FIELD_UPDATER
    // 
    // Returns a function which when called updates a field
    //
    // memory: dojo.store.JsonRest
    //  the JsonRest instance
    // 
    // widget: dojo._WidgetBase
    //  the widget to update the data to
    //
    // query_data: String or function
    //  the data to be queried to, Anonymous functions are accepted
    // 
    // selected: Array
    //  stores what is selected among the data
    // 
    'use strict';
    var fieldUpdater = function (kwargs) {
        var memory, widget, callBackFunction, query_data, selected, placeHolder;

        kwargs = lang.mixin(
            {
                memory: null,
                callBack: function (arg) {},
                query_data: null,
                placeHolder: '',
                selected: []
            }, kwargs
        );

        memory = kwargs.memory;
        widget = kwargs.widget;
        callBackFunction = kwargs.callBack;
        query_data = kwargs.query_data;
        selected = kwargs.selected;
        placeHolder = kwargs.placeHolder;

        // set default placeHolder


        return function () {
            var i, query, data_id, animate;
            animate = arguments[0] || true;

            if (query_data !== null) {
                if (typeof query_data === 'function') {
                    data_id = query_data();
                } else {
                    data_id = query_data;
                }

                if (data_id === '') {
                    return;
                }

                query = memory.query(data_id);
            } else {
                query = memory.query();
            }

            return query.then(function (data) {

                // if the widget is a MultiSelect
                if (widget.declaredClass === "dijit.form.MultiSelect") {
                    widget.reset();
                    // add options manually
                    // remove the previous options first
                    dojoQuery('option', widget.domNode).forEach(
                        function (opt, idx, arr) {
                            domConstruct.destroy(opt);
                        }
                    );

                    // add options
                    var data_length = data.length;
                    for (i = 0; i < data_length; i++) {
                        domConstruct.create(
                            'option',
                            {
                                'value': data[i].id,
                                'innerHTML': data[i].name
                            },
                            widget.domNode
                        );
                    }

                    // select selected
                    if (selected.length) {
                        widget.set('value', selected);
                    }
                } else if (widget.declaredClass === 'dojox.grid.DataGrid') {
                    // just call render
                    widget.render();
                } else {
                    // store current value
                    var old_value = widget.get('value');
                    try {
                        widget.reset();
                    } catch (err) {
                        // don't do anything
                    }
                    // set the data normally
                    widget.set('collection', new Memory({data: data}));

                    if (data.length > 0) {
                        if (widget.label) {
                            placeHolder = 'Select a ' + widget.label;
                        } else {
                            placeHolder = 'Select an item from list';
                        }
                        widget.set('placeHolder', placeHolder);

                        if (widget.declaredClass !== 'dijit.form.FilteringSelect') {
                            try {
                                widget.attr('value', data[0].id);
                            } catch (err) {
                                // don't do anything
                            }
                        }

                        // restore the old value
//                        try {
//                            if (old_value) {
//                                console.log('old value setted!')
//                                widget.set('value', old_value);
//                            }
//                        } catch (err) {
//                            // don't do anything
//                        }

                    } else {
                        if (widget.label) {
                            placeHolder = 'Create New ' + widget.label;
                        } else {
                            placeHolder = 'Create New';
                        }
                        widget.set('placeHolder', placeHolder);
                    }
                    if (selected.length) {
//                        console.log('selected value setted!');
                        widget.set('value', selected);
                    }


                }



                if (animate === true) {
                    // animate the field to indicate it is updated;

                    var domNode = widget.domNode;
                    var bgColor = domNode.style.backgroundColor;
                    fx.animateProperty({
                        node: domNode,
                        duration: 500,
                        properties: {
                            backgroundColor: {
                                start: "#00ff00",
                                end: bgColor
                            }
                        }
                    }).play();
                }

                // TODO: callBackFunction should get more then the data
                //   use kwargs
                //   kwargs.data
                //   kwargs.widget

                callBackFunction(data);

            });
        };
    };
    return fieldUpdater;
});
