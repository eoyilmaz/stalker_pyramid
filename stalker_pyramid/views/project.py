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

import time
import datetime
import logging

from pyramid.httpexceptions import HTTPOk, HTTPFound
from pyramid.response import Response
from pyramid.view import view_config

from stalker.db import DBSession
from stalker import (db, ImageFormat, Repository, Structure, Status,
                     StatusList, Project, Entity, Studio, defaults, Client,
                     Budget, BudgetEntry)
from stalker.models import local_to_utc
from stalker.models.project import ProjectUser
import transaction

from stalker_pyramid.views import (get_date_range,
                                   get_logged_in_user,
                                   milliseconds_since_epoch, PermissionChecker)
from stalker_pyramid.views.role import query_role
from stalker_pyramid.views.type import query_type

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@view_config(
    route_name='create_project'
)
def create_project(request):
    """called when adding a new Project
    """
    logged_in_user = get_logged_in_user(request)

    came_from = request.params.get('came_from', '/')

    # parameters
    name = request.params.get('name')
    code = request.params.get('code')
    fps = int(request.params.get('fps'))
    # get the dates
    start, end = get_date_range(request, 'start_and_end_dates')

    imf_id = request.params.get('image_format_id', -1)
    imf = ImageFormat.query.filter_by(id=imf_id).first()
    if not imf:
        transaction.abort()
        return Response('Can not find a ImageFormat with code: %s' % imf_id, 500)

    repo_id = request.params.get('repository_id', -1)
    repo = Repository.query.filter_by(id=repo_id).first()
    if not repo:
        transaction.abort()
        return Response('Can not find a Repository with code: %s' % repo_id, 500)

    structure_id = request.params.get('structure_id', -1)
    structure = Structure.query.filter_by(id=structure_id).first()
    if not structure:
        transaction.abort()
        return Response('Can not find a structure with code: %s' % structure_id, 500)

    status = Status.query.filter_by(name='New').first()
    if not status:
        transaction.abort()
        return Response('Can not find a status with code: %s' % status.id, 500)

    client_id = request.params.get('client_id', -1)
    client = Client.query.filter_by(id=client_id).first()
    if not client:
        transaction.abort()
        return Response('Can not find a client with id: %s' % client_id, 500)

    logger.debug('create_project          :')

    logger.debug('name          : %s' % name)
    logger.debug('code          : %s' % code)
    logger.debug('fps           : %s' % fps)
    logger.debug('imf_id        : %s' % imf_id)
    logger.debug('repo_id       : %s' % repo_id)
    logger.debug('repo          : %s' % repo)
    logger.debug('structure_id  : %s' % structure_id)
    logger.debug('structure     : %s' % structure)
    logger.debug('start         : %s' % start)
    logger.debug('end           : %s' % end)
    logger.debug('client_id           : %s' % client_id)

    if name and code and fps and start and end:
        # status is always New
        # lets create the project

        # status list
        status_list = StatusList.query \
            .filter_by(target_entity_type='Project').first()

        try:
            new_project = Project(
                name=name,
                code=code,
                image_format=imf,
                repositories=[repo],
                created_by=logged_in_user,
                fps=fps,
                structure=structure,
                status_list=status_list,
                status=status,
                start=start,
                end=end,
                client=client
            )

            DBSession.add(new_project)
            # flash success message
            request.session.flash(
                'success:Project <strong>%s</strong> is created '
                'successfully' % name
            )
        except BaseException as e:
            request.session.flash('error: %s' % e)
            HTTPFound(location=came_from)

    else:
        transaction.abort()
        return Response('There are missing parameters', 500)

    return Response(
        'success:Project with the code <strong>%s</strong> is created.'
        % code
    )


