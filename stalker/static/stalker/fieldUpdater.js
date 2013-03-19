define(['dojo/store/Memory', 'dojo/_base/fx'],
    function(Memory, fx){
        // ********************************************************************
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
        var fieldUpdater = function(kwargs){
            var memory = kwargs.memory;
            var widget = kwargs.widget;
            var query_data = kwargs.query_data || null;
            var selected = kwargs.selected || [];
            var placeHolder = kwargs.placeHolder || '';
            console.log("fieldUpdater runs");
            // set default placeHolder


            return function(){
                var animate = arguments[0] || true;
                var query;

                if (query_data != null){
                    var data_id;
                    if (typeof(query_data) == 'function'){
                        data_id = query_data();
                    } else {
                        data_id = query_data;
                    }
                    
                    if (data_id == ''){
                        return;
                    }
                    
                    query = memory.query(data_id);
                } else {
                    query = memory.query();
                }
                
                var result = query.then(function(data){

                    // if the widget is a MultiSelect
                    if (widget.declaredClass == "dijit.form.MultiSelect"){
                        widget.reset();
                        // add options manually
                        // remove the previous options first
                        dojo.query('option', widget.domNode).forEach(function(opt, idx, arr){
                            dojo.destroy(opt);
                        });

                        // add options
                        for (var i=0; i < data.length; i++){
                            dojo.create(
                                'option',
                                {
                                    'value': data[i].id,
                                    'innerHTML': data[i].name
                                },
                                widget.domNode
                            );
                        }
                        
                        // select selected
                        if (selected.length){
                            widget.setValue(selected);
                        }
                    } else if (widget.declaredClass == 'dojox.grid.DataGrid') {
                        // just call render
                        widget.render();
                    } else {

                        try{
                            widget.reset();
                        } catch(err) {
                            // don't do anything
                        }
                        // set the data normally
                        widget.set('store', new Memory({data: data}));

                        if (data.length > 0){
                            if (placeHolder == '' ){
                                if(widget.label){
                                    placeHolder = 'Select a ' + widget.label;
                                }
                                else{

                                    placeHolder = 'Select an item from list';

                                }

                            }
                            widget.set('placeHolder', placeHolder);
                            console.log("placeHolder "+placeHolder);

                            if(widget.declaredClass == 'dijit.form.FilteringSelect'){

                            }
                            else{

                                try{
                                    widget.attr('value', data[0].id);
                                } catch(err) {
                                    // don't do anything
                                }
                            }
                        }
                        else{
                            if (placeHolder == '' ){
                                if(widget.label){
                                    placeHolder = 'No ' + widget.label + " in DB.";
                                }
                                else{

                                    placeHolder = 'No item in DB';

                                }

                            }
                            widget.set('placeHolder', placeHolder);
                        }


                    }
                    
                    if (animate == true){
                        // animate the field to indicate it is updated
                        console.log("animate");

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
                });
            };
        };
        return fieldUpdater;
});
