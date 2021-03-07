# -*- coding: utf-8 -*-

from pyramid.view import view_config
import transaction
from stalker.db.session import DBSession
from stalker import Sequence, Shot, Project, Entity, Task

import logging
from pyramid.response import Response
from stalker_pyramid.views import get_logged_in_user, PermissionChecker, \
    get_parent_task_status, to_seconds, invalidate_all_caches
from stalker_pyramid.views.task import duplicate_task_hierarchy_action

from stalker_pyramid import logger_name
logger = logging.getLogger(logger_name)


@view_config(
    route_name='update_scene_dialog',
    renderer='templates/scene/dialog/scene_dialog.jinja2',
)
@view_config(
    route_name='create_scene_dialog',
    renderer='templates/scene/dialog/scene_dialog.jinja2'
)
def scene_dialog(request):
    """a generic function which will create a dictionary with enough data
    """
    logged_in_user = get_logged_in_user(request)

    entity_id = request.params.get('entity_id')
    entity = Entity.query.filter_by(id=entity_id).first()

    mode = request.params.get('mode')

    scene_id = request.matchdict.get('id', -1)
    scene = Task.query.filter(Task.id == scene_id).first()

    shot_count = 1
    if scene:
        shots_folder = Task.query.filter(Task.name == 'Shots').filter(Task.parent == scene).first()
        if shots_folder:
            shots = Shot.query.filter(Shot.parent == shots_folder).all()
            shot_count = len(shots)

    project = None
    sequence = None

    if entity.entity_type == "Project":
        project = entity
    elif entity.entity_type == "Sequence":
        sequence = entity
        project = sequence.project

    logger.debug('project_id    : %s' % project.id)

    return {
        'project': project,
        'sequence': sequence,
        'logged_in_user': logged_in_user,
        'mode': mode,
        'scene': scene,
        'shot_count': shot_count
    }


@view_config(
    route_name='create_scene'
)
def create_scene(request):
    """runs when adding a new sequence
    """
    logged_in_user = get_logged_in_user(request)

    sequence_id = request.params.get('sequence_id')
    sequence = Sequence.query.filter_by(id=sequence_id).first()

    sequence_name = sequence.name
    scene_name = request.params.get('name')

    import re
    regex = re.compile('[0-9]+')

    scene_number = regex.findall(scene_name)[-1]

    temp_scene_id = request.params.get('temp_scene_id')
    temp_scene = Task.query.filter_by(id=temp_scene_id).first()

    temp_shot_id = request.params.get('temp_shot_id')
    temp_shot = Shot.query.filter_by(id=temp_shot_id).first()

    shot_count = request.params.get('shot_count')

    logger.debug('sequence_id: %s' % sequence_id)

    if sequence and scene_name and temp_scene and temp_shot and shot_count:
        # get descriptions
        description = request.params.get('description', '')

        # do not create a new scene if there is one
        new_scene = Task.query \
            .filter(Task.name == scene_name) \
            .filter(Task.parent == sequence) \
            .first()

        if new_scene is None:
            try:
                new_scene = duplicate_task_hierarchy_action(
                    temp_scene,
                    sequence,
                    scene_name,
                    description,
                    logged_in_user
                )
                DBSession.flush()
            except BaseException as e:
                transaction.abort()
                return Response(body=str(e), status=500)
            else:
                transaction.commit()
                sequence = Sequence.query.filter_by(id=sequence_id).first()
                new_scene = Task.query\
                    .filter(Task.name == scene_name)\
                    .filter(Task.parent == sequence)\
                    .first()
                if not new_scene:
                    transaction.abort()
                    return Response('no new_scene', status=500)

            logger.debug('new_scene: %s' % new_scene.name)
        else:
            logger.debug('found scene with the same name, not generating a new one: %s' % scene_name)

        # transaction.commit()
        shots_task = Task.query.filter(Task.name == 'Shots').filter(Task.parent == new_scene).first()
        logger.debug('shots_task.id: %s' % shots_task.id)

        temp_shot = Shot.query.filter_by(id=temp_shot_id).first()
        if not shots_task:
            transaction.abort()
            return Response('There is no shots under scene task', 500)

        # sometimes the scene template already has some shots
        # so delete any existing shots
        # with DBSession.no_autoflush:
        #     residual_shots = Shot.query.filter(Shot.parent == shots_task).all()

        # create shots based on shot template
        shot_number_start_from = 0

        # pick the greatest shot number from the scene if there are any shots
        with DBSession.no_autoflush:
            existing_shots = DBSession.query(Shot.name).filter(Shot.parent==shots_task).order_by(Shot.name.asc()).all()
            if existing_shots:
                shot_number_start_from = int(regex.findall(existing_shots[-1][0].split('_')[-1])[-1])

        logger.debug('shot_number_start_from: %s' % shot_number_start_from)

        for i in range(1, int(shot_count) + 1):
            new_shot_name = '%s_%s_%s' % (sequence_name, scene_number, str(i * 10 + shot_number_start_from).zfill(4))
            new_shot = \
                duplicate_task_hierarchy_action(temp_shot, shots_task, new_shot_name, description, logged_in_user)
            logger.debug('new_shot_name: %s' % new_shot.name)
            new_shot.sequences = [sequence]

        # do residual shot deletion here
        # if residual_shots:
        #     for shot in residual_shots:
        #         DBSession.delete(shot)

        invalidate_all_caches()

    else:
        logger.debug('there are missing parameters')
        logger.debug('sequence_name    : %s' % sequence_name)
        logger.debug('scene_name       : %s' % scene_name)
        logger.debug('scene_number     : %s' % scene_number)
        logger.debug('temp_shot_id     : %s' % temp_shot_id)
        logger.debug('temp_scene_id    : %s' % temp_scene_id)
        logger.debug('shot_count   : %s' % shot_count)
        transaction.abort()
        return Response('There is no shots under scene task', 500)

    return Response('Task %s is created successfully' % new_scene)