@view_config(
    route_name='update_project'
)
def update_project(request):
    """called when updating a Project
    """
    logged_in_user = get_logged_in_user(request)

    # parameters
    project_id = request.matchdict.get('id', -1)
    project = Project.query.filter_by(id=project_id).first()
    if not project:
        transaction.abort()
        return Response('Can not find a project with code: %s' % project_id, 500)

    imf_id = request.params.get('image_format_id', -1)
    imf = ImageFormat.query.filter_by(id=imf_id).first()
    if not imf:
        transaction.abort()
        return Response('Can not find a ImageFormat with code: %s' % imf_id, 500)

    repo_id = request.params.get('repository_id', -1)
    repo = Repository.query.filter_by(id=repo_id).first()
    if not repo:
        transaction.abort()
        return Response('Can not find a Repository with code: %s' % repo_id, 500)

    structure_id = request.params.get('structure_id', -1)
    structure = Structure.query.filter_by(id=structure_id).first()
    if not structure:
        transaction.abort()
        return Response('Can not find a structure with code: %s' % structure_id, 500)

    status_id = request.params.get('status_id', -1)
    status = Status.query.filter_by(id=status_id).first()
    if not status:
        transaction.abort()
        return Response('Can not find a status with code: %s' % status_id, 500)

    client_id = request.params.get('client_id', -1)
    client = None
    logger.debug('client_id: %s' % client_id)
    if client_id not in [-1, '']:
        client = Client.query.get(int(client_id))

    if not client:
        transaction.abort()
        return Response('Can not find a client with id: %s' % client_id, 500)

    name = request.params.get('name')
    fps = int(request.params.get('fps'))
    # get the dates
    start, end = get_date_range(request, 'start_and_end_dates')


    logger.debug('update_project          :')

    logger.debug('name          : %s' % name)
    logger.debug('fps           : %s' % fps)
    logger.debug('imf_id        : %s' % imf_id)
    logger.debug('repo_id       : %s' % repo_id)
    logger.debug('repo          : %s' % repo)
    logger.debug('structure_id  : %s' % structure_id)
    logger.debug('structure     : %s' % structure)
    logger.debug('start         : %s' % start)
    logger.debug('end           : %s' % end)
    logger.debug('project           : %s' % project)
    logger.debug('client           : %s' % client)

    if name and fps and start and end:
        project.name = name
        project.image_format = imf
        project.repository = repo
        project.updated_by = logged_in_user
        project.date_updated = datetime.datetime.now()
        project.fps = fps
        project.structure = structure
        project.status = status
        project.start = start
        project.end = end
        project.client = client

    else:
        transaction.abort()
        return Response('There are missing parameters', 500)

    request.session.flash(
        'success:Project with the code <strong>%s</strong> is updated.'
        % project.code
    )
    return Response(
        'success:Project with the code <strong>%s</strong> is updated.'
        % project.code
    )


@view_config(
    route_name='get_entity_projects',
    renderer='json'
)
def get_entity_projects(request):
    """
    """

    logger.debug('***get_entity_projects method starts ***')

    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    logger.debug('entity.projects count :%s', entity.projects)

    return_data = []

    lead_role = query_role('Lead')

    for project in entity.projects:

        lead = ProjectUser.query\
            .filter_by(project=project)\
            .filter_by(role=lead_role)\
            .first()

        return_data.append(
            {
                'id': project.id,
                'name': project.name,

                'lead_id': lead.id if lead else None,
                'lead_name': lead.name if lead else None,

                'date_created': milliseconds_since_epoch(project.date_created),
                'created_by_id': project.created_by.id,
                'created_by_name': project.created_by.name,
                'thumbnail_full_path': project.thumbnail.full_path if project.thumbnail else None,
                'status': project.status.name,
                'description': len(project.users),
                'percent_complete': project.percent_complete,
                'item_view_link':'/project/%s/view'%project.id,
                'item_remove_link':'/entities/%s/%s/remove/dialog?came_from=%s'%(project.id, entity.id, request.current_route_path())
                if PermissionChecker(request)('Update_Project') else None
            }
        )

    return return_data


@view_config(
    route_name='get_projects',
    renderer='json'
)
def get_projects(request):
    """returns all the Project instances in the database
    """
    return [
        {
            'id': proj.id,
            'name': proj.name
        }
        for proj in Project.query.all()
    ]


@view_config(
    route_name='get_project_lead',
    renderer='json'
)
def get_project_lead(request):
    """returns the project lead as a json data
    """
    project_id = request.matchdict.get('id', -1)
    project = Project.query.filter(Project.id == project_id).first()
    lead_data = {}
    if project:
        lead = project.lead
        lead_data = {
            'id': lead.id,
            'name': lead.name,
            'login': lead.login
        }

    return lead_data



