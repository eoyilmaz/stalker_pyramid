// -*- coding: utf-8 -*-
// Stalker Pyramid a Web Base Production Asset Management System
// Copyright (C) 2009-2018 Erkan Ozgur Yilmaz
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
// Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301
// USA

/// <reference path="../node_modules/@types/jquery/index.d.ts"/>



// import * as $ from 'jquery';
import * as jQuery from 'jquery';

import 'bootstrap';
import './less/ace.less';
import 'fullcalendar';


import { Ace } from './js/ace';
import './js/ace-elements.js';
import './js/cache_users';

import get_icon from './js/utils.js';

const doT = require('./../node_modules/dot/doT.js');



declare global {
    interface Window {
        ace: any;
        $: any;
        jQuery: any;
        bootbox: any;
        resize_page_content: any;
        copyToClipboard: any;
        do_playblast: any;
        export_alembics: any;
        flash_message: any;
        scrollToTaskItem: any;
        menus_under_title: any;
        submenu_of: any;
        menu_of: any;
        init_dialog: any;
        destruct_dialog: any;
        init_html_modal: any;
        destruct_html_modal: any;
    }

    interface JQuery {
        editableform: any;
    }

    interface JQueryStatic {
        gritter: any;
        editableform: any;
        // editable(options?: any): XEditable;
    }

    interface XEditable {
        options: XEditableOptions;
    }

}

window.ace = new Ace();
window.jQuery = jQuery;
window.$ = jQuery;


window.console.debug('window.$:', window.$);
window.console.debug('window.$.getJSON:', window.$.getJSON);
window.console.debug('jQuery:', jQuery);
window.console.debug('jQuery.getJSON:', jQuery.getJSON);


window.$(function () {
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

window.jQuery(function () {
    window.resize_page_content();
});


window.$(function () {
    // hide ace-settings bar
    $('#ace-settings-box').toggleClass('open');
});


// {# copyToClipboard #}
window.copyToClipboard = function (text) {
    window.prompt('Copy to clipboard: Ctrl+C, Enter', text);
};


// Do Playblast
window.do_playblast = function (version_id) {
    var result = window.confirm("Do Playblast?:" + version_id);
    if (result === true){
        $.post("/versions/" + version_id + "/do_playblast").done(function(){
            const message = '<div>Job created! Check Afanasy</div>';
            window.bootbox.alert(message);
            $('.bootbox').prepend('<div class="modal-header alert-success"><strong>Success</strong></div>');
        }).fail(function(jqXHR){
            const message = '<div>' + jqXHR.responseText + '</div>';
            window.bootbox.alert(message);
            $('.bootbox').prepend('<div class="modal-header alert-danger"><strong>Fail</strong></div>');
        });
    }
};


// Export Alembics
window.export_alembics = function (version_id) {
    var result = window.confirm("Export Alembics?" + version_id);
    if (result === true){
        $.post("/versions/" + version_id + "/export_alembics").done(function(){
            var message = '<div>Job created! Check Afanasy</div>';
            window.bootbox.alert(message);
            $('.bootbox').prepend('<div class="modal-header alert-success"><strong>Success</strong></div>');
        }).fail(function(jqXHR){
            var message = '<div>' + jqXHR.responseText + '</div>';
            window.bootbox.alert(message);
            $('.bootbox').prepend('<div class="modal-header alert-danger"><strong>Fail</strong></div>');
        });
    }
};

// Pop Flash Messages
window.flash_message = function (settings) {
    settings.container = settings.container || 'body';
    settings.title = settings.title || '';
    settings.message = settings.message || '';
    settings.type = settings.type || 'success'; // success, warning, error

    jQuery.gritter.add({
        title: settings.title,
        text: settings.message,
        class_name: 'gritter-' + settings.type
    });
};

// flash all session messages as gritter
$(function () {
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
$(function () {
    $('a.dialog').each(function (i) {
        const href = this.getAttribute('href');
        if (href !== '#') {
            this.setAttribute('href', href + '?came_from={{ request.path }}')
        }
    });
});


// {# Gantt Chart Scroll #}
window.scrollToTaskItem = function (start) {
    $('#gantt_scroll_to_button').attr('start', start).trigger('click');
};



// {# Event Dialog Initialize #}
$(function () {
    const event_dialog = $('#dialog_template');

    const init_them_all = function() {
        if (event_dialog.find('script.dialog_loaded')[0] !== undefined) {
            try {
                setTimeout(function() {
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
            setTimeout(function() {
                // destruct_dialog() will be loaded with the dialog itself
                window.destruct_dialog();
            });
        } catch (e) {
            console.log(e);
        }
    });
});



// {# HTML Dialog Initialize #}
$(function () {
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
$(function () {
    // $.fn.editable.defaults.mode = 'inline';
    $.fn.editableform.loading = '<div class=\'editableform-loading\'><i class=\'light-blue icon-2x icon-spinner icon-spin\'></i></div>';
    $.fn.editableform.buttons = '<button type="submit" class="btn btn-info editable-submit"><i class="icon-ok icon-white"></i></button>' +
        '<button type="button" class="btn editable-cancel"><i class="icon-remove"></i></button>';
});


window.menus_under_title = function (title, icon, menuItems) {
    $(function () {
        const sidebar_list = $('#sidebar_list');
        const tree_link_template = doT.template($('#tmpl_sidebar_tree_link').html());
        const data_counts = menuItems.length;

        if (data_counts > 0) {
            sidebar_list.append(tree_link_template({
                'title': title,
                'icon': get_icon(icon)
            }));
        }

        const item_sublink = $('#' + title + '_sublink');
        const tree_sublink_template = doT.template($('#tmpl_sidebar_tree_sublink').html());

        for (let i = 0; i < data_counts; i++) {
            item_sublink.append(tree_sublink_template(menuItems[i]));
        }
    });
};


window.submenu_of = function (id, treeItemType) {
    $.getJSON('/entities/' + id + '/' + treeItemType.toLowerCase() + 's/').then(function (data) {
        $(function () {
            const sidebar_list = $('#sidebar_list');
            const tree_link_template = doT.template($('#tmpl_sidebar_tree_link').html());
            const data_counts = data.length;

            if (data_counts > 0) {
                sidebar_list.append(tree_link_template({
                    'title': treeItemType + 's',
                    'icon': get_icon(treeItemType.toLowerCase())
                }));
            }

            const item_sublink = $('#' + treeItemType + 's_sublink');
            const tree_sublink_template = doT.template($('#tmpl_sidebar_tree_sublink').html());

            for (let i = 0; i < data_counts; i++) {
                data[i].link = '/' + treeItemType.toLowerCase() + 's/' + data[i].id + '/view';
                item_sublink.append(tree_sublink_template(data[i]));
            }
        });
    });
};


window.menu_of = function (title, state, address, icon, count) {
    const sidebar_list = $('#sidebar_list');
    const link_template = doT.template($('#tmpl_sidebar_link').html());

    const options = {
        'title': title,
        'state': state,
        'link': address,
        'icon': icon,
        'count': count
    };

    const rendered_template = $($.parseHTML(link_template(options)));
    sidebar_list.append(rendered_template);

    const badge = rendered_template.find('.badge');

    // update the badge
    if ( typeof(count) === 'string' && count !== 'no_badge') {
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

