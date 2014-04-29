# -*- coding: utf-8 -*-
# Stalker Pyramid a Web Base Production Asset Management System
# Copyright (C) 2009-2014 Erkan Ozgur Yilmaz
#
# This file is part of Stalker Pyramid.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA

import os
import time
import logging
import datetime
import re
import transaction

from pyramid.response import Response
from pyramid.view import view_config
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message, Attachment

from stalker.db import DBSession
from stalker import User, Ticket, Project, Note, Type, Task

from stalker_pyramid.views import (get_logged_in_user, PermissionChecker,
                                   dummy_email_address, local_to_utc,
                                   get_multi_integer)
from stalker_pyramid.views.link import (replace_img_data_with_links,
                                        MediaManager)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@view_config(
    route_name='get_ticket_resolutions',
    renderer='json'
)
def get_ticket_resolutions(request):
    """returns the ticket resolutions defined in the system
    """
    from stalker import defaults
    return defaults.ticket_resolutions


@view_config(
    route_name='get_ticket_workflow',
    renderer='json'
)
def get_ticket_workflow(request):
    """returns the ticket workflow defined in the config
    """
    from stalker import defaults
    return defaults.ticket_workflow


@view_config(
    route_name='create_ticket_dialog',
    renderer='templates/ticket/dialog/ticket_dialog.jinja2',
)
def create_ticket_dialog(request):
    """creates a create_ticket_dialog by using the given task
    """
    logged_in_user = get_logged_in_user(request)

    project_id = request.params.get('project_id', -1)
    project = Project.query.filter(Project.id == project_id).first()

    task_id = request.params.get('task_id', -1)
    owner_id= request.params.get('owner_id', -1)

    if not project:
        return Response('No project found with id: %s' % project_id, 500)

    return {
        'mode': 'create',
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'task_id': task_id,
        'owner_id':owner_id,
        'project': project,
        'ticket_types':
            Type.query.filter_by(target_entity_type='Ticket').all(),
        'ticket_priorities': [
            "TRIVIAL",
            "MINOR",
            "MAJOR",
            "CRITICAL",
            "BLOCKER"
        ]
    }


@view_config(
    route_name='create_ticket'
)
def create_ticket(request):
    """runs when creating a ticket
    """
    logged_in_user = get_logged_in_user(request)

    #**************************************************************************
    # collect data

    description = request.params.get('description')
    summary = request.params.get('summary')

    project_id = request.params.get('project_id', None)
    project = Project.query.filter(Project.id == project_id).first()

    owner_id = request.params.get('owner_id', None)
    owner = User.query.filter(User.id == owner_id).first()

    priority = request.params.get('priority', "TRIVIAL")
    type_name = request.params.get('type')

    send_email = request.params.get('send_email', 1)  # for testing purposes

    logger.debug('*******************************')

    logger.debug('create_ticket is running')

    logger.debug('project_id : %s' % project_id)
    logger.debug('owner_id : %s' % owner_id)
    logger.debug('owner: %s' % owner)

    if not summary:
        return Response('Please supply a summary', 500)

    if not description:
        return Response('Please supply a description', 500)

    if not type_name:
        return Response('Please supply a type for this ticket', 500)

    type_ = Type.query.filter_by(name=type_name).first()

    if not project:
        return Response('There is no project with id: %s' % project_id, 500)

    if owner_id:
        if not owner:
            # there is an owner id but no resource found
            return Response('There is no user with id: %s' % owner_id, 500)
    else:
        return Response('Please supply an owner for this ticket', 500)

    link_ids = get_multi_integer(request, 'link_ids')
    links = Task.query.filter(Task.id.in_(link_ids)).all()

    # we are ready to create the time log
    # Ticket should handle the extension of the effort
    utc_now = local_to_utc(datetime.datetime.now())
    ticket = Ticket(
        project=project,
        summary=summary,
        description=description,
        priority=priority,
        type=type_,
        created_by=logged_in_user,
        date_created=utc_now,
        date_updated=utc_now
    )
    ticket.links = links
    ticket.set_owner(owner)

    # email the ticket to the owner and to the created by
    if send_email:
        # send email to responsible and resources of the task
        mailer = get_mailer(request)

        recipients = [logged_in_user.email, owner.email]

        # append link resources
        for link in links:
            for resource in link.resources:
                recipients.append(resource.email)

        # make recipients unique
        recipients = list(set(recipients))

        description_text = \
            'A New Ticket for project "%s" has been created by %s with the ' \
            'following description:\n\n%s' % (
                project.name, logged_in_user.name, description
            )

        # TODO: add project link, after the server can be reached outside
        description_html = \
            'A <strong>New Ticket</strong> for project <strong>%s</strong> ' \
            'has been created by <strong>%s</strong> and assigned to ' \
            '<strong>%s</strong> with the following description:<br><br>%s' % (
                project.name, logged_in_user.name, owner.name,
                description.replace('\n', '<br>')
            )

        message = Message(
            subject='New Ticket: %s' % summary,
            sender=dummy_email_address,
            recipients=recipients,
            body=description_text,
            html=description_html
        )
        mailer.send(message)

    DBSession.add(ticket)

    return Response('Ticket Created successfully')


