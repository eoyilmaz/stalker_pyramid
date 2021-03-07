# -*- coding: utf-8 -*-

import pytz
import datetime

import transaction
from pyramid.httpexceptions import HTTPOk
from pyramid.response import Response
from pyramid.view import view_config
from stalker import Type, Status, Asset, Studio, Entity, Project, Task, Shot
from stalker.db.session import DBSession

import logging
from webob import Response
import stalker_pyramid
from stalker_pyramid.views import (get_logged_in_user, PermissionChecker,
                                   milliseconds_since_epoch, get_multi_string,
                                   get_multi_integer)
from stalker_pyramid.views.shot import update_shot_task_dependencies
from stalker_pyramid.views.task import generate_recursive_task_query

from stalker_pyramid import logger_name
logger = logging.getLogger(logger_name)


@view_config(
    route_name='update_asset',
    permission='Update_Asset'
)
def update_asset(request):
    """updates an Asset
    """
    logger.debug('***update_asset method starts ***')
    logged_in_user = get_logged_in_user(request)

    # get params
    asset_id = request.matchdict.get('id', -1)
    asset = Asset.query.filter_by(id=asset_id).first()

    name = request.params.get('name')
    code = request.params.get('code')
    description = request.params.get('description')
    type_name = request.params.get('type_name')

    status_id = request.params.get('status_id')
    status = Status.query.filter_by(id=status_id).first()

    if asset and name and code and type_name and status:
        # get the type
        type_ = Type.query\
            .filter_by(target_entity_type='Asset')\
            .filter_by(name=type_name)\
            .first()

        if type_ is None:
            # create a new Type
            type_ = Type(
                name=type_name,
                code=type_name,
                target_entity_type='Asset'
            )

        # update the asset
        logger.debug('code      : %s' % code)
        asset.name = name
        asset.code = code
        asset.description = description
        asset.type = type_
        asset.status = status
        asset.updated_by = logged_in_user
        utc_now = datetime.datetime.now(pytz.utc)
        asset.date_updated = utc_now

        DBSession.add(asset)

    return HTTPOk()


@view_config(
    route_name='get_entity_assets_count',
    renderer='json',
    permission='List_Asset'
)
@view_config(
    route_name='get_project_assets_count',
    renderer='json',
    permission='List_Asset'
)
def get_assets_count(request):
    """returns the count of assets in a project
    """
    logger.debug("get_assets_count is started")
    project_id = request.matchdict.get('id', -1)

    sql_query = """select count(1)
    from "Assets"
        join "Tasks" on "Assets".id = "Tasks".id
    where "Tasks".project_id = %s
    """ % project_id

    asset_count = DBSession.connection().execute(sql_query).fetchone()[0]
    logger.debug("get_assets_count: %s" % asset_count)
    return asset_count


@view_config(
    route_name='list_project_assets',
    renderer='templates/asset/list/list_entity_assets.jinja2'
)
def list_project_assets(request):
    """view for generic data
    """
    logger.debug('get_entity_related_data')
    logged_in_user = get_logged_in_user(request)

    asset_type_id = request.params.get('asset_type_id', None)

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
        'asset_type_id':asset_type_id,
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
    route_name='get_assets_types',
    renderer='json'
)
def get_assets_types(request):
    """returns the Asset Types
    """

    project_id = request.params.get('project_id', None)
    project = Project.query.filter(Project.id == project_id).first()

    sql_query = """select
     "Assets_Types_SimpleEntities".id,
     "Assets_Types_SimpleEntities".name

     from "Assets"

     join "SimpleEntities" as "Assets_SimpleEntities" on "Assets_SimpleEntities".id = "Assets".id
     join "SimpleEntities" as "Assets_Types_SimpleEntities" on "Assets_Types_SimpleEntities".id = "Assets_SimpleEntities".type_id

     %(where_condition)s
     group by
        "Assets_Types_SimpleEntities".name,
        "Assets_Types_SimpleEntities".id
     order by "Assets_Types_SimpleEntities".name
     """

    where_condition = ""
    if project:
        where_condition = """join "Tasks" on "Tasks".id = "Assets".id
                             where "Tasks".project_id = %(project_id)s """ % \
                          {'project_id': project.id}

    sql_query = sql_query % {'where_condition': where_condition}

    result = DBSession.connection().execute(sql_query)

    return_data = [
        {
            'asset_type_id': r[0],
            'asset_type_name': r[1]

        }
        for r in result.fetchall()
    ]

    content_range = '%s-%s/%s'

    type_count = len(return_data)
    content_range = content_range % (0, type_count - 1, type_count)

    logger.debug('content_range : %s' % content_range)

    resp = Response(
        json_body=return_data
    )
    resp.content_range = content_range
    return resp


