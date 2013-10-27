# -*- coding: utf-8 -*-
# Stalker a Production Asset Management System
# Copyright (C) 2009-2013 Erkan Ozgur Yilmaz
# 
# This file is part of Stalker.
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
from pyramid.httpexceptions import HTTPServerError, HTTPFound, HTTPOk
from pyramid.view import view_config
from stalker import Entity, Studio, Project, Group, User, Department
from stalker.db import DBSession

import stalker_pyramid
from stalker_pyramid.views import PermissionChecker, get_logged_in_user, milliseconds_since_epoch, get_multi_integer


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@view_config(
    route_name='user_dialog',
    renderer='templates/auth/dialog/user_dialog.jinja2',
)
@view_config(
    route_name='create_user_dialog',
    renderer='templates/auth/dialog/create_user_dialog.jinja2',
)

@view_config(
    route_name='list_entity_users',
    renderer='templates/auth/list/list_entity_users.jinja2'
)
@view_config(
    route_name='list_studio_users',
    renderer='templates/auth/list/list_entity_users.jinja2'
)
@view_config(
    route_name='list_project_users',
    renderer='templates/auth/list/list_entity_users.jinja2'
)
@view_config(
    route_name='list_department_users',
    renderer='templates/auth/list/list_entity_users.jinja2'
)
@view_config(
    route_name='list_group_users',
    renderer='templates/auth/list/list_entity_users.jinja2'
)
@view_config(
    route_name='list_users',
    renderer='templates/auth/list/list_entity_users.jinja2'
)
@view_config(
    route_name='view_user',
    renderer='templates/auth/view/view_user.jinja2'
)
@view_config(
    route_name='list_user_groups',
    renderer='templates/group/list/list_entity_groups.jinja2'
)
@view_config(
    route_name='list_entity_groups',
    renderer='templates/group/list/list_entity_groups.jinja2'
)
@view_config(
    route_name='department_dialog',
    renderer='templates/department/dialog/department_dialog.jinja2',
)
@view_config(
    route_name='list_entity_departments',
    renderer='templates/department/list/list_entity_departments.jinja2'
)
@view_config(
    route_name='list_user_departments',
    renderer='templates/department/list/list_entity_departments.jinja2'
)
@view_config(
    route_name='list_studio_departments',
    renderer='templates/department/list/list_entity_departments.jinja2'
)
@view_config(
    route_name='project_dialog',
    renderer='templates/project/dialog/project_dialog.jinja2',
)
@view_config(
    route_name='list_projects',
    renderer='templates/project/list/list_entity_projects.jinja2'
)
@view_config(
    route_name='list_entity_projects',
    renderer='templates/project/list/list_entity_projects.jinja2'
)
@view_config(
    route_name='list_user_projects',
    renderer='templates/project/list/list_entity_projects.jinja2'
)
@view_config(
    route_name='list_studio_projects',
    renderer='templates/project/list/list_entity_projects.jinja2'
)
@view_config(
    route_name='view_project',
    renderer='templates/project/view/view_project.jinja2'
)
@view_config(
    route_name='view_studio',
    renderer='templates/studio/view/view_studio.jinja2'
)
@view_config(
    route_name='view_task',
    renderer='templates/task/view/view_task.jinja2'
)
@view_config(
    route_name='list_entity_tasks',
    renderer='templates/task/list/list_entity_tasks.jinja2'
)
@view_config(
    route_name='list_project_tasks',
    renderer='templates/task/list/list_entity_tasks.jinja2'
)
@view_config(
    route_name='list_user_tasks',
    renderer='templates/task/list/list_entity_tasks.jinja2'
)
@view_config(
    route_name='list_task_tasks',
    renderer='templates/task/list/list_entity_tasks.jinja2'
)
@view_config(
    route_name='list_studio_tasks',
    renderer='templates/task/list/list_entity_tasks.jinja2'
)
@view_config(
    route_name='view_asset',
    renderer='templates/task/view/view_task.jinja2'
)
@view_config(
    route_name='list_project_assets',
    renderer='templates/asset/list/list_entity_assets.jinja2'
)
@view_config(
    route_name='view_shot',
    renderer='templates/task/view/view_task.jinja2'
)
@view_config(
    route_name='list_project_shots',
    renderer='templates/shot/list/list_entity_shots.jinja2'
)
@view_config(
    route_name='view_sequence',
    renderer='templates/task/view/view_task.jinja2'
)
@view_config(
    route_name='list_project_sequences',
    renderer='templates/sequence/list/list_entity_sequences.jinja2'
)
@view_config(
    route_name='upload_entity_reference_dialog',
    renderer='templates/link/dialogs/upload_reference_dialog.jinja2'
)
@view_config(
    route_name='upload_entity_thumbnail_dialog',
    renderer='templates/link/dialogs/upload_thumbnail_dialog.jinja2'
)
@view_config(
    route_name='list_entity_tickets',
    renderer='templates/ticket/list_entity_tickets.jinja2'
)
@view_config(
    route_name='list_user_tickets',
    renderer='templates/ticket/list_entity_tickets.jinja2'
)
@view_config(
    route_name='list_project_tickets',
    renderer='templates/ticket/list_entity_tickets.jinja2'
)
@view_config(
    route_name='list_task_tickets',
    renderer='templates/ticket/list_entity_tickets.jinja2'
)
@view_config(
    route_name='view_ticket',
    renderer='templates/ticket/view_ticket.jinja2'
)
@view_config(
    route_name='list_entity_vacations',
    renderer='templates/vacation/list/list_entity_vacations.jinja2'
)
@view_config(
    route_name='list_studio_vacations',
    renderer='templates/vacation/list/list_entity_vacations.jinja2'
)
@view_config(
    route_name='list_user_vacations',
    renderer='templates/vacation/list/list_entity_vacations.jinja2'
)
@view_config(
    route_name='list_project_references',
    renderer='templates/link/list_entity_references.jinja2'
)
@view_config(
    route_name='list_task_references',
    renderer='templates/link/list_entity_references.jinja2'
)
@view_config(
    route_name='list_entity_references',
    renderer='templates/link/list_entity_references.jinja2'
)
@view_config(
    route_name='list_task_versions',
    renderer='templates/version/list/list_entity_versions.jinja2'
)
def get_entity_related_data(request):
    """lists the time logs of the given task
    """
    logged_in_user = get_logged_in_user(request)

    studio = Studio.query.first()

    entity_id = request.matchdict.get('id')
    if not entity_id:
        entity = studio
    else:
        entity = Entity.query.filter_by(id=entity_id).first()

    projects = Project.query.all()

    mode = request.matchdict.get('mode', None)

    came_from = request.params.get('came_from', request.url)

    return {
        'mode': mode,
        'entity': entity,
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'milliseconds_since_epoch': milliseconds_since_epoch,
        'stalker_pyramid': stalker_pyramid,
        'projects': projects,
        'studio': studio,
        'came_from': came_from
    }