@view_config(
    route_name='update_ticket',
)
def update_ticket(request):
    """runs when updating a ticket
    """
    logged_in_user = get_logged_in_user(request)

    ticket_id = request.matchdict.get('id', -1)
    ticket = Ticket.query.filter_by(id=ticket_id).first()

    #**************************************************************************
    # collect data
    comment = request.params.get('comment')
    comment_as_text = request.params.get('comment_as_text')
    action = request.params.get('action')

    logger.debug('updating ticket')
    if not ticket:
        transaction.abort()
        return Response('No ticket with id : %s' % ticket_id, 500)

    utc_now = local_to_utc(datetime.datetime.now())
    ticket_log = None

    if not action.startswith('leave_as'):
        if logged_in_user == ticket.owner or \
           logged_in_user == ticket.created_by:
            if action.startswith('resolve_as'):
                resolution = action.split(':')[1]
                ticket_log = ticket.resolve(logged_in_user, resolution)
            elif action.startswith('set_owner'):
                user_id = int(action.split(':')[1])
                assign_to = User.query.get(user_id)
                ticket_log = ticket.reassign(logged_in_user, assign_to)
            elif action.startswith('delete_resolution'):
                ticket_log = ticket.reopen(logged_in_user)
            ticket.date_updated = utc_now
            if ticket_log:
                ticket_log.date_created = utc_now
                ticket_log.date_updated = utc_now
        else:
            transaction.abort()
            return Response(
                'Error: You are not the owner nor the creator of this ticket'
                '\n\nSo, you do not have permission to update the ticket', 500
            )

    # mail
    recipients = [
        logged_in_user.email,
        ticket.created_by.email,
        ticket.owner.email
    ]

    # mail the comment to anybody related to the ticket
    if comment:
        # convert images to Links
        attachments = []
        comment, links = replace_img_data_with_links(comment)
        if links:
            # update created_by attributes of links
            for link in links:
                link.created_by = logged_in_user

                # manage attachments
                link_full_path = MediaManager.convert_file_link_to_full_path(link.full_path)
                link_data = open(link_full_path, "rb").read()

                link_extension = os.path.splitext(link.filename)[1].lower()
                mime_type = ''
                if link_extension in ['.jpeg', '.jpg']:
                    mime_type = 'image/jpg'
                elif link_extension in ['.png']:
                    mime_type = 'image/png'

                attachment = Attachment(
                    link.filename,
                    mime_type,
                    link_data
                )
                attachments.append(attachment)
            DBSession.add_all(links)

        note = Note(
            content=comment,
            created_by=logged_in_user,
            date_created=utc_now
        )
        ticket.comments.append(note)
        DBSession.add(note)

        # send email to the owner about the new comment
        mailer = get_mailer(request)

        # also inform ticket commenter
        for t_comment in ticket.comments:
            recipients.append(t_comment.created_by.email)

        message_body_text = "%(who)s has added a the following comment to " \
                            "%(ticket)s:\n\n%(comment)s"

        message_body_html = "<div>%(who)s has added a the following comment " \
                            "to %(ticket)s:<br><br>%(comment)s</div>"

        message_body_text = message_body_text % {
            'who': logged_in_user.name,
            'ticket': "Ticket #%s" % ticket.number,
            'comment': comment_as_text
        }

        message_body_html = message_body_html % {
            'who': '<a href="%(link)s">%(name)s</a>' % {
                'link': request.route_url('view_user', id=logged_in_user.id),
                'name': logged_in_user.name
            },
            'ticket': '<a href="%(link)s">%(name)s</a>' % {
                'link': request.route_url('view_ticket', id=ticket.id),
                'name': "Ticket #%(number)s - %(summary)s" % {
                    'number': ticket.number,
                    'summary': ticket.summary
                }
            },
            'comment': re.sub(
                r'/SPL/[a-z0-9]+/[a-z0-9]+/',
                'cid:',
                comment
            )
        }

        # make recipients unique
        recipients = list(set(recipients))
        message = Message(
            subject="Stalker Pyramid: New comment on Ticket #%s" %
                    ticket.number,
            sender=dummy_email_address,
            recipients=recipients,
            body=message_body_text,
            html=message_body_html,
            attachments=attachments
        )
        mailer.send(message)

    # mail about changes in ticket status
    if ticket_log:
        from stalker import TicketLog

        assert isinstance(ticket_log, TicketLog)
        mailer = get_mailer(request)

        # just inform anybody in the previously created recipients list

        message_body_text = \
            '%(user)s has changed the status of %(ticket)s\n\n' \
            'from "%(from)s" to "%(to)s"'

        message_body_html = \
            '<div>%(user)s has changed the status of ' \
            '%(ticket)s:<br><br>from %(from)s to %(to)s</div>'

        message_body_text = message_body_text % {
            'user': ticket_log.created_by.name,
            'ticket': "Ticket #%s" % ticket.number,
            'from': ticket_log.from_status.name,
            'to': ticket_log.to_status.name
        }

        message_body_html = message_body_html % {
            'user': '<strong>%(name)s</strong>' % {
                'name': ticket_log.created_by.name
            },
            'ticket': "<strong>Ticket #%(number)s - %(summary)s</strong>" % {
                'number': ticket.number,
                'summary': ticket.summary
            },
            'from': '<strong>%s</strong>' % ticket_log.from_status.name,
            'to': '<strong>%s</strong>' % ticket_log.to_status.name
        }

        message = Message(
            subject="Stalker Pyramid: Status Update on "
                    "Ticket #%(ticket_number)s - %(ticket_summary)s" % {
                        'ticket_number': ticket.number,
                        'ticket_summary': ticket.summary
                    },
            sender=dummy_email_address,
            recipients=recipients,
            body=message_body_text,
            html=message_body_html
        )
        mailer.send(message)

    logger.debug('successfully updated ticket')

    request.session.flash('Success: Successfully updated ticket')
    return Response('Successfully updated ticket')