@view_config(
    route_name='get_assets_children_task_type',
    renderer='json'
)
@view_config(
    route_name='get_assets_type_task_types',
    renderer='json'
)
def get_assets_type_task_types(request):
    """returns the Task Types defined under the Asset container
    """
    type_id = request.matchdict.get('t_id', None)

    logger.debug('type_id %s'% type_id)

    sql_query = """select
        "SimpleEntities".id as type_id,
        "SimpleEntities".name as type_name
    from "SimpleEntities"
    join "SimpleEntities" as "Task_SimpleEntities" on "SimpleEntities".id = "Task_SimpleEntities".type_id
    join "Tasks" on "Task_SimpleEntities".id = "Tasks".id

    join "Assets" on "Tasks".parent_id = "Assets".id
    join "SimpleEntities" as "Assets_SimpleEntities" on "Assets_SimpleEntities".id = "Assets".id

    %(where_condition)s

    group by "SimpleEntities".id, "SimpleEntities".name
    order by "SimpleEntities".name"""

    where_condition = ''

    if type_id:
        where_condition = 'where "Assets_SimpleEntities".type_id = %(type_id)s' % {'type_id': type_id}

    sql_query = sql_query % {'where_condition': where_condition}

    result = DBSession.connection().execute(sql_query)

    return_data = [
        {
            'id': r[0],
            'name': r[1]

        }
        for r in result.fetchall()
    ]

    content_range = '%s-%s/%s'

    type_count = len(return_data)
    content_range = content_range % (0, type_count - 1, type_count)

    logger.debug('content_range : %s' % content_range)

    resp = Response(
        json_body=return_data
    )
    resp.content_range = content_range
    return resp


