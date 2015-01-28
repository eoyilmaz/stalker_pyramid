# -*- coding: utf-8 -*-
# Stalker a Production Asset Management System
# Copyright (C) 2009-2014 Erkan Ozgur Yilmaz
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
import re
import logging

from pyramid.httpexceptions import HTTPServerError, HTTPOk, HTTPForbidden
from pyramid.view import view_config
from pyramid.response import Response

from stalker.db import DBSession
from stalker import (db, defaults, Entity, Studio, Project, User, Group, Department,Sequence,Asset,Shot,Ticket,Task,
                     Status)
import transaction

import stalker_pyramid
from stalker_pyramid.views import (PermissionChecker, get_logged_in_user,
                                   milliseconds_since_epoch, get_multi_integer,
                                   multi_permission_checker, get_multi_string,
                                   StdErrToHTMLConverter)


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@view_config(
    route_name='update_client_dialog',
    renderer='templates/client/dialog/update_client_dialog.jinja2',
)
@view_config(
    route_name='create_client_dialog',
    renderer='templates/client/dialog/create_client_dialog.jinja2',
)
@view_config(
    route_name='list_studio_clients',
    renderer='templates/client/list/list_studio_clients.jinja2'
)
@view_config(
    route_name='view_client',
    renderer='templates/client/view/view_client.jinja2'
)
@view_config(
    route_name='update_user_dialog',
    renderer='templates/auth/dialog/update_user_dialog.jinja2',
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
    route_name='list_resource_rates',
    renderer='templates/resource/list/list_resource_rates.jinja2'
)
@view_config(
    route_name='view_user',
    renderer='templates/auth/view/view_user.jinja2'
)
@view_config(
    route_name='view_user_reports',
    renderer='templates/auth/report/view_user_reports.jinja2'
)
@view_config(
    route_name='update_group_dialog',
    renderer='templates/group/dialog/update_group_dialog.jinja2',
)
@view_config(
    route_name='create_group_dialog',
    renderer='templates/group/dialog/create_group_dialog.jinja2',
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
    route_name='update_department_dialog',
    renderer='templates/department/dialog/update_department_dialog.jinja2',
)
@view_config(
    route_name='create_department_dialog',
    renderer='templates/department/dialog/create_department_dialog.jinja2',
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
    route_name='view_department',
    renderer='templates/department/view/view_department.jinja2'
)
@view_config(
    route_name='view_department_reports',
    renderer='templates/department/report/view_department_reports.jinja2',
)
@view_config(
    route_name='create_project_dialog',
    renderer='templates/project/dialog/create_project_dialog.jinja2',
)
@view_config(
    route_name='update_project_dialog',
    renderer='templates/project/dialog/update_project_dialog.jinja2',
)
@view_config(
    route_name='view_project_reports',
    renderer='templates/project/report/view_project_reports.jinja2'
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
    route_name='update_studio_dialog',
    renderer='templates/studio/dialog/update_studio_dialog.jinja2',
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
    renderer='templates/task/list/list_user_tasks.jinja2'
)
@view_config(
    route_name='list_user_tasks_responsible_of',
    renderer='templates/task/list/list_user_tasks_responsible_of.jinja2'
)
@view_config(
    route_name='list_user_tasks_watching',
    renderer='templates/task/list/list_user_tasks_watching.jinja2'
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
    route_name='view_shot',
    renderer='templates/task/view/view_task.jinja2'
)
@view_config(
    route_name='list_project_shots',
    renderer='templates/shot/list/list_entity_shots.jinja2'
)
@view_config(
    route_name='list_sequence_shots',
    renderer='templates/shot/list/list_entity_shots.jinja2'
)
@view_config(
    route_name='list_entity_shots',
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
    route_name='list_entity_scenes',
    renderer='templates/scene/list/list_entity_scenes.jinja2'
)
@view_config(
    route_name='upload_entity_reference_dialog',
    renderer='templates/link/dialogs/upload_reference_dialog.jinja2'
)
@view_config(
    route_name='upload_entity_output_dialog',
    renderer='templates/link/dialogs/upload_output_dialog.jinja2'
)
@view_config(
    route_name='upload_entity_thumbnail_dialog',
    renderer='templates/link/dialogs/upload_thumbnail_dialog.jinja2'
)
@view_config(
    route_name='list_entity_tickets',
    renderer='templates/ticket/list/list_entity_tickets.jinja2'
)
@view_config(
    route_name='list_user_tickets',
    renderer='templates/ticket/list/list_entity_tickets.jinja2'
)
@view_config(
    route_name='list_project_tickets',
    renderer='templates/ticket/list/list_entity_tickets.jinja2'
)
@view_config(
    route_name='list_task_tickets',
    renderer='templates/ticket/list/list_entity_tickets.jinja2'
)
@view_config(
    route_name='view_ticket',
    renderer='templates/ticket/view/view_ticket.jinja2'
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
    route_name='view_version',
    renderer='templates/version/view/view_version.jinja2'
)
@view_config(
    route_name='list_task_versions',
    renderer='templates/version/list/list_entity_versions.jinja2'
)
@view_config(
    route_name='list_task_outputs',
    renderer='templates/version/list/list_entity_outputs.jinja2'
)
@view_config(
    route_name='list_user_reviews',
    renderer='templates/review/list/list_reviews.jinja2'
)
@view_config(
    route_name='list_task_reviews',
    renderer='templates/review/list/list_task_reviews.jinja2'
)
@view_config(
    route_name='list_project_reviews',
    renderer='templates/review/list/list_reviews.jinja2'
)

