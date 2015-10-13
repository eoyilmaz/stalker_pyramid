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


import datetime
from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config

from stalker import db, Client, Status, Client, Studio, User, Role, ClientUser
from stalker.db import DBSession

import transaction

from webob import Response
from stalker_pyramid.views import (get_logged_in_user, logger,
                                   PermissionChecker, milliseconds_since_epoch,
                                   local_to_utc)
from stalker_pyramid.views.role import query_role

from stalker_pyramid.views.task import generate_recursive_task_query
from stalker_pyramid.views.type import query_type

@view_config(
    route_name='create_client'
)
def create_client(request):
    """called when adding a new client
    """
    logged_in_user = get_logged_in_user(request)
    utc_now = local_to_utc(datetime.datetime.now())

    came_from = request.params.get('came_from', '/')

    # parameters
    name = request.params.get('name')
    description = request.params.get('description')

    logger.debug('create_client          :')

    logger.debug('name          : %s' % name)
    logger.debug('description   : %s' % description)

    if name and description:

        try:
            new_client = Client(
                name=name,
                description=description,
                created_by=logged_in_user,
                date_created=utc_now,
                date_updated=utc_now
            )

            DBSession.add(new_client)
            # flash success message
            request.session.flash(
                'success:Client <strong>%s</strong> is created '
                'successfully' % name
            )
        except BaseException as e:
            request.session.flash('error: %s' % e)
            HTTPFound(location=came_from)

    else:
        transaction.abort()
        return Response('There are missing parameters', 500)

    return Response(
        'success:Client with name <strong>%s</strong> is created.'
        % name
    )

@view_config(
    route_name='update_client'
)
def update_client(request):
    """called when updating a client
    """
    logged_in_user = get_logged_in_user(request)
    utc_now = local_to_utc(datetime.datetime.now())

    client_id = request.matchdict.get('id', -1)
    client = Client.query.filter_by(id=client_id).first()
    if not client:
        transaction.abort()
        return Response('Can not find a client with id: %s' % client_id, 500)


    # parameters
    name = request.params.get('name')
    description = request.params.get('description')

    logger.debug('create_client          :')

    logger.debug('name          : %s' % name)
    logger.debug('description   : %s' % description)

    if name and description:
        client.name = name
        client.description = description
        client.updated_by = logged_in_user
        client.date_updated = utc_now

        DBSession.add(client)

    else:
        transaction.abort()
        return Response('There are missing parameters', 500)

    request.session.flash(
        'success:Client <strong>%s</strong> is updated '
        'successfully' % name
    )

    return Response(
        'success:Client with name <strong>%s</strong> is updated.'
        % name
    )


@view_config(
    route_name='get_clients',
    renderer='json'
)
@view_config(
    route_name='get_studio_clients',
    renderer='json'
)
def get_studio_clients(request):
    """returns client with the given id
    """

    logger.debug('get_studio_clients is working for the studio')

    sql_query = """
         select
            "Clients".id,
            "Client_SimpleEntities".name,
            "Client_SimpleEntities".description,
            "Thumbnail_Links".full_path,
            projects.project_count
        from "Clients"
        join "SimpleEntities" as "Client_SimpleEntities" on "Client_SimpleEntities".id = "Clients".id
        left outer join "Links" as "Thumbnail_Links" on "Client_SimpleEntities".thumbnail_id = "Thumbnail_Links".id
        left outer join  (
            select "Projects".client_id as client_id,
                    count("Projects".id) as project_count
                from "Projects"
                group by "Projects".client_id)as projects on projects.client_id = "Clients".id
    """

    clients = []

    result = db.DBSession.connection().execute(sql_query)
    update_client_permission = \
        PermissionChecker(request)('Update_Client')

    for r in result.fetchall():
        client = {
            'id': r[0],
            'name': r[1],
            'description': r[2],
            'thumbnail_full_path': r[3],
            'projectsCount': r[4] if r[4] else 0
        }
        if update_client_permission:
            client['item_update_link'] = \
                '/clients/%s/update/dialog' % client['id']
            client['item_remove_link'] =\
                '/clients/%s/delete/dialog?came_from=%s' % (
                    client['id'],
                    request.current_route_path()
                )

        clients.append(client)

    resp = Response(
        json_body=clients
    )

    return resp