@view_config(
    route_name='get_entity_assets',
    renderer='json',
    permission='List_Asset'
)
@view_config(
    route_name='get_project_assets',
    renderer='json',
    permission='List_Asset'
)
def get_assets(request):
    """returns all the Assets of a given Project
    """
    logger.debug('*** get_assets method starts ***')

    project_id = request.matchdict.get('id', -1)
    asset_type_id = request.params.get('asset_type_id', None)

    asset_id = request.params.get('entity_id', None)
    parent_name = request.params.get('parent_name', None)

    asset_type_names = get_multi_string(request, 'asset_type_names')

    logger.debug('asset_type_names : %s' % asset_type_names)

    sql_query = """
        select
            "Assets".id as asset_id,
            assets.full_path as asset_name,
            "Asset_SimpleEntities".description as asset_description,
            "Links".full_path as asset_full_path,
            "Distinct_Asset_Statuses".asset_status_code as asset_status_code,
            "Distinct_Asset_Statuses".asset_status_html_class as asset_status_html_class,
            array_agg("Distinct_Asset_Task_Types".type_name) as type_name,
            array_agg("Tasks".id) as task_id,
            array_agg("Task_SimpleEntities".name) as task_name,
            array_agg("Task_Statuses".code) as status_code,
            array_agg("Task_Statuses_SimpleEntities".html_class) as status_html_class,
            array_agg(coalesce(
                    -- for parent tasks
                    (case "Tasks".schedule_seconds
                        when 0 then 0
                        else "Tasks".total_logged_seconds::float / "Tasks".schedule_seconds * 100
                     end
                    ),
                    -- for child tasks we need to count the total seconds of related TimeLogs
                    (coalesce("Task_TimeLogs".duration, 0.0))::float /
                        ("Tasks".schedule_timing * (case "Tasks".schedule_unit
                            when 'min' then 60
                            when 'h' then 3600
                            when 'd' then 32400
                            when 'w' then 183600
                            when 'm' then 734400
                            when 'y' then 9573418
                            else 0
                        end)) * 100.0
                )) as percent_complete,
            "Assets_Types_SimpleEntities".name as asset_type_name,
            array_agg("Task_Resource_SimpleEntities".name) as resources_name,
            array_agg("Task_Resource_SimpleEntities".id) as resources_id
        from "Tasks"
        join "Assets" on "Assets".id = "Tasks".parent_id
        join (
            %(generate_recursive_task_query)s
        ) as assets on assets.id = "Assets".id
        join "SimpleEntities" as "Asset_SimpleEntities" on "Assets".id = "Asset_SimpleEntities".id
        join "SimpleEntities" as "Task_SimpleEntities" on "Tasks".id = "Task_SimpleEntities".id
        left outer join "Task_Resources"  on "Tasks".id = "Task_Resources".task_id
        left outer join "SimpleEntities" as "Task_Resource_SimpleEntities" on "Task_Resources".resource_id = "Task_Resource_SimpleEntities".id
        left join "Types" as "Assets_Types" on "Assets_Types".id = "Asset_SimpleEntities".type_id
        join "SimpleEntities" as "Assets_Types_SimpleEntities" on "Assets_Types_SimpleEntities".id = "Assets_Types".id
        left join "Links" on "Asset_SimpleEntities".thumbnail_id = "Links".id
        join(
            select
                "Assets".id as asset_id,
                "Statuses".code as asset_status_code,
                "SimpleEntities".html_class as asset_status_html_class
            from "Tasks"
            join "Assets" on "Assets".id = "Tasks".id
            join "Statuses" on "Statuses".id = "Tasks".status_id
            join "SimpleEntities" on "SimpleEntities".id = "Statuses".id
            )as "Distinct_Asset_Statuses" on "Assets".id = "Distinct_Asset_Statuses".asset_id
        left join (
            select
                "SimpleEntities".id as type_id,
                "SimpleEntities".name as type_name
            from "SimpleEntities"
            join "SimpleEntities" as "Task_SimpleEntities" on "SimpleEntities".id = "Task_SimpleEntities".type_id
            join "Tasks" on "Task_SimpleEntities".id = "Tasks".id
            join "Assets" on "Tasks".parent_id = "Assets".id
            group by "SimpleEntities".id, "SimpleEntities".name
            order by "SimpleEntities".id
        ) as "Distinct_Asset_Task_Types" on "Task_SimpleEntities".type_id = "Distinct_Asset_Task_Types".type_id
        join "Statuses" as "Task_Statuses" on "Tasks".status_id = "Task_Statuses".id
        join "SimpleEntities" as "Task_Statuses_SimpleEntities" on "Task_Statuses_SimpleEntities".id = "Tasks".status_id

        left outer join (
                    select
                        "TimeLogs".task_id,
                        extract(epoch from sum("TimeLogs".end - "TimeLogs".start)) as duration
                    from "TimeLogs"
                    group by task_id
                ) as "Task_TimeLogs" on "Task_TimeLogs".task_id = "Tasks".id
        where "Tasks".project_id = %(project_id)s  %(where_conditions)s
        group by
            "Assets".id,
            "Asset_SimpleEntities".name,
            assets.full_path,
            "Asset_SimpleEntities".description,
            "Links".full_path,
            "Distinct_Asset_Statuses".asset_status_code,
            "Distinct_Asset_Statuses".asset_status_html_class,
            "Assets_Types_SimpleEntities".name
        order by "Asset_SimpleEntities".name
    """

    where_conditions = ''

    if asset_type_id:
        where_conditions = """and "Assets_Types_SimpleEntities".id = %(asset_type_id)s""" %({'asset_type_id':asset_type_id})
    if asset_id:
        where_conditions = """and "Assets".id = %(asset_id)s""" %({'asset_id':asset_id})
    if len(asset_type_names):
        asset_type_names_buffer = []
        for asset_type_name in asset_type_names:
            asset_type_names_buffer.append(
                """"Assets_Types_SimpleEntities".name = '%s'""" %
                asset_type_name
            )

        logger.debug('asset_type_names_buffer : %s' % asset_type_names_buffer)
        where_conditions_for_type_names = ' or '.join(asset_type_names_buffer)
        where_conditions = """and (%s)""" % where_conditions_for_type_names
        logger.debug('where_conditions : %s' % where_conditions)

    if parent_name:
        where_conditions += """ and assets.full_path ilike (%s)""" % parent_name

    sql_query = sql_query % {
        'where_conditions': where_conditions,
        'project_id': project_id,
        'generate_recursive_task_query': generate_recursive_task_query(),
    }

    update_asset_permission = \
        PermissionChecker(request)('Update_Asset')
    delete_asset_permission = \
        PermissionChecker(request)('Delete_Asset')

    result = DBSession.connection().execute(sql_query)

    return_data = []

    for r in result.fetchall():
        r_data = {
            'id': r[0],
            'name': r[1],
            'description': r[2],
            'thumbnail_full_path': r[3] if r[3] else None,
            'status': r[4],
            'status_color': r[5],
            'update_asset_action': '/tasks/%s/update/dialog' % r[0]
                if update_asset_permission else None,
            'delete_asset_action': '/tasks/%s/delete/dialog' % r[0]
                if delete_asset_permission else None
        }
        task_types_names = r[6]
        task_ids = r[7]
        task_names = r[8]
        task_statuses = r[9]
        task_percent_complete = r[11]
        task_resource_name = r[13]
        task_resource_id = r[14]

        # logger.debug('task_types_names %s ' % task_types_names)
        r_data['nulls'] = []

        for index1 in range(len(task_types_names)):
            if task_types_names[index1]:
                r_data[task_types_names[index1]]= []

        for index in range(len(task_types_names)):
            task = {
                'id': task_ids[index],
                'name': task_names[index],
                'status': task_statuses[index],
                'percent': task_percent_complete[index],
                'resource_name': task_resource_name[index],
                'resource_id': task_resource_id[index]
            }
            if task_types_names[index]:
                r_data[task_types_names[index]].append(task)
            else:
                r_data['nulls'].append(task)

        return_data.append(r_data)

    return return_data