@view_config(
    route_name='list_entity_resources',
    renderer='templates/resource/list/list_entity_resources.jinja2'
)
@view_config(
    route_name='list_entity_notes',
    renderer='templates/note/list/list_entity_notes.jinja2'
)
@view_config(
    route_name='view_daily',
    renderer='templates/daily/view/view_daily.jinja2'
)
@view_config(
    route_name='list_project_dailies',
    renderer='templates/daily/list/list_project_dailies.jinja2'
)
@view_config(
    route_name='view_budget',
    renderer='templates/budget/view/view_budget.jinja2'
)
@view_config(
    route_name='list_project_budgets',
    renderer='templates/budget/list/list_project_budgets.jinja2'
)
@view_config(
    route_name='test_page',
    renderer='templates/test_page.jinja2'
)
def get_entity_related_data(request):
    """view for generic data
    """
    logger.debug('get_entity_related_data')
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
    route_name='get_entity',
    renderer='json'
)
def get_entity(request):
    """returns all the departments in the database
    """
    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    return[
        {
            'id': entity_id,
            'name': entity.name,
            'thumbnail_full_path': entity.thumbnail.full_path if entity.thumbnail else None,
        }
    ]


@view_config(
    route_name='list_entity_tasks_by_filter',
    renderer='templates/task/list/list_entity_tasks_by_filter.jinja2',
)
def list_entity_tasks_by_filter(request):
    """creates a list_entity_tasks_by_filter by using the given entity and filter
    """
    logger.debug('inside list_entity_tasks_by_filter')

    # get logged in user
    logged_in_user = get_logged_in_user(request)

    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    filter_id = request.matchdict.get('f_id', -1)
    filter_entity = Entity.query.filter_by(id=filter_id).first()
    is_warning_list = False
    if not filter_entity:
        is_warning_list = True
        filter_entity = Status.query.filter_by(code='WIP').first()

    studio = Studio.query.first()
    if not studio:
        studio = defaults

    return {
        'mode': 'create',
        'has_permission': PermissionChecker(request),
        'studio': studio,
        'logged_in_user': logged_in_user,
        'entity': entity,
        'filter': filter_entity,
        'is_warning_list':is_warning_list,
        'milliseconds_since_epoch': milliseconds_since_epoch,
    }


