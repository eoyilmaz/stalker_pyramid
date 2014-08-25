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
            if (search_params[key] !== undefined){
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
};
