# -*- coding: utf-8 -*-

import pytz
import datetime

from pyramid.httpexceptions import HTTPServerError, HTTPOk
from pyramid.view import view_config

from stalker.db.session import DBSession
from stalker import Sequence, StatusList, Status, Shot, Project, Entity, Task

import logging
import transaction
from webob import Response
from stalker_pyramid.views import get_logged_in_user, PermissionChecker 

#logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)
from stalker_pyramid import logger_name
logger = logging.getLogger(logger_name)


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

        # update the shot

        shot.name = name
        shot.code = code
        shot.description = description
        shot.sequences = [sequence]
        shot.status = status
        shot.updated_by = logged_in_user
        date_updated = datetime.datetime.now(pytz.utc)
        shot.date_updated = date_updated
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

    entity_id = request.params.get('entity_id', -1)
    entity = Entity.query.filter(Entity.id == entity_id).first()

    where_condition = ""
    if entity:
        if entity.entity_type == "Sequence":
            where_condition = """join "Shot_Sequences" on "Shot_Sequences".shot_id = "Shots".id
                                 where "Shot_Sequences".sequence_id = %(seq_id)s""" % {'seq_id': entity.id }
        else:
            if entity.type:
                if entity.type.name == "Scene":
                    where_condition = """ join "Tasks" as "Shots_as_Task" on "Shots_as_Task".id = "Tasks".parent_id
                                            join "Tasks" as "Parent_Tasks" on "Parent_Tasks".id = "Shots_as_Task".parent_id
                                            join "Tasks" as "Scene_Tasks" on "Scene_Tasks".id = "Parent_Tasks".parent_id
                                            where "Scene_Tasks".id = %(scene_id)s and "Tasks".schedule_model='effort' """% {'scene_id': entity.id}

    sql_query = """select
        "SimpleEntities".id as type_id,
        "SimpleEntities".name as type_name
    from "SimpleEntities"
    join "SimpleEntities" as "Task_SimpleEntities" on "SimpleEntities".id = "Task_SimpleEntities".type_id
    join "Tasks" on "Task_SimpleEntities".id = "Tasks".id
    join "Shots" on "Tasks".parent_id = "Shots".id
    %(where_condition)s
    group by "SimpleEntities".id, "SimpleEntities".name
    order by "SimpleEntities".name"""

    sql_query = sql_query % {'where_condition': where_condition}
    logger.debug('get_shots_children_task_type sql_query: %s' % sql_query)
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
    """returns the count of Shots in the given Project or Sequence
    """

    logger.debug('get_shots_count starts')

    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter(Entity.id == entity_id).first()

    sql_query = """select
        count(1)
    from "Shots"
        join "Tasks" on "Shots".id = "Tasks".id
    %(where_condition)s"""

    where_condition = ''

    if entity.entity_type == 'Sequence':
        where_condition = """left join "Shot_Sequences" on "Shot_Sequences".shot_id = "Shots".id
                          where "Shot_Sequences".sequence_id = %s""" % entity_id
    elif entity.entity_type == 'Project':
        where_condition = 'where "Tasks".project_id = %s' % entity_id

    logger.debug('where_condition : %s ' % where_condition)
    sql_query = sql_query % {'where_condition': where_condition}

    return DBSession.connection().execute(sql_query).fetchone()[0]