@view_config(
    route_name='append_entities_to_entity_dialog',
    renderer='templates/entity/append_entities_to_entity_dialog.jinja2'
)
def append_entities_to_entity_dialog(request):

    logger.debug('append_entities_to_entity_dialog is running')

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

    query_string = '%(class_name)s.query.filter(~%(class_name)s.%(attr_name)s.contains(entity)).order_by(%(class_name)s.name.asc())'
    q = eval(query_string % {'class_name': entities_name, 'attr_name': attr_name})
    list_of_container_objects = q.all()

    out_stack = []

    for entity_s in list_of_container_objects:
        # logger.debug('entity_s %s' % entity_s.name)
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

    # selected_list = get_multi_integer(request, 'selected_items[]')
    selected_list = get_multi_integer(request, 'selected_ids')
    logger.debug('selected_list: %s' % selected_list)

    if entity and selected_list:

        appended_entities = Entity.query\
            .filter(Entity.id.in_(selected_list)).all()
        if appended_entities:
            attr_name = appended_entities[0].plural_class_name.lower()
            eval(
                'entity.%(attr_name)s.extend(appended_entities)' %
                {'attr_name': attr_name}
            )
            DBSession.add(entity)

            logger.debug('entity is updated successfully')

            request.session.flash(
                'success:User <strong>%s</strong> is updated successfully' %
                entity.name
            )
            logger.debug('***append_entities_to_entity method ends ***')
    else:
        logger.debug('not all parameters are in request.params')
        HTTPServerError()

    return HTTPOk()


@view_config(
    route_name='remove_entity_from_entity_dialog',
    renderer='templates/modals/confirm_dialog.jinja2'
)
def remove_entity_from_entity_dialog(request):
    """deletes the user with the given id
    """
    logger.debug('delete_user_dialog is starts')

    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    selected_entity_id = request.matchdict.get('entity_id', -1)
    selected_entity = Entity.query.filter_by(id=selected_entity_id).first()

    came_from = request.params.get('came_from', request.current_route_path())

    action = '/entities/%s/%s/remove?came_from=%s'% (selected_entity_id,entity_id,came_from)


    message = 'Are you sure you want to <strong>remove %s </strong>?'% (entity.name)

    logger.debug('action: %s' % action)

    return {
            'came_from': came_from,
            'message':message,
            'action': action
        }

@view_config(
    route_name='remove_entity_from_entity',
)
def remove_entity_from_entity(request):
    """Removes entitiy from entity for example removes selected project from user.projects
    etc.
    """
    logger.debug('remove_entity_from_entity is running')

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
            'success:%s <strong>%s</strong> is successfully removed from %s '
            '\'s %s' % (
                selected_entity.entity_type,
                selected_entity.name, entity.name, attr_name
            )
        )
        logger.debug('***remove_entity_from_entity method ends ***')
    else:
        logger.debug('not all parameters are in request.params')
        request.session.flash(
            'failed:not all parameters are in request.params'
        )
        HTTPServerError()

    return Response(
        'success:%s <strong>%s</strong> is '
        'successfully removed from %s \'s %s' % (
            selected_entity.entity_type,
            selected_entity.name,
            entity.name,
            attr_name
        )
    )



