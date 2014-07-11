# -*- coding: utf-8 -*-
# Stalker Pyramid a Web Base Production Asset Management System
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
from pyramid.view import view_config
from stalker import db, Project, Status, Daily
from stalker.db import DBSession
import transaction
from webob import Response
from stalker_pyramid.views import get_logged_in_user, logger, PermissionChecker, \
    milliseconds_since_epoch, local_to_utc
from stalker_pyramid.views.task import generate_recursive_task_query


@view_config(
    route_name='create_daily_dialog',
    renderer='templates/daily/dialog/create_daily_dialog.jinja2'
)
def create_daily_dialog(request):
    """called when creating dailies
    """
    came_from = request.params.get('came_from','/')
    logger.debug('came_from %s: '% came_from)

    # get logged in user
    logged_in_user = get_logged_in_user(request)

    project_id = request.params.get('project_id', -1)
    project = Project.query.filter(Project.id == project_id).first()

    if not project:
        return Response('No project found with id: %s' % project_id, 500)

    return {
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'project': project,
        'came_from':came_from,
        'mode':'Create',
        'milliseconds_since_epoch': milliseconds_since_epoch
    }


@view_config(
    route_name='create_daily'
)
def create_daily(request):
    """runs when creating a daily
    """

    logged_in_user = get_logged_in_user(request)
    utc_now = local_to_utc(datetime.datetime.now())

    name = request.params.get('name')
    description = request.params.get('description')

    status_code = 'OPEN'
    status = Status.query.filter(Status.code == status_code).first()

    project_id = request.params.get('project_id', None)
    project = Project.query.filter(Project.id == project_id).first()

    if not name:
        return Response('Please supply a name', 500)

    if not description:
        return Response('Please supply a description', 500)

    if not status:
        return Response('There is no status with code: %s' % status_code, 500)

    if not project:
        return Response('There is no project with id: %s' % project_id, 500)

    daily = Daily(
        project=project,
        name=name,
        status=status,
        description=description,
        created_by=logged_in_user,
        date_created=utc_now,
        date_updated=utc_now
    )
    db.DBSession.add(daily)

    return Response('Daily Created successfully')

@view_config(
    route_name='update_daily_dialog',
    renderer='templates/daily/dialog/update_daily_dialog.jinja2'
)
def update_daily_dialog(request):
    """called when updating dailies
    """
    came_from = request.params.get('came_from','/')
    logger.debug('came_from %s: '% came_from)

    # get logged in user
    logged_in_user = get_logged_in_user(request)

    daily_id = request.matchdict.get('id', -1)
    daily = Daily.query.filter(Daily.id == daily_id).first()

    return {
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'daily': daily,
        'came_from':came_from,
        'milliseconds_since_epoch': milliseconds_since_epoch,
    }


@view_config(
    route_name='update_daily'
)
def update_daily(request):
    """runs when updating a daily
    """

    logged_in_user = get_logged_in_user(request)
    utc_now = local_to_utc(datetime.datetime.now())

    daily_id = request.matchdict.get('id', -1)
    daily = Daily.query.filter(Daily.id == daily_id).first()

    if not daily:
        transaction.abort()
        return Response('No daily with id : %s' % daily_id, 500)

    name = request.params.get('name')
    description = request.params.get('description')

    status_code = request.params.get('status_code', None)
    status = Status.query.filter(Status.code == status_code).first()

    if not name:
        return Response('Please supply a name', 500)

    if not description:
        return Response('Please supply a description', 500)

    if not status:
        return Response('There is no status with code: %s' % status_code, 500)


    daily.name = name
    daily.description = description
    daily.status = status
    daily.date_updated = utc_now
    daily.updated_by = logged_in_user



    request.session.flash('Success: Successfully updated daily')
    return Response('Successfully updated daily')

@view_config(
    route_name='get_project_dailies',
    renderer='json'
)
def get_dailies(request):

    project_id = request.matchdict.get('id')
    logger.debug('---------------------project_id  : %s' % project_id)

    sql_query = """
        select
            "Dailies_SimpleEntities".id,
            "Dailies_SimpleEntities".name,
            "Dailies_Statuses".code,
            "Dailies_Statuses".id,
            "Dailies_Statuses_SimpleEntities".name,
            "Dailies_SimpleEntities".created_by_id,
            "Dailies_Creator_SimpleEntities".name,
            daily_count.link_count

        from "Projects"
        join "Dailies" on "Dailies".project_id = "Projects".id
        join "SimpleEntities" as "Dailies_SimpleEntities" on "Dailies_SimpleEntities".id = "Dailies".id
        join "SimpleEntities" as "Dailies_Creator_SimpleEntities" on "Dailies_Creator_SimpleEntities".id = "Dailies_SimpleEntities".created_by_id
        join "Statuses" as "Dailies_Statuses" on "Dailies_Statuses".id = "Dailies".status_id
        join "SimpleEntities" as "Dailies_Statuses_SimpleEntities" on "Dailies_Statuses_SimpleEntities".id = "Dailies".status_id

        left outer join (
            select
                "Daily_Links".daily_id as daily_id,
                count("Daily_Links".link_id) as link_count
            from "Daily_Links"
            join "Dailies" on "Dailies".id = "Daily_Links".daily_id
            group by "Daily_Links".daily_id
        ) as daily_count on daily_count.daily_id ="Dailies".id
        where "Projects".id = %(project_id)s
    """
    sql_query = sql_query % {'project_id': project_id}

    result = db.DBSession.connection().execute(sql_query)

    dailies = []

    update_daily_permission = \
        PermissionChecker(request)('Update_Daily')

    for r in result.fetchall():
        daily = {
            'id': r[0],
            'name': r[1],
            'status_code':r[2].lower(),
            'status_id':r[3],
            'status_name':r[4],
            'created_by_id':r[5],
            'created_by_name':r[6],
            'link_count':r[7] if r[7] else 0,
            'item_view_link':'/dailies/%s/view'%r[0]
        }
        if update_daily_permission:
            daily['item_update_link'] = \
                '/dailies/%s/update/dialog' % daily['id']
            daily['item_remove_link'] = '/entities/%s/delete/dialog?came_from=%s'%(daily['id'], request.current_route_path())

        dailies.append(daily)
    logger.debug('---------------------dailies  : %s' % dailies)
    resp = Response(
        json_body=dailies
    )

    return resp