@view_config(
    route_name='update_scene'
)
def update_scene(request):
    """runs when updating a scene
    """
    logged_in_user = get_logged_in_user(request)

    scene_id = request.matchdict.get('id', -1)
    scene = Task.query.filter(Task.id == scene_id).first()

    if not scene:
        transaction.abort()
        return Response('There is no scene task', 500)

    sequence = scene.parent

    temp_shot_id = request.params.get('temp_shot_id')
    temp_shot = Shot.query.filter_by(id=temp_shot_id).first()

    shot_count = request.params.get('shot_count')

    if sequence and temp_shot and shot_count:
        # get descriptions
        description = request.params.get('description', '')

        logger.debug('new_scene   : %s' % scene.name)
        # transaction.commit()
        shots_folder = Task.query.filter(Task.name == 'Shots').filter(Task.parent == scene).first()
        temp_shot = Shot.query.filter_by(id=temp_shot_id).first()

        if not shots_folder:
            transaction.abort()
            return Response('There is no shots under scene task', 500)
        shots = Shot.query.filter(Shot.parent == shots_folder).all()

        for i in range(len(shots)+1, int(shot_count)+1):
            new_shot_name = '%s_%s' % (scene.name, str(i * 10).zfill(4))
            new_shot = duplicate_task_hierarchy_action(temp_shot, shots_folder, new_shot_name, description, logged_in_user)
            logger.debug('new_shot   : %s' % new_shot.name)
            new_shot.sequences = [sequence]
    else:
        logger.debug('there are missing parameters')
        logger.debug('scene_name      : %s' % scene.name)
        logger.debug('temp_shot_id    : %s' % temp_shot_id)
        logger.debug('shot_count      : %s' % shot_count)
        transaction.abort()
        return Response('There is no shots under scene task', 500)

    return Response('Task %s is updated successfully' % scene)


@view_config(
    route_name='get_entity_scenes_simple',
    renderer='json'
)
def get_scenes_simple(request):
    """returns all the Scenes of the given Project
    """

    logger.debug('get_entity_scenes_simple starts ')

    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()
    logger.debug('entity_id : %s' % entity_id)

    sql_query =""" select "Scene_SimpleEntities".id as id,
       "Scene_SimpleEntities".name as name

    from "Tasks"
    join "SimpleEntities" as "Scene_SimpleEntities" on "Scene_SimpleEntities".id = "Tasks".id
    join "SimpleEntities" as "Type_SimpleEntities" on "Type_SimpleEntities".id = "Scene_SimpleEntities".type_id

    where "Type_SimpleEntities".name = 'Scene' %(where_condition)s

    order by "Scene_SimpleEntities".name """

    # set the content range to prevent JSONRest Store to query the data twice
    content_range = '%s-%s/%s'
    where_condition = ''
    project_id = ''

    if entity.entity_type == 'Project':
        where_condition = 'and "Tasks".project_id = %s' % entity.id
        project_id = entity.id

    elif entity.entity_type == 'Sequence':
        where_condition = 'where "Tasks".parent_id = %s' % entity_id
        project_id = entity.project.id

    project = Project.query.filter(Project.id == project_id).first()
    sql_query = sql_query % {'where_condition': where_condition}

    result = DBSession.connection().execute(sql_query)

    return_data = []

    for r in result.fetchall():
        r_data = {
            'id': r[0],
            'name': r[1]
        }
        return_data.append(r_data)


    content_range = content_range % (0, len(return_data) - 1, len(return_data))
    logger.debug('get_scenes ends ')
    resp = Response(
        json_body=return_data
    )
    resp.content_range = content_range
    return resp


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

    array_agg(("Shots".id)) as shot_id,
    array_agg("Distinct_Shot_Task_Types".type_name) as type_name,
    array_agg("Tasks".id) as task_id,
    array_agg("Task_SimpleEntities".name) as task_name,
    array_agg("Task_Statuses".code) as status_code,

    array_agg("Tasks".bid_timing) as bid_timing,
    array_agg("Tasks".bid_unit) as bid_unit,
    array_agg("Tasks".schedule_timing) as schedule_timing,
    array_agg("Tasks".schedule_unit) as schedule_unit,
    array_agg(coalesce ("Task_TimeLogs".duration,0)) as total_logged_seconds,

    array_agg("Resources_SimpleEntities".name) as resource_name,
    array_agg("Resources_SimpleEntities".id) as resource_id,
    array_agg(("Shots".cut_out-"Shots".cut_in)) as shot_duration

