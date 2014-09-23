// Stalker Pyramid a Web Base Production Asset Management System
// Copyright (C) 2009-2014 Erkan Ozgur Yilmaz
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

try {
    var jQuery = require('../../jquery/jquery-2.0.3.min');
} catch (e) {}


/**
 * Queries Task data from server
 * 
 * @param search_string
 *   A string value containing the query words
 * @param callback
 *   A function that will be called with the retrieved data
 */
function get_task_data(options) {
    'use strict';
    options = $.extend({
        search_string: '',
        callback: function () { return; },
        project_id: null
    }, options);

    var search_buffer, search_params = {}, key_value_pair, key, value, i;

    search_params.project_id = options.project_id;

    // iterate over each key value pair

    if (options.search_string.indexOf(':') === -1) {
        if (options.search_string.length < 3) {
            // not finished typing yet
            return;
        }

        search_buffer = options.search_string.split(' ');
        // use a direct search with given words as the task full_path
        $.extend(
            search_params,
            {
                path: search_buffer
            }
        );
    } else {
        // so we have some key value pairs
        search_buffer = options.search_string.split(',');

        var current_pair;
        for (i = 0; i < search_buffer.length; i += 1) {
            current_pair = search_buffer[i];

            if (current_pair.length === 0 || current_pair.indexOf(':') === -1) {
                // not finished typing yet
                continue;
            }

            key_value_pair = search_buffer[i].split(':');

            key = key_value_pair[0];
            value = key_value_pair[1].replace(/[\s]+/, ' ').trim(); //.split(' ');

            if (value === '') {
                // not finished typing yet
                continue;
            }

            // if there is a key expand it
            if (search_params[key] !== undefined) {
                search_params[key].push(value);
            } else {
                search_params[key] = [value];
            }
        }
    }

    $.getJSON('/tasks/', search_params, function (data) {
        var input_source = [];
        var result_count = data.length;
        var max_count = 250;
        for (i = 0; i < Math.min(result_count, max_count); i += 1) {
            input_source.push(data[i].full_path);
        }
        if (result_count > max_count) {
            input_source.push('' + (result_count - max_count) + ' more items...');
        }
        options.callback(input_source);
    });
}

var units = ['y', 'm', 'w', 'd', 'h', 'min'];

function get_icon(entity_type) {
    'use strict';
    switch (entity_type) {
    case 'PREV':
        return 'icon-pencil';
    case 'HREV':
        return 'icon-mail-reply-all';
    case 'RTS':
        return 'icon-check-empty';
    case 'CMPL':
        return 'icon-check';
    case 'WIP':
        return 'icon-play';
    case 'WFD':
        return 'icon-circle';
    case 'DREV':
        return 'icon-step-backward';
    case 'OH':
        return 'icon-pause';
    case 'STOP':
        return 'icon-stop';
    case 'asset':
        return 'icon-puzzle-piece';
    case 'dashboard':
        return 'icon-dashboard';
    case 'department':
        return 'icon-group';
    case 'group':
        return 'icon-key';
    case 'project':
        return 'icon-folder-close-alt';
    case 'permission':
        return 'icon-key';
    case 'reference':
        return 'icon-book';
    case 'review':
        return 'icon-comments-alt';
    case 'sequence':
        return 'icon-film';
    case 'shot':
        return 'icon-camera';
    case 'task':
        return 'icon-tasks';
    case 'previs':
        return 'icon-coffee';
    case 'ticket':
        return 'icon-ticket';
    case 'vacation':
        return 'icon-sun';
    case 'version':
        return 'icon-sitemap';
    case 'version_output':
        return 'icon-picture';
    case 'user':
        return 'icon-user';
    case 'resource':
        return 'icon-user';
    case 'daily':
        return 'icon-eye-open';
    case 'report':
        return 'icon-bar-chart';
    default:
        return 'icon-key';
    }
}


/**
 * Creates a chosen field
 * 
 * @param field
 *   field
 * @param url
 *   data url
 * @param data_template
 *   the doT template for the data
 * @param selected_id
 *   a list of integers for pre-selecting items
 * @param chosen_options
 *   Extra options to be attached to chosen options
 */
function chosen_field_creator(field, url, data_template, selected_id, chosen_options) {
    'use strict';
    // fill field with new json data
    // set the field to updating mode
    field.attr('is_updating', true);

    return $.getJSON(url).then(function (data) {
        // remove current data
        field.empty();

        // append new options to the select
        var i, data_count = data.length;
        for (i = 0; i < data_count; i += 1) {

            data[i].selected = '';

            if (data[i].id === selected_id) {
                data[i].selected = 'selected';
            }

            field.append(data_template(data[i]));
        }
        // set the field to normal mode
        field.attr('is_updating', false);
    });
}


