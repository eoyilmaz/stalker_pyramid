import * as jQuery from "jquery";
import * as $ from "jquery";

import { Calendar } from '@fullcalendar/core';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import listPlugin from '@fullcalendar/list';
import interactionPlugin from '@fullcalendar/interaction';
import "free-jqgrid";
import "datatables.net";

import "bootstrap";
import "bootstrap-typeahead";
import "chosen-js";
// import "x-editable";


import "./less/ace.less";

import './js/ace-elements';
import './js/cache_users';
import './js/Paginator';
import './js/Studio';
import {
    get_icon,
    append_thumbnail,
    chosen_field_creator,
    chosen_searchable_field_creator,
    chosen_searchable_field_creator_by_data,
    convert_seconds_to_hour,
    convert_seconds_to_time_range,
    to_seconds,
    get_date_range,
    get_date_picker,
    get_task_data,
    meaningful_time,
    meaningful_time_between,
    remove_thumbnails,
    seconds_in_unit,
    set_entity_thumbnail,
    units,
    findArrayElement,
    validate_timing_value,
    page_of
} from './js/utils';

import * as stalker from "./js/stalker";
import * as ace from "./js/ace";


var dojoConfig = {async: true, parseOnLoad: true}
// const dojo = require("../node_modules/dojo/dojo");

import {template} from "dot";
import * as moment from "moment";


declare global {
    interface Window {
        ace: any;
        stalker: any;
        bootbox: any;
        copyToClipboard: any;
        destruct_dialog: any;
        destruct_html_modal: any;
        init_dialog: any;
        init_html_modal: any;
        flash_message: any;
        menu_of: any;
        menus_under_title: any;
        resize_page_content: any;
        scrollToTaskItem: any;
        submenu_of: any;

        get_icon: any,
        append_thumbnail: any,
        chosen_field_creator: any,
        chosen_searchable_field_creator: any,
        chosen_searchable_field_creator_by_data: any,
        convert_seconds_to_hour: any,
        convert_seconds_to_time_range: any,
        to_seconds: any,
        get_date_range: any,
        get_date_picker: any,
        get_task_data: any,
        meaningful_time: any,
        meaningful_time_between: any,
        remove_thumbnails: any,
        seconds_in_unit: any,
        set_entity_thumbnail: any,
        units: any,
        findArrayElement: any,
        validate_timing_value: any,
        page_of: any,

        dot_template: any,
        moment: any,

    }
}

// window.$ = jQuery;
// window.jQuery = jQuery;
// window.ace = new Ace();
// window.stalker = stalker;
window.stalker = new stalker.Stalker();

window.get_icon = get_icon;
window.append_thumbnail = append_thumbnail;
window.chosen_field_creator = chosen_field_creator;
window.chosen_searchable_field_creator = chosen_searchable_field_creator;
window.chosen_searchable_field_creator_by_data = chosen_searchable_field_creator_by_data;
window.convert_seconds_to_hour = convert_seconds_to_hour;
window.convert_seconds_to_time_range = convert_seconds_to_time_range;
window.findArrayElement = findArrayElement;
window.get_date_range = get_date_range;
window.get_date_picker = get_date_picker;
window.get_task_data = get_task_data;
window.meaningful_time = meaningful_time;
window.meaningful_time_between = meaningful_time_between;
window.page_of = page_of;
window.remove_thumbnails = remove_thumbnails;
window.seconds_in_unit = seconds_in_unit;
window.set_entity_thumbnail = set_entity_thumbnail;
window.to_seconds = to_seconds;
window.units = units;
window.validate_timing_value = validate_timing_value;

window.dot_template = template;
window.moment = moment;

jQuery(function() {
    // choose default skin
    const skin_class = 'skin-1';
    const body = $(document.body);
    body.removeClass('skin-1 skin-2 skin-3');
    body.addClass(skin_class);
    $('.ace-nav > li.grey').addClass('dark');
});