@view_config(
    route_name='get_entity_assets_names',
    renderer='json',
    permission='List_Asset'
)
@view_config(
    route_name='get_project_assets_names',
    renderer='json',
    permission='List_Asset'
)
def get_assets_names(request):
    """returns all the Assets of a given Project
    """
    logger.debug('*** get_assets method starts ***')

    project_id = request.matchdict.get('id', -1)
    asset_type_id = request.params.get('asset_type_id', None)

    asset_id = request.params.get('entity_id', None)
    parent_name = request.params.get('parent_name', None)
    search_name = request.params.get('search_name', None)

    asset_type_names = get_multi_string(request, 'asset_type_names')

    logger.debug('asset_type_names : %s' % asset_type_names)
    logger.debug('search_name : %s' % search_name)

    sql_query = """
        select
                "Assets".id as asset_id,
                assets.full_path as name
        from "Assets"
        join "Tasks" on "Assets".id = "Tasks".id
        join (
                    %(generate_recursive_task_query)s
                ) as assets on assets.id = "Assets".id
        join "SimpleEntities" as "Assets_SimpleEntities" on "Assets_SimpleEntities".id = "Assets".id
        join "SimpleEntities" as "Asset_Types_SimpleEntities" on "Asset_Types_SimpleEntities".id = "Assets_SimpleEntities".type_id

        where "Tasks".project_id = %(project_id)s %(where_conditions)s
    """

    where_conditions = ''

    if asset_type_id:
        where_conditions = """and "Asset_Types_SimpleEntities".id = %(asset_type_id)s""" %({'asset_type_id':asset_type_id})
    if asset_id:
        where_conditions = """and "Assets".id = %(asset_id)s""" %({'asset_id':asset_id})
    if len(asset_type_names):
        asset_type_names_buffer = []
        for asset_type_name in asset_type_names:
            asset_type_names_buffer.append(
                """"Asset_Types_SimpleEntities".name = '%s'""" %
                asset_type_name
            )

        logger.debug('asset_type_names_buffer : %s' % asset_type_names_buffer)
        where_conditions_for_type_names = ' or '.join(asset_type_names_buffer)
        where_conditions = """and (%s)""" % where_conditions_for_type_names
        logger.debug('where_conditions : %s' % where_conditions)

    if parent_name:
        where_conditions += """ and assets.full_path ilike (%s)""" % parent_name

    if search_name:
        where_conditions += """ and "Assets_SimpleEntities".name ilike '%s'""" % search_name

    logger.debug('sql_query : %s' % sql_query)
    sql_query = sql_query % {
        'where_conditions': where_conditions,
        'project_id': project_id,
        'generate_recursive_task_query': generate_recursive_task_query(),
    }
    logger.debug('sql_query : %s' % sql_query)
    from sqlalchemy import text
    result = DBSession.connection().execute(text(sql_query))

    assets = []

    for r in result.fetchall():
        asset = {
            'id': r[0],
            'name': r[1]
        }
        assets.append(asset)

    resp = Response(
        json_body=assets
    )

    logger.debug('assets : %s' % assets)

    return resp


