/* ==========================================================
 * bootstrap-tag.js v2.2.5
 * https://github.com/fdeschenes/bootstrap-tag
 * ==========================================================
 * Copyright 2012 Francois Deschenes.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 * ========================================================== */

!function ($) {
    'use strict';

    var Tag = function (element, options) {
        this.element = $(element);
        this.options = $.extend(true, {}, $.fn.tag.defaults, options);
        this.values = $.grep($.map(this.element.val().split(','), $.trim), function (value) {
            return value.length > 0;
        });

        this.show();

        // for a moment allow new items so the data in the input field can be injected
        var original_setting = this.options.allowNewItems;
        this.options.allowNewItems = true;

        for (var i=0; i < this.options.values.length; i += 1){
            this.add(this.options.values[i]);
        }

        this.options.allowNewItems = original_setting;

        if (this.options.disabled){
            this.input.attr('disabled', 'disabled');
        }
    };

    Tag.prototype = {
        constructor: Tag,
        show: function () {
            var self = this;

            self.element.parent().prepend(self.element.detach().hide());
            self.element
                .wrap($('<div class="tags">'))
                .parent()
                .on('click', function () {
                    self.input.focus();
                });

            if (self.values.length) {
                $.each(self.values, function () {
                    self.createBadge(this);
                });
            }

            self.input = $('<input type="text">')
                .attr('placeholder', self.options.placeholder)
                .insertAfter(self.element)
                .on('focus', function () {
                    self.element.parent().addClass('tags-hover');
                })
                .on('blur', function () {
                    if (!self.skip) {
                        self.process();
                        self.element.parent().removeClass('tags-hover');
                        self.element.siblings('.tag').removeClass('tag-important');
                    }
                    self.skip = false;
                })
                .on('keydown', function (event) {
                    if (event.keyCode  === 188 || event.keyCode  === 13 || event.keyCode  === 9) {
                        if ($.trim($(this).val()) && (!self.element.siblings('.typeahead').length || self.element.siblings('.typeahead').is(':hidden'))) {
                            if (event.keyCode !== 9) {
                                event.preventDefault();
                            }
                            self.process();
                        } else if (event.keyCode === 188 && self.options.allowNewItems) {
                            if (!self.element.siblings('.typeahead').length || self.element.siblings('.typeahead').is(':hidden')) {
                                event.preventDefault();
                            } else {
                                self.input.data('typeahead').select();
                                event.stopPropagation();
                                event.preventDefault();
                            }
                        }
                    } else if (!$.trim($(this).val()) && event.keyCode === 8) {
                        var count = self.element.siblings('.tag').length;
                        if (count) {
                            var tag = self.element.siblings('.tag:eq(' + (count - 1) + ')');
                            if (tag.hasClass('tag-important')) {
                                self.remove(count - 1);
                            } else {
                                tag.addClass('tag-important');
                            }
                        }
                    } else {
                        self.element.siblings('.tag').removeClass('tag-important');
                    }
                })
                .typeahead({
                    source: self.options.source,
                    matcher: function (value) {
                        var query = this.query.toLowerCase();
                        if (query.indexOf(':') !== -1) {
                            if (!self.options.allowNewItems) {
                                return true;
                            }
                        }

                        return ~value.toLowerCase().indexOf(query) && (self.inValues(value) === -1 || self.options.allowDuplicaes);
                    },
                    updater: function (value) {
                        // remove the full path part of the values
                        if (typeof self.options.resultFilter === 'function') {
                            value = self.options.resultFilter(value);
                        }
                        $.proxy(self.add, self)(value);
                    }
                });

            $(self.input.data('typeahead').$menu).on('mousedown', function () {
                self.skip = true;
            });

//            this.element.trigger('shown'); // this was causing init_dialogs to be triggered
        },
        inValues: function (value) {
            // if there is a result filter the value may become an object
            // instead of a plain string
            if (typeof value !== 'string') {
                value = value.input;
            }

            if (this.options.caseInsensitive) {
                var index = -1;
                $.each(this.values, function (indexInArray, valueOfElement) {

                    if (typeof valueOfElement !== 'string') {
                        valueOfElement = valueOfElement.input;
                    }

                    if (valueOfElement.toLowerCase() === value.toLowerCase()) {
                        index = indexInArray;
                        return false;
                    }
                });
                return index;
            } else {
                return $.inArray(value, this.values);
            }
        },
        createBadge: function (value) {
            var self = this;

            var tag = $('<span/>', {
                'class': "tag"
            }).text(value);

            if (!self.options.disabled){
                tag.append(
                    $('<button type="button" class="close">&times;</button>')
                        .on('click', function () {
                            self.remove(self.element.siblings('.tag').index($(this).closest('.tag')));
                        })
                );
            }
            if (value.input !== undefined){
                tag.attr('title', value.input);
            } else {
                tag.attr('title', value);
            }
            tag.insertBefore(self.element);
        },
        add: function (value) {
            var self = this;

            if (!self.options.allowDuplicates) {
                var index = self.inValues(value);
                if (index !== -1) {
                    var badge = self.element.siblings('.tag:eq(' + index + ')');
                    badge.addClass('tag-warning');
                    setTimeout(function () {
                        $(badge).removeClass('tag-warning');
                    }, 500);
                    return;
                }
            }

            this.values.push(value);
            this.createBadge(value);

            this.element.val(this.values.join(', '));
            this.element.trigger('added', [value]);
        },
        remove: function (index) {
            if (index >= 0) {
                var value = this.values.splice(index, 1);
                this.element.siblings('.tag:eq(' + index + ')').remove();
                this.element.val(this.values.join(', '));

                this.element.trigger('removed', [value]);
            }
        },
        /**
         * Processes anything on the input field, it first splits the input
         * from the coma (,) characters and then trims them
         */
        process: function () {
            if (this.options.allowNewItems) {
                var values, self = this;

                values = $.grep($.map(this.input.val().split(','), $.trim), function (value) {
                    return value.length > 0;
                });

                $.each(values, function () {
                    self.add(this);
                });
            }
            this.input.val('');
        },
        skip: false
    };

    var old = $.fn.tag;

    $.fn.tag = function (option) {
        return this.each(function () {
            var self = $(this),
                data = self.data('tag'),
                options = typeof option === 'object' && option;
            if (!data) {
                self.data('tag', (data = new Tag(this, options)));
            }
            if (typeof option === 'string') {
                data[option]();
            }
        });
    };

    $.fn.tag.defaults = {
        allowDuplicates: false,
        caseInsensitive: true,
        placeholder: '',
        source: [],
        allowNewItems: true,
        resultFilter: undefined,
        values: []
    };

    $.fn.tag.Constructor = Tag;

    $.fn.tag.noConflict = function () {
        $.fn.tag = old;
        return this;
    };

    $(window).on('load', function () {
        $('[data-provide="tag"]').each(function () {
            var self = $(this);
            if (self.data('tag')) {
                return;
            }
            self.tag(self.data());
        });
    });
}(window.jQuery);
