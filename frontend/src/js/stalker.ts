import * as $ from 'jquery';
import * as jQuery from 'jquery';
import {drawCalendar} from "./calendar";
import {template} from "dot";

import "./date_stalker";


interface StalkerBase {

    update_open_ticket_count(logged_in_user_id: Number, notification_url: string);

    update_user_tasks_count(logged_in_user_id: Number);

    // Do Playblast
    do_playblast(version_id: Number);

    // Export Alembics
    export_alembics(version_id: Number);

    // copyToClipboard
    copyToClipboard(text: String);

    // drawCalendar
    drawCalendar(cid: String, events: []);
}


export class Stalker implements StalkerBase {

    update_open_ticket_count = function (logged_in_user_id: Number, notification_url: string) {
        jQuery.getJSON('/users/' + logged_in_user_id + '/open_tickets/').then(function (data) {
            jQuery(function () {
                let notifications = $('#notifications');
                let total_tickets = data.length;

                if (total_tickets === 0) {
                    notifications.append('<a data-toggle="dropdown" class="dropdown-toggle" href="#"><i class="icon-bell-alt icon-bell light-grey"></i><span class="badge badge-important">0</span></a>');
                } else {
                    notifications.append('<a data-toggle="dropdown" class="dropdown-toggle" href="#"><i class="icon-bell-alt icon-animated-bell"></i><span class="badge badge-important">' + total_tickets + '</span></a>');
                }

                notifications.append('<ul class="pull-right dropdown-navbar dropdown-menu dropdown-caret dropdown-closer"></ul>');

                let row_template = template($('#tmpl_notificationRow').html());

                let notifications_list = notifications.find('ul');
                notifications_list.append('<li class="nav-header"><i class="icon-warning-sign"></i>' + total_tickets + ' Open Tickets</li>');

                let limit = Math.min(5, total_tickets);
                for (let i = 0; i < limit; i++) {
                    notifications_list.append(row_template(data[i]));
                }

                notifications_list.append('<li><a href="' + notification_url + '">See all tickets<i class="icon-arrow-right"></i></a></li>');
            });
        });

        jQuery.getJSON('/users/' + logged_in_user_id + '/tasks/count/').then(function (data) {
            $(function () {
                $('#nav_bar_task_count').text(data);
            })
        });
    };

    update_user_tasks_count = function (logged_in_user_id: Number) {
        jQuery.getJSON('/users/' + logged_in_user_id + '/tasks/count/').then(function (data) {
            $(function () {
                $('#nav_bar_task_count').text(data);
            })
        });
    };

    // Do Playblast
    do_playblast = function (version_id) {
        let result = window.confirm("Do Playblast?:" + version_id);
        if (result === true) {
            $.post("/versions/" + version_id + "/do_playblast").done(function () {
                const message = '<div>Job created! Check Afanasy</div>';
                window.bootbox.alert(message);
                $('.bootbox').prepend('<div class="modal-header alert-success"><strong>Success</strong></div>');
            }).fail(function (jqXHR) {
                const message = '<div>' + jqXHR.responseText + '</div>';
                window.bootbox.alert(message);
                $('.bootbox').prepend('<div class="modal-header alert-danger"><strong>Fail</strong></div>');
            });
        }
    };

    // Export Alembics
    export_alembics = function (version_id) {
        let result = window.confirm("Export Alembics?" + version_id);
        if (result === true) {
            $.post("/versions/" + version_id + "/export_alembics").done(function () {
                let message = '<div>Job created! Check Afanasy</div>';
                window.bootbox.alert(message);
                $('.bootbox').prepend('<div class="modal-header alert-success"><strong>Success</strong></div>');
            }).fail(function (jqXHR) {
                let message = '<div>' + jqXHR.responseText + '</div>';
                window.bootbox.alert(message);
                $('.bootbox').prepend('<div class="modal-header alert-danger"><strong>Fail</strong></div>');
            });
        }
    };

    // copyToClipboard
    copyToClipboard = function (text) {
        window.prompt('Copy to clipboard: Ctrl+C, Enter', text);
    };

    drawCalendar = drawCalendar;
}

export default Stalker;
