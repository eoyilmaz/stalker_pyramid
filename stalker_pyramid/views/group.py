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
import datetime
# import colander
# from deform import widget
# import deform

from pyramid.httpexceptions import HTTPFound, HTTPOk, HTTPServerError
from pyramid.security import authenticated_userid, forget, remember, has_permission
from pyramid.view import view_config, forbidden_view_config
from sqlalchemy import or_

import stalker_pyramid
from stalker import (defaults, User, Department, Group, Project, Entity,
                     Studio, Permission, EntityType, Task)
from stalker.db import DBSession
from stalker_pyramid.views import (log_param, get_logged_in_user,
                                   PermissionChecker, get_multi_integer, get_tags, milliseconds_since_epoch)

import logging
from stalker_pyramid.views.auth import logout, get_permissions_from_multi_dict

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)



@view_config(
    route_name='group_dialog',
    renderer='templates/group/dialog/group_dialog.jinja2',
)
def group_dialog(request):
    """create group dialog
    """

    logger.debug('***group_dialog method starts ***')

    logged_in_user = get_logged_in_user(request)

    if not logged_in_user:
        return logout(request)

    permissions = Permission.query.all()
    entity_types = EntityType.query.all()

    permissions_list = []

    for entity_type in entity_types:

        permission_item = {
            'label':entity_type.name

        }

        for permission in permissions:
            permission_item[permission.action] = ''

        permissions_list.append(permission_item)

    entity_id = request.matchdict.get('eid', -1)
    entity = Entity.query.filter_by(id=entity_id).first()


    studio = Studio.query.first()
    projects = Project.query.all()

    return {
        'entity' : entity,
        'mode': 'CREATE',
        'actions': defaults.actions,
        'permissions_list': permissions_list,
        'logged_in_user': logged_in_user,
        'stalker_pyramid': stalker_pyramid,
        'has_permission': PermissionChecker(request),
        'studio': studio,
        'projects': projects
    }


@view_config(
    route_name='create_group'
)
def create_group(request):
    """creates a new Group
    """

    logger.debug('***create group method starts ***')

    logged_in_user = get_logged_in_user(request)

    # get params
    post_multi_dict = request.POST

    came_from = request.params.get('came_from', '/')
    name = post_multi_dict['name']

    logger.debug('new group name : %s' % name)

    if name:

        description = post_multi_dict['description']
        logger.debug('new group description : %s' % description)

        # remove name and description to leave only permissions in the dictionary
        post_multi_dict.pop('name')
        post_multi_dict.pop('description')

        permissions = get_permissions_from_multi_dict(post_multi_dict)
        logger.debug('new group permissions : %s' % permissions)

        try:
            # create the new group
            new_group = Group(
                name=name
            )
            new_group.description = description
            new_group.created_by = logged_in_user
            new_group.permissions = permissions

            DBSession.add(new_group)

            logger.debug('added new group successfully')

            request.session.flash(
                'success:Group <strong>%s</strong> is created successfully' % name
            )

            logger.debug('***create group method ends ***')

        except BaseException as e:
            request.session.flash('error:' + e.message)
            HTTPFound(location=came_from)
    else:
        logger.debug('not all parameters are in request.params')
        log_param(request, 'name')
        HTTPServerError()

    return HTTPFound(
        location=came_from
    )


@view_config(
    route_name='update_group'
)
def update_group(request):
    """updates the group with data from request
    """

    logger.debug('***update group method starts ***')

    logged_in_user = get_logged_in_user(request)

    # get parameters
    post_multi_dict = request.POST

    came_from = request.params.get('came_from', '/')
    group_id = int(post_multi_dict['group_id'])
    group = Group.query.filter_by(id=group_id).first()

    name = post_multi_dict['name']

    if group and name:

        description = post_multi_dict['description']

        # remove name and description to leave only permission in the dictionary
        post_multi_dict.pop('name')
        post_multi_dict.pop('description')
        permissions = get_permissions_from_multi_dict(post_multi_dict)

         # update the group
        group.name = name
        group.description = description
        group.permissions = permissions
        group.updated_by = logged_in_user
        group.date_updated = datetime.datetime.now()

        DBSession.add(group)

        logger.debug('group is updated successfully')

        request.session.flash(
                'success:Group <strong>%s</strong> is updated successfully' % name
            )

        logger.debug('***update group method ends ***')
    else:
        logger.debug('not all parameters are in request.params')
        log_param(request, 'group_id')
        log_param(request, 'name')
        HTTPServerError()

    return HTTPFound(
        location=came_from
    )


@view_config(
    route_name='list_studio_groups',
    renderer='templates/group/list/list_entity_groups.jinja2'
)
@view_config(
    route_name='list_groups',
    renderer='templates/group/list/list_entity_groups.jinja2'
)
def list_groups(request):
    """
    """
    logger.debug('***list_groups method starts ***')

    logged_in_user = get_logged_in_user(request)

    groups = Group.query.all()
    studio = Studio.query.first()
    projects = Project.query.all()

    return {
        'stalker_pyramid': stalker_pyramid,
        'studio': studio,
        'logged_in_user': logged_in_user,
        'milliseconds_since_epoch': milliseconds_since_epoch,
        'has_permission': PermissionChecker(request),
        'projects': projects,
        'groups': groups
    }


