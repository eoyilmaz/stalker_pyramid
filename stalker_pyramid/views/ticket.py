# -*- coding: utf-8 -*-
# Stalker Pyramid a Web Base Production Asset Management System
# Copyright (C) 2009-2013 Erkan Ozgur Yilmaz
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

import time
import logging

from pyramid.httpexceptions import HTTPOk
from pyramid.response import Response
from pyramid.url import resource_url
from pyramid.view import view_config
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message

from stalker import User, Ticket, Entity, Project, Status, Note

from stalker.db import DBSession
from stalker_pyramid.views import (get_logged_in_user, PermissionChecker,
                                   milliseconds_since_epoch,
                                   dummy_email_address)

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
    route_name='dialog_create_ticket',
    renderer='templates/ticket/dialog_create_ticket.jinja2',
)
def create_ticket_dialog(request):
    """creates a create_ticket_dialog by using the given task
    """
    logged_in_user = get_logged_in_user(request)

    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter(Entity.entity_id==entity_id).first()

    # TODO: remove 'mode': 'CREATE' by considering it the default mode

    return {
        'mode': 'create',
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'entity': entity,
        'milliseconds_since_epoch': milliseconds_since_epoch
    }


@view_config(
    route_name='dialog_update_ticket',
    renderer='templates/ticket/dialog_create_ticket.jinja2',
)
def update_ticket_dialog(request):
    """updates a create_ticket_dialog by using the given task
    """
    logger.debug('inside updates_ticket_dialog')

    # get logged in user
    logged_in_user = get_logged_in_user(request)

    ticket_id = request.matchdict.get('id', -1)
    ticket = Ticket.query.filter_by(id=ticket_id).first()

    return {
        'mode': 'UPDATE',
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'ticket': ticket,
        'entity': ticket.project,
        'milliseconds_since_epoch': milliseconds_since_epoch
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
    project = Project.query.filter(Project.id==project_id).first()

    owner_id = request.params.get('owner_id', None)
    owner = User.query.filter(User.id==owner_id).first()

    status_id = request.params.get('status_id')
    status = Status.query.filter_by(id=status_id).first()

    logger.debug('*******************************')

    logger.debug('create_ticket is running')

    logger.debug('project_id : %s' % project_id)
    logger.debug('owner_id : %s' % owner_id)
    logger.debug('owner: %s' % owner)

    if description and project and owner:
        # we are ready to create the time log
        # Ticket should handle the extension of the effort
        ticket = Ticket(
            status=status,
            summary=summary,
            description=description,
            project=project,
            created_by=logged_in_user,
        )
        ticket.set_owner(owner)

        DBSession.add(ticket)

    return HTTPOk()


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
        return Response('No ticket with id : %s' % ticket_id, 500)

    if not action.startswith('leave_as'):
        if logged_in_user == ticket.owner or \
           logged_in_user == ticket.created_by:
            if action.startswith('resolve_as'):
                resolution = action.split(':')[1]
                ticket.resolve(logged_in_user, resolution)
            elif action.startswith('set_owner'):
                user_id = int(action.split(':')[1])
                assign_to = User.query.get(user_id)
                ticket.reassign(logged_in_user, assign_to)
                # send mail to the new owner
            elif action.startswith('delete_resolution'):
                ticket.reopen(logged_in_user)
        else:
            request.session.flash(
                'Error: You do not have permission to update the ticket'
            )

    if comment:
        note = Note(
            content=comment,
            created_by=logged_in_user,
        )
        ticket.comments.append(note)
        DBSession.add(note)

        # send email to the owner about the new comment
        mailer = get_mailer(request)

        recipients = [logged_in_user.email]
        if ticket.created_by.email not in recipients:
            recipients.append(ticket.created_by.email)

        message_body = "%(who)s has added a the following comment to " \
            "#%(ticket)s:\n\n%(comment)s"

        message_body_text = message_body % \
            {
                'who': logged_in_user.name,
                'ticket': "Ticket #%s" % ticket.number,
                'comment': comment_as_text
            }

        message_body_html = message_body % \
            {
                'who': '<a href="%(link)s">%(name)s</a>' % {
                    'link': request.route_url('view_user',
                                              id=logged_in_user.id),
                    'name': logged_in_user.name
                },
                'ticket': '<a href="%(link)s">%(name)s</a>' % {
                    'link': request.route_url('view_ticket', id=ticket.id),
                    'name': "Ticket #%s" % ticket.number
                },
                'comment': comment_as_text
            }

        message = Message(
            subject="Stalker Pyramid: New comment on Ticket #%s" %
                    ticket.number,
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
        "SimpleEntities_Ticket".date_created,
        "SimpleEntities_Ticket".date_updated,
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
            'date_created' : milliseconds_since_epoch(r[8]),
            'date_updated' : milliseconds_since_epoch(r[9]),
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
    logger.debug('get_entity_tickets took : %s seconds for %s rows' % (end - start, len(data)))
    return data
