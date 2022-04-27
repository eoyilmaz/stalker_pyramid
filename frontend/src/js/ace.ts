// if (!('ace' in window)) window['ace'] = {};
import * as $ from 'jquery';

import 'bootstrap';
import './jquery_extend';
import './ace-elements';
import './additional-methods';
import 'x-editable/dist/bootstrap-editable/js/bootstrap-editable';
import 'select2';

// import "moment/dist/moment";

require("../../node_modules/moment/dist/moment");
require("../../node_modules/as-jqplot/dist/jquery.jqplot.min");
require("../../node_modules/as-jqplot/dist/plugins/jqplot.categoryAxisRenderer.min");
require("../../node_modules/as-jqplot/dist/plugins/jqplot.barRenderer.min");
require("../../node_modules/as-jqplot/dist/plugins/jqplot.dateAxisRenderer.min");
require("../../node_modules/as-jqplot/dist/plugins/jqplot.logAxisRenderer.min");
require("../../node_modules/as-jqplot/dist/plugins/jqplot.canvasAxisTickRenderer.min");
require("../../node_modules/as-jqplot/dist/plugins/jqplot.canvasTextRenderer.min");
require("../../node_modules/as-jqplot/dist/plugins/jqplot.pointLabels.min");
require("../../node_modules/as-jqplot/dist/plugins/jqplot.highlighter.min");
require("../../node_modules/as-jqplot/dist/plugins/jqplot.cursor.min");
require("../../node_modules/as-jqplot/dist/examples/syntaxhighlighter/scripts/shCore");
require("../../node_modules/as-jqplot/dist/examples/syntaxhighlighter/scripts/shBrushJScript");
require("../../node_modules/as-jqplot/dist/examples/syntaxhighlighter/scripts/shBrushXml");
require("../../node_modules/accounting/accounting.min");
require("../../node_modules/dropzone/dist/dropzone-min");

require("../../node_modules/bootstrap-wysiwyg/js/bootstrap-wysiwyg.min");
require("../../node_modules/bootstrap-tagsinput/dist/bootstrap-tagsinput.min")  // TODO: This is not the intended plugin
require("../../node_modules/bootstrap-datepicker/js/bootstrap-datepicker");
require("../../node_modules/bootstrap-markdown/js/bootstrap-markdown");
require("../../node_modules/bootstrap-colorpicker/dist/js/bootstrap-colorpicker.min");

require("../../node_modules/dhtmlx-suite/codebase/dhtmlx");
require("../../node_modules/dhtmlx-gantt/codebase/dhtmlxgantt");
require("../../node_modules/daterangepicker/daterangepicker");
require("../../node_modules/easy-pie-chart/dist/jquery.easypiechart");
require("../../node_modules/jquery-ui/ui/widgets/accordion");
require("../../node_modules/jquery-ui/ui/widgets/sortable");
require("../../node_modules/jquery-ui-touch-punch/jquery.ui.touch-punch");
require("../../node_modules/jquery-autosize/jquery.autosize");
require("../../node_modules/jquery.flot/jquery.flot");
require("../../node_modules/jquery.flot/jquery.flot.pie");
require("../../node_modules/jquery.flot/jquery.flot.resize");
require("../../node_modules/jquery.hotkeys/jquery.hotkeys");
require("../../node_modules/jquery.maskedinput/src/jquery.maskedinput");
require("../../node_modules/jquery-mobile/dist/jquery.mobile.min");
require("../../node_modules/jquery-inputlimiter/jquery.inputlimiter");
require("../../node_modules/jquery-validation/dist/jquery.validate");
require("../../node_modules/jquery-slimscroll/jquery.slimscroll");
require("../../node_modules/gritter/js/jquery.gritter");
require("../../node_modules/free-jqgrid/dist/i18n/grid.locale-en");
require("../../node_modules/free-jqgrid/dist/jquery.jqgrid.min");
require("../../node_modules/free-jqgrid/dist/plugins/ui.multiselect");
require("../../node_modules/markdown/lib/markdown");
require("../../node_modules/select2/dist/js/select2")
require("../../node_modules/fuelux/js/spinbox");
require("../../node_modules/fullcalendar/dist/fullcalendar.min");
require("../../node_modules/datatables/media/js/jquery.dataTables.min");
require("./dataTable_num-html_sort");

