

interface Window {
    all_users: [];
    all_projects: [];
}

jQuery(function(){
        $.getJSON('/users/').then(function (data) {
        window.all_users = data;
    });

    $.getJSON('/projects/').then(function (data) {
        window.all_projects = data;
    });


    const get_entity_name = function(id, entity_list) {
        const user = objectFindByKey(entity_list, 'id', id);
        if (user != null) {
            return user.name;
        }
        return id;
    };

    function objectFindByKey(array, key, value) {
        for (let i = 0; i < array.length; i++) {
            if (array[i][key] === value) {
                return array[i];
            }
        }
        return null;
    }

    const get_user_name = function(id) {
        return get_entity_name(id, window.all_users);
    };

    const get_project_name = function(id) {
        return get_entity_name(id, window.all_projects);
    };
});