@view_config(
    route_name='get_related_assets',
    renderer='json',
    permission='List_Asset'
)
def get_related_assets(request):
    """returns get_related_assets
        """
    logger.debug('*** get_related_assets method starts ***')

    project_id = request.matchdict.get('id', -1)

    asset_ids = get_multi_integer(request, 'asset_ids', 'GET')

    logger.debug('asset_ids : %s' % asset_ids)
    return_data = []
    if len(asset_ids):

        sql_query = """
            select  "Asset_SimpleEntities".id,
                    assets.full_path as asset_name,
                    "Asset_SimpleEntities".description,
                    "Links".full_path as asset_full_path,
                    "Distinct_Asset_Statuses".asset_status_code as asset_status_code,
                    "Distinct_Asset_Statuses".asset_status_html_class as asset_status_html_class,
                    array_agg("Distinct_Asset_Task_Types".type_name) as type_name,
                    array_agg("Distinct_Asset_Task_Types".type_id) as type_id,
                    array_agg("Tasks".id) as task_id,
                    array_agg("Task_SimpleEntities".name) as task_name,
                    array_agg("Task_Statuses".code) as status_code,
                    array_agg("Task_Resource_SimpleEntities".name) as resources_name,
                    array_agg("Task_Resource_SimpleEntities".id) as resources_id
            from "Tasks"
            join "Assets" on "Assets".id = "Tasks".parent_id
            join "SimpleEntities" as "Asset_SimpleEntities" on "Asset_SimpleEntities".id = "Assets".id
            join "SimpleEntities" as "Task_SimpleEntities" on "Task_SimpleEntities".id = "Tasks".id
            left join (
            select
                    "SimpleEntities".id as type_id,
                    "SimpleEntities".name as type_name
                from "SimpleEntities"
                join "SimpleEntities" as "Task_SimpleEntities" on "SimpleEntities".id = "Task_SimpleEntities".type_id
                join "Tasks" on "Task_SimpleEntities".id = "Tasks".id
                join "Assets" on "Tasks".parent_id = "Assets".id
                group by "SimpleEntities".id, "SimpleEntities".name
                order by "SimpleEntities".id
            ) as "Distinct_Asset_Task_Types" on "Task_SimpleEntities".type_id = "Distinct_Asset_Task_Types".type_id
            join "Statuses" as "Task_Statuses" on "Tasks".status_id = "Task_Statuses".id
            join (
                %(generate_recursive_task_query)s
            ) as assets on assets.id = "Assets".id
            left join "Links" on "Asset_SimpleEntities".thumbnail_id = "Links".id
            left outer join "Task_Resources"  on "Tasks".id = "Task_Resources".task_id
            left outer join "SimpleEntities" as "Task_Resource_SimpleEntities" on "Task_Resources".resource_id = "Task_Resource_SimpleEntities".id
            join(
                select
                    "Assets".id as asset_id,
                    "Statuses".code as asset_status_code,
                    "SimpleEntities".html_class as asset_status_html_class
                from "Tasks"
                join "Assets" on "Assets".id = "Tasks".id
                join "Statuses" on "Statuses".id = "Tasks".status_id
                join "SimpleEntities" on "SimpleEntities".id = "Statuses".id
                )as "Distinct_Asset_Statuses" on "Assets".id = "Distinct_Asset_Statuses".asset_id
            where %(where_conditions)s
            group by
                "Asset_SimpleEntities".id,
                assets.full_path,
                "Asset_SimpleEntities".description,
                "Links".full_path,
                "Distinct_Asset_Statuses".asset_status_code,
                "Distinct_Asset_Statuses".asset_status_html_class
        """

        asset_id_buffer = []
        for asset_id in asset_ids:
            asset_id_buffer.append(
                """"Asset_SimpleEntities".id = '%s'""" %
                asset_id
            )

        logger.debug('asset_id_buffer : %s' % asset_id_buffer)
        where_conditions = ' or '.join(asset_id_buffer)
        logger.debug('where_conditions : %s' % where_conditions)

        sql_query = sql_query % {
            'where_conditions': where_conditions,
            'generate_recursive_task_query': generate_recursive_task_query(),
        }

        update_asset_permission = \
            PermissionChecker(request)('Update_Asset')
        delete_asset_permission = \
            PermissionChecker(request)('Delete_Asset')

        result = DBSession.connection().execute(sql_query)
        all_types_list = []


        for r in result.fetchall():
            r_data = {
                'id': r[0],
                'name': r[1],
                'description': r[2],
                'thumbnail_full_path': r[3] if r[3] else None,
                'status': r[4],
                'status_color': r[5],
                'update_asset_action': '/tasks/%s/update/dialog' % r[0]
                    if update_asset_permission else None,
                'delete_asset_action': '/tasks/%s/delete/dialog' % r[0]
                    if delete_asset_permission else None
            }
            task_types_names = r[6]
            task_types_ids = r[7]
            task_ids = r[8]
            task_names = r[9]
            task_statuses = r[10]
            task_resource_name = r[11]
            task_resource_id = r[12]

            # logger.debug('task_types_names %s ' % task_types_names)
            r_data['nulls'] = []

            for index1 in range(len(task_types_names)):
                if task_types_names[index1]:
                    r_data[task_types_names[index1]]= []
                    if {'name':task_types_names[index1], 'id':task_types_ids[index1]} not in all_types_list:
                        all_types_list.append({'name':task_types_names[index1], 'id':task_types_ids[index1]})

            for index in range(len(task_types_names)):
                task = {
                    'id': task_ids[index],
                    'name': task_names[index],
                    'status': task_statuses[index],
                    'resource_name': task_resource_name[index],
                    'resource_id': task_resource_id[index]
                }
                if task_types_names[index]:
                    r_data[task_types_names[index]].append(task)
                else:
                    r_data['nulls'].append(task)

            return_data.append(r_data)
        return_data.append({'all_types_list': all_types_list})
    return return_data


