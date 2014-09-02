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
import transaction
from webob import Response
from stalker_pyramid.views import get_logged_in_user, PermissionChecker, \
    local_to_utc

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@view_config(
    route_name='create_shot'
)
def create_shot(request):
    """runs when adding a new shot
    """
    logged_in_user = get_logged_in_user(request)

    name = request.params.get('name')
    code = request.params.get('code')

    status_id = request.params.get('status_id')
    status = Status.query.filter_by(id=status_id).first()

    project_id = request.params.get('project_id')
    project = Project.query.filter_by(id=project_id).first()
    logger.debug('project_id   : %s' % project_id)

    if name and code and status and project:
        # get descriptions
        description = request.params.get('description')

        sequence_id = request.params['sequence_id']
        sequence = Sequence.query.filter_by(id=sequence_id).first()

        # get the status_list
        status_list = StatusList.query.filter_by(
            target_entity_type='Shot'
        ).first()

        # there should be a status_list
        # TODO: you should think about how much possible this is
        if status_list is None:
            return HTTPServerError(detail='No StatusList found')

        new_shot = Shot(
            name=name,
            code=code,
            description=description,
            sequence=sequence,
            status_list=status_list,
            status=status,
            created_by=logged_in_user,
            project=project
        )

        DBSession.add(new_shot)

    else:
        logger.debug('there are missing parameters')
        logger.debug('name      : %s' % name)
        logger.debug('code      : %s' % code)
        logger.debug('status    : %s' % status)
        logger.debug('project   : %s' % project)
        HTTPServerError()

    return HTTPOk()



@view_config(
    route_name='update_shot'
)
def update_shot(request):
    """runs when adding a new shot
    """
    logged_in_user = get_logged_in_user(request)

    shot_id = request.params.get('shot_id')
    shot = Shot.query.filter_by(id=shot_id).first()

    name = request.params.get('name')
    code = request.params.get('code')

    cut_in = int(request.params.get('cut_in', 1))
    cut_out = int(request.params.get('cut_out', 1))

    status_id = request.params.get('status_id')
    status = Status.query.filter_by(id=status_id).first()

    if shot and code and name and status:
        # get descriptions
        description = request.params.get('description')

        sequence_id = request.params['sequence_id']
        sequence = Sequence.query.filter_by(id=sequence_id).first()

        #update the shot

        shot.name = name
        shot.code = code
        shot.description = description
        shot.sequences = [sequence]
        shot.status = status
        shot.updated_by = logged_in_user
        shot.date_updated = datetime.datetime.now()
        shot.cut_in = cut_in
        shot.cut_out = cut_out



        DBSession.add(shot)

    else:
        logger.debug('there are missing parameters')
        logger.debug('name      : %s' % name)
        logger.debug('status    : %s' % status)
        HTTPServerError()

    return HTTPOk()


@view_config(
    route_name='get_shots_children_task_type',
    renderer='json'
)
def get_shots_children_task_type(request):
    """returns the Task Types defined under the Shot container
    """

    sql_query = """select
        "SimpleEntities".id as type_id,
        "SimpleEntities".name as type_name
    from "SimpleEntities"
    join "SimpleEntities" as "Task_SimpleEntities" on "SimpleEntities".id = "Task_SimpleEntities".type_id
    join "Tasks" on "Task_SimpleEntities".id = "Tasks".id
    join "Shots" on "Tasks".parent_id = "Shots".id
    group by "SimpleEntities".id, "SimpleEntities".name
    order by "SimpleEntities".name"""

    result = DBSession.connection().execute(sql_query)

    return [
        {
            'id': r[0],
            'name': r[1]
        }
        for r in result.fetchall()
    ]


@view_config(
    route_name='get_entity_shots_count',
    renderer='json'
)
@view_config(
    route_name='get_project_shots_count',
    renderer='json'
)
def get_shots_count(request):
    """returns the count of Shots in the given Project
    """
    project_id = request.matchdict.get('id', -1)

    sql_query = """select
        count(1)
    from "Shots"
        join "Tasks" on "Shots".id = "Tasks".id
    where "Tasks".project_id = %s""" % project_id

    return DBSession.connection().execute(sql_query).fetchone()[0]


