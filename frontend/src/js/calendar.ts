

import * as jQuery from "jquery";
import "bootstrap";
import { Calendar } from '@fullcalendar/core';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import listPlugin from '@fullcalendar/list';
import interactionPlugin from '@fullcalendar/interaction';


export function drawCalendar(cid, events) {

    console.debug("Code is here A1");

    let update_event_action = function (event_type, event_id) {
        let event_dialog = jQuery('#dialog_template');
        event_dialog.modal({
            'remote': "/" + event_type + "/" + event_id + "/update/dialog?came_from={{ request.current_route_path() }}"
        });
    };
    console.debug("Code is here A2");

    let create_event_action = function (start, end, allDay, entity_id, event_type) {
        let event_dialog = jQuery('#dialog_template');

        event_dialog.attr('start', start);
        event_dialog.attr('end', end);
        event_dialog.attr('allDay', allDay);

        event_dialog.modal({
            'remote': "/entities/" + entity_id + "/" + event_type +"s/create/dialog?came_from={{ request.current_route_path() }}"
        });
    };
    console.debug("Code is here A3");

    /* initialize the calendar
    -----------------------------------------------------------------*/
    let calendarEl = document.getElementById(cid);
    console.debug("Code is here A4");
    let calendar = new Calendar(calendarEl, {
        // {% if event_type %}
        //     {% if has_permission('Create_' + event_type) %}
        //         select: function (start, end, allDay) {
        //             {% if  event_type=='TimeLog' %}
        //                 var now = new Date();
        //                 if(now > end){
        //                     create_event_action(start, end, allDay, '{{ entity.id }}', '{{ event_type.lower() }}')
        //                 }
        //             {% else %}
        //                     create_event_action(start, end, allDay, '{{ entity.id }}', '{{ event_type.lower() }}')
        //             {% endif %}
        //             this.unselect();
        //         },
        //     {% endif %}
        // {% endif %}

        // eventClick: function ({el, event, jsEvent, view}){
        //     jsEvent.preventDefault();
        //     jsEvent.stopPropagation();
        //
        //     if (event.extendedProps.entity_type === 'vacations') {
        //         jQuery.getJSON("/has_permission?permission=Update_Vacation").then(function (permission) {
        //             if(permission === 1) {
        //                 if (event.title === 'StudioWide') {
        //                     jQuery.getJSON("/has_permission?permission=Update_Studio").then(function (permission_inner) {
        //                         if(permission_inner === 1) {
        //                             update_event_action(event.extendedProps.entity_type, event.id);
        //                         }
        //                     });
        //                 } else {
        //                     update_event_action(event.extendedProps.entity_type, event.id);
        //                 }
        //             }
        //         });
        //     } else if (event.extendedProps.entity_type === 'timelogs') {
        //         jQuery.getJSON("/has_permission?permission=Update_TimeLog").then(function (permission) {
        //             if (permission === 1){
        //                 update_event_action(event.extendedProps.entity_type, event.id);
        //             }
        //         });
        //     } else if (event.extendedProps.entity_type === 'tasks') {
        //         if(jsEvent.button === 0) {
        //             window.location.assign("/tasks/" + event.id + "/view");
        //         } else if (jsEvent.button === 1) {
        //             window.open("/tasks/" + event.id + "/view", '_blank');
        //         }
        //     }
        // },
        //
        // eventMouseEnter: function({el, event, jsEvent, view}){
        //     // add title attribute to each event
        //     setTimeout(function(){
        //         jQuery(jsEvent.target).find('.fc-event-title').each(function(){
        //             let self = jQuery(this);
        //             self.attr('title', self.text());
        //         });
        //     }, 0);
        // },
        //
        // buttonText: {
        //     prev: '<i class="icon-chevron-left"></i>',
        //     next: '<i class="icon-chevron-right"></i>'
        // },
        //
        // header: {
        //     left: 'prev,next today',
        //     center: 'title',
        //     right: 'month,agendaWeek,agendaDay'
        // },
        // events: events,
        // editable: true,
        // droppable: false, // this allows things to be dropped onto the calendar !!!
        //
        // selectable: true,
        // // selectHelper: true,
        // firstDay: 1,
        //
        // eventTimeFormat: "H:mm {- H:mm}",
    });
    console.debug("Code is here A5")

    console.debug("calendar: ", calendar);

}