@view_config(
    route_name='add_related_assets_dialog',
    renderer='templates/asset/dialog/add_related_assets_dialog.jinja2',
    permission='Update_Task'
)
def add_related_assets_dialog(request):
    """
    """
    logger.debug('add_related_assets_dialog starts')

    # get logged in user
    logged_in_user = get_logged_in_user(request)

    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    project_id = request.params.get('project_id', None)
    project = Project.query.filter_by(id=project_id).first()

    return {
        'mode': 'create',
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'entity': entity,
        'project': project
    }


@view_config(
    route_name='add_related_assets'
)
def add_related_assets(request):
    """
    """

    logger.debug('add_related_assets starts')

    # get logged in user
    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    if not entity:
        transaction.abort()
        return Response('There is no entity with id: %s' % entity_id, 500)

    character_ids = get_multi_integer(request, 'character_ids')
    characters = Asset.query.filter(Asset.id.in_(character_ids)).all()

    active_prop_ids = get_multi_integer(request, 'active_prop_ids')
    active_props = Asset.query.filter(Asset.id.in_(active_prop_ids)).all()
    characters.extend(active_props)

    vehicle_ids = get_multi_integer(request, 'vehicle_ids')
    vehicles = Asset.query.filter(Asset.id.in_(vehicle_ids)).all()
    characters.extend(vehicles)

    environment_ids = get_multi_integer(request, 'environment_ids')
    assets = Asset.query.filter(Asset.id.in_(environment_ids)).all()
    assets.extend(characters)

    asset_dependencies_animation = []
    asset_dependencies_lighting = []
    asset_dependencies_scene_assembly = []

    for character in characters:
        asset_dependencies_animation.append(
            find_asset_task_by_type(character, 'Rig')
        )

    for asset in assets:
        layout = find_asset_task_by_type(asset, 'Layout')
        asset_dependencies_animation.append(
            layout
        )
        asset_dependencies_scene_assembly.append(
            layout
        )
        asset_dependencies_lighting.append(
            find_asset_task_by_type(asset, 'Lighting')
        )

        asset_dependencies_lighting.append(
            find_asset_task_by_type(asset, 'Look Development')
        )

    if entity.type.name == 'Scene':
        scene = entity
        # Shots----------------------------------------------------
        shots_folder = Task.query\
            .filter(Task.name == 'Shots')\
            .filter(Task.parent == scene)\
            .first()

        if not shots_folder:
            transaction.abort()
            return Response(
                'There is no shots folder under: : %s' % entity_id,
                500
            )

        shots = Shot.query.filter(Shot.parent == shots_folder).all()
        for shot in shots:
            update_shot_task_dependencies('append', shot, 'Animation', asset_dependencies_animation, logged_in_user, utc_now)
            update_shot_task_dependencies('append', shot, 'Lighting', asset_dependencies_lighting, logged_in_user, utc_now)
            update_shot_task_dependencies('append', shot, 'Scene Assembly', asset_dependencies_scene_assembly, logged_in_user, utc_now)
    elif entity.entity_type == 'Shot':
        update_shot_task_dependencies('append', entity, 'Animation', asset_dependencies_animation, logged_in_user, utc_now)
        update_shot_task_dependencies('append', entity, 'Lighting', asset_dependencies_lighting, logged_in_user, utc_now)
        update_shot_task_dependencies('append', entity, 'Scene Assembly', asset_dependencies_scene_assembly, logged_in_user, utc_now)

    # if len(messages)>0:
    #     response_messages = \
    #             '\n'.join(messages)
    #     request.session.flash(response_messages)

    return Response('ok')