@view_config(
    route_name='get_entity_events',
    renderer='json'
)
@view_config(
    route_name='get_user_events',
    renderer='json'
)
def get_entity_events(request):
    """Returns entity "events" like TimeLogs, Vacations and Tasks which are
    events to be drawn in Calendars
    """
    logger.debug('get_entity_events is running')

    if not multi_permission_checker(
            request, ['Read_User', 'Read_TimeLog', 'Read_Vacation']):
        return HTTPForbidden(headers=request)

    keys = get_multi_string(request, 'keys')
    entity_id = request.matchdict.get('id', -1)

    logger.debug('keys: %s' % keys)
    logger.debug('entity_id : %s' % entity_id)

    sql_query = ""
    if 'time_log' in keys:
        sql_query = """
        select
            "TimeLogs".id,
            'timelogs' as entity_type, -- entity_type
            "Task_SimpleEntities".name || ' (' || parent_names.path_names || ')' as title,
            (extract(epoch from "TimeLogs".start::timestamp AT TIME ZONE 'UTC') * 1000)::bigint as start,
            (extract(epoch from "TimeLogs".end::timestamp AT TIME ZONE 'UTC') * 1000)::bigint as end,
            'label-success' as "className",
            false as "allDay",
            "Status_SimpleEntities".name as status
        from "TimeLogs"
        join "Tasks" on "TimeLogs".task_id = "Tasks".id
        join "SimpleEntities" as "Task_SimpleEntities" on "Tasks".id = "Task_SimpleEntities".id
        join "SimpleEntities" as "Status_SimpleEntities" on "Tasks".status_id = "Status_SimpleEntities".id

        join (
            with recursive recursive_task(id, parent_id, path, path_names) as (
                select
                    task.id,
                    task.project_id,
                    array[task.project_id] as path,
                    ("Projects".code || '') as path_names
                from "Tasks" as task
                join "Projects" on task.project_id = "Projects".id
                where task.parent_id is NULL
            union all
                select
                    task.id,
                    task.parent_id,
                    (parent.path || task.parent_id) as path,
                    (parent.path_names || '|' || "Parent_SimpleEntities".name) as path_names
                from "Tasks" as task
                join recursive_task as parent on task.parent_id = parent.id
                join "SimpleEntities" as "Parent_SimpleEntities" on parent.id = "Parent_SimpleEntities".id
                --where parent.id = t_path.parent_id
            ) select
                recursive_task.id,
                recursive_task.path,
                recursive_task.path_names
            from recursive_task
            order by path
        ) as parent_names on "TimeLogs".task_id = parent_names.id

        where "TimeLogs".resource_id = %(id)s
        """ % {'id': entity_id}

    if 'vacation' in keys:
        vacation_sql_query = """
        select
            "Vacations".id,
            'vacations' as entity_type,
            "Type_SimpleEntities".name as title,
            (extract(epoch from "Vacations".start::timestamp at time zone 'UTC') * 1000)::bigint as start,
            (extract(epoch from "Vacations".end::timestamp at time zone 'UTC') * 1000)::bigint as end,
            'label-yellow' as "className",
            true as "allDay",
            NULL as status
        from "Vacations"
        join "SimpleEntities" on "Vacations".id = "SimpleEntities".id
        join "Types" on "SimpleEntities".type_id = "Types".id
        join "SimpleEntities" as "Type_SimpleEntities" on "Types".id = "Type_SimpleEntities".id
        where "Vacations".user_id is NULL or "Vacations".user_id = %(id)s
        """ % {'id': entity_id}

        if sql_query != '':
            sql_query = '(%s) union (%s)' % (sql_query, vacation_sql_query)
        else:
            sql_query = vacation_sql_query

    if 'task' in keys:
        task_sql_query = """
        select
            "Tasks".id,
            'tasks' as entity_type,
            "Task_SimpleEntities".name || ' (' || parent_names.path_names || ')' as title,
            (extract(epoch from "Tasks".computed_start::timestamp at time zone 'UTC') * 1000)::bigint as start,
            (extract(epoch from "Tasks".computed_end::timestamp at time zone 'UTC') * 1000)::bigint as end,
            'label' as "className",
            false as "allDay",
            "Status_SimpleEntities".name as status
        from "Tasks"
        join "SimpleEntities" as "Task_SimpleEntities" on "Tasks".id = "Task_SimpleEntities".id
        join "SimpleEntities" as "Status_SimpleEntities" on "Tasks".status_id = "Status_SimpleEntities".id

        join (
            with recursive recursive_task(id, parent_id, path, path_names) as (
                select
                    task.id,
                    task.project_id,
                    array[task.project_id] as path,
                    ("Projects".code || '') as path_names
                from "Tasks" as task
                join "Projects" on task.project_id = "Projects".id
                where task.parent_id is NULL
            union all
                select
                    task.id,
                    task.parent_id,
                    (parent.path || task.parent_id) as path,
                    (parent.path_names || '|' || "Parent_SimpleEntities".name) as path_names
                from "Tasks" as task
                join recursive_task as parent on task.parent_id = parent.id
                join "SimpleEntities" as "Parent_SimpleEntities" on parent.id = "Parent_SimpleEntities".id
                --where parent.id = t_path.parent_id
            ) select
                recursive_task.id,
                recursive_task.path,
                recursive_task.path_names
            from recursive_task
            order by path
        ) as parent_names on "Tasks".id = parent_names.id

        join "Task_Resources" on "Tasks".id = "Task_Resources".task_id

        where "Task_Resources".resource_id = %(id)s and "Tasks".computed_end > current_date::date at time zone 'UTC'
        """ % {'id': entity_id}

        if sql_query != '':
            sql_query = '(%s) union (%s)' % (sql_query, task_sql_query)
        else:
            sql_query = task_sql_query

    result = db.DBSession.connection().execute(sql_query)
    return [{
        'id': r[0],
        'entity_type': r[1],
        'title': r[2],
        'start': r[3],
        'end': r[4],
        'className': r[5],
        'allDay': r[6],
        'status': r[7]
    } for r in result.fetchall()]


@view_config(
    route_name='get_search_result',
    renderer='json'
)
def get_search_result(request):
    """returns search result
    """
    logger.debug('get_search_result is running')

    q_string = request.params.get('str', -1)

    sql_query_buffer = [
        'select id, name, entity_type from "SimpleEntities"',
        'where'
    ]

    for i, part in enumerate(re.findall(r'[\w\d]+', q_string)):
        if i > 0:
            sql_query_buffer.append('and')
        sql_query_buffer.append(
            """"SimpleEntities".name ilike '%{s}%' """.format(s=part)
        )

    sql_query_buffer.append('order by "SimpleEntities".name')

    sql_query = '\n'.join(sql_query_buffer)

    from sqlalchemy import text  # to be able to use "%" sign use this function
    result = DBSession.connection().execute(text(sql_query))
    return [
        {
            'id': r[0],
            'name': r[1],
            'entity_type': r[2]
        }
        for r in result.fetchall()
    ]


@view_config(
    route_name='submit_search',
    renderer='json'
)
def submit_search(request):
    """submits a search link suitable to be used with list_search_results()
    function.
    """
    logger.debug('***submit_search user method starts ***')

    # get params
    q_string = request.params.get('str', None)
    entity_id = request.params.get('id', None)

    logger.debug('qString : %s' % q_string)

    logger.debug('q_string: %s' % q_string)
    entity_type = None
    q_entity_type = ''
    if ':' in q_string:
        q_string, entity_type = q_string.split(':')

    result_location = '/'

    if q_string:
        sql_query_buffer = [
            'select count(1)',
            'from "Entities"',
            'join "SimpleEntities" on "Entities".id = "SimpleEntities".id',
            'where'
        ]

        for i, part in enumerate(re.findall(r'[\w\d]+', q_string)):
            if i > 0:
                sql_query_buffer.append('and')
            sql_query_buffer.append(
                """"SimpleEntities".name ilike '%{s}%' """.format(s=part)
            )
        if entity_type:

            q_entity_type = '&entity_type=%s'%entity_type

            sql_query_buffer.append(
                """and "SimpleEntities".entity_type='%s' """ % entity_type
            )
        sql_query = '\n'.join(sql_query_buffer)

        logger.debug('sql_query:  %s' % sql_query)

        from sqlalchemy import text
        result = DBSession.connection().execute(text(sql_query))

        entity_count = result.fetchone()[0]
        logger.debug('entity_count : %s' % entity_count)

        # if entity_count > 1:
        result_location = \
            '/list/search_results?str=%s&eid=%s%s' % \
            (q_string, entity_id, q_entity_type)

        # elif entity_count == 1:
        #     sql_query_buffer[0] = 'select "SimpleEntities".id'
        #     sql_query = '\n'.join(sql_query_buffer)
        # 
        #     logger.debug('sql_query: %s' % sql_query)
        #     result = DBSession.connection().execute(text(sql_query))
        # 
        #     entity = Entity.query.get(result.fetchone()[0])
        #     result_location = \
        #         '/%s/%s/view' % (entity.plural_class_name.lower(), entity.id)

    logger.debug('result_location : %s' % result_location)

    return {
        'url': result_location
    }