@view_config(
    route_name='get_project_dailies_count',
    renderer='json'
)
def get_dailies_count(request):


    project_id = request.matchdict.get('id')
    logger.debug('---------------------project_id  : %s' % project_id)

    sql_query = """
select count(1) from (
select "Dailies".id

from "Projects"
join "Dailies" on "Dailies".project_id = "Projects".id
join "Statuses" on "Dailies".status_id = "Statuses".id

where "Statuses".code = 'OPEN' and "Projects".id = %(project_id)s
) as data
    """
    sql_query = sql_query % {'project_id': project_id}

    from sqlalchemy import text  # to be able to use "%" sign use this function
    result = DBSession.connection().execute(text(sql_query))

    return result.fetchone()[0]

@view_config(
    route_name='get_daily_outputs',
    renderer='json'
)
def get_daily_outputs(request):

    daily_id = request.matchdict.get('id')
    logger.debug('daily_id  : %s' % daily_id)

    sql_query = """
        select
            "Tasks".id as task_id,
            "ParentTasks".full_path as task_name,
            "Task_Statuses".code as task_status_code,
            "Task_Status_SimpleEntities".name as task_status_name,
            "Versions".id as version_id,
            "Versions".take_name as version_take_name,
            "Versions".version_number as version_number,
            "Versions".is_published as version_is_published,
            "Links".id as link_id,
            'repositories/' || task_repositories.repo_id || '/' || "Links".original_filename as link_original_filename,
            'repositories/' || task_repositories.repo_id || '/' || "Links_ForWeb".full_path as link_full_path,
            'repositories/' || task_repositories.repo_id || '/' || "Thumbnails".full_path as link_thumbnail_full_path

        from "Daily_Links"
        join "Dailies" on "Dailies".id = "Daily_Links".daily_id
        join "Links" on "Links".id = "Daily_Links".link_id
        join "SimpleEntities" as "Link_SimpleEntities" on "Link_SimpleEntities".id = "Links".id
        join "Links" as "Links_ForWeb" on "Link_SimpleEntities".thumbnail_id = "Links_ForWeb".id
        join "SimpleEntities" as "Links_ForWeb_SimpleEntities" on "Links_ForWeb".id = "Links_ForWeb_SimpleEntities".id
        join "Links" as "Thumbnails" on "Links_ForWeb_SimpleEntities".thumbnail_id = "Thumbnails".id
        join "Version_Outputs" on "Version_Outputs".link_id = "Daily_Links".link_id
        join "Versions" on "Versions".id = "Version_Outputs".version_id
        join "Tasks" on "Tasks".id = "Versions".task_id
        join "Statuses" as "Task_Statuses" on "Task_Statuses".id = "Tasks".status_id
        join "SimpleEntities" as "Task_Status_SimpleEntities" on "Task_Status_SimpleEntities".id = "Tasks".status_id

        left join (
            %(generate_recursive_task_query)s
        ) as "ParentTasks" on "Tasks".id = "ParentTasks".id

        -- find repository id
        join (
            select
                "Tasks".id as task_id,
                "Repositories".id as repo_id
            from "Tasks"
            join "Projects" on "Tasks".project_id = "Projects".id
            join "Repositories" on "Projects".repository_id = "Repositories".id
        ) as task_repositories on "Tasks".id = task_repositories.task_id

        where "Dailies".id = %(daily_id)s
    """
    sql_query = sql_query % {'daily_id': daily_id, 'generate_recursive_task_query': generate_recursive_task_query()}

    result = db.DBSession.connection().execute(sql_query)

    tasks = []

    for r in result.fetchall():
        task = {
            'task_id': r[0],
            'task_name': r[1],
            'task_status_code': r[2].lower(),
            'task_status_name': r[3],
            'version_id':r[4],
            'version_take_name': r[5],
            'version_number': r[6],
            'version_published':r[7],
            'link_id':r[8],
            'original_filename':r[9],
            'full_path':r[10],
            'thumbnail_full_path':r[11]
        }
        tasks.append(task)

    logger.debug('---------------------tasks  : %s' % tasks)
    resp = Response(
        json_body=tasks
    )

    return resp