@view_config(
    route_name='get_tickets',
    renderer='json'
)
@view_config(
    route_name='get_task_tickets',
    renderer='json'
)
@view_config(
    route_name='get_project_tickets',
    renderer='json'
)
@view_config(
    route_name='get_entity_tickets',
    renderer='json'
)
@view_config(
    route_name='get_user_tickets',
    renderer='json'
)
def get_tickets(request):
    """returns all the tickets related to an entity or not
    """
    entity_id = request.matchdict.get('id')
    #entity = Entity.query.filter_by(id=entity_id).first()

    entity_type = None
    if entity_id:
        # get the entity type
        sql_query = \
            'select entity_type from "SimpleEntities" where id=%s' % entity_id
        data = DBSession.connection().execute(sql_query).fetchone()
        entity_type = data[0] if data else None

    logger.debug('entity_id  : %s' % entity_id)
    logger.debug('entity_type: %s' % entity_type)

    sql_query = """select
        "SimpleEntities_Ticket".id,
        "SimpleEntities_Ticket".name,
        "Tickets".number,
        "Tickets".summary,
        "Tickets".project_id,
        "SimpleEntities_Project".name as project_name,
        "Tickets".owner_id as owner_id,
        "SimpleEntities_Owner".name as owner_name,
        extract(epoch from "SimpleEntities_Ticket".date_created::timestamp AT TIME ZONE 'UTC') * 1000 as date_created,
        extract(epoch from "SimpleEntities_Ticket".date_updated::timestamp AT TIME ZONE 'UTC') * 1000 as date_updated,
        "SimpleEntities_Ticket".created_by_id,
        "SimpleEntities_CreatedBy".name as created_by_name,
        "SimpleEntities_Ticket".updated_by_id,
        "SimpleEntities_UpdatedBy".name as updated_by_name,
        "SimpleEntities_Status".name as status_name,
        "Tickets".priority,
        "SimpleEntities_Type".name as type_name
    from "Tickets"
    join "SimpleEntities" as "SimpleEntities_Ticket" on "Tickets".id = "SimpleEntities_Ticket".id
    join "SimpleEntities" as "SimpleEntities_Project" on "Tickets".project_id = "SimpleEntities_Project".id
    left outer join "SimpleEntities" as "SimpleEntities_Owner" on "Tickets".owner_id = "SimpleEntities_Owner".id
    left outer join "SimpleEntities" as "SimpleEntities_CreatedBy" on "SimpleEntities_Ticket".created_by_id = "SimpleEntities_CreatedBy".id
    left outer join "SimpleEntities" as "SimpleEntities_UpdatedBy" on "SimpleEntities_Ticket".updated_by_id = "SimpleEntities_UpdatedBy".id
    join "SimpleEntities" as "SimpleEntities_Status" on "Tickets".status_id = "SimpleEntities_Status".id
    left outer join "SimpleEntities" as "SimpleEntities_Type" on "SimpleEntities_Ticket".type_id = "SimpleEntities_Type".id
    """

    if entity_type:
        if entity_type == u"Project":
            sql_query += """where "Tickets".project_id = %s""" % entity_id
        elif entity_type == u"User":
            sql_query += """where "Tickets".owner_id = %s""" % entity_id
        else:
            sql_query += \
                """join "Ticket_SimpleEntities" on
                    "Tickets".id = "Ticket_SimpleEntities".ticket_id
                where "Ticket_SimpleEntities".simple_entity_id = %s
                """ % entity_id
    sql_query += 'order by "Tickets".number'

    start = time.time()
    result = DBSession.connection().execute(sql_query)
    data = [
        {
            'id': r[0],
            'name': r[1],
            'number': r[2],
            'summary': r[3],
            'project_id': r[4],
            'project_name': r[5],
            'owner_id': r[6],
            'owner_name': r[7],
            'date_created': r[8],
            'date_updated': r[9],
            'created_by_id': r[10],
            'created_by_name': r[11],
            'updated_by_id': r[12],
            'updated_by_name': r[13],
            'status': r[14],
            'priority': r[15],
            'type': r[16]
        } for r in result.fetchall()
    ]
    end = time.time()
    logger.debug(
        'get_entity_tickets took : %s seconds for %s rows' %
        (end - start, len(data))
    )
    return data


@view_config(
    route_name='get_user_open_tickets',
    renderer='json'
)
def get_user_open_tickets(request):
    user_id = request.matchdict.get('id')
    user = User.query.filter_by(id=user_id).first()

    open_tickets = []

    for ticket in user.open_tickets:
        open_tickets.append(
            {
                'id': ticket.id,
                'summary': ticket.summary,
                'created_by_name': ticket.created_by.name,
                'created_by_thumbnail': ticket.created_by.thumbnail.full_path
                    if ticket.created_by.thumbnail else None,
                'date_updated': ''

            }
        )

    return open_tickets
