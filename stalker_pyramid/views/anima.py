# -*- coding: utf-8 -*-
# Stalker Pyramid a Web Based Production Asset Management System
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
import logging



from pyramid.response import Response
from pyramid.view import view_config
from stalker.db import DBSession
import transaction

from stalker import db,Project, Entity, Task, Shot, Type, Asset

from stalker_pyramid.views import (get_logged_in_user,
                                   PermissionChecker, get_multi_integer,
                                   local_to_utc)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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
    utc_now = local_to_utc(datetime.datetime.now())
    from stalker_pyramid import __stalker_version_number__
    if __stalker_version_number__ >= 218:
        import pytz
        utc_now = utc_now.replace(tzinfo=pytz.utc)

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
    utc_now = local_to_utc(datetime.datetime.now())
    from stalker_pyramid import __stalker_version_number__
    if __stalker_version_number__ >= 218:
        import pytz
        utc_now = utc_now.replace(tzinfo=pytz.utc)

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
        min(extract(epoch from results.start::timestamp AT TIME ZONE 'UTC')) as start,
        min(extract(epoch from results.scheduled_start::timestamp AT TIME ZONE 'UTC')) as scheduled_start,
        array_agg(distinct(results.shot_name)) as shot_names,
        results.resource_id as resource_ids,
        results.scheduled_resource_id as scheduled_resource_ids,
        sum(results.approved_shot_seconds*results.timelog_duration/results.schedule_seconds) as approved_shot_seconds,
        sum(results.shot_seconds*results.timelog_duration/results.schedule_seconds) as shot_seconds,
        sum(results.approved_timelog_duration/results.schedule_seconds) as approved_percent,
        sum(results.timelog_duration/results.schedule_seconds) as percent,
        sum(results.shot_seconds*1.00) as total_assigned_shot_seconds,
        results.scene_name as scene_name

from (
        select
            "TimeLogs".start as start,
            tasks.start as scheduled_start,
            tasks.shot_name as shot_name,
            tasks.scene_name as scene_name,
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
                        when 'CMPL' then (extract(epoch from "TimeLogs".end::timestamp AT TIME ZONE 'UTC' - "TimeLogs".start::timestamp AT TIME ZONE 'UTC'))
                        else 0
                    end) as approved_timelog_duration,
            (extract(epoch from "TimeLogs".end::timestamp AT TIME ZONE 'UTC' - "TimeLogs".start::timestamp AT TIME ZONE 'UTC')) as timelog_duration


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
                        "Scene_SimpleEntities".name as scene_name,
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
                join "SimpleEntities" as "Scene_SimpleEntities" on "Scene_SimpleEntities".id = "Scenes".id

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
group by  date_trunc('week', results.start),
          results.resource_id,
          results.scheduled_resource_id,
          results.scene_name
order by start,
    resource_ids
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
        'start_date': r[0] if r[0] else r[1],
        'scheduled_start_date': r[1],
        'shot_names': r[2],
        'resource_ids': [r[3]] if r[3] else r[4],
        'scheduled_resource_ids': r[4],
        'approved_seconds': r[5] if r[5] else 0,
        'total_seconds': r[6] if r[6] else 0,
        'approved_shots':r[7] if r[7] else 0,
        'total_shots':r[8] if r[8] else 0,
        'total_assigned_shot_seconds':float(r[9]),
        'scene_name':r[10]
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


