# -*- coding: utf-8 -*-
# Stalker a Production Shot Management System
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

from pyramid.httpexceptions import HTTPServerError, HTTPOk
from pyramid.view import view_config

from stalker.db import DBSession
from stalker import Sequence, StatusList, Status, Shot, Project, Entity

import logging
from webob import Response
from stalker_pyramid.views import get_logged_in_user, PermissionChecker, \
    get_parent_task_status

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


#
# @view_config(
#     route_name='get_scenes_children_task_type',
#     renderer='json'
# )
# def get_scenes_children_task_type(request):
#     """returns the Task Types defined under the Scene container
#     """
#
#     sql_query = """select
#         "SimpleEntities".id as type_id,
#         "SimpleEntities".name as type_name
#     from "SimpleEntities"
#     join "SimpleEntities" as "Task_SimpleEntities" on "SimpleEntities".id = "Task_SimpleEntities".type_id
#     join "Tasks" on "Task_SimpleEntities".id = "Tasks".id
#     join "Tasks" on "Tasks".parent_id = "Scenes".id
#     group by "SimpleEntities".id, "SimpleEntities".name
#     order by "SimpleEntities".name"""
#
#     result = DBSession.connection().execute(sql_query)
#
#     return_data = [
#         {
#             'id': r[0],
#             'name': r[1]
#
#         }
#         for r in result.fetchall()
#     ]
#
#     content_range = '%s-%s/%s'
#
#     type_count = len(return_data)
#     content_range = content_range % (0, type_count - 1, type_count)
#
#     logger.debug('content_range : %s' % content_range)
#
#     resp = Response(
#         json_body=return_data
#     )
#     resp.content_range = content_range
#     return resp
#
#
# @view_config(
#     route_name='get_entity_scenes_count',
#     renderer='json'
# )
# @view_config(
#     route_name='get_project_scenes_count',
#     renderer='json'
# )
# def get_scenes_count(request):
#     """returns the count of Scenes in the given Project
#     """
#     project_id = request.matchdict.get('id', -1)
#
#     sql_query = """select
#         count(1)
#     from "Scenes"
#         join "Tasks" on "Scenes".id = "Tasks".id
#     where "Tasks".project_id = %s""" % project_id
#
#     return DBSession.connection().execute(sql_query).fetchone()[0]
#