@view_config(
    route_name='remove_related_asset_dialog',
    renderer='templates/modals/confirm_dialog.jinja2',
    permission='Update_Task'
)
def remove_related_asset_dialog(request):
    """
    """
    logger.debug('remove_related_asset_dialog starts')

    entity_id = request.matchdict.get('id')
    entity = Entity.query.filter_by(id=entity_id).first()

    asset_id = request.matchdict.get('a_id')
    asset = Asset.query.filter_by(id=asset_id).first()

    action = '/entities/%s/assets/%s/remove' % (entity_id, asset_id)
    came_from = request.params.get('came_from', '/')

    message = 'Relation will be deleted between %s and %s ' \
              '<br><br>Are you sure?' % (entity.name, asset.name)

    logger.debug('action: %s' % action)

    return {
        'message': message,
        'came_from': came_from,
        'action': action
    }


@view_config(
    route_name='remove_related_asset'
)
def remove_related_assets(request):
    """
    """

    logger.debug('add_related_assets starts')

    # get logged in user
    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    asset_id = request.matchdict.get('a_id')
    asset = Asset.query.filter(Asset.id == asset_id).first()

    layout = find_asset_task_by_type(asset, 'Layout')
    asset_dependencies_animation = [find_asset_task_by_type(asset, 'Rig'), layout]
    asset_dependencies_scene_assembly = [layout]
    asset_dependencies_lighting = [find_asset_task_by_type(asset, 'Lighting'),
                                   find_asset_task_by_type(asset, 'Look Development')]

    if not entity:
        transaction.abort()
        return Response('There is no entity with id: %s' % entity_id, 500)

    if not asset:
        transaction.abort()
        return Response('There is no asset with id: %s' % asset_id, 500)

    if entity.type.name == 'Scene':
        scene = entity
        # Shots----------------------------------------------------
        shots_folder = Task.query.filter(Task.name == 'Shots').filter(Task.parent == scene).first()
        if not shots_folder:
            transaction.abort()
            return Response('There is no shots folder under: : %s' % entity_id, 500)

        shots = Shot.query.filter(Shot.parent == shots_folder).all()
        for shot in shots:
            update_shot_task_dependencies('remove', shot, 'Animation', asset_dependencies_animation, logged_in_user, utc_now)
            update_shot_task_dependencies('remove', shot, 'Scene Assembly', asset_dependencies_scene_assembly, logged_in_user, utc_now)
            update_shot_task_dependencies('remove', shot, 'Lighting', asset_dependencies_lighting, logged_in_user, utc_now)

    elif entity.entity_type == 'Shot':
        update_shot_task_dependencies('remove', entity, 'Animation', asset_dependencies_animation, logged_in_user, utc_now)
        update_shot_task_dependencies('remove', entity, 'Scene Assembly', asset_dependencies_scene_assembly, logged_in_user, utc_now)
        update_shot_task_dependencies('remove', entity, 'Lighting', asset_dependencies_lighting, logged_in_user, utc_now)

    # logger.debug('messages %s' % messages)
    # if len(messages)>0:
    #     response_messages = \
    #             '\n'.join(messages)
    #     request.session.flash(response_messages)
    return Response('Ok')