@view_config(
    route_name='append_user_to_client_dialog',
    renderer='templates/client/dialog/append_user_to_client_dialog.jinja2'
)
def append_user_to_client_dialog(request):
    """called when appending user to client
#     """

    logged_in_user = get_logged_in_user(request)
    came_from = request.params.get('came_from', '/')

    client_id = request.matchdict.get('id', -1)
    client = Client.query.filter(Client.id == client_id).first()
    if not client:
        transaction.abort()
        return Response('Can not find a client with id: %s' % client_id, 500)

    return {
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'client': client,
        'came_from':came_from,
        'milliseconds_since_epoch': milliseconds_since_epoch
    }


@view_config(
    route_name='get_client_users_out_stack',
    renderer='json'
)
def get_client_users_out_stack(request):

    logger.debug('get_client_users_out_stack is running')

    client_id = request.matchdict.get('id', -1)
    client = Client.query.filter_by(id=client_id).first()
    if not client:
        transaction.abort()
        return Response('Can not find a client with id: %s' % client_id, 500)

    sql_query = """
            select
                "User_SimpleEntities".name,
                "User_SimpleEntities".id
            from "Users"
            left outer join "Client_Users" on "Client_Users".uid = "Users".id
            join "SimpleEntities" as "User_SimpleEntities" on "User_SimpleEntities".id = "Users".id

            where "Client_Users".cid != %(client_id)s or "Client_Users".cid is Null
    """

    sql_query = sql_query % {'client_id': client_id}
    result = db.DBSession.connection().execute(sql_query)

    users = []
    for r in result.fetchall():
        user = {
            'name': r[0],
            'id': r[1]
        }
        users.append(user)

    resp = Response(
        json_body=users
    )

    return resp


@view_config(
    route_name='append_user_to_client'
)
def append_user_to_client(request):

    logged_in_user = get_logged_in_user(request)
    utc_now = local_to_utc(datetime.datetime.now())

    came_from = request.params.get('came_from', '/')

    client_id = request.matchdict.get('id', -1)
    client = Client.query.filter(Client.id == client_id).first()
    if not client:
        transaction.abort()
        return Response('Can not find a client with id: %s' % client_id, 500)

    user_id = request.params.get('user_id', -1)
    user = User.query.filter(User.id == user_id).first()
    if not user:
        transaction.abort()
        return Response('Can not find a user with id: %s' % user_id, 500)

    role_name = request.params.get('role_name', None)
    role = query_role(role_name)
    role.updated_by = logged_in_user
    role.date_created = utc_now

    logger.debug("%s role is created" % role.name)
    logger.debug(client.users)

    client_user = ClientUser()
    client_user.client = client
    client_user.role = role
    client_user.user = user
    client_user.date_created = utc_now
    client_user.created_by = logged_in_user

    DBSession.add(client_user)

    if user not in client.users:
        client.users.append(user)
        request.session.flash('success:%s is added to %s user list' % (user.name, client.name))

    logger.debug(client.users)

    return Response(
        'success:%s is added to %s.'
        % (user.name, client.name)
    )

@view_config(
    route_name='get_client_users',
    renderer='json'
)
def get_client_users(request):
    """get_client_users
    """
# if there is an id it is probably a project
    client_id = request.matchdict.get('id')
    client = Client.query.filter(Client.id == client_id).first()

    has_permission = PermissionChecker(request)
    has_update_user_permission = has_permission('Update_User')
    has_delete_user_permission = has_permission('Delete_User')

    delete_user_action = '/users/%(id)s/delete/dialog'
    return_data = []
    for user in client.users:
        client_user = ClientUser.query.filter(ClientUser.user == user).first()
        return_data.append(
            {
                'id': user.id,
                'name': user.name,
                'login': user.login,
                'email': user.email,
                'role': client_user.role.name,
                'update_user_action': '/users/%s/update/dialog' % user.id if has_update_user_permission else None,
                'delete_user_action': delete_user_action % {
                    'id': user.id, 'entity_id': client_id
                } if has_delete_user_permission else None
            }
        )

    return return_data