//
// import "moment/dist/moment";
//
// import "as-jqplot/dist/jquery.jqplot.min";
// import "as-jqplot/dist/plugins/jqplot.categoryAxisRenderer.min";
// import "as-jqplot/dist/plugins/jqplot.barRenderer.min";
// import "as-jqplot/dist/plugins/jqplot.dateAxisRenderer.min";
// import "as-jqplot/dist/plugins/jqplot.logAxisRenderer.min";
// import "as-jqplot/dist/plugins/jqplot.canvasAxisTickRenderer.min";
// import "as-jqplot/dist/plugins/jqplot.canvasTextRenderer.min";
// import "as-jqplot/dist/plugins/jqplot.pointLabels.min";
// import "as-jqplot/dist/plugins/jqplot.highlighter.min";
// import "as-jqplot/dist/plugins/jqplot.cursor.min";
// import "as-jqplot/dist/examples/syntaxhighlighter/scripts/shCore";
// import "as-jqplot/dist/examples/syntaxhighlighter/scripts/shBrushJScript";
// import "as-jqplot/dist/examples/syntaxhighlighter/scripts/shBrushXml";
// import "accounting/accounting.min";
// import "dropzone/dist/dropzone-min";
//
// import "bootstrap-wysiwyg/js/bootstrap-wysiwyg.min";
// import "bootstrap-tagsinput/dist/bootstrap-tagsinput.min";  // TODO: This is not the intended plugin
// import "bootstrap-datepicker/js/bootstrap-datepicker";
// import "bootstrap-markdown/js/bootstrap-markdown";
// import "bootstrap-colorpicker/dist/js/bootstrap-colorpicker.min";
//
// import "dhtmlx-suite/codebase/dhtmlx";
// import "dhtmlx-gantt/codebase/dhtmlxgantt";
// import "daterangepicker/daterangepicker";
// import "easy-pie-chart/dist/jquery.easypiechart";
// import "jquery-ui/ui/widgets/accordion";
// import "jquery-ui/ui/widgets/sortable";
// import "jquery-ui-touch-punch/jquery.ui.touch-punch";
// import "jquery-autosize/jquery.autosize";
// import "jquery.flot/jquery.flot";
// import "jquery.flot/jquery.flot.pie";
// import "jquery.flot/jquery.flot.resize";
// import "jquery.hotkeys/jquery.hotkeys";
// import "jquery.maskedinput/src/jquery.maskedinput";
// import "jquery-mobile/dist/jquery.mobile.min";
// import "jquery-inputlimiter/jquery.inputlimiter";
// import "jquery-validation/dist/jquery.validate";
// import "jquery-slimscroll/jquery.slimscroll";
// import "gritter/js/jquery.gritter";
// import "free-jqgrid/dist/i18n/grid.locale-en";
// import "free-jqgrid/dist/jquery.jqgrid.min";
// import "free-jqgrid/dist/plugins/ui.multiselect";
// import "markdown/lib/markdown";
// import "select2/dist/js/select2";
// import "fuelux/js/spinbox";
// import "fullcalendar/dist/fullcalendar.min";
// import "datatables/media/js/jquery.dataTables.min";
// import "./dataTable_num-html_sort";





// declare global {
//     interface Window {
//         ace: any;
//     }
// }


jQuery(function (parameters: { $: any }) {
    // at some places we try to use 'tap' event instead of 'click' if jquery mobile plugin is available
    // window.ace = new Ace();
    if (jQuery.fn.hasOwnProperty('tap')) {
        // window.ace.click_event = $.fn.tap ? "tap" : "click";
    }
});


jQuery(function (parameters: { $: any }) {
    // ace.click_event defined in ace-elements.js
    const ace = window.ace;
    ace.handle_side_menu();
    ace.enable_search_ahead();
    ace.general_things(); // and settings
    ace.widget_boxes();

    /**
     //make sidebar scrollbar when it is fixed and some parts of it is out of view
     //>> you should include jquery-ui and slimscroll javascript files in your file
     //>> you can call this function when sidebar is clicked to be fixed
     $('.nav-list').slimScroll({
        height: '400px',
        distance:0,
        size : '6px'
    });
     */
});