@view_config(
    route_name='get_project_tasks_cost',
    renderer='json'
)
def get_project_tasks_cost(request):
    """returns the project lead as a json data
    """
    project_id = request.matchdict.get('id', -1)
    sql_query = """
        select
           goods.id,
           goods.name,
           goods.msrp,
           goods.cost,
           goods.unit,
           sum(goods.bid_total) as bid_total,
           sum(goods.bid_total * goods.user_rate) as realize_total

        from ( select
                "Good_SimpleEntities".name as name,
                "Good_SimpleEntities".id as id,
                "Task_Goods".msrp as msrp,
                "Task_Goods".cost as cost,
                "Task_Goods".unit as unit,
                sum("Tasks".bid_timing * (case "Tasks".bid_unit
                                    when 'min' then 60
                                    when 'h' then 3600
                                    when 'd' then 32400
                                    when 'w' then 183600
                                    when 'm' then 590400
                                    when 'y' then 7696277
                                    else 0
                                end)/3600) as bid_total,
                "Users".rate as user_rate

                from "Tasks"
                join "Goods" as "Task_Goods" on "Task_Goods".id = "Tasks".good_id
                join "SimpleEntities" as "Good_SimpleEntities" on "Good_SimpleEntities".id = "Task_Goods".id
                join "Task_Resources" on "Task_Resources".task_id = "Tasks".id
                join "Users" on "Users".id = "Task_Resources".resource_id

                where "Tasks".project_id = %(project_id)s and not exists (
                            select 1 from "Tasks" as "All_Tasks"
                            where "All_Tasks".parent_id = "Tasks".id
                            )

                group by "Good_SimpleEntities".name,
                         "Good_SimpleEntities".id,
                         "Task_Goods".msrp,
                         "Task_Goods".cost,
                         "Task_Goods".unit,
                         "Users".rate
        ) as goods
        group by
               goods.name,
               goods.id,
               goods.msrp,
               goods.cost,
               goods.unit
"""

    sql_query = sql_query % {'project_id': project_id}
    result = DBSession.connection().execute(sql_query)
    return_data = [
        {
            'good_id': r[0],
            'good_name': r[1],
            'msrp': int(r[2]),
            'cost': int(r[3]),
            'unit': r[4],
            'amount':r[5],
            'realized_total':r[6]
        }
        for r in result.fetchall()
    ]

    return return_data


@view_config(
    route_name='add_project_entries_to_budget'
)
def add_project_entries_to_budget(request):
    """ adds entries to bugdet"""

    logged_in_user = get_logged_in_user(request)
    utc_now = local_to_utc(datetime.datetime.now())

    project_id = request.matchdict.get('id', -1)
    project = Project.query.filter(Project.id == project_id).first()
    if not project:
        transaction.abort()
        return Response('Can not find a project with id: %s' % project_id, 500)

    budget_id = request.matchdict.get('bid', -1)
    budget = Budget.query.filter(Budget.id == budget_id).first()
    if not budget:
        transaction.abort()
        return Response('Can not find a budget with id: %s' % budget_id, 500)

    project_entries = get_project_tasks_cost(request)

    for project_entry in project_entries:
        new_budget_entry_type = query_type('BudgetEntry', 'CalenderBasedEntry')
        new_budget = True
        logger.debug('realized_total: %s' % (project_entry['realized_total']))
        for budget_entry in budget.entries:
            if budget_entry.name == project_entry['good_name']:
                budget_entry.type = new_budget_entry_type
                budget_entry.amount = project_entry['amount']
                budget_entry.cost = project_entry['cost']
                budget_entry.msrp = project_entry['msrp']
                budget_entry.realized_total = project_entry['realized_total']
                budget_entry.unit = project_entry['unit']
                budget_entry.date_updated = utc_now
                budget_entry.updated_by = logged_in_user
                new_budget = False

        if new_budget:
            new_budget_entry = BudgetEntry(
                budget=budget,
                name=project_entry['good_name'],
                type=new_budget_entry_type,
                amount=project_entry['amount'],
                cost=project_entry['cost'],
                msrp=project_entry['msrp'],
                price=project_entry['cost'],
                realized_total=project_entry['realized_total'],
                unit=project_entry['unit'],
                description='',
                created_by=logged_in_user,
                date_created=utc_now,
                date_updated=utc_now
            )
            DBSession.add(new_budget_entry)

    return Response(
        'success:Budget Entries are updated for <strong>%s</strong> project.'
        % project.name
    )




