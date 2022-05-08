define([
    'dijit/Menu',
    'dijit/MenuItem',

    'stalker/js/dialogs',
    'stalker/js/dialogCreator',

    'dojo/domReady!'
], function (Menu, MenuItem, dialogs, dialogCreator) {

    // ************************************************************************
    // Thumbnail Menu
    // 
    return function (kwargs){
        var targetNodeIds = kwargs['targetNodeIds'];
        var selector = kwargs['selector'];
        var leftClickToOpen = kwargs['leftClickToOpen'] || true;
        var entity_id = kwargs['entity_id'] || -1;
        var related_field_updater = kwargs['related_field_updater'] || function(){};

        // create the thumbnail upload menu
        var t_menu = new Menu({
            targetNodeIds: targetNodeIds,
            selector: selector,
            leftClickToOpen: leftClickToOpen
        });

        var t_menuItem_creator = function () {
            return new MenuItem({
                label: 'Upload Thumbnail...',
                onClick: function () {
                    var node = this.getParent().currentTarget;
                    var dialog = dialogCreator({
                        dialog_id: 'upload_thumbnail_dialog',
                        data_id: entity_id,
                        content_creator: dialogs.upload_thumbnail_dialog,
                        related_field_updater: related_field_updater
                    });
                    dialog.show();
                }
            });
        };

        t_menu.addChild(t_menuItem_creator());
    };
});