def find_asset_task_by_type(asset, type_name):
    """please add docstring
    """
    if type_name == 'Rig':
        # animation_test_type = Type.query.filter_by(name='Animation Test').first()
        # animation_bible_type = Type.query.filter_by(name='Animation Bible').first()
        # animation_bible = Task.query.filter(Task.parent == asset).filter(Task.type == animation_bible_type).first()
        #
        # if animation_bible:
        #     return animation_bible
        # else:
        #     animation_test = Task.query.filter(Task.parent == asset).filter(Task.type == animation_test_type).first()
        #     if animation_test:
        #         return animation_test
        #     else:
        rig_folder = Task.query.filter(Task.name == 'Rig').filter(Task.parent == asset).first()
        if rig_folder:
            main_rig = Task.query.filter(Task.name == 'Main').filter(Task.parent == rig_folder).first()
            if main_rig:
                return main_rig
            else:
                hires_rig = Task.query.filter(Task.name == 'Hires').filter(Task.parent == rig_folder).first()
                if hires_rig:
                    return hires_rig
                else:
                    return rig_folder
        else:
            return None
    elif type_name == 'Layout':
        task_type = Type.query.filter_by(name=type_name).first()
        layout = Task.query.filter(Task.parent == asset).filter(Task.type == task_type).first()
        if layout:
            hires_layout = Task.query.filter(Task.parent == layout).filter(Task.name == 'Hires').filter(Task.type == task_type).first()
            if hires_layout:
                return hires_layout
            else:
                return layout
    else:
        task_type = Type.query.filter_by(name=type_name).first()
        task = Task.query.filter(Task.parent == asset).filter(Task.type == task_type).first()
        return task