@view_config(
    route_name='list_search_result',
    renderer='list_search_result.jinja2'
)
def list_search_result(request):
    """lists the search result, it should use raw SQL instead of Python
    """
    qString = request.params.get('str', None)
    q_entity_type = request.params.get('entity_type', None)

    entity_id = request.params.get('eid', None)

    entity = Entity.query.filter_by(id=entity_id).first()

    results = []

    if q_entity_type:

        query_string = '%(class_name)s.query.filter(%(class_name)s.name.ilike(\'%(qString)s\')).order_by(%(class_name)s.name.asc())'
        query_string = query_string % {'class_name': q_entity_type, 'qString': qString}

        logger.debug(query_string)
        q = eval(query_string)

        results = q.all()
    else:
        results = Entity.query.filter(
            Entity.name.ilike('%' + qString + '%')
        ).order_by(Entity.name.asc()).all()

    projects = Project.query.all()
    logged_in_user = get_logged_in_user(request)

    studio = Studio.query.first()

    return {
        'entity': entity,
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'milliseconds_since_epoch': milliseconds_since_epoch,
        'stalker_pyramid': stalker_pyramid,
        'projects': projects,
        'studio': studio,
        'results': results
    }


@view_config(
    route_name='delete_entity_dialog',
    renderer='templates/modals/confirm_dialog.jinja2'
)
def delete_entity_dialog(request):
    """deletes the entity with the given id
    """
    logger.debug('delete_entity_dialog is starts')

    entity_id = request.matchdict.get('id')
    entity = Entity.query.get(entity_id)

    action = '/entities/%s/delete' % entity_id

    came_from = request.params.get('came_from', '/')

    message = 'Are you sure to delete?'

    logger.debug('action: %s' % action)

    return {
        'message': message,
        'came_from': came_from,
        'action': action
    }


@view_config(
    route_name='delete_entity',
    permission='Delete_Task'
)
def delete_entity(request):
    """deletes the task with the given id
    """

    logger.debug('delete_entity is starts')

    entity_id = request.matchdict.get('id')
    entity = Entity.query.filter_by(id=entity_id).first()

    if not entity:
        transaction.abort()
        return Response('Can not find an Entity with id: %s' % entity_id, 500)

    try:

        DBSession.delete(entity)
        transaction.commit()
    except Exception as e:
        transaction.abort()
        c = StdErrToHTMLConverter(e)
        transaction.abort()
        return Response(c.html(), 500)

    return Response('Successfully deleted %s: %s' % (entity.entity_type,entity.name))


@view_config(
    route_name='get_entity_total_schedule_seconds',
    renderer='json'
)
def get_entity_total_schedule_seconds(request):
    """gives entity's task total schedule_seconds
    """
    logger.debug('get_project_total_schedule_seconds starts')
    entity_id = request.matchdict.get('id')
    entity = Entity.query.filter_by(id=entity_id).first()

    sql_query = """select
        SUM(
            "Tasks".schedule_timing * (
                case "Tasks".schedule_unit
                    when 'min' then 60
                    when 'h' then 3600
                    when 'd' then 32400 -- 9 hours/day
                    when 'w' then 183600 -- 51 hours/week
                    when 'm' then 734400  -- 4 week/month * 51 hours/week
                    when 'y' then 9573418 -- 52.1428 week * 51 hours/week
                    else 0
                end
            )
        ) as schedule_seconds
    from "Tasks"
    join "Task_Resources" on "Task_Resources".task_id = "Tasks".id
    where not exists(select 1 from "Tasks" as t where t.parent_id = "Tasks".id)
    %(where_conditions)s
    """
    where_conditions = ''

    if entity.entity_type == 'Project':
        where_conditions = """and "Tasks".project_id = %(project_id)s """ % {'project_id': entity_id}
    elif entity.entity_type == 'User':
        where_conditions = """and "Task_Resources".resource_id = %(resource_id)s """ % {'resource_id': entity_id}
    elif entity.entity_type == 'Department':
        temp_buffer = [""" and ("""]
        for i, resource in enumerate(entity.users):
            if i > 0:
                temp_buffer.append(' or')
            temp_buffer.append(""" "Task_Resources".resource_id='%s'""" % resource.id)
        temp_buffer.append(' )')
        where_conditions = ''.join(temp_buffer)

    logger.debug('where_conditions: %s' % where_conditions)

    sql_query = sql_query % {'where_conditions': where_conditions}

    result = db.DBSession.connection().execute(sql_query).fetchone()

    logger.debug('get_project_total_schedule_seconds: %s' % result[0])
    return result[0]