@view_config(
    route_name='get_project_tasks_today',
    renderer='json'
)
def get_project_tasks_today(request):
    """returns the project lead as a json data
    """
    project_id = request.matchdict.get('id', -1)
    action = request.matchdict.get('action', -1)

    today = datetime.date.today()
    start = datetime.time(0, 0)
    end = datetime.time(23, 59, 59)

    start_of_today = datetime.datetime.combine(today, start)
    end_of_today = datetime.datetime.combine(today, end)

    start = time.time()

    sql_query = """select "Tasks".id,
           "SimpleEntities".name,
           array_agg(distinct("SimpleEntities_Resource".id)),
           array_agg(distinct("SimpleEntities_Resource".name)),
           "SimpleEntities_Status".name,
           "SimpleEntities_Status".html_class,
           (coalesce("Task_TimeLogs".duration, 0.0))::float /
           ("Tasks".schedule_timing * (case "Tasks".schedule_unit
                when 'min' then 60
                when 'h' then %(working_seconds_per_hour)s
                when 'd' then %(working_seconds_per_day)s
                when 'w' then %(working_seconds_per_week)s
                when 'm' then %(working_seconds_per_month)s
                when 'y' then %(working_seconds_per_year)s
                else 0
            end)) * 100.0 as percent_complete
    from "Tasks"
        join "SimpleEntities" on "Tasks".id = "SimpleEntities".id
        join "Task_Resources" on "Tasks".id = "Task_Resources".task_id
        join "SimpleEntities" as "SimpleEntities_Resource" on "Task_Resources".resource_id = "SimpleEntities_Resource".id
        join "Statuses" on "Tasks".status_id = "Statuses".id
        join "SimpleEntities" as "SimpleEntities_Status" on "Statuses".id = "SimpleEntities_Status".id
        left outer join (
            select
                "TimeLogs".task_id,
                extract(epoch from sum("TimeLogs".end::timestamp AT TIME ZONE 'UTC' - "TimeLogs".start::timestamp AT TIME ZONE 'UTC')) as duration
            from "TimeLogs"
            group by task_id
        ) as "Task_TimeLogs" on "Task_TimeLogs".task_id = "Tasks".id
        left outer join "TimeLogs" on "Tasks".id = "TimeLogs".task_id
        """

    if action == 'progress':
        sql_query += """where
            "Tasks".computed_start::timestamp AT TIME ZONE 'UTC' < '%(end_of_today)s' and
            "Tasks".computed_end::timestamp AT TIME ZONE 'UTC' > '%(start_of_today)s'"""
    elif action == 'end':
        sql_query += """where
            "Tasks".computed_end::timestamp AT TIME ZONE 'UTC' > '%(start_of_today)s' and
            "Tasks".computed_end::timestamp AT TIME ZONE 'UTC' <= '%(end_of_today)s'
            """

    sql_query += """   and "Tasks".project_id = %(project_id)s
        group by "Tasks".id,
             "SimpleEntities".name,
             "SimpleEntities_Status".name,
             "SimpleEntities_Status".html_class,
             "Task_TimeLogs".duration,
             "Tasks".schedule_timing,
             "Tasks".schedule_unit
        """

    studio = Studio.query.first()
    assert isinstance(studio, Studio)

    ws_per_hour = 3600
    ws_per_day = studio.daily_working_hours * ws_per_hour
    ws_per_week = studio.weekly_working_days * ws_per_day
    ws_per_month = ws_per_week * 4
    ws_per_year = studio.yearly_working_days * ws_per_day

    sql_query = sql_query % {
        'project_id': project_id,
        'start_of_today': start_of_today.strftime('%Y-%m-%d %H:%M:%S'),
        'end_of_today': end_of_today.strftime('%Y-%m-%d %H:%M:%S'),
        'working_seconds_per_hour': ws_per_hour,
        'working_seconds_per_day': ws_per_day,
        'working_seconds_per_week': ws_per_week,
        'working_seconds_per_month': ws_per_month,
        'working_seconds_per_year': ws_per_year
    }

    logger.debug('sql_query : %s' % sql_query)

    result = DBSession.connection().execute(sql_query)

    data = [
        {
            'task_id': r[0],
            'task_name': r[1],
            'resources': [
                '<a href="/users/%(id)s/view">%(name)s</a>' % {
                    'id': r[2][i],
                    'name': r[3][i]
                } for i in range(len(r[2]))
            ],
            'status': r[4],
            'status_color': r[5],
            'percent_complete': r[6]
        } for r in result.fetchall()
    ]

    end = time.time()
    logger.debug('%s rows took : %s seconds' % (len(data), (end - start)))

    return data


@view_config(
    route_name='view_project',
    renderer='templates/project/view/view_project.jinja2'
)
def view_project(request):
    """creates a list_entity_tasks_by_filter by using the given entity and filter
    """
    logger.debug('inside view_project')

    # get logged in user
    logged_in_user = get_logged_in_user(request)

    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    filter_id = request.params.get('f_id', -1)
    filter_entity = Entity.query.filter_by(id=filter_id).first()
    is_warning_list = False
    if not filter_entity:
        is_warning_list = True
        filter_entity = Status.query.filter_by(code='WIP').first()

    projects = Project.query.all()

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
        'is_warning_list': is_warning_list,
        'milliseconds_since_epoch': milliseconds_since_epoch,
        'projects': projects
    }