@view_config(
    route_name='get_entity_shots_simple',
    renderer='json'
)
def get_shots_simple(request):
    """returns all the Shots of the given Project
    """
    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    shot_id = request.params.get('entity_id', None)

    logger.debug('get_shots starts ')

    sql_query = """select "Shot_SimpleEntities".id as id,
                          "Shot_SimpleEntities".name as name

    from "Shots"
    join "Tasks" as "Shot_Tasks" on "Shot_Tasks".id = "Shots".id
    join "SimpleEntities" as "Shot_SimpleEntities" on "Shot_SimpleEntities".id = "Shots".id

    %(where_condition)s
    order by "Shot_SimpleEntities".name
"""

    # set the content range to prevent JSONRest Store to query the data twice
    content_range = '%s-%s/%s'
    where_condition = ''

    if entity.entity_type == 'Sequence':
        where_condition = 'where "Shot_Sequences".sequence_id = %s' % entity_id
    elif entity.entity_type == 'Project':
        where_condition = 'where "Shot_Tasks".project_id = %s' % entity_id


    sql_query = sql_query % {'where_condition': where_condition}
    logger.debug('entity_id : %s' % entity_id)

    # convert to dgrid format right here in place
    result = DBSession.connection().execute(sql_query)

    return_data = []

    for r in result.fetchall():
        r_data = {
            'id': r[0],
            'name': r[1]
        }

        return_data.append(r_data)

    shot_count = len(return_data)
    content_range = content_range % (0, shot_count - 1, shot_count)

    logger.debug('get_shots_simple ends ')
    resp = Response(
        json_body=return_data
    )
    resp.content_range = content_range
    return resp


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
    "Links".full_path as shot_thumbnail_full_path,
    "Distinct_Shot_Statuses".shot_status_code as shot_status_code,
    "Distinct_Shot_Statuses".shot_status_html_class as shot_status_html_class,
    array_agg("Distinct_Shot_Task_Types".type_name) as task_type_names,
    array_agg("Tasks".id) as task_ids,
    array_agg("Task_SimpleEntities".name) as task_names,
    array_agg("Task_Statuses".code) as task_status_codes,
    array_agg("Task_Statuses_SimpleEntities".html_class) as task_status_html_classes,
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
    "Shot_Sequences".sequence_id as sequence_id,
    "Shot_Sequences_SimpleEntities".name as sequence_name,
    array_agg("Tasks".bid_timing) as bid_timing,
    array_agg("Tasks".bid_unit)::text[] as bid_unit,
    array_agg("Tasks".schedule_timing) as schedule_timing,
    array_agg("Tasks".schedule_unit)::text[] as schedule_unit,
    array_agg("Resources_SimpleEntities".name) as resource_name,
    array_agg("Resources_SimpleEntities".id) as resource_id,
    "Shots".cut_in as cut_in,
    "Shots".cut_out as cut_out,
    "Shots".fps as fps,
    array_agg(coalesce(reviews.rev_count, 0)) as review_count

from "Tasks"
join "Shots" on "Shots".id = "Tasks".parent_id
join "SimpleEntities" as "Shot_SimpleEntities" on "Shots".id = "Shot_SimpleEntities".id
join "SimpleEntities" as "Task_SimpleEntities" on "Tasks".id = "Task_SimpleEntities".id
left join "Links" on "Shot_SimpleEntities".thumbnail_id = "Links".id
join(
    select
        "Shots".id as shot_id,
        "Statuses".code as shot_status_code,
        "SimpleEntities".html_class as shot_status_html_class,
        "Tasks".parent_id as shot_parent
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
                extract(epoch from sum("TimeLogs".end - "TimeLogs".start)) as duration
            from "TimeLogs"
            group by task_id
        ) as "Task_TimeLogs" on "Task_TimeLogs".task_id = "Tasks".id

left outer join (
        select  count("Statuses".code) as rev_count,
                "Tasks".id as task_id
        from "Reviews"
        join "Tasks" on "Reviews".task_id = "Tasks".id
        join "Statuses" on "Statuses".id = "Reviews".status_id
        where "Statuses".code = 'RREV'
        group by "Tasks".id) as reviews on reviews.task_id = "Tasks".id

left outer join "Task_Resources" on "Tasks".id = "Task_Resources".task_id
left outer join "SimpleEntities" as "Resources_SimpleEntities" on "Resources_SimpleEntities".id = "Task_Resources".resource_id

%(where_condition)s
group by
    "Shots".id,
    "Shot_SimpleEntities".name,
    "Shot_SimpleEntities".description,
    "Links".full_path,
    "Distinct_Shot_Statuses".shot_status_code,
    "Distinct_Shot_Statuses".shot_status_html_class,
    "Shot_Sequences".sequence_id,
    "Shot_Sequences_SimpleEntities".name,
    "Shots".cut_in,
    "Shots".cut_out,
    "Shots".fps