export class Ace {

    click_event: string;
    variable_US_STATES: string[];
    settings: any;

    handle_side_menu() {
        const self = this;
        jQuery('#menu-toggler').on(this.click_event, function () {
            jQuery('#sidebar').toggleClass('display');
            jQuery(this).toggleClass('display');
            return false;
        });

        // mini
        let $minimized = $('#sidebar').hasClass('menu-min');
        $('#sidebar-collapse').on(this.click_event, function () {
            $minimized = $('#sidebar').hasClass('menu-min');
            self.settings.sidebar_collapsed(!$minimized); // @ ace-extra.js
        });

        const touch = 'ontouchend' in document;

        // opening submenu
        $('.nav-list').on(this.click_event, function (e) {
            // check to see if we have clicked on an element which is inside a .dropdown-toggle element?!
            // if so, it means we should toggle a submenu
            const link_element = $(e.target).closest('a');
            if (!link_element || link_element.length === 0) {
                return; // if not clicked inside a link element
            }

            $minimized = $('#sidebar').hasClass('menu-min');

            if (!link_element.hasClass('dropdown-toggle')) { // it doesn't have a submenu return
                // just one thing before we return
                // if sidebar is collapsed(minimized) and we click on a first level menu item
                // and the click is on the icon, not on the menu text then let's cancel event and cancel navigation
                // Good for touch devices, that when the icon is tapped to see the menu text, navigation is cancelled
                // navigation is only done when menu text is tapped
                if ($minimized && self.click_event === 'tap' &&
                    link_element.get(0).parentNode.parentNode === this /*.nav-list*/) { // i.e. only level-1 links
                    const text = link_element.find('.menu-text').get(0);
                    if (e.target !== text && !$.contains(text, e.target)) { // not clicking on the text or its children
                        return false;
                    }
                }

                return;
            }
            //
            const sub = link_element.next().get(0);

            // if we are opening this submenu, close all other submenus except the ".active" one
            if (!$(sub).is(':visible')) { // if not open and visible, let's open it and make it visible
                const parent_ul = $(sub.parentNode).closest('ul');
                if ($minimized && parent_ul.hasClass('nav-list')) {
                    return;
                }

                parent_ul.find('> .open > .submenu').each(function () {
                    // close all other open submenus except for the active one
                    if (this !== sub && !$(this.parentNode).hasClass('active')) {
                        $(this).slideUp(200).parent().removeClass('open');

                        // uncomment the following line to close all submenus on deeper levels when closing a submenu
                        // $(this).find('.open > .submenu').slideUp(0).parent().removeClass('open');
                    }
                });
            } else {
                // uncomment the following line to close all submenus on deeper levels when closing a submenu
                // $(sub).find('.open > .submenu').slideUp(0).parent().removeClass('open');
            }

            if ($minimized && $(sub.parentNode.parentNode).hasClass('nav-list')) {
                return false;
            }

            $(sub).slideToggle(200).parent().toggleClass('open');
            return false;
        });
    };

