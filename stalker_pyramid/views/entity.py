# -*- coding: utf-8 -*-
import re
import logging

from pyramid.httpexceptions import HTTPServerError, HTTPOk, HTTPForbidden
from pyramid.view import view_config
from pyramid.response import Response

from stalker.db.session import DBSession
from stalker import defaults, Entity, Studio, Project, Task, Status
import transaction

import stalker_pyramid
from stalker_pyramid.views import (PermissionChecker, get_logged_in_user,
                                   milliseconds_since_epoch, get_multi_integer,
                                   multi_permission_checker, get_multi_string,
                                   StdErrToHTMLConverter)

from stalker_pyramid import logger_name

logger = logging.getLogger(logger_name)


@view_config(
    route_name='list_studio_clients',
    renderer='templates/client/list/list_studio_clients.jinja2'
)
@view_config(
    route_name='view_client',
    renderer='templates/client/view/view_client.jinja2'
)
@view_config(
    route_name='view_invoice',
    renderer='templates/invoice/view/view_invoice.jinja2'
)
@view_config(
    route_name='list_client_users',
    renderer='templates/auth/list/list_client_users.jinja2'
)
@view_config(
    route_name='update_user_dialog',
    renderer='templates/auth/dialog/update_user_dialog.jinja2',
)
@view_config(
    route_name='view_user_profile',
    renderer='templates/auth/view/view_user_profile.jinja2',
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
    route_name='list_entity_users_role',
    renderer='templates/auth/list/list_entity_users_role.jinja2'
)
@view_config(
    route_name='list_studio_users',
    renderer='templates/auth/list/list_entity_users.jinja2'
)
@view_config(
    route_name='list_project_users',
    renderer='templates/auth/list/list_project_users.jinja2'
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
    renderer='templates/project/dialog/project_dialog.jinja2',
)
@view_config(
    route_name='update_project_dialog',
    renderer='templates/project/dialog/project_dialog.jinja2',
)
@view_config(
    route_name='update_project_details_view',
    renderer='templates/project/dialog/update_project_details_view.jinja2',
)
@view_config(
    route_name='view_project_reports',
    renderer='templates/project/report/view_project_reports.jinja2'
)
@view_config(
    route_name='view_project_cost_sheet',
    renderer='templates/project/report/view_project_cost_sheet.jinja2'
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
    route_name='list_user_timelogs',
    renderer='templates/time_log/list/list_entity_timelogs.jinja2'
)
@view_config(
    route_name='list_user_versions',
    renderer='templates/version/list/list_entity_versions.jinja2'
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
    route_name='list_entity_notes_inmodal',
    renderer='templates/note/list/list_notes.jinja2'
)
@view_config(
    route_name='list_project_notes',
    renderer='templates/note/list/list_project_notes.jinja2'
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
    renderer='templates/budget/view/view_budget.jinja2',
    permission='Read_Budget'
)
@view_config(
    route_name='list_project_budgets',
    renderer='templates/budget/list/list_project_budgets.jinja2',
    permission='List_Budget'

)
@view_config(
    route_name='list_budget_invoices',
    renderer='templates/invoice/list/list_budget_invoices.jinja2',
    permission='List_Invoice'
)
@view_config(
    route_name='list_entity_invoices',
    renderer='templates/invoice/list/list_entity_invoices.jinja2',
    permission='List_Invoice'
)
@view_config(
    route_name='list_studio_goods',
    renderer='templates/good/list/list_studio_goods.jinja2',
    permission='List_Good'
)
@view_config(
    route_name='test_page',
    renderer='templates/test_page.jinja2'
)
@view_config(
    route_name='view_entity_result',
    renderer='templates/entity/view_entity_result.jinja2'
)
@view_config(
    route_name='list_entity_related_assets',
    renderer='templates/asset/list/list_entity_related_assets.jinja2'
)
@view_config(
    route_name='list_entity_authlogs',
    renderer='templates/authlog/list_entity_authlogs.jinja2'
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
    if not mode:
        mode = request.params.get('mode', None)

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
    """removes the user with the given id
    """
    logger.debug('remove_entity_from_entity_dialog is starts')

    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    selected_entity_id = request.matchdict.get('entity_id', -1)
    selected_entity = Entity.query.filter_by(id=selected_entity_id).first()

    came_from = request.params.get('came_from', request.current_route_path())

    action = '/entities/%s/%s/remove?came_from=%s' % (entity_id, selected_entity_id, came_from)
    message = 'Are you sure you want to <strong>remove %s from %s</strong>?' % (selected_entity.name, entity.name)

    logger.debug('action: %s' % action)

    return {
        'came_from': came_from,
        'message': message,
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
        raise HTTPForbidden(headers=request)

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
            (extract(epoch from "TimeLogs".start) * 1000)::bigint as start,
            (extract(epoch from "TimeLogs".end) * 1000)::bigint as end,
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
            (extract(epoch from "Vacations".start) * 1000)::bigint as start,
            (extract(epoch from "Vacations".end) * 1000)::bigint as end,
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
            (extract(epoch from "Tasks".computed_start) * 1000)::bigint as start,
            (extract(epoch from "Tasks".computed_end) * 1000)::bigint as end,
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

    result = DBSession.connection().execute(sql_query)
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

        # logger.debug('sql_query:  %s' % sql_query)

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
    logger.debug("entity_name : %s" % entity.name)

    results = []
    project = None
    if entity.entity_type == "Task" or entity.entity_type == "Asset" or entity.entity_type == "Shot" or entity.entity_type == "Sequence":
        project = entity.project
    elif entity.entity_type == "Project":
        project = entity

    logger.debug("project_name : %s" % project)

    if q_entity_type:

        query_string = '%(class_name)s.query.filter(%(class_name)s.name.ilike(\'%%%(qString)s%%\')).order_by(%(class_name)s.name.asc())'
        logger.debug(query_string)
        query_string = query_string % {'class_name': q_entity_type, 'qString': qString}

        logger.debug(query_string)
        q = eval(query_string)

        results = q.all()
    else:
        if project:
            results = Task.query.filter(
                            Task.name.ilike('%' + qString + '%')
                        ).filter(Task.project == project).order_by(Task.name.asc()).all()
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
    #entity = Entity.query.get(entity_id)

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
    SUM(("Tasks".schedule_timing
             * (
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
            - coalesce(timelogs.total_timelogs, 0)
            )
            / %(division)s
         )
         as schedule_seconds

    from "Tasks"
    join "Task_Resources" on "Task_Resources".task_id = "Tasks".id
    join "Statuses" on "Statuses".id = "Tasks".status_id
    left outer join (
        select
            "Tasks".id as task_id,
            sum(extract(epoch from "TimeLogs".end - "TimeLogs".start)) as total_timelogs
        from "TimeLogs"
        join "Tasks" on "Tasks".id = "TimeLogs".task_id

        group by "Tasks".id
    ) as timelogs on timelogs.task_id = "Tasks".id

   where "Statuses".code !='CMPL'
    %(where_conditions)s
    """
    where_conditions = ''
    division = '1'

    if entity.entity_type == 'Project':
        where_conditions = """and "Tasks".project_id = %(project_id)s """ % {'project_id': entity_id}
    elif entity.entity_type == 'User':
        where_conditions = """and "Task_Resources".resource_id = %(resource_id)s """ % {'resource_id': entity_id}
        division = """(
                select
                    count(1)
                from "Task_Resources" as inner_task_resources
                where inner_task_resources.task_id = "Tasks".id
            )"""
    elif entity.entity_type == 'Department':

        temp_buffer = [""" and ("""]
        for i, resource in enumerate(entity.users):
            if i > 0:
                temp_buffer.append(' or')
            temp_buffer.append(""" "Task_Resources".resource_id='%s'""" % resource.id)
        temp_buffer.append(' )')
        where_conditions = ''.join(temp_buffer)

        division = """(
                select
                    count(1)
                from "Task_Resources" as inner_task_resources
                where inner_task_resources.task_id = "Tasks".id
            )"""

    logger.debug('where_conditions: %s' % where_conditions)

    sql_query = sql_query % {'where_conditions': where_conditions, 'division':division}

    result = DBSession.connection().execute(sql_query).fetchone()

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
            min(extract(epoch from "Tasks".start)) as start
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

    result = DBSession.connection().execute(sql_query).fetchone()

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
            max(extract(epoch from "Tasks".end)) as end
        from "Users"
        join "Task_Resources" on "Task_Resources".resource_id = "Users".id
        join "Tasks" on "Tasks".id = "Task_Resources".task_id

    --where not exists(select 1 from "Tasks" as t where t.parent_id = "Tasks".id)
    %(where_conditions)s
    """
    where_conditions = ''

    if entity.entity_type == 'Project':
        where_conditions = """where "Tasks".project_id = %(project_id)s """ % {'project_id': entity_id}
    elif entity.entity_type == 'User':
        where_conditions = """where "Task_Resources".resource_id = %(resource_id)s """ % {'resource_id': entity_id}
    elif entity.entity_type == 'Department':
        temp_buffer = ["""where ("""]
        for i, resource in enumerate(entity.users):
            if i > 0:
                temp_buffer.append(' or')
            temp_buffer.append(""" "Task_Resources".resource_id='%s'""" % resource.id)
        temp_buffer.append(' )')
        where_conditions = ''.join(temp_buffer)

    logger.debug('where_conditions: %s' % where_conditions)

    sql_query = sql_query % {'where_conditions': where_conditions}

    result = DBSession.connection().execute(sql_query).fetchone()

    return result[0]


@view_config(
    route_name='get_entity_thumbnail',
    renderer='json'
)
def get_entity_thumbnail(request):
    """returns entity thumbnail, this is good for one single entity
    """
    entity_id = request.matchdict['id']
    entity = Entity.query.filter(Entity.id == entity_id).first()

    thumbnail_path = None

    if entity:
        if entity.thumbnail:
            thumbnail_path = entity.thumbnail.full_path
        else:
            if isinstance(entity, Task):
                for parent in reversed(entity.parents):
                    if parent.thumbnail:
                        thumbnail_path = parent.thumbnail.full_path
                        break

    logger.debug('thumbnail_path: %s' % thumbnail_path)
    return {
        'thumbnail_path': thumbnail_path
    }


@view_config(
    route_name='get_entity_authlogs',
    renderer='json'
)
def get_entity_authlogs(request):

    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()
    if not entity:
        transaction.abort()
        return Response('Can not find a entity with id: %s' % entity_id, 500)

    sql_query = """
    select
        "AuthenticationLogs".uid as uid,
        "AuthenticationLogs".action as action,
        "AuthenticationLogs".date as date
        %(attributes)s
    
    from "AuthenticationLogs"
    %(join_tables)s
    
    %(where_conditions)s
    """
    where_conditions = ''
    join_tables = ''
    attributes = ''

    if entity.entity_type == 'User':
        where_conditions = """where "AuthenticationLogs".uid = %(user_id)s """ % {'user_id': entity_id}

    elif entity.entity_type == 'Project':
        attributes = """,  "Role_SimpleEntities".name"""
        join_tables = """join "Project_Users" on "Project_Users".user_id = "AuthenticationLogs".uid
                        join "SimpleEntities" as "Role_SimpleEntities" on "Role_SimpleEntities".id = "Project_Users".rid """

        temp_buffer = ["""where  ("""]
        for i, user in enumerate(entity.users):
            if i > 0:
                temp_buffer.append(' or')
            temp_buffer.append(""" "AuthenticationLogs".uid='%s'""" % user.id)
        temp_buffer.append(' )')
        where_conditions = ''.join(temp_buffer)

    logger.debug('where_conditions: %s' % where_conditions)

    sql_query = sql_query % {
        'where_conditions': where_conditions,
        'join_tables': join_tables,
        'attributes': attributes
    }

    # logger.debug('sql_query: %s' % sql_query)

    from sqlalchemy import text  # to be able to use "%" sign use this function
    result = DBSession.connection().execute(text(sql_query))
    return [
        {
            'user_id': r['uid'],
            'action': r['action'],
            'date_created': milliseconds_since_epoch(r['date']),
            'role_name':  r[3] if len(r) > 3 else ''
        }
        for r in result.fetchall()
    ]


@view_config(
    route_name='get_entity_task_type_result',
    renderer='json'
)
def get_entity_task_type_result(request):
    """gives get_entity_task_type_result
    """
    logger.debug('get_entity_task_type_result starts')
    entity_id = request.matchdict.get('id')
    entity = Entity.query.filter_by(id=entity_id).first()

    task_type = request.matchdict.get('task_type')
    project_id = request.params.get('project_id', -1)

    logger.debug('project_id %s' % project_id)
    project = Project.query.filter_by(id=project_id).first()
    if not project:
        return 'There is no project with id %s' % project_id

    sql_query = """
select
        -- min(extract(epoch from results.start)) as start,
        -- min(extract(epoch from results.scheduled_start)) as scheduled_start,
        array_agg(distinct(results.shot_name)) as shot_names,
        results.resource_id as resource_ids,
        results.scheduled_resource_id as scheduled_resource_ids,
        sum(results.approved_shot_seconds*results.timelog_duration/results.schedule_seconds) as approved_shot_seconds,
        sum(results.shot_seconds*results.timelog_duration/results.schedule_seconds) as shot_seconds,
        sum(results.approved_timelog_duration/results.schedule_seconds) as approved_percent,
        sum(results.timelog_duration/results.schedule_seconds) as percent,
        sum(results.shot_seconds*1.00) as total_assigned_shot_seconds,
        -- results.scene_name as scene_name
        results.sequence_name as sequence_name

from (
        select
            "TimeLogs".start as start,
            tasks.start as scheduled_start,
            tasks.shot_name as shot_name,
            -- tasks.scene_name as scene_name,
            tasks.sequence_name as sequence_name,
            tasks.status_code as shot_status,
            "TimeLogs".resource_id as resource_id,
            resource_info.resource_id as scheduled_resource_id,
            tasks.seconds as shot_seconds,
            (case tasks.status_code
                        when 'CMPL' then tasks.seconds
                        else 0
                    end) as approved_shot_seconds,

            tasks.schedule_seconds,
            (case tasks.status_code
                        when 'CMPL' then (extract(epoch from "TimeLogs".end - "TimeLogs".start))
                        else 0
                    end) as approved_timelog_duration,
            (extract(epoch from "TimeLogs".end - "TimeLogs".start)) as timelog_duration


        from (
                select "Tasks".id as id,
                       "Tasks".schedule_timing *(case "Tasks".schedule_unit
                                                    when 'min' then 60
                                                    when 'h' then 3600
                                                    when 'd' then 32400
                                                    when 'w' then 147600
                                                    when 'm' then 590400
                                                    when 'y' then 7696277
                                                    else 0
                                                end) as schedule_seconds,
                        "Shot_SimpleEntities".name as shot_name,
                        ("Shots".cut_out - "Shots".cut_in)/(coalesce("Shots".fps, %(project_fps)s)) as seconds,
                        "Statuses".code as status_code,
                        -- "Scene_SimpleEntities".name as scene_name,
                        "Sequence_SimpleEntities".name as sequence_name,

                        "Tasks".start as start

                from "Tasks"
                join "SimpleEntities" as "Task_SimpleEntities" on "Task_SimpleEntities".id = "Tasks".id
                join "SimpleEntities" as "Type_SimpleEntities" on "Type_SimpleEntities".id = "Task_SimpleEntities".type_id
                join "Shots" on "Shots".id = "Tasks".parent_id
                join "SimpleEntities" as "Shot_SimpleEntities" on "Shot_SimpleEntities".id = "Shots".id
                join "Statuses" on "Statuses".id = "Tasks".status_id
                join "Tasks" as "Shot_Tasks" on "Shot_Tasks".id = "Shots".id

                -- join "Tasks" as "Shot_Folders" on "Shot_Folders".id = "Shot_Tasks".parent_id
                -- join "Tasks" as "Scenes" on "Scenes".id = "Shot_Folders".parent_id
                left join "Shot_Sequences" on "Shots".id = "Shot_Sequences".shot_id
                left join "Sequences" on "Shot_Sequences".sequence_id = "Sequences".id

                --join "SimpleEntities" as "Scene_SimpleEntities" on "Scene_SimpleEntities".id = "Scenes".id
                join "SimpleEntities" as "Sequence_SimpleEntities" on "Sequence_SimpleEntities".id = "Sequences".id

                where "Type_SimpleEntities".name = '%(task_type)s' %(project_query)s
            ) as tasks
        left outer join (
            select
                "Tasks".id as task_id,
                array_agg("Task_Resources".resource_id) as resource_id
            from "Tasks"
            join "Task_Resources" on "Tasks".id = "Task_Resources".task_id
            group by "Tasks".id
        ) as resource_info on tasks.id = resource_info.task_id

        left outer join "TimeLogs" on tasks.id = "TimeLogs".task_id
        where exists (
                    select * from (
                        select unnest(resource_info.resource_id)
                    ) x(resource_id)
                    where %(resource_where_conditions)s
                )
    ) as results
group by  -- date_trunc('week', results.start),
          results.resource_id,
          results.scheduled_resource_id,
          -- results.scene_name
          results.sequence_name
order by sequence_name, resource_ids
"""

    resource_where_conditions = ''
    if entity.entity_type == 'User':
        resource_where_conditions = """x.resource_id = %(resource_id)s """ % {'resource_id': entity_id}
    elif entity.entity_type == 'Department' or entity.entity_type == 'Project':
        temp_buffer = ["""("""]
        for i, resource in enumerate(entity.users):
            if i > 0:
                temp_buffer.append(' or')
            temp_buffer.append(""" x.resource_id='%s'""" % resource.id)
        temp_buffer.append(' )')
        resource_where_conditions = ''.join(temp_buffer)

    project_query = """ and "Tasks".project_id = %(project_id)s""" % {'project_id': project.id}
    logger.debug('project_query:  %s' % project_query)
    sql_query = sql_query % {'resource_where_conditions': resource_where_conditions,
                             'task_type': task_type,
                             'project_query': project_query,
                             'project_fps': project.fps
                             }

    # logger.debug('sql_query:  %s' % sql_query)
    result = DBSession.connection().execute(sql_query).fetchall()

    return [{
        # 'start_date': r['start'] if r['start'] else r['scheduled_start'],
        # 'scheduled_start_date': r['scheduled_start'],
        'shot_names': r['shot_names'],
        'resource_ids': [r['resource_ids']] if r['resource_ids'] else r['scheduled_resource_ids'],
        'scheduled_resource_ids': r['scheduled_resource_ids'],
        'approved_seconds': r['approved_shot_seconds'] if r['approved_shot_seconds'] else 0,
        'total_seconds': r['shot_seconds'] if r['shot_seconds'] else 0,
        'approved_shots':r['approved_percent'] if r['approved_percent'] else 0,
        'total_shots':r['percent'] if r['percent'] else 0,
        'total_assigned_shot_seconds':float(r['total_assigned_shot_seconds']),
        'sequence_name':r['sequence_name']
    } for r in result]


@view_config(
    route_name='get_entity_task_type_assigned',
    renderer='json'
)
def get_entity_task_type_assigned(request):
    """gives get_entity_task_type_result
    """
    logger.debug('get_entity_task_type_result starts')
    entity_id = request.matchdict.get('id')
    entity = Entity.query.filter_by(id=entity_id).first()

    task_type = request.matchdict.get('task_type')
    project_id = request.params.get('project_id', -1)

    logger.debug('project_id %s' % project_id)
    project = Project.query.filter_by(id=project_id).first()
    if not project:
        return 'There is no project with id %s' % project_id

    sql_query = """
select
            results.seq_name as seq_name,
            array_agg(distinct(results.shot_name)) as shot_names,
            sum(results.shot_seconds*1.00) as total_assigned_shot_seconds

    from (
            select
                tasks.start as scheduled_start,
                tasks.shot_name as shot_name,
                tasks.seq_name as seq_name,
                tasks.status_code as shot_status,
                resource_info.resource_id as scheduled_resource_id,
                tasks.seconds as shot_seconds

            from (
                    select "Tasks".id as id,
                            "Shot_SimpleEntities".name as shot_name,
                            ("Shots".cut_out - "Shots".cut_in)/%(project_fps)s as seconds,
                            "Statuses".code as status_code,
                            "Sequence_SimpleEntities".name as seq_name,
                            "Tasks".start as start

                    from "Tasks"
                    join "SimpleEntities" as "Task_SimpleEntities" on "Task_SimpleEntities".id = "Tasks".id
                    join "SimpleEntities" as "Type_SimpleEntities" on "Type_SimpleEntities".id = "Task_SimpleEntities".type_id
                    join "Shots" on "Shots".id = "Tasks".parent_id
                    join "SimpleEntities" as "Shot_SimpleEntities" on "Shot_SimpleEntities".id = "Shots".id
                    join "Statuses" on "Statuses".id = "Tasks".status_id
                    join "Tasks" as "Shot_Tasks" on "Shot_Tasks".id = "Shots".id
                    join "Tasks" as "Shot_Folders" on "Shot_Folders".id = "Shot_Tasks".parent_id
                    join "Tasks" as "Scenes" on "Scenes".id = "Shot_Folders".parent_id
                    join "Tasks" as "Sequences" on "Sequences".id = "Scenes".parent_id
                    join "SimpleEntities" as "Sequence_SimpleEntities" on "Sequence_SimpleEntities".id = "Sequences".id

                    where "Type_SimpleEntities".name = '%(task_type)s'  %(project_query)s
                ) as tasks

            left outer join (
                select
                    "Tasks".id as task_id,
                    array_agg("Task_Resources".resource_id) as resource_id
                from "Tasks"
                join "Task_Resources" on "Tasks".id = "Task_Resources".task_id
                group by "Tasks".id
            ) as resource_info on tasks.id = resource_info.task_id

            where exists (
                select * from (
                    select unnest(resource_info.resource_id)
                ) x(resource_id)
                where %(resource_where_conditions)s
            )
        ) as results
    group by
              results.seq_name
    order by seq_name
"""

    resource_where_conditions = ''
    if entity.entity_type == 'User':
        resource_where_conditions = """x.resource_id = %(resource_id)s """ % {'resource_id': entity_id}
    elif entity.entity_type == 'Department' or entity.entity_type == 'Project':
        temp_buffer = ["""("""]
        for i, resource in enumerate(entity.users):
            if i > 0:
                temp_buffer.append(' or')
            temp_buffer.append(""" x.resource_id='%s'""" % resource.id)
        temp_buffer.append(' )')
        resource_where_conditions = ''.join(temp_buffer)

    project_query = """ and "Tasks".project_id = %(project_id)s""" % {'project_id': project.id}
    logger.debug('project_query:  %s' % project_query)
    sql_query = sql_query % {'resource_where_conditions': resource_where_conditions,
                             'task_type': task_type,
                             'project_query': project_query,
                             'project_fps': project.fps
                             }

    # logger.debug('sql_query:  %s' % sql_query)
    result = DBSession.connection().execute(sql_query).fetchall()

    return [{
        'seq_name': r[0],
        'shot_names': r[1],
        'total_assigned_shot_seconds': float(r[2])
    } for r in result]