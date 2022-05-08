define([
    'dojo/store/JsonRest',
    'stalker/js/TagSelect',
    'stalker/js/fieldUpdater'
], function (JsonRest, TagSelect, fieldUpdater) {

    // ********************************************************************
    // tagField
    // 
    // An input field for tags.
    // 
    // PARAMETERS
    // 
    // attach_to:
    //   a dom element to attach the created tagSelect field
    // 
    // selected_tags:
    //   a list of integers showing the selected tags
    return function (kwargs) {

        var attach_to = kwargs.attach_to || null,
            selected_tags = kwargs.selected_tags || [],

        // ********************************************************************
        // Tags
            tags_jsonRest = new JsonRest({
                target: 'tags/'
            }),

            tags_tagSelect = new TagSelect({
                name: 'tag_names',
                type: 'ComboBox'
            }, attach_to),

        // The Updater
            tags_field_updater = fieldUpdater({
                memory: tags_jsonRest,
                widget: tags_tagSelect,
                selected: selected_tags
            });
        tags_field_updater({animate: false});

        return tags_tagSelect;
    };
});