from "Tasks"
join "Shots" on "Shots".id = "Tasks".parent_id
join "SimpleEntities" as "Task_SimpleEntities" on "Tasks".id = "Task_SimpleEntities".id
join "Shot_Sequences" on "Shots".id = "Shot_Sequences".shot_id

left outer join (
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
left outer join "Statuses" as "Task_Statuses" on "Tasks".status_id = "Task_Statuses".id

left outer join (
            select
                "TimeLogs".task_id,
                extract(epoch from sum("TimeLogs".end - "TimeLogs".start)) as duration
            from "TimeLogs"
            group by task_id
        ) as "Task_TimeLogs" on "Task_TimeLogs".task_id = "Tasks".id



join "Tasks" as "Shot_As_Tasks" on "Shot_As_Tasks".id = "Shots".id
join "Tasks" as "Shot_Parents" on "Shot_Parents".id = "Shot_As_Tasks".parent_id

left outer join "Task_Resources" on "Tasks".id = "Task_Resources".task_id
left outer join "SimpleEntities" as "Resources_SimpleEntities" on "Resources_SimpleEntities".id = "Task_Resources".resource_id

left outer join(
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
    left outer join "Tasks" as "Child_Tasks" on "Child_Tasks".parent_id = "Scene_SimpleEntities".id
    left outer join "SimpleEntities" as "Child_SimpleEntities" on "Child_SimpleEntities".id = "Child_Tasks".id
    left outer join "Statuses" as "Child_Task_Statuses" on "Child_Task_Statuses".id = "Child_Tasks".status_id
    left outer join "SimpleEntities" as "Type_Child_SimpleEntities" on "Type_Child_SimpleEntities".id = "Child_SimpleEntities".type_id

    left outer join "Task_Resources" as "Child_Task_Resources" on "Child_Tasks".id = "Child_Task_Resources".task_id
    left outer join "SimpleEntities" as "Child_Task_Resources_SimpleEntities" on "Child_Task_Resources_SimpleEntities".id = "Child_Task_Resources".resource_id


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

    project = Project.query.filter(Project.id == project_id).first()
    sql_query = sql_query % {
        'where_condition': where_condition
    }

    result = DBSession.connection().execute(sql_query)

    return_data = []

    update_task_permission = PermissionChecker(request)('Update_Task')

    for r in result.fetchall():

        shot_ids = r[8]
        shot_durations = r[20]
        scene_total_frame = 0
        distinct_shot_ids = []

        for x in range(len(shot_ids)):
            if shot_ids[x] not in distinct_shot_ids:
                distinct_shot_ids.append(shot_ids[x])
                scene_total_frame += shot_durations[x]
        r_data = {
            'id': r['scene_id'],
            'name': r['scene_name'],
            'description': r['scene_description'],
            'num_of_shots': len(distinct_shot_ids),
            'total_seconds': float(scene_total_frame/project.fps),
            'update_scene_action': '/scenes/%(id)s/update/dialog?entity_id=%(entity_id)s&mode=Update' % {'id':r[0],'entity_id':entity.id} if update_task_permission else None
        }

        layout_task_ids = r['children_id']
        layout_task_type_names = r['children_type_name'] if r['children_type_name'] else []
        layout_task_status_codes = r['children_status_code']
        layout_task_resource_ids = r['child_task_resource_id']
        layout_task_resource_names = r['child_task_resource_name']
        shot_task_types = r['type_name']
        shot_task_ids = r['task_id']
        shot_task_names = r['task_name']
        shot_task_status_codes = r['status_code']
        shot_task_bid_timing = r['bid_timing']
        shot_task_bid_unit = r['bid_unit']
        shot_task_schedule_timing = r['schedule_timing']
        shot_task_schedule_unit = r['schedule_unit']
        shot_task_total_logged_seconds = r['total_logged_seconds']
        shot_task_resource_names = r['resource_name']
        shot_task_resource_ids = r['resource_id']

        # if layout_task_type_names:
        #     for i in range(len(layout_task_type_names)):
        #         task_type_name = layout_task_type_names[i]
        #         r_data[task_type_name] = {
        #             'id': '',
        #             'name': '',
        #             'resource_id': '',
        #             'resource_name': '',
        #             'update_task_resource_action': None
        #         }
        for task_type_name in layout_task_type_names:
            r_data[task_type_name] = {
                'id': '',
                'name': '',
                'resource_id': '',
                'resource_name': '',
                'update_task_resource_action': None
            }

        # if layout_task_type_names:
        #     for j in range(len(layout_task_type_names)):
        #         task_type_name = layout_task_type_names[j]
        #         task = r_data[task_type_name]
        #         task['id'] = layout_task_ids[j]
        #         task['name'] = task_type_name
        #         task['resource_name'] = layout_task_resource_names[j]
        #         task['resource_id'] = layout_task_resource_ids[j]
        #         task['status'] = layout_task_status_codes[j].lower()
        #         if update_task_permission:
        #             task['update_task_resource_action'] = request.route_url('change_tasks_users_dialog', user_type='Resources',  _query={'project_id':project_id,'task_ids': [task['id']]})
        #             task['update_task_priority_action'] = request.route_url('change_tasks_priority_dialog',  _query={'task_ids': [task['id']]})

        for j, task_type_name in enumerate(layout_task_type_names):
            task = r_data[task_type_name]
            task['id'] = layout_task_ids[j]
            task['name'] = task_type_name
            task['resource_name'] = layout_task_resource_names[j]
            task['resource_id'] = layout_task_resource_ids[j]
            task['status'] = layout_task_status_codes[j].lower()
            if update_task_permission:
                task['update_task_resource_action'] = request.route_url('change_tasks_users_dialog', user_type='Resources',  _query={'project_id':project_id,'task_ids': [task['id']]})
                task['update_task_priority_action'] = request.route_url('change_tasks_priority_dialog',  _query={'task_ids': [task['id']]})

        # for m in range(len(shot_task_types)):
        #     shot_task_type_name = shot_task_types[m]
        #     r_data[shot_task_type_name] = {
        #             'name': shot_task_type_name,
        #             'ids': [],
        #             'resource_ids': [],
        #             'resource_names': [],
        #             'bid_seconds': 0,
        #             'schedule_seconds': 0,
        #             'total_logged_seconds': 0,
        #             'child_statuses': [],
        #             'status': '',
        #             'num_of_task': 0,
        #             'update_task_resource_action': None
        #     }

        for shot_task_type_name in shot_task_types:
            r_data[shot_task_type_name] = {
                    'name': shot_task_type_name,
                    'ids': [],
                    'resource_ids': [],
                    'resource_names': [],
                    'bid_seconds': 0,
                    'schedule_seconds': 0,
                    'total_logged_seconds': 0,
                    'child_statuses': [],
                    'status': '',
                    'num_of_task': 0,
                    'update_task_resource_action': None
            }

        for k, shot_task_type_name in enumerate(shot_task_types):
            shot_task = r_data[shot_task_type_name]
            if shot_task_ids[k] not in shot_task['ids']:
                shot_task['ids'].append(shot_task_ids[k])

            if shot_task_resource_ids[k] not in shot_task['resource_ids']:
                shot_task['resource_ids'].append(shot_task_resource_ids[k])
                shot_task['resource_names'].append(shot_task_resource_names[k])

            # if shot_task_status_codes[k] not in shot_task['child_statuses']:
            shot_task['child_statuses'].append(shot_task_status_codes[k])

            # shot_task['percent'] += float(shot_task_percents[k])
            shot_task['bid_seconds'] += float(to_seconds(shot_task_bid_timing[k], shot_task_bid_unit[k]))
            shot_task['schedule_seconds'] += float(to_seconds(shot_task_schedule_timing[k], shot_task_schedule_unit[k]))
            shot_task['total_logged_seconds'] += float(shot_task_total_logged_seconds[k])
            shot_task['num_of_task'] += 1

        for shot_task_type_name in shot_task_types:
            shot_task = r_data[shot_task_type_name]

            # logger.debug('shot_task : %s %s %s' % (r[1], shot_task_type_name, shot_task['child_statuses']))
            shot_task['child_statuses'] = list(set(shot_task['child_statuses']))
            # logger.debug('shot_task : %s' % shot_task['child_statuses'])

            shot_task['status'] = get_parent_task_status(shot_task['child_statuses']).lower()
            # shot_task['percent'] = shot_task['percent']/shot_task['num_of_task']
            if update_task_permission:
                shot_task['update_task_action'] =request.route_url('change_tasks_properties_dialog',   _query={'task_ids': shot_task['ids']})

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