@view_config(
    route_name='get_entity_task_min_start',
    renderer='json'
)
def get_entity_task_min_start(request):
    """gives entity's tasks min start date
    """
     
    logger.debug('get_entity_task_min_start starts')
    entity_id = request.matchdict.get('id')
    entity = Entity.query.filter_by(id=entity_id).first()

    sql_query = """select
            min(extract(epoch from "Tasks".start::timestamp AT TIME ZONE 'UTC')) as start
        from "Users"
        join "Task_Resources" on "Task_Resources".resource_id = "Users".id
        join "Tasks" on "Tasks".id = "Task_Resources".task_id

    where not exists(select 1 from "Tasks" as t where t.parent_id = "Tasks".id)
    %(where_conditions)s
    """
    where_conditions = ''

    if entity.entity_type == 'Project':
        where_conditions = """and "Tasks".project_id = %(project_id)s """ % {'project_id': entity_id}
    elif entity.entity_type == 'User':
        where_conditions = """and "Task_Resources".resource_id = %(resource_id)s """ % {'resource_id': entity_id}
    elif entity.entity_type == 'Department':
        temp_buffer = [""" and ("""]
        for i, resource in enumerate(entity.users):
            if i > 0:
                temp_buffer.append(' or')
            temp_buffer.append(""" "Task_Resources".resource_id='%s'""" % resource.id)
        temp_buffer.append(' )')
        where_conditions = ''.join(temp_buffer)

    logger.debug('where_conditions: %s' % where_conditions)

    sql_query = sql_query % {'where_conditions': where_conditions}

    result = db.DBSession.connection().execute(sql_query).fetchone()

    return result[0]

@view_config(
    route_name='get_entity_task_max_end',
    renderer='json'
)
def get_entity_task_max_end(request):
    """gives entity's tasks max end date
    """
     
    logger.debug('get_entity_task_max_end starts')
    entity_id = request.matchdict.get('id')
    entity = Entity.query.filter_by(id=entity_id).first()

    sql_query = """select
            max(extract(epoch from "Tasks".end::timestamp AT TIME ZONE 'UTC')) as end
        from "Users"
        join "Task_Resources" on "Task_Resources".resource_id = "Users".id
        join "Tasks" on "Tasks".id = "Task_Resources".task_id

    where not exists(select 1 from "Tasks" as t where t.parent_id = "Tasks".id)
    %(where_conditions)s
    """
    where_conditions = ''

    if entity.entity_type == 'Project':
        where_conditions = """and "Tasks".project_id = %(project_id)s """ % {'project_id': entity_id}
    elif entity.entity_type == 'User':
        where_conditions = """and "Task_Resources".resource_id = %(resource_id)s """ % {'resource_id': entity_id}
    elif entity.entity_type == 'Department':
        temp_buffer = [""" and ("""]
        for i, resource in enumerate(entity.users):
            if i > 0:
                temp_buffer.append(' or')
            temp_buffer.append(""" "Task_Resources".resource_id='%s'""" % resource.id)
        temp_buffer.append(' )')
        where_conditions = ''.join(temp_buffer)

    logger.debug('where_conditions: %s' % where_conditions)

    sql_query = sql_query % {'where_conditions': where_conditions}

    result = db.DBSession.connection().execute(sql_query).fetchone()

    return result[0]