// if it is smaller resize the page content to the window height
window.resize_page_content = function () {
    const page_content = $('.page-content');
    const page_content_height = page_content.height();
    const window_height = $(window).height() - 118;  // 230
    const new_height = Math.max(window_height, page_content_height);
    if (page_content_height < window_height) {
        page_content.css({'min-height': window_height});
    }
};

jQuery(function() {
    window.resize_page_content();
});


jQuery(function() {
    // hide ace-settings bar
    $('#ace-settings-box').toggleClass('open');
});


// {# copyToClipboard #}
window.copyToClipboard = function (text) {
    window.prompt('Copy to clipboard: Ctrl+C, Enter', text);
};


// Pop Flash Messages
window.flash_message = function (settings) {
    settings.container = settings.container || 'body';
    settings.title = settings.title || '';
    settings.message = settings.message || '';
    settings.type = settings.type || 'success'; // success, warning, error

    // jQuery.gritter.add({
    //     title: settings.title,
    //     text: settings.message,
    //     class_name: 'gritter-' + settings.type
    // });
};

// flash all session messages as gritter
jQuery(function() {
    let item, title, type, message;
    const all_messages = $.parseHTML($('#tmpl_flash_message').text());
    for (let i = 0; i < all_messages.length; i++) {
        item = $(all_messages[i]);
        title = item.attr('title');
        type = item.attr('type');
        message = item.text();
        if (title !== undefined && type !== undefined) {
            window.flash_message({
                type: type,
                title: title,
                message: message
            });
        }
    }
});

// {# Add came_from attribute to all a's #}
jQuery(function() {
    jQuery('a.dialog').each(function (i) {
        const href = this.getAttribute('href');
        if (href !== '#') {
            this.setAttribute('href', href + '?came_from={{ request.path }}')
        }
    });
});


// {# Gantt Chart Scroll #}
window.scrollToTaskItem = function (start) {
    jQuery('#gantt_scroll_to_button').attr('start', start).trigger('click');
};


// {# Event Dialog Initialize #}
jQuery(function() {
    const event_dialog = jQuery('#dialog_template');

    const init_them_all = function () {
        if (event_dialog.find('script.dialog_loaded')[0] !== undefined) {
            try {
                setTimeout(function () {
                    // init_dialog() will be loaded with the dialog itself
                    window.init_dialog();
                });
            } catch (e) {
                console.log(e);
            }
        } else {
            setTimeout(init_them_all, 500);
        }
    };

    event_dialog.on('shown', function (e) {
        $('#dialog_template_delete_button').hide();
        e.stopPropagation();
        e.preventDefault();
        init_them_all();
    });

    event_dialog.on('hidden', function (e) {
        e.stopPropagation();
        e.preventDefault();
        try {
            setTimeout(function () {
                // destruct_dialog() will be loaded with the dialog itself
                window.destruct_dialog();
            });
        } catch (e) {
            console.log(e);
        }
    });
});


// {# HTML Dialog Initialize #}
jQuery(function() {
    const html_dialog = $('#html_template');
    html_dialog.on('shown', function (e) {
        e.stopPropagation();
        e.preventDefault();
        try {
            window.init_html_modal(-1);
        } catch (e) {
            console.log(e)
        }
    });
    html_dialog.on('hidden', function (e) {
        e.stopPropagation();
        e.preventDefault();

        try {
            window.destruct_html_modal();
        } catch (e) {
            console.log(e)
        }
    });
});


// {# Inline Edits #}
// $(function () {
//     // $.fn.editable.defaults.mode = 'inline';
//     $.fn.editableform.loading = '<div class=\'editableform-loading\'><i class=\'light-blue icon-2x icon-spinner icon-spin\'></i></div>';
//     $.fn.editableform.buttons = '<button type="submit" class="btn btn-info editable-submit"><i class="icon-ok icon-white"></i></button>' +
//         '<button type="button" class="btn editable-cancel"><i class="icon-remove"></i></button>';
// });


