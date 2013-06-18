// Stalker Pyramid a Web Base Production Asset Management System
// Copyright (C) 2009-2013 Erkan Ozgur Yilmaz
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

define(['dijit/form/Button', 'dijit/MenuItem', 'stalker/dialogCreator'],
    function(Button, MenuItem, dialogCreator){
        // ********************************************************************
        // DialogCaller
        //
        // Creates a widget (a button or a menuItem) which calls the given
        // dialog and also works together with stalker.submitForm and updates
        // the given field with the newly created or edited value.
        // 
        // PARAMETERS
        // 
        // label:
        //   The label of the widget, default is 'Add'
        // 
        // dialog_id:
        //   the id of the parent dialog
        // 
        // content_creator:
        //   the content creator function for the dialog
        // 
        // attach_to:
        //   the dom element to attach this button to
        // 
        // data_id:
        //   if we already have some id for the data, let say if we are adding
        //   a new Sequence to a Project then this is the id or a function that
        //   returns the Project.id or if we are editing a data then this is
        //   the id or a function returning the edited data id (ex:
        //   scene_id).
        //   
        //   If the id of the edited data is not yet known you can pass a
        //   function that will return the data id.
        //
        // related_field_updater:
        //   a function object without any parameters which will update the
        //   the related field which this form is adding data to.
        // 
        // widget_type: 'Button' or 'MenuItem'
        //   the type of widget
        //
        
        // it calls a dialog which generally adds or edits a data
        // but it is not limited with that, it just calls the dialog
        
        var dialogCaller = function(kwargs){
            var label = kwargs.label || 'Add';
            var dialog_id = kwargs.dialog_id || null;
            var content_creator = kwargs.content_creator;
            var attach_to = kwargs.attach_to;
            var data_id = kwargs.data_id || function(){};
            var related_field_updater = kwargs.related_field_updater || function(){};
            var widget_type = kwargs.widget_type || 'Button';
            
            var WidgetClass = Button;
            if (widget_type == 'MenuItem'){
                WidgetClass = MenuItem;
            }


            var widget = new WidgetClass({
                label: label,
                onClick: function(){
                    var myDialog = dialogCreator({
                        dialog_id: dialog_id,
                        data_id: data_id,
                        content_creator: content_creator,
                        related_field_updater: related_field_updater
                    });
                    myDialog.show();
                }
            }, attach_to);
            
            return widget;
        };
        
        return dialogCaller;
    }
);

