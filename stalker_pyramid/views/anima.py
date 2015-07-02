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

    character_dependencies = []
    asset_dependencies_lighting = []
    asset_dependencies_scene_assembly = []

    for character in characters:
        character_dependencies.append(
            find_asset_task_by_type(character, 'Rig')
        )

    for asset in assets:
        asset_dependencies_scene_assembly.append(
            find_asset_task_by_type(asset, 'Layout')
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
            update_shot_task_dependencies('append', shot, 'Animation', character_dependencies, logged_in_user, utc_now)
            update_shot_task_dependencies('append', shot, 'Lighting', asset_dependencies_lighting, logged_in_user, utc_now)
            update_shot_task_dependencies('append', shot, 'Scene Assembly', asset_dependencies_scene_assembly, logged_in_user, utc_now)
    elif entity.entity_type == 'Shot':
        update_shot_task_dependencies('append', entity, 'Animation', character_dependencies, logged_in_user, utc_now)
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

    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    asset_id = request.matchdict.get('a_id')
    asset = Asset.query.filter(Asset.id == asset_id).first()

    character_dependencies = [find_asset_task_by_type(asset, 'Rig')]
    asset_dependencies_scene_assembly = [find_asset_task_by_type(asset, 'Layout')]
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
            update_shot_task_dependencies('remove', shot, 'Animation', character_dependencies, logged_in_user, utc_now)
            update_shot_task_dependencies('remove', shot, 'Scene Assembly', asset_dependencies_scene_assembly, logged_in_user, utc_now)
            update_shot_task_dependencies('remove', shot, 'Lighting', asset_dependencies_lighting, logged_in_user, utc_now)

    elif entity.entity_type == 'Shot':
        update_shot_task_dependencies('remove', entity, 'Animation', character_dependencies, logged_in_user, utc_now)
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
        animation_test_type = Type.query.filter_by(name='Animation Test').first()
        animation_bible_type = Type.query.filter_by(name='Animation Bible').first()
        animation_bible = Task.query.filter(Task.parent == asset).filter(Task.type == animation_bible_type).first()

        if animation_bible:
            return animation_bible
        else:
            animation_test = Task.query.filter(Task.parent == asset).filter(Task.type == animation_test_type).first()
            if animation_test:
                return animation_test
            else:
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
    sql_query = """select
    min(extract(epoch from "TimeLogs".start::timestamp AT TIME ZONE 'UTC')) as start,
    array_agg(distinct(tasks.shot_name)) as shot_names,
    array_agg(distinct("TimeLogs".resource_id)) as resource_ids,
    sum((tasks.frames*(extract(epoch from "TimeLogs".end::timestamp AT TIME ZONE 'UTC' - "TimeLogs".start::timestamp AT TIME ZONE 'UTC'))/(tasks.schedule_timing *
        (case tasks.schedule_unit
                    when 'min' then 60
                    when 'h' then 3600
                    when 'd' then 32400
                    when 'w' then 147600
                    when 'm' then 590400
                    when 'y' then 7696277
                    else 0
                end)
    ))/24.0) as r_seconds
from "TimeLogs"
join (
        select "Tasks".id as id,
                "Tasks".schedule_timing,
                "Tasks".schedule_unit,
                "Shot_SimpleEntities".name as shot_name,
                ("Shots".cut_out - "Shots".cut_in) as frames

        from "Tasks"
        join "SimpleEntities" as "Task_SimpleEntities" on "Task_SimpleEntities".id = "Tasks".id
        join "SimpleEntities" as "Type_SimpleEntities" on "Type_SimpleEntities".id = "Task_SimpleEntities".type_id
        join "Shots" on "Shots".id = "Tasks".parent_id
        join "SimpleEntities" as "Shot_SimpleEntities" on "Shot_SimpleEntities".id = "Shots".id


        where "Type_SimpleEntities".name = '%(task_type)s'
    ) as tasks on tasks.id = "TimeLogs".task_id

where %(where_conditions)s
group by  date_trunc('week', "TimeLogs".start)
order by start
"""

    where_conditions = ''
    if entity.entity_type == 'User':
        where_conditions = """"TimeLogs".resource_id = %(resource_id)s """ % {'resource_id': entity_id}
    elif entity.entity_type == 'Department':
        temp_buffer = ["""("""]
        for i, resource in enumerate(entity.users):
            if i > 0:
                temp_buffer.append(' or')
            temp_buffer.append(""" "TimeLogs".resource_id='%s'""" % resource.id)
        temp_buffer.append(' )')
        where_conditions = ''.join(temp_buffer)

    sql_query = sql_query % {'where_conditions': where_conditions, 'task_type':task_type}
    result = DBSession.connection().execute(sql_query).fetchall()

    return [{
        'start_date': r[0],
        'shot_names': r[1],
        'resource_ids': r[2],
        'total_seconds': r[3]
    } for r in result]