@view_config(
    route_name='append_entities_to_entity_dialog',
    renderer='templates/entity/append_entities_to_entity_dialog.jinja2'
)
def append_entities_to_entity_dialog(request):

    logger.debug('append_class_to_entity_dialog is running')

    came_from = request.params.get('came_from', '/')

    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    entities_name = request.matchdict.get('entities', -1)


    logger.debug('came_from: %s' % came_from)

    logger.debug('entities_name %s'% entities_name)

    return {
        'has_permission': PermissionChecker(request),
        'milliseconds_since_epoch': milliseconds_since_epoch,
        'came_from': came_from,
        'entity': entity,
        'entities_name': entities_name
    }

@view_config(
    route_name='get_entity_entities_out_stack',
    renderer='json'
)
def get_entity_entities_out_stack(request):

    logger.debug('get_entity_entities_out_stack is running')

    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    entities_name = request.matchdict.get('entities', -1)
    attr_name = entity.plural_class_name.lower()

    logger.debug('entities_name %s'% entities_name)
    logger.debug('attr_name %s'% attr_name)

    queryString = '%(class_name)s.query.filter(~%(class_name)s.%(attr_name)s.contains(entity))'
    q = eval(queryString % {'class_name': entities_name, 'attr_name': attr_name})
    list_of_container_objects = q.all()

    out_stack = []

    for entity_s in list_of_container_objects:
        logger.debug('entity_s %s' % entity_s.name)
        out_stack.append({
             'id': entity_s.id,
            'name':entity_s.name,
            'thumnail_path':entity_s.thumbnail.full_path if entity_s.thumbnail else None,
            'description':entity_s.description if entity_s.description else None
        })

    return out_stack


