// Stalker Pyramid
// Copyright (C) 2013 Erkan Ozgur Yilmaz
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
    var doT = require('../../doT/doT.min');
    var jQuery = require('../../jquery/jquery-2.1.1.min');
} catch (e) {}


(function ($) {
    'use strict';

    /**
     * Page class
     * 
     * @param options
     * @constructor
     */
    var Page = function (options) {
        options = $.extend({
            number: null,
            prev_page: null,
            next_page: null,
            active: false,
            disabled: false,
            callback: function () {}
        }, options);

        this.number = options.number;
        this.prev_page = options.prev_page;
        this.next_page = options.next_page;
        this.disabled = options.disabled;
        this.active = options.active;
        this.callback = options.callback;
    };

    /**
     * Draws itself
     */
    Page.prototype.to_html = function () {
        var template = '<li>';
        if (this.active) {
            template = '<li class="active">';
        }
        template += '<a href="#">' + this.number + '</a></li>';
        return template;
    };

    /**
     * PageManager class
     * 
     * @param options
     * @constructor
     */
    var PageManager = function (options) {
        this.pages = [];
        this.shown_pages = [];
        this.current_page_number = null;
        this.max_number_of_page_shortcuts = 5;
    };

    Object.defineProperty(
        PageManager.prototype,
        'number_of_pages',
        {
            get: function () {
                return this.pages.length;
            }
        }
    );

    var container = null;
    var number_of_pages = 0;
    var number_of_items = 0;
    var items_per_page = 10;
    var current_page_number = 0;
    var max_number_of_page_shortcuts = 5;
    var callback = function () {};
    var pages = [];
    var pages_shown = [];

    var main_template = '<ul>' +
        '    <li class="disabled">' +
        '        <a href="#">' +
        '            <i class="icon-double-angle-left"></i>' +
        '        </a>' +
        '    </li>' +
        '    {{~ it.pages :p:i }}' +
        '    <li>' +
        '        <a href="#">{{=p}}</a>' +
        '    </li>' +
        '    {{~}}' +
        '    <li>' +
        '        <a href="#">' +
        '            <i class="icon-double-angle-right"></i>' +
        '        </a>' +
        '    </li>' +
        '</ul>';

    var main_template_function = doT.template(main_template);

    $.fn.paginator = function (options) {
        options = options || {};
        container = this;

        var settings = $.extend({
            number_of_items: number_of_items,
            items_per_page: items_per_page,
            current_page_number: current_page_number,
            max_number_of_page_shortcuts: max_number_of_page_shortcuts,
            callback: function (current_page_number) {}
        }, options);

        number_of_items = settings.number_of_items;
        items_per_page = settings.items_per_page;
        current_page_number = settings.current_page_number;
        number_of_pages = 0;

        max_number_of_page_shortcuts = settings.max_number_of_page_shortcuts;

        callback = settings.callback;

        $.fn.paginator.initialize();
        return this;
    };


    /**
     * Initializes the paginator
     * 
     * @param options
     * @private
     */
    $.fn.paginator.initialize = function () {
        $.fn.paginator.get_pages();
        $.fn.paginator.get_pages_shown();
        $.fn.paginator.render_page_icons();
        $.fn.paginator.register_events();
    };

    /**
     * returns an array of pages
     * 
     * @param options
     * @returns {Array}
     */
    $.fn.paginator.get_pages = function () {
        number_of_pages = Math.ceil(number_of_items / items_per_page);
        current_page_number = Math.max(1, Math.min(number_of_pages, current_page_number));
        // get the pages
        var pages = [], i;
        for (i = 0; i < number_of_pages; i += 1) {
            pages.push(i + 1);
        }
        return pages;
    };

    /**
     * fills the page_shown attribute of this object
     */
    $.fn.paginator.get_pages_shown = function () {
        var page_min = Math.floor(current_page_number - max_number_of_page_shortcuts / 2);
        var page_max = page_min + Math.min(number_of_pages, max_number_of_page_shortcuts) - 1;

        if (page_max >= number_of_pages) {
            page_max = number_of_pages - 1;
            page_min = Math.max(0, page_max - max_number_of_page_shortcuts);
        }

        if (page_min < 0) {
            page_min = 0;
            page_max = page_min + Math.min(number_of_pages, max_number_of_page_shortcuts) - 1;
        }

        // get the pages
        pages_shown = [];
        var i;
        for (i = page_min; i <= page_max; i += 1) {
            pages_shown.push(i + 1);
        }
    };

    /**
     * sets the current page
     * 
     * @param page_number
     */
    $.fn.paginator.set_current_page = function (page_number) {
        if (page_number === '+1') {
            page_number = Math.min(current_page_number + 1, number_of_pages);
        } else if (page_number === -1) {
            page_number = Math.max(current_page_number - 1, 1);
        }

        if (isNaN(parseInt(page_number))) {
            return;
        }

        current_page_number = page_number;
        $.fn.paginator.initialize();

        // call the callback function
        callback(current_page_number);
    };

    /**
     * Goes to next page
     */
    $.fn.paginator.next = function () {

    };

    /**
     * Goes to previous page
     */
    $.fn.paginator.prev = function () {

    };

    $.fn.paginator.render_left_icon = function () {
        var icon_class = current_page_number === 1 ? 'disabled' : '';

        return '<li class="' + icon_class + '">' +
            '<a class="paginator_page_icon" href="#" data-page-number="-1">' +
            '   <i class="icon-angle-left">' +
            '   </i>' +
            '</a></li>';
    };

    $.fn.paginator.render_right_icon = function () {
        var icon_class = current_page_number === number_of_pages ? 'disabled' : '';

        return '<li class="' + icon_class + '">' +
            '   <a class="paginator_page_icon" href="#" data-page-number="+1">' +
            '       <i class="icon-angle-right">' +
            '       </i>' +
            '   </a>' +
            '</li>';
    };

    $.fn.paginator.render_left_most_icon = function () {
        var icon_class = current_page_number === 1 ? 'disabled' : '';

        return '<li class="' + icon_class + '">' +
            '<a class="paginator_page_icon" href="#" data-page-number="1">' +
            '   <i class="icon-double-angle-left">' +
            '   </i>' +
            '</a></li>';
    };

    $.fn.paginator.render_right_most_icon = function () {
        var icon_class = current_page_number === number_of_pages ? 'disabled' : '';

        return '<li class="' + icon_class + '">' +
            '   <a class="paginator_page_icon" href="#" data-page-number="' + number_of_pages + '">' +
            '       <i class="icon-double-angle-right">' +
            '       </i>' +
            '   </a>' +
            '</li>';
    };

    $.fn.paginator.render_page_icon = function (page_number) {
        var template = '<li class="paginator_page_box">';
        if (page_number === current_page_number) {
            template = '<li class="paginator_page_box active">';
        }
        template += '<a class="paginator_page_icon" href="#" data-page-number="' + page_number + '">' + page_number + '</a></li>';
        return template;
    };

    $.fn.paginator.render_jump_to_page_controls = function () {
        var template = '<form class="form-search span6">' +
            '<input id="paginator_jump_to_page_input" class="input-medium search-query" type="text" style="width: 26px" value="' + current_page_number +  '">' +
            '<span> of ' + number_of_pages + '&nbsp</span>' +
            '<button id="paginator_jump_to_page_button" class="btn btn-info btn-small">Go</button>' +
            '</form>';
        return template;
    };

    $.fn.paginator.register_jump_to_page_button_callback = function () {
        $('#paginator_jump_to_page_button').on('click', function (e) {
            e.stopPropagation();
            e.preventDefault();
            $.fn.paginator.set_current_page($('#paginator_jump_to_page_input').val());
        });
    };

    /**
     * Registers the page icon events
     * 
     * One click event to update what is shown
     */
    $.fn.paginator.register_page_icon_events = function () {
        $('.paginator_page_icon').on('click', function (e) {
            e.stopPropagation();
            e.preventDefault();
            var self = $(this);
            if (!self.parent().hasClass('disabled')) {
                $.fn.paginator.set_current_page(self.data('page-number'));
            }
        });
    };

    $.fn.paginator.register_events = function () {
        $.fn.paginator.register_page_icon_events();
        $.fn.paginator.register_jump_to_page_button_callback();
    };

    $.fn.paginator.render_page_icons = function () {
        // remove any previous page icons first
        container.find('div').remove();
        var paginator_container = $($.parseHTML('<div class="row-fluid "></div>'));
        var page_jumper = $($.parseHTML($.fn.paginator.render_jump_to_page_controls()));
        var ul_item = $($.parseHTML('<ul class="span6"></ul>'));

        paginator_container.append(ul_item);
        paginator_container.append(page_jumper);

        var left_icon = $($.parseHTML($.fn.paginator.render_left_most_icon()));
        ul_item.append(left_icon);

        var left_icon = $($.parseHTML($.fn.paginator.render_left_icon()));
        ul_item.append(left_icon);

        var page_icon = null;
        var i = null;
        for (i = 0; i < pages_shown.length; i += 1) {
            page_icon = $($.parseHTML($.fn.paginator.render_page_icon(pages_shown[i])));
            ul_item.append(page_icon);
        }
        var right_icon = $($.parseHTML($.fn.paginator.render_right_icon()));
        ul_item.append(right_icon);

        var right_most_icon = $($.parseHTML($.fn.paginator.render_right_most_icon()));
        ul_item.append(right_most_icon);

        container.append(paginator_container);
    };

}(jQuery));




try {
    module.exports.Paginator = Paginator;
} catch (e) {}