@view_config(
    route_name='get_entity_scenes',
    renderer='json'
)
@view_config(
    route_name='get_project_scenes',
    renderer='json'
)
def get_scenes(request):
    """returns all the Scenes of the given Project
    """

    logger.debug('get_scenes starts ')

    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()
    logger.debug('entity_id : %s' % entity_id)



    sql_query = """select
    "Task_Scenes".id as scene_id,
    "Task_Scenes".name as scene_name,
    "Task_Scenes".description as scene_description,
    "Task_Scenes".children_id as children_id,
    "Task_Scenes".children_type_name as children_type_name,
    "Task_Scenes".children_status_code as children_status_code,
    "Task_Scenes".child_task_resource_id as child_task_resource_id,
    "Task_Scenes".child_task_resource_name as child_task_resource_name,

    array_agg(distinct("Shots".id)) as shot_id,
    array_agg("Distinct_Shot_Task_Types".type_name) as type_name,
    array_agg("Tasks".id) as task_id,
    array_agg("Task_SimpleEntities".name) as task_name,
    array_agg("Task_Statuses".code) as status_code,
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
                    when 'w' then 147600
                    when 'm' then 590400
                    when 'y' then 7696277
                    else 0
                end)) * 100.0
        )) as percent_complete,
    array_agg("Resources_SimpleEntities".name) as resource_name,
    array_agg("Resources_SimpleEntities".id) as resource_id

from "Tasks"
join "Shots" on "Shots".id = "Tasks".parent_id
join "SimpleEntities" as "Task_SimpleEntities" on "Tasks".id = "Task_SimpleEntities".id
join "Shot_Sequences" on "Shots".id = "Shot_Sequences".shot_id

left join (
    select
        "SimpleEntities".id as type_id,
        "SimpleEntities".name as type_name
    from "SimpleEntities"
    join "SimpleEntities" as "Task_SimpleEntities" on "SimpleEntities".id = "Task_SimpleEntities".type_id
    join "Tasks" on "Task_SimpleEntities".id = "Tasks".id
    join "Shots" on "Tasks".parent_id = "Shots".id
    group by "SimpleEntities".id, "SimpleEntities".name
    order by "SimpleEntities".id
) as "Distinct_Shot_Task_Types" on "Task_SimpleEntities".type_id = "Distinct_Shot_Task_Types".type_id
join "Statuses" as "Task_Statuses" on "Tasks".status_id = "Task_Statuses".id

left outer join (
            select
                "TimeLogs".task_id,
                extract(epoch from sum("TimeLogs".end::timestamp AT TIME ZONE 'UTC' - "TimeLogs".start::timestamp AT TIME ZONE 'UTC')) as duration
            from "TimeLogs"
            group by task_id
        ) as "Task_TimeLogs" on "Task_TimeLogs".task_id = "Tasks".id

left outer join "Task_Resources" on "Tasks".id = "Task_Resources".task_id
join "SimpleEntities" as "Resources_SimpleEntities" on "Resources_SimpleEntities".id = "Task_Resources".resource_id

join "Tasks" as "Shot_As_Tasks" on "Shot_As_Tasks".id = "Shots".id
join "Tasks" as "Shot_Parents" on "Shot_Parents".id = "Shot_As_Tasks".parent_id

join(
select "Scene_SimpleEntities".name as name,
       "Scene_SimpleEntities".id as id,
       "Scene_SimpleEntities".description as description,
       array_agg("Child_SimpleEntities".id) as children_id,
       array_agg("Type_Child_SimpleEntities".name) as children_type_name,
       array_agg("Child_Task_Statuses".code) as children_status_code,
       array_agg("Child_Task_Resources_SimpleEntities".id) as child_task_resource_id,
       array_agg("Child_Task_Resources_SimpleEntities".name) as child_task_resource_name

    from "Tasks"
    join "SimpleEntities" as "Scene_SimpleEntities" on "Scene_SimpleEntities".id = "Tasks".id
    join "SimpleEntities" as "Type_SimpleEntities" on "Type_SimpleEntities".id = "Scene_SimpleEntities".type_id
    join "Tasks" as "Child_Tasks" on "Child_Tasks".parent_id = "Scene_SimpleEntities".id
    join "SimpleEntities" as "Child_SimpleEntities" on "Child_SimpleEntities".id = "Child_Tasks".id
    join "Statuses" as "Child_Task_Statuses" on "Child_Task_Statuses".id = "Child_Tasks".status_id
    join "SimpleEntities" as "Type_Child_SimpleEntities" on "Type_Child_SimpleEntities".id = "Child_SimpleEntities".type_id

    left outer join "Task_Resources" as "Child_Task_Resources" on "Child_Tasks".id = "Child_Task_Resources".task_id
    join "SimpleEntities" as "Child_Task_Resources_SimpleEntities" on "Child_Task_Resources_SimpleEntities".id = "Child_Task_Resources".resource_id


    where "Type_SimpleEntities".name = 'Scene'

    group by "Scene_SimpleEntities".name,
        "Scene_SimpleEntities".id

    order by "Scene_SimpleEntities".name
) as "Task_Scenes" on "Task_Scenes".id = "Shot_Parents".parent_id

%(where_condition)s

group by
    "Task_Scenes".id,
    "Task_Scenes".name,
    "Task_Scenes".description,
    "Task_Scenes".children_id,
    "Task_Scenes".children_type_name,
    "Task_Scenes".children_status_code,
    "Task_Scenes".child_task_resource_id,
    "Task_Scenes".child_task_resource_name
order by "Task_Scenes".id"""

    # set the content range to prevent JSONRest Store to query the data twice
    content_range = '%s-%s/%s'
    where_condition = ''
    project_id = ''

    if entity.entity_type == 'Project':
        where_condition = 'where "Tasks".project_id = %s' % entity.id
        project_id = entity.id

    elif entity.entity_type == 'Sequence':
        where_condition = 'where "Shot_Sequences".sequence_id = %s' % entity_id
        project_id = entity.project.id

    sql_query = sql_query % {'where_condition': where_condition}



    result = DBSession.connection().execute(sql_query)

    return_data = []

    for r in result.fetchall():
        r_data = {
            'id': r[0],
            'name': r[1],
            'description': r[2],
            'num_of_shots': len(r[8])
        }


        layout_task_ids = r[3]
        layout_task_type_names = r[4]
        layout_task_status_codes = r[5]
        layout_task_resource_ids = r[6]
        layout_task_resource_names = r[7]
        shot_task_types = r[9]
        shot_task_ids = r[10]
        shot_task_names = r[11]
        shot_task_status_codes = r[12]
        shot_task_percents = r[13]
        shot_task_resource_names = r[14]
        shot_task_resource_ids = r[15]

        update_task_permission = PermissionChecker(request)('Update_Task')


        for i in range(len(layout_task_type_names)):
            task_type_name = layout_task_type_names[i]
            r_data[task_type_name]= {'id':'', 'name':'','resource_id':'','resource_name':'', 'update_task_resource_action':None}

        for j in range(len(layout_task_type_names)):
            task_type_name = layout_task_type_names[j]
            task = r_data[task_type_name]
            task['id'] = layout_task_ids[j]
            task['name'] = task_type_name
            task['resource_name'] = layout_task_resource_names[j]
            task['resource_id'] = layout_task_resource_ids[j]
            task['status'] = layout_task_status_codes[j].lower()
            if update_task_permission:
                task['update_task_resource_action'] =request.route_url('change_tasks_users_dialog', user_type='Resources',  _query={'project_id':project_id,'task_ids': [task['id']]})
                task['update_task_priority_action'] =request.route_url('change_tasks_priority_dialog',  _query={'task_ids': [task['id']]})

        for m in range(len(shot_task_types)):
            shot_task_type_name = shot_task_types[m]
            r_data[shot_task_type_name]= {'name':shot_task_type_name, 'ids':[], 'resource_ids':[],'resource_names':[], 'percent':0, 'child_statuses':[], 'status':'', 'num_of_task':0, 'update_task_resource_action':None}

        for k in range(len(shot_task_types)):
            shot_task_type_name = shot_task_types[k]
            shot_task = r_data[shot_task_type_name]
            if shot_task_ids[k] not in shot_task['ids']:
                shot_task['ids'].append(shot_task_ids[k])

            if shot_task_resource_ids[k] not in shot_task['resource_ids']:
                shot_task['resource_ids'].append(shot_task_resource_ids[k])
                shot_task['resource_names'].append(shot_task_resource_names[k])

            if shot_task_status_codes[k] not in shot_task['child_statuses']:
                shot_task['child_statuses'].append(shot_task_status_codes[k])

            shot_task['percent'] += float(shot_task_percents[k])
            shot_task['num_of_task'] += 1

        for l in range(len(shot_task_types)):
            shot_task_type_name = shot_task_types[l]
            shot_task = r_data[shot_task_type_name]
            shot_task['status'] = get_parent_task_status(shot_task['child_statuses']).lower()
            shot_task['percent'] = shot_task['percent']/shot_task['num_of_task']
            if update_task_permission:
                shot_task['update_task_resource_action'] =request.route_url('change_tasks_users_dialog', user_type='Resources',  _query={'project_id':project_id,'task_ids': shot_task['ids']})
                shot_task['update_task_priority_action'] =request.route_url('change_tasks_priority_dialog',  _query={'task_ids': [shot_task['ids']]})

        return_data.append(r_data)

    shot_count = len(return_data)
    content_range = content_range % (0, shot_count - 1, shot_count)

    logger.debug('get_scenes ends ')
    resp = Response(
        json_body=return_data
    )
    resp.content_range = content_range
    return resp