order by "Shot_SimpleEntities".name
"""

    # set the content range to prevent JSONRest Store to query the data twice
    content_range = '%s-%s/%s'
    where_condition = ''

    if entity.entity_type == 'Sequence':
        where_condition = 'where "Shot_Sequences".sequence_id = %s' % entity_id

    elif entity.entity_type == 'Project':
        where_condition = 'where "Tasks".project_id = %s' % entity_id

    elif entity.entity_type == 'Task':
        if entity.type.name == 'Scene':
            where_condition = """join "Tasks" as "Parent_Tasks" on "Parent_Tasks".id = "Distinct_Shot_Statuses".shot_parent
                                 join "Tasks" as "Scene_Tasks" on "Scene_Tasks".id = "Parent_Tasks".parent_id
                                 where "Scene_Tasks".id = %s""" % entity_id

    if shot_id:
        where_condition = 'where "Shots".id = %(shot_id)s' % ({'shot_id': shot_id})

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
            'id': r['shot_id'],
            'name': r['shot_name'],
            'description': r['shot_description'],
            'thumbnail_full_path': r['shot_thumbnail_full_path']
            if r['shot_thumbnail_full_path'] else None,
            'status': r['shot_status_code'],
            'status_color': r['shot_status_html_class'],
            'sequence_id': r['sequence_id'],
            'sequence_name': r['sequence_name'],
            'cut_in': r['cut_in'],
            'cut_out': r['cut_out'],
            'fps': r['fps'],
            'update_shot_action': '/tasks/%s/update/dialog' % r['shot_id']
                if update_shot_permission else None,
            'delete_shot_action': '/tasks/%s/delete/dialog' % r['shot_id']
                if delete_shot_permission else None
        }
        task_types_names = r['task_type_names']
        task_ids = r['task_ids']
        task_names = r['task_names']
        task_statuses = r['task_status_codes']
        task_statuses_color = r['task_status_html_classes']
        task_percent_complete = r['percent_complete']
        task_bid_timing = r['bid_timing']
        task_bid_unit = r['bid_unit']
        task_schedule_timing = r['schedule_timing']
        task_schedule_unit = r['schedule_unit']
        task_resource_name = r['resource_name']
        task_resource_id = r['resource_id']
        task_review_count = r['review_count']

        r_data['nulls'] = []

        for index1 in range(len(task_types_names)):

            if task_types_names[index1]:
                r_data[task_types_names[index1]] = []

        for index in range(len(task_types_names)):
            task = {
                     'id': task_ids[index],
                     'name': task_names[index],
                     'status': task_statuses[index],
                     'percent': task_percent_complete[index],
                     'bid_timing': task_bid_timing[index],
                     'bid_unit': task_bid_unit[index],
                     'schedule_timing': task_schedule_timing[index],
                     'schedule_unit': task_schedule_unit[index],
                     'resource_name': task_resource_name[index],
                     'resource_id': task_resource_id[index],
                     'review_count': task_review_count[index]
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


def update_shot_task_dependencies(action, shot, task_name, dependencies, user, date_updated):
    """please add docstring
    """
    task = Task.query.filter(Task.name == task_name).filter(Task.parent == shot).first()
    if not task:
        return 'There is no %s under: %s' % (task_name, shot.name)

    if task.status.code not in ['WFD', 'RTS']:
        return '%s: %s status is %s, task can not change!!!' % (shot.name, task.name, task.status.code)

    for dependency in dependencies:
        if dependency:
            if action == 'append':
                if dependency not in task.depends:
                    task.depends.append(dependency)
                    task.updated_by = user
                    task.date_updated = date_updated
                #     return '%s: %s is added to dependencies of %s, ' % (shot.name, dependency.name, task.name)
                # else:
                #     return '%s: %s is already depended to %s, ' % (shot.name, task.name, dependency.name)
            elif action == 'remove':
                if dependency in task.depends:
                    task.depends.remove(dependency)
                    task.updated_by = user
                    task.date_updated = date_updated
                #     return '%s: %s is removed to dependencies of %s, ' % (shot.name, dependency.name, task.name)
                # else:
                #     return '%s: %s does not depend to %s, ' % (shot.name, task.name, dependency.name)
            # else:
            #     return 'There is no type'

        # else:
        #     return 'There is no dependency task'