    general_things() {
        const self = this;

        $('.ace-nav [class*="icon-animated-"]').closest('a').on('click', function () {
            const icon = $(this).find('[class*="icon-animated-"]').eq(0);
            const $match = icon.attr('class').match(/icon-animated-([\d\w]+)/);
            icon.removeClass($match[0]);
            $(this).off('click');
        });

        $('.nav-list .badge[title],.nav-list .label[title]').tooltip({'placement': 'right'});

        // simple settings
        $('#ace-settings-btn').on(this.click_event, function () {
            $(this).toggleClass('open');
            $('#ace-settings-box').toggleClass('open');
        });


        let check_box;
        const ace_settings_navbar = $('#ace-settings-navbar');
        ace_settings_navbar.on('click', function () {
            // self.settings.navbar_fixed(this.checked); // @ ace-extra.js
            self.settings.navbar_fixed(true); // @ ace-extra.js
        });
        check_box = ace_settings_navbar.get(0);
        if (check_box) {
            check_box.checked = this.settings.is('navbar', 'fixed');
        }

        const ace_settings_sidebar = $('#ace-settings-sidebar');
        ace_settings_sidebar.on('click', function () {
            // self.settings.sidebar_fixed(this.checked); // @ ace-extra.js
            self.settings.sidebar_fixed(true); // @ ace-extra.js
        });
        check_box = ace_settings_sidebar.get(0);
        if (check_box) {
            check_box.checked = this.settings.is('sidebar', 'fixed');
        }

        const ace_settings_breadcrumbs = $('#ace-settings-breadcrumbs');
        ace_settings_breadcrumbs.on('click', function () {
            // self.settings.breadcrumbs_fixed(this.checked); // @ ace-extra.js
            self.settings.breadcrumbs_fixed(true); // @ ace-extra.js
        });
        check_box = ace_settings_breadcrumbs.get(0);
        if (check_box) {
            check_box.checked = this.settings.is('breadcrumbs', 'fixed');
        }


        // Switching to RTL (right to left) Mode
        $('#ace-settings-rtl').removeAttr('checked').on('click', function () {
            self.switch_direction();
        });


        $('#btn-scroll-up').on(this.click_event, function () {
            const duration = Math.max(100, $('html').scrollTop() / 3);
            $('html,body').animate({scrollTop: 0}, duration);
            return false;
        });

        try {
            $('#skin-colorpicker').ace_colorpicker();
        } catch (e) {
        }

        $('#skin-colorpicker').on('change', function () {
            const skin_class = $(this).find('option:selected').data('skin');

            const body = $(document.body);
            body.removeClass('skin-1 skin-2 skin-3');


            if (skin_class !== 'default') {
                body.addClass(skin_class);
            }

            if (skin_class === 'skin-1') {
                $('.ace-nav > li.grey').addClass('dark');
            } else {
                $('.ace-nav > li.grey').removeClass('dark');
            }

            if (skin_class === 'skin-2') {
                $('.ace-nav > li').addClass('no-border margin-1');
                $('.ace-nav > li:not(:last-child)')
                    .addClass('light-pink')
                    .find('> a > [class*="icon-"]')
                    .addClass('pink')
                    .end()
                    .eq(0)
                    .find('.badge')
                    .addClass('badge-warning');
            } else {
                $('.ace-nav > li').removeClass('no-border margin-1');
                $('.ace-nav > li:not(:last-child)')
                    .removeClass('light-pink')
                    .find('> a > [class*="icon-"]')
                    .removeClass('pink')
                    .end()
                    .eq(0)
                    .find('.badge')
                    .removeClass('badge-warning');
            }

            if (skin_class === 'skin-3') {
                $('.ace-nav > li.grey').addClass('red').find('.badge').addClass('badge-yellow');
            } else {
                $('.ace-nav > li.grey').removeClass('red').find('.badge').removeClass('badge-yellow');
            }
        });

    };

    widget_boxes() {
        $('.page-content,#page-content').delegate('.widget-toolbar > [data-action]', 'click', function (ev) {
            ev.preventDefault();

            const $this = $(this);
            const $action = $this.data('action');
            const $box = $this.closest('.widget-box');

            if ($box.hasClass('ui-sortable-helper')) {
                return;
            }

            if ($action === 'collapse') {
                let $body = $box.find('.widget-body');
                const $icon = $this.find('[class*=icon-]').eq(0);
                const $match = $icon.attr('class').match(/icon-(.*)-(up|down)/);
                const $icon_down = 'icon-' + $match[1] + '-down';
                const $icon_up = 'icon-' + $match[1] + '-up';

                const $body_inner = $body.find('.widget-body-inner');
                if ($body_inner.length === 0) {
                    $body = $body.wrapInner('<div class="widget-body-inner"></div>').find(':first-child').eq(0);
                } else {
                    $body = $body_inner.eq(0);
                }

                const expandSpeed = 300;
                const collapseSpeed = 200;

                if ($box.hasClass('collapsed')) {
                    if ($icon) {
                        $icon.addClass($icon_up).removeClass($icon_down);
                    }
                    $box.removeClass('collapsed');
                    $body.slideUp(0, function () {
                        $body.slideDown(expandSpeed)
                    });
                } else {
                    if ($icon) {
                        $icon.addClass($icon_down).removeClass($icon_up);
                    }
                    $body.slideUp(collapseSpeed, function () {
                        $box.addClass('collapsed')
                    });
                }
            } else if ($action === 'close') {
                const closeSpeed = parseInt($this.data('close-speed'), 10) || 300;
                $box.hide(closeSpeed, function () {
                    $box.remove()
                });
            } else if ($action === 'reload') {
                $this.blur();

                let $remove = false;
                if ($box.css('position') === 'static') {
                    $remove = true;
                    $box.addClass('position-relative');
                }
                $box.append('<div class="widget-box-layer"><i class="icon-spinner icon-spin icon-2x white"></i></div>');
                let random_duration:number;
                random_duration = Math.random() * 1000 + 1000;
                setTimeout(function () {
                    $box.find('.widget-box-layer').remove();
                    if ($remove) {
                        $box.removeClass('position-relative');
                    }
                }, parseInt(random_duration.toFixed(0)));
            } else if ($action === 'settings') {
            }

        });
    }