@view_config(
    route_name='get_entity_shots',
    renderer='json'
)
@view_config(
    route_name='get_project_shots',
    renderer='json'
)
def get_shots(request):
    """returns all the Shots of the given Project
    """
    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    shot_id = request.params.get('entity_id', None)

    logger.debug('get_shots starts ')

    sql_query = """select
    "Shots".id as shot_id,
    "Shot_SimpleEntities".name as shot_name,
    "Shot_SimpleEntities".description as shot_description,
    "Links".full_path as shot_full_path,
    "Distinct_Shot_Statuses".shot_status_code as shot_status_code,
    "Distinct_Shot_Statuses".shot_status_html_class as shot_status_html_class,
    array_agg("Distinct_Shot_Task_Types".type_name) as type_name,
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
                    when 'w' then 147600
                    when 'm' then 590400
                    when 'y' then 7696277
                    else 0
                end)) * 100.0
        )) as percent_complete,
    "Shot_Sequences".sequence_id as sequence_id,
    "Shot_Sequences_SimpleEntities".name as sequence_name,
    array_agg("Tasks".bid_timing) as bid_timing,
    array_agg("Tasks".bid_unit)::text[] as bid_unit,
    array_agg("Tasks".schedule_timing) as schedule_timing,
    array_agg("Tasks".schedule_unit)::text[] as schedule_unit,
    array_agg("Resources_SimpleEntities".name) as resource_name,
    array_agg("Resources_SimpleEntities".id) as resource_id

from "Tasks"
join "Shots" on "Shots".id = "Tasks".parent_id
join "SimpleEntities" as "Shot_SimpleEntities" on "Shots".id = "Shot_SimpleEntities".id
join "SimpleEntities" as "Task_SimpleEntities" on "Tasks".id = "Task_SimpleEntities".id
left join "Links" on "Shot_SimpleEntities".thumbnail_id = "Links".id
join(
    select
        "Shots".id as shot_id,
        "Statuses".code as shot_status_code,
        "SimpleEntities".html_class as shot_status_html_class
    from "Tasks"
    join "Shots" on "Shots".id = "Tasks".id
    join "Statuses" on "Statuses".id = "Tasks".status_id
    join "SimpleEntities" on "SimpleEntities".id = "Statuses".id
    )as "Distinct_Shot_Statuses" on "Shots".id = "Distinct_Shot_Statuses".shot_id
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
join "SimpleEntities" as "Task_Statuses_SimpleEntities" on "Task_Statuses_SimpleEntities".id = "Tasks".status_id
left join "Shot_Sequences" on "Shot_Sequences".shot_id = "Shots".id
left join "SimpleEntities" as "Shot_Sequences_SimpleEntities" on "Shot_Sequences_SimpleEntities".id = "Shot_Sequences".sequence_id
left outer join (
            select
                "TimeLogs".task_id,
                extract(epoch from sum("TimeLogs".end::timestamp AT TIME ZONE 'UTC' - "TimeLogs".start::timestamp AT TIME ZONE 'UTC')) as duration
            from "TimeLogs"
            group by task_id
        ) as "Task_TimeLogs" on "Task_TimeLogs".task_id = "Tasks".id

left outer join "Task_Resources" on "Tasks".id = "Task_Resources".task_id
join "SimpleEntities" as "Resources_SimpleEntities" on "Resources_SimpleEntities".id = "Task_Resources".resource_id

%(where_condition)s
group by
    "Shots".id,
    "Shot_SimpleEntities".name,
    "Shot_SimpleEntities".description,
    "Links".full_path,
    "Distinct_Shot_Statuses".shot_status_code,
    "Distinct_Shot_Statuses".shot_status_html_class,
    "Shot_Sequences".sequence_id,
    "Shot_Sequences_SimpleEntities".name
order by "Shot_SimpleEntities".name
"""

    # set the content range to prevent JSONRest Store to query the data twice
    content_range = '%s-%s/%s'
    where_condition = ''

    if entity.entity_type == 'Sequence':
        where_condition = 'where "Shot_Sequences".sequence_id = %s' % entity_id

    elif entity.entity_type == 'Project':
        where_condition = ''

    if shot_id:
        where_condition = 'where "Shots".id = %(shot_id)s'%({'shot_id':shot_id})

    update_shot_permission = \
        PermissionChecker(request)('Update_Shot')
    delete_shot_permission = \
        PermissionChecker(request)('Delete_Shot')

    sql_query = sql_query % {'where_condition': where_condition}
    logger.debug('entity_id : %s' % entity_id)

    # convert to dgrid format right here in place
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
            'sequence_id': r[12],
            'sequence_name': r[13],
            'update_shot_action': '/tasks/%s/update/dialog' % r[0]
                if update_shot_permission else None,
            'delete_shot_action': '/tasks/%s/delete/dialog' % r[0]
                if delete_shot_permission else None
        }
        task_types_names = r[6]
        task_ids = r[7]
        task_names = r[8]
        task_statuses = r[9]
        task_statuses_color = r[10]
        task_percent_complete = r[11]
        task_bid_timing = r[14]
        task_bid_unit = r[15]
        task_schedule_timing = r[16]
        task_schedule_unit = r[17]
        task_resource_name = r[18]
        task_resource_id = r[19]

        r_data['nulls'] = []

        for index1 in range(len(task_types_names)):

            if task_types_names[index1]:

                r_data[task_types_names[index1]]= []

        for index in range(len(task_types_names)):
            task = {
                     'id':task_ids[index],
                     'name':task_names[index],
                     'status':task_statuses[index],
                     'percent':task_percent_complete[index],
                     'bid_timing':task_bid_timing[index],
                     'bid_unit':task_bid_unit[index],
                     'schedule_timing':task_schedule_timing[index],
                     'schedule_unit':task_schedule_unit[index],
                     'resource_name':task_resource_name[index],
                     'resource_id':task_resource_id[index]
                    }
            if task_types_names[index]:
                r_data[task_types_names[index]].append(task)
            else:
                r_data['nulls'].append(task)

        return_data.append(r_data)

    shot_count = len(return_data)
    content_range = content_range % (0, shot_count - 1, shot_count)

    logger.debug('get_shots ends ')
    resp = Response(
        json_body=return_data
    )
    resp.content_range = content_range
    return resp