@view_config(
    route_name='view_group',
    renderer='templates/group/view/view_group.jinja2'
)
def view_group(request):
    """create group dialog
    """
    logger.debug('***view_entity_group method starts ***')

    logged_in_user = get_logged_in_user(request)

    permissions = Permission.query.all()
    entity_types = EntityType.query.all()



    group_id = request.matchdict.get('id', -1)
    group = Group.query.filter_by(id=group_id).first()

    studio = Studio.query.first()
    projects = Project.query.all()

    return {
        'entity': group,
        'actions': defaults.actions,
        'permissions': permissions,
        'entity_types': entity_types,
        'logged_in_user': logged_in_user,
        'stalker_pyramid': stalker_pyramid,
        'has_permission': PermissionChecker(request),
        'studio': studio,
        'projects': projects

    }


@view_config(
    route_name='list_group_permissions',
    renderer='templates/group/list/list_group_permissions.jinja2'
)
def list_group_permissions(request):
    """create group dialog
    """
    logger.debug('***view_entity_group method starts ***')

    logged_in_user = get_logged_in_user(request)

    permissions = Permission.query.all()
    entity_types = EntityType.query.all()

    group_id = request.matchdict.get('id', -1)
    group = Group.query.filter_by(id=group_id).first()

    studio = Studio.query.first()
    projects = Project.query.all()



    return {
        'entity': group,
        'actions': defaults.actions,
        'permissions': permissions,
        'entity_types': entity_types,
        'logged_in_user': logged_in_user,
        'stalker_pyramid': stalker_pyramid,
        'has_permission': PermissionChecker(request),
        'studio': studio,
        'projects': projects

    }

@view_config(
    route_name='get_group_permissions',
    renderer='json'
)
def get_group_permissions(request):



    group_id = request.matchdict.get('id', -1)
    group = Group.query.filter_by(id=group_id).first()

    permissions = Permission.query.all()
    entity_types = EntityType.query.all()

    permissions_list = []

    for entity_type in entity_types:

        permission_item = {
            'label':entity_type.name

        }

        for permission in permissions:
            permission_item[permission.action] = ''

        permissions_list.append(permission_item)

    for group_permission in group.permissions:

        label_indexer = dict((p['label'], i) for i, p in enumerate(permissions_list))
        index = label_indexer.get(group_permission.class_name, -1)

        permissions_list[index][group_permission.action] = 'checked'



    return permissions_list





# @view_config(
#     route_name='view_group',
#     renderer='templates/group/view/view_group.jinja2'
# )
# def view_group(request):
#     """create group dialog
#     """
#     logger.debug('***view_group method starts ***')
#
#     logged_in_user = get_logged_in_user(request)
#
#     permissions = Permission.query.all()
#     entity_types = EntityType.query.all()
#
#     group_id = request.matchdict.get('id', -1)
#     group = Group.query.filter_by(id=group_id).first()
#
#     entity_id = request.matchdict.get('id', -1)
#     entity = Entity.query.filter_by(id=entity_id).first()
#
#     studio = Studio.query.first()
#     projects = Project.query.all()
#
#     return {
#         'mode': 'UPDATE',
#         'entity': entity,
#         'actions': defaults.actions,
#         'permissions': permissions,
#         'entity_types': entity_types,
#         'logged_in_user': logged_in_user,
#         'stalker_pyramid': stalker_pyramid,
#         'has_permission': PermissionChecker(request),
#         'studio': studio,
#         'projects': projects
#
#     }
#
#
#
@view_config(
    route_name='get_groups',
    renderer='json',
    permission='List_Group'
)
def get_groups(request):
    """returns all the groups in database
    """
    return [
        {
            'group_id': group.id,
            'group_name': group.name,
            'thumbnail_full_path': group.thumbnail.full_path if group.thumbnail else None,
            'created_by_id': group.created_by.id,
            'created_by_name': group.created_by.name,
            'users_count': len(group.users)
        }
        for group in Group.query.order_by(Group.name.asc()).all()
    ]


@view_config(
    route_name='get_entity_groups',
    renderer='json',
    permission='List_Group'
)
@view_config(
    route_name='get_user_groups',
    renderer='json',
    permission='List_Group'
)
def get_entity_groups(request):
    """returns all the groups of a given Entity
    """
    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    return [
        {
            'group_id': group.id,
            'group_name': group.name,
            'thumbnail_full_path': group.thumbnail.full_path if group.thumbnail else None,
            'created_by_id': group.created_by.id,
            'created_by_name': group.created_by.name,
            'users_count': len(group.users)
        }
        for group in sorted(entity.groups, key=lambda x: x.name.lower())
    ]