# @view_config(
#     route_name='get_entity_task_type_result',
#     renderer='json'
# )
# def get_entity_task_type_result(request):
#     """gives get_entity_task_type_result
#     """
#     logger.debug('get_entity_task_type_result starts')
#     entity_id = request.matchdict.get('id')
#     entity = Entity.query.filter_by(id=entity_id).first()
#
#     task_type = request.matchdict.get('task_type')
#     project_id = request.params.get('project_id', -1)
#
#     logger.debug('project_id %s' % project_id)
#     project = Project.query.filter_by(id=project_id).first()
#     if not project:
#         return 'There is no project with id %s' % project_id
#
#     sql_query = """
# select
#         min(extract(epoch from results.start::timestamp AT TIME ZONE 'UTC')) as start,
#         array_agg(distinct(results.shot_name)) as shot_names,
#         results.resource_id as resource_ids,
#         sum(results.approved_shot_seconds*results.timelog_duration/results.schedule_seconds) as approved_shot_seconds,
#         sum(results.shot_seconds*results.timelog_duration/results.schedule_seconds) as shot_seconds,
#         sum(results.approved_timelog_duration/results.schedule_seconds) as approved_percent,
#         sum(results.timelog_duration/results.schedule_seconds) as percent,
#         results.scene_name as scene_name
#
# from (
#         select
#             "TimeLogs".start as start,
#             tasks.shot_name as shot_name,
#             tasks.scene_name as scene_name,
#             tasks.status_code as shot_status,
#             "TimeLogs".resource_id as resource_id,
#             tasks.seconds as shot_seconds,
#             (case tasks.status_code
#                         when 'CMPL' then tasks.seconds
#                         else 0
#                     end) as approved_shot_seconds,
#
#             tasks.schedule_seconds,
#              (case tasks.status_code
#                         when 'CMPL' then (extract(epoch from "TimeLogs".end::timestamp AT TIME ZONE 'UTC' - "TimeLogs".start::timestamp AT TIME ZONE 'UTC'))
#                         else 0
#                     end) as approved_timelog_duration,
#             (extract(epoch from "TimeLogs".end::timestamp AT TIME ZONE 'UTC' - "TimeLogs".start::timestamp AT TIME ZONE 'UTC')) as timelog_duration
#
#         from "TimeLogs"
#         join (
#                 select "Tasks".id as id,
#                        "Tasks".schedule_timing *(case "Tasks".schedule_unit
#                                                     when 'min' then 60
#                                                     when 'h' then 3600
#                                                     when 'd' then 32400
#                                                     when 'w' then 147600
#                                                     when 'm' then 590400
#                                                     when 'y' then 7696277
#                                                     else 0
#                                                 end) as schedule_seconds,
#                         "Shot_SimpleEntities".name as shot_name,
#                         ("Shots".cut_out - "Shots".cut_in)/%(project_fps)s as seconds,
#                         "Statuses".code as status_code,
#                         "Scene_SimpleEntities".name as scene_name
#
#                 from "Tasks"
#                 join "SimpleEntities" as "Task_SimpleEntities" on "Task_SimpleEntities".id = "Tasks".id
#                 join "SimpleEntities" as "Type_SimpleEntities" on "Type_SimpleEntities".id = "Task_SimpleEntities".type_id
#                 join "Shots" on "Shots".id = "Tasks".parent_id
#                 join "SimpleEntities" as "Shot_SimpleEntities" on "Shot_SimpleEntities".id = "Shots".id
#                 join "Statuses" on "Statuses".id = "Tasks".status_id
#                 join "Tasks" as "Shot_Tasks" on "Shot_Tasks".id = "Shots".id
#                 join "Tasks" as "Shot_Folders" on "Shot_Folders".id = "Shot_Tasks".parent_id
#                 join "Tasks" as "Scenes" on "Scenes".id = "Shot_Folders".parent_id
#                 join "SimpleEntities" as "Scene_SimpleEntities" on "Scene_SimpleEntities".id = "Scenes".id
#
#                 where "Type_SimpleEntities".name = '%(task_type)s' %(project_query)s
#             ) as tasks on tasks.id = "TimeLogs".task_id
#         where %(where_conditions)s
#     ) as results
# group by  date_trunc('week', results.start),
#           results.resource_id,
#           results.scene_name
# order by start,
#     resource_ids
# """
#
#     where_conditions = ''
#     if entity.entity_type == 'User':
#         where_conditions = """"TimeLogs".resource_id = %(resource_id)s """ % {'resource_id': entity_id}
#     elif entity.entity_type == 'Department' or entity.entity_type == 'Project':
#         temp_buffer = ["""("""]
#         for i, resource in enumerate(entity.users):
#             if i > 0:
#                 temp_buffer.append(' or')
#             temp_buffer.append(""" "TimeLogs".resource_id='%s'""" % resource.id)
#         temp_buffer.append(' )')
#         where_conditions = ''.join(temp_buffer)
#
#     project_query = """ and "Tasks".project_id = %(project_id)s""" % {'project_id': project.id}
#     logger.debug('project_query:  %s' % project_query)
#     sql_query = sql_query % {'where_conditions': where_conditions,
#                              'task_type': task_type,
#                              'project_query': project_query,
#                              'project_fps': project.fps
#                              }
#
#     logger.debug('sql_query:  %s' % sql_query)
#     result = DBSession.connection().execute(sql_query).fetchall()
#
#     return [{
#         'start_date': r[0],
#         'shot_names': r[1],
#         'resource_ids': r[2],
#         'approved_seconds': r[3],
#         'total_seconds': r[4],
#         'approved_shots':r[5],
#         'total_shots':r[6],
#         'scene_name':r[7]
#
#     } for r in result]
#