window.menus_under_title = function (title, icon, menuItems) {
    $(function () {
        const sidebar_list = $('#sidebar_list');
        const tree_link_template = template($('#tmpl_sidebar_tree_link').html());
        const data_counts = menuItems.length;

        if (data_counts > 0) {
            sidebar_list.append(tree_link_template({
                'title': title,
                'icon': get_icon(icon)
            }));
        }

        const item_sublink = $('#' + title + '_sublink');
        const tree_sublink_template = template($('#tmpl_sidebar_tree_sublink').html());

        for (let i = 0; i < data_counts; i++) {
            item_sublink.append(tree_sublink_template(menuItems[i]));
        }
    });
};


window.submenu_of = function (id, treeItemType) {
    $.getJSON('/entities/' + id + '/' + treeItemType.toLowerCase() + 's/').then(function (data) {
        $(function () {
            const sidebar_list = $('#sidebar_list');
            const tree_link_template = template($('#tmpl_sidebar_tree_link').html());
            const data_counts = data.length;

            if (data_counts > 0) {
                sidebar_list.append(tree_link_template({
                    'title': treeItemType + 's',
                    'icon': get_icon(treeItemType.toLowerCase())
                }));
            }

            const item_sublink = $('#' + treeItemType + 's_sublink');
            const tree_sublink_template = template($('#tmpl_sidebar_tree_sublink').html());

            for (let i = 0; i < data_counts; i++) {
                data[i].link = '/' + treeItemType.toLowerCase() + 's/' + data[i].id + '/view';
                item_sublink.append(tree_sublink_template(data[i]));
            }
        });
    });
};


window.menu_of = function (title, state, address, icon, count) {
    const sidebar_list = $('#sidebar_list');
    const link_template = template($('#tmpl_sidebar_link').html());

    const options = {
        'title': title,
        'state': state,
        'link': address,
        'icon': icon,
        'count': count
    };

    const rendered_template = $($.parseHTML(link_template(options)));
    sidebar_list.append(rendered_template[0]);

    const badge = rendered_template.find('.badge');

    // update the badge
    if (typeof (count) === 'string' && count !== 'no_badge') {
        // it is the address of the source
        $.getJSON(count).then(function (data) {
            count = data;
            // now update the side bar badge
            badge.text(count);
            if (count > 0) {
                badge.removeClass('badge-success').addClass('badge-important');
            }
        });
    }
};


// document.addEventListener('DOMContentLoaded', function() {
//   let calendarEl: HTMLElement = document.getElementById('calendar')!;
//
//   let calendar = new Calendar(calendarEl, {
//     plugins: [ dayGridPlugin ]
//     // options here
//   });
//
//   calendar.render();
// });

jQuery(function() {
    let entity_id = 31; // TODO: Fix this with the value of template variable {{ entity.id }}
    jQuery.getJSON('/users/'+ entity_id +'/events/?keys=time_log&keys=vacation').then(function (data) {
        let events = [];
        let total_timelogs = 0;

        for (let i = 0; i < data.length; i++) {
            let start_date = new Date(parseInt(data[i].start));
            let end_date = new Date(parseInt(data[i].end));
            let title = data[i].title;

            if(data[i].entity_type === 'timelogs'){
                let timelog_hours = (Number(end_date) - Number(start_date)) / 3600000;
                total_timelogs += timelog_hours;
                title = data[i].title;
            }

            let event = {
                id: data[i].id,
                extendedProps: {
                    entity_type: data[i].entity_type
                },
                title: title,
                start: start_date,
                end: end_date,
                className: data[i].className,
                allDay: data[i].allDay
            };

            events.push(event);
        }
        let stalker_ = new stalker.Stalker();
        stalker_.drawCalendar('calendar', events);
    });
});


jQuery(function() {
    jQuery.getJSON("/get_logged_in_user_id", function(logged_in_user_id){
        jQuery.getJSON("/request_route_path?route_name=list_entity_tickets&id=" + logged_in_user_id, function(notification_url){
            let stalker_ = new stalker.Stalker();
            stalker_.update_open_ticket_count(logged_in_user_id, notification_url);
            stalker_.update_user_tasks_count(logged_in_user_id);
        });
    });
});