@view_config(
    route_name='append_entities_to_entity',
)
def append_entities_to_entity(request):
    """Appends entities to entity for example appends Projects to user.projects
    etc.
    """
    logger.debug('append_class_to_entity is running')



    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    selected_list = get_multi_integer(request, 'selected_items[]')


    logger.debug('selected_list: %s' % selected_list)


    if entity and selected_list:

        appended_entities = Entity.query.filter(Entity.id.in_(selected_list)).all()
        if appended_entities:
            attr_name = appended_entities[0].plural_class_name.lower()
            eval('entity.%(attr_name)s.extend(appended_entities)' % {'attr_name': attr_name})
            DBSession.add(entity)

            logger.debug('entity is updated successfully')

            request.session.flash(
                'success:User <strong>%s</strong> is updated successfully' % entity.name
            )
            logger.debug('***append_entities_to_entity method ends ***')
    else:
        logger.debug('not all parameters are in request.params')
        HTTPServerError()

    return HTTPOk()

@view_config(
    route_name='append_entities_to_entity',
)
def append_entities_to_entity(request):
    """Appends entities to entity for example appends Projects to user.projects
    etc.
    """
    logger.debug('append_class_to_entity is running')



    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    selected_list = get_multi_integer(request, 'selected_items[]')


    logger.debug('selected_list: %s' % selected_list)


    if entity and selected_list:

        appended_entities = Entity.query.filter(Entity.id.in_(selected_list)).all()
        if appended_entities:
            attr_name = appended_entities[0].plural_class_name.lower()
            eval('entity.%(attr_name)s.extend(appended_entities)' % {'attr_name': attr_name})
            DBSession.add(entity)

            logger.debug('entity is updated successfully')

            request.session.flash(
                'success:Selected %s are added to %s <strong>%s</strong> \'s %s' % (attr_name,entity.entity_type.lower(),entity.name, attr_name)
            )
            logger.debug('***append_entities_to_entity method ends ***')
    else:
        logger.debug('not all parameters are in request.params')
        HTTPServerError()

    return HTTPOk()


@view_config(
    route_name='remove_entity_from_entity',
)
def remove_entity_from_entity(request):
    """Removes entitiy from entity for example removes selected project from user.projects
    etc.
    """
    logger.debug('append_class_to_entity is running')

    came_from = request.params.get('came_from', '/')

    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    selected_entity_id = request.matchdict.get('entity_id', -1)
    selected_entity = Entity.query.filter_by(id=selected_entity_id).first()


    logger.debug('selected_entity: %s' % selected_entity)


    if entity and selected_entity:

        attr_name = selected_entity.plural_class_name.lower()
        eval('entity.%(attr_name)s.remove(selected_entity)' % {'attr_name': attr_name})
        DBSession.add(entity)

        logger.debug('entity is updated successfully')

        request.session.flash(
            'success:%s <strong>%s</strong> is removed from %s \'s %s  successfully' % (selected_entity.entity_type, selected_entity.name, entity.name, attr_name)
        )
        logger.debug('***append_entities_to_entity method ends ***')
    else:
        logger.debug('not all parameters are in request.params')
        HTTPServerError()

    return HTTPFound(
        location=came_from
    )