    // search box's dropdown autocomplete
    enable_search_ahead() {
        this.variable_US_STATES = [
            'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California',
            'Colorado', 'Connecticut', 'Delaware', 'Florida', 'Georgia',
            'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa', 'Kansas',
            'Kentucky', 'Louisiana', 'Maine', 'Maryland', 'Massachusetts',
            'Michigan', 'Minnesota', 'Mississippi', 'Missouri', 'Montana',
            'Nebraska', 'Nevada', 'New Hampshire', 'New Jersey', 'New Mexico',
            'New York', 'North Dakota', 'North Carolina', 'Ohio', 'Oklahoma',
            'Oregon', 'Pennsylvania', 'Rhode Island', 'South Carolina',
            'South Dakota', 'Tennessee', 'Texas', 'Utah', 'Vermont',
            'Virginia', 'Washington', 'West Virginia', 'Wisconsin',
            'Wyoming'];

        // $('#nav-search-input').typeahead({
        //     source: this.variable_US_STATES,
        //     updater: function (item) {
        //         $('#nav-search-input').focus();
        //         return item;
        //     }
        // });
    };

    switch_direction() {
        const $body = $(document.body);
        $body
            .toggleClass('rtl')
            // toggle pull-right class on dropdown-menu
            .find('.dropdown-menu:not(.datepicker-dropdown,.colorpicker)').toggleClass('pull-right')
            .end()
            // swap pull-left & pull-right
            .find('.pull-right:not(.dropdown-menu,blockquote,.dropdown-submenu,.profile-skills ' +
                '.pull-right,.control-group .controls > [class*="span"]:first-child)')
            .removeClass('pull-right')
            .addClass('tmp-rtl-pull-right')
            .end()
            .find('.pull-left:not(.dropdown-submenu,.profile-skills .pull-left)').removeClass('pull-left').addClass('pull-right')
            .end()
            .find('.tmp-rtl-pull-right').removeClass('tmp-rtl-pull-right').addClass('pull-left')
            .end()

            .find('.chosen-container').toggleClass('chosen-rtl')
            .end()

            .find('.control-group .controls > [class*="span"]:first-child').toggleClass('pull-right')
            .end();

        function swap_classes(class1, class2) {
            $body
                .find('.' + class1).removeClass(class1).addClass('tmp-rtl-' + class1)
                .end()
                .find('.' + class2).removeClass(class2).addClass(class1)
                .end()
                .find('.tmp-rtl-' + class1).removeClass('tmp-rtl-' + class1).addClass(class2)
        }

        function swap_styles(style1, style2, elements) {
            elements.each(function () {
                const e = $(this);
                const tmp = e.css(style2).val()[0];
                e.css(style2, e.css(style1).val()[0]);
                e.css(style1, tmp);
            });
        }

        swap_classes('align-left', 'align-right');
        swap_classes('arrowed', 'arrowed-right');
        swap_classes('arrowed-in', 'arrowed-in-right');
        swap_classes('messagebar-item-left', 'messagebar-item-right'); // for inbox page

        // redraw the traffic pie chart on homepage with a different parameter
        const placeholder = $('#piechart-placeholder');
        if (placeholder.length > 0) {
            const pos = $(document.body).hasClass('rtl') ? 'nw' : 'ne'; // draw on north-west or north-east?
            placeholder.data('draw').call(placeholder.get(0), placeholder, placeholder.data('chart'), pos);
        }
    }

}