function unit_by_seconds(unit) {
    'use strict';
    switch (unit) {
    case 'min':
        return 60;
    case 'h':
        return 3600;
    case 'd':
        return 32400; // TODO: this is not true, please use: stalker.defaults.daily_working_hours
    case 'w':
        return 194400; // TODO: this is not true, please use: stalker.defaults.weekly_working_hours
    case 'm':
        return 2419200; // TODO: this is not true, please use: 4 * stalker.defaults.weekly_working_hours
    case 'y':
        return 31536000; // TODO: this is not true, please use: stalker.defaults.yearly_working_days * stalker.defaults.daily_working_hours
    }
    return 0;
}

function calculate_seconds(timing, unit) {
    'use strict';
    var u_seconds = unit_by_seconds(unit);
    return timing * u_seconds;
}

function meaningful_time(time) {
    'use strict';
    time = Math.round(time);

    if (time !== 0) {
        if (time % unit_by_seconds('y') === 0) {
            return time / unit_by_seconds('y') + ' y';
        } else if (time % unit_by_seconds('m') === 0) {
            return time / unit_by_seconds('m') + ' m';
        } else if (time % unit_by_seconds('w') === 0) {
            return time / unit_by_seconds('w') + ' w';
        } else if (time % unit_by_seconds('d') === 0) {
            return time / unit_by_seconds('d') + ' d';
        } else if (time % unit_by_seconds('h') === 0) {
            return time / unit_by_seconds('h') + ' h';
        } else if (time % unit_by_seconds('min') === 0) {
            return time / unit_by_seconds('min') + ' min';
        } else {
            return time + ' seconds';
        }
    } else {
        return '0';
    }
}

function meaningful_time_calculator(time, unit) {
    'use strict';
    var calc_time = Math.round(time);
    var index = units.indexOf(unit);
    var time_str = '';
    var u_seconds = unit_by_seconds(unit);

    if (unit !== null || unit !== undefined) {
        if (calc_time !== 0) {
            if (calc_time > u_seconds) {
                var time_unit = parseInt(time / u_seconds, 10);
                calc_time = calc_time % u_seconds;
                time_str += time_unit + ' ' + unit;

                if (calc_time > 0) {
                    if (index < units.length - 1) {
                        time_str += ' ' + meaningful_time_calculator(calc_time, units[index + 1]);
                    }
                }
            } else {
                if (index < units.length - 1) {
                    time_str += ' ' + meaningful_time_calculator(calc_time, units[index + 1]);
                }
            }
        }
    }

    return time_str;
}

function meaningful_time_between(time1, time2) {
    'use strict';
    var seconds_between = time1 - time2;
    return meaningful_time(seconds_between);
}

function page_of(name, code, thumbnail_full_path, update_link) {
    'use strict';
    var sidebar_list = $('#sidebar_list');
    var media_template = doT.template($('#tmpl_sidebar_media').html());

    sidebar_list.append(media_template({
        'name': name,
        'thumbnail_full_path': thumbnail_full_path,
        'code': code,
        'update_link': update_link
    }));
}


/**
 * Appends a new item to the thumbnail list
 *
 * @param options
 *   An object that holds options.
 */
function append_thumbnail(options) {
    'use strict';
    //
    // adds only one item to the list
    //
    // compile the output item template

    options = $.extend({
        data: null,
        template: null,
        colorbox_params: {},
        animate: false,
        container: null
    }, options);

    var data = options.data;
    var template = options.template;
    var colorbox_params = options.colorbox_params;
    var animate = options.animate;
    var container = options.container;

    // check if there is any video
    data.hires_download_path = data.hires_full_path;
    data.webres_download_path = data.webres_full_path;

    colorbox_params.iframe = false;
    if (data.webres_full_path.search('.webm') !== -1) {
        // it should have video replace the address with video player
        data.webres_full_path = 'video_player?video_full_path=/' + data.webres_full_path;
        colorbox_params.iframe = false;
    }

    var ref_item = $($.parseHTML(template(data)));

    if (animate) {
        ref_item.css({display: 'none'});
    }

    container.append(ref_item);
    if (animate) {
        ref_item.toggle('slow');
    }

    ref_item.find('[data-rel="colorbox"]').colorbox(colorbox_params);
}

/**
 * Removes the thumbnails from list
 */
var remove_thumbnails = function (options) {
    'use strict';
    options = $.extend({
        container: null
    }, options);
    var container = options.container;
    container.children().remove('*');
    container.colorbox.remove();
};
