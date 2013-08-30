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

import logging

from pyramid.httpexceptions import HTTPOk
from pyramid.view import view_config
from sqlalchemy.orm import aliased

from stalker import User, Ticket, Entity, Project, Status, SimpleEntity, Task

from stalker.db import DBSession
from stalker_pyramid.views import (get_logged_in_user, PermissionChecker,
                                   milliseconds_since_epoch)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@view_config(
    route_name='dialog_create_ticket',
    renderer='templates/ticket/dialog_create_ticket.jinja2',
)
def create_ticket_dialog(request):
    """creates a create_ticket_dialog by using the given task
    """
    logged_in_user = get_logged_in_user(request)
    if not logged_in_user:
        import auth
        return auth.logout(request)

    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter(Entity.entity_id==entity_id).first()

    # TODO: remove 'mode': 'CREATE' by considering it the default mode

    return {
        'mode': 'CREATE',
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
    if not logged_in_user:
        import auth
        return auth.logout(request)

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
    if not logged_in_user:
        import auth
        return auth.logout(request)

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
            status = status,
            summary=summary,
            description=description,
            project=project,
            created_by=logged_in_user,
        )
        ticket.set_owner(owner)

        DBSession.add(ticket)

    return HTTPOk()


@view_config(
    route_name='update_ticket'
)
def update_ticket(request):
    """runs when updating a ticket
    """
    logged_in_user = get_logged_in_user(request)
    if not logged_in_user:
        import auth
        return auth.logout(request)

    ticket_id = request.matchdict.get('id', -1)
    ticket = Ticket.query.filter_by(id=ticket_id).first()

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
    logger.debug('update_ticket is running')
    logger.debug('ticket: %s' % ticket)
    logger.debug('project_id : %s' % project_id)
    logger.debug('owner_id : %s' % owner_id)
    logger.debug('owner: %s' % owner)
    logger.debug('project: %s' % project)
    logger.debug('summary: %s' % summary)
    logger.debug('description: %s' % description)

    if ticket and description and project and owner:
        logger.debug('updating ticket')
        # we are ready to create the time log
        # Ticket should handle the extension of the effort
        ticket.summary = summary
        ticket.description = description
        ticket.status = status
        if ticket.owner != owner:
            ticket.set_owner(owner)
        ticket.updated_by = logged_in_user

        DBSession.add(ticket)
        logger.debug('successfully updated ticket')

    logger.debug('returning from update_ticket')

    return HTTPOk()

@view_config(
    route_name='view_ticket',
    renderer='templates/ticket/page_view_ticket.jinja2'
)
def view_ticket(request):
    """runs when viewing an ticket
    """
    logged_in_user = get_logged_in_user(request)
    if not logged_in_user:
        import auth
        return auth.logout(request)

    ticket_id = request.matchdict.get('id', -1)
    ticket = Ticket.query.filter_by(id=ticket_id).first()

    return {
        'user': logged_in_user,
        'has_permission': PermissionChecker(request),
        'ticket': ticket
    }


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
    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    tickets = []
    if entity:
        if isinstance(entity, User):
            # return user tickets
            logger.debug('getting user tickets')
            tickets = Ticket.query.\
                filter(Ticket.owner_id==entity_id).\
                order_by(Ticket.number.asc()).all()
        elif isinstance(entity, Project):
            # return project tickets
            logger.debug('getting project tickets')
            tickets = Ticket.query.\
                filter(Ticket.project_id==entity_id).\
                order_by(Ticket.number.asc()).\
                all()
        else:
            logger.debug('getting entity linked tickets')
            # query all the tickets where the Ticket.links collection has the entity
            simpleEntity_alias = aliased(SimpleEntity)
            tickets = Ticket.query.join(simpleEntity_alias, Ticket.links).\
                filter(SimpleEntity.id==entity_id).\
                order_by(Ticket.number.asc()).all()
    else:
        tickets = Ticket.query.all()

    return [
        {
            'id': ticket.id,
            'name': ticket.name,
            'number': ticket.number,
            'summary': ticket.summary,
            'project_id': ticket.project_id,
            'project_name': ticket.project.name,
            'owner_id': ticket.owner_id if ticket.owner else -1,
            'owner_name': ticket.owner.name if ticket.owner else '',
            'created_by_id': ticket.created_by_id,
            'created_by_name': ticket.created_by.name,
            'updated_by_id': ticket.updated_by_id,
            'updated_by_name': ticket.updated_by.name,
            'status': ticket.status.name
        } for ticket in tickets
    ]
