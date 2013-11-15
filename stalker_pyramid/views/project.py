# -*- coding: utf-8 -*-
# Stalker Pyramid a Web Base Production Asset Management System
# Copyright (C) 2009-2013 Erkan Ozgur Yilmaz
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
from pyramid.httpexceptions import HTTPOk, HTTPServerError, HTTPFound
from pyramid.view import view_config

from stalker.db import DBSession
from stalker import (User, ImageFormat, Repository, Structure, Status,
                     StatusList, Project, Entity, Task)
from stalker_pyramid.views import (get_date, get_date_range,
                                   get_logged_in_user,
                                   milliseconds_since_epoch)

import logging

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

    imf_id = request.params.get('image_format_id', -1)
    imf = ImageFormat.query.filter_by(id=imf_id).first()

    repo_id = request.params.get('repository_id', -1)
    repo = Repository.query.filter_by(id=repo_id).first()

    structure_id = request.params.get('structure_id', -1)
    structure = Structure.query.filter_by(id=structure_id).first()

    lead_id = request.params.get('lead_id', -1)
    lead = User.query.filter_by(id=lead_id).first()

    status = Status.query.filter_by(name='New').first()

    # get the dates
    start, end = get_date_range(request, 'start_and_end_dates')

    logger.debug('create_project          :')

    logger.debug('name          : %s' % name)
    logger.debug('code          : %s' % code)
    logger.debug('fps           : %s' % fps)
    logger.debug('imf_id        : %s' % imf_id)
    logger.debug('repo_id       : %s' % repo_id)
    logger.debug('repo          : %s' % repo)
    logger.debug('structure_id  : %s' % structure_id)
    logger.debug('structure     : %s' % structure)
    logger.debug('lead_id       : %s' % lead_id)
    logger.debug('lead          : %s' % lead)
    logger.debug('start         : %s' % start)
    logger.debug('end           : %s' % end)

    if name and code and imf and repo and structure and lead_id:
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
                repository=repo,
                created_by=logged_in_user,
                fps=fps,
                structure=structure,
                lead=lead,
                status_list=status_list,
                status=status,
                start=start,
                end=end
            )

            DBSession.add(new_project)
            # flash success message
            request.session.flash(
                'success:Project <strong>%s</strong> is created '
                'successfully' % name
            )
        except BaseException as e:
            request.session.flash('error:' + e.message)
            HTTPFound(location=came_from)

    else:
        logger.debug('there are missing parameters')
        HTTPServerError()

    return HTTPFound(
        location=came_from
    )


@view_config(
    route_name='update_project'
)
def update_project(request):
    """called when updating a Project
    """
    logged_in_user = get_logged_in_user(request)

    # parameters
    project_id = request.params.get('project_id', -1)
    project = Project.query.filter_by(id=project_id).first()

    name = request.params.get('name')

    fps = int(request.params.get('fps'))

    imf_id = request.params.get('image_format', -1)
    imf = ImageFormat.query.filter_by(id=imf_id).first()

    repo_id = request.params.get('repository_id', -1)
    repo = Repository.query.filter_by(id=repo_id).first()

    structure_id = request.params.get('structure_id', -1)
    structure = Structure.query.filter_by(id=structure_id).first()

    lead_id = request.params.get('lead_id', -1)
    lead = User.query.filter_by(id=lead_id).first()

    status_id = request.params.get('status_id', -1)
    status = Status.query.filter_by(id=status_id).first()

    # get the dates
    start = get_date(request, 'start')
    end = get_date(request, 'end')

    if project and name and imf and repo and structure and lead and \
            status:

        project.name = name
        project.image_format = imf
        project.repository = repo
        project.updated_by = logged_in_user
        project.date_updated = datetime.datetime.now()
        project.fps = fps
        project.structure = structure
        project.lead = lead
        project.status = status
        project.start = start
        project.end = end

        DBSession.add(project)

    else:
        logger.debug('there are missing parameters')
        HTTPServerError()

    return HTTPOk()


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

    return [
        {
            'project_id': project.id,
            'project_name': project.name,
            'lead_id': project.lead.id,
            'lead_name': project.lead.name,
            'date_created': milliseconds_since_epoch(project.date_created),
            'created_by_id': project.created_by.id,
            'created_by_name': project.created_by.name,
            'thumbnail_full_path': project.thumbnail.full_path
            if project.thumbnail else None,
            'status': project.status.name,
            'users_count': len(project.users),
            'percent_complete': project.percent_complete
        }
        for project in entity.projects
    ]


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

    tasks_today = []

    if action == 'progress':
        tasks_today = Task.query.join(Project, Task.project) \
            .filter(Project.id == project_id) \
            .filter(Task.computed_start < end_of_today) \
            .filter(Task.computed_end > start_of_today).all()

    elif action == 'end':
        tasks_today = Task.query.join(Project, Task.project) \
            .filter(Project.id == project_id) \
            .filter(Task.computed_end > start_of_today) \
            .filter(Task.computed_end <= end_of_today).all()

    task_today_list = []

    for task in tasks_today:
        assert isinstance(task, Task)
        if task.is_leaf:
            resources_str = ''
            for user in task.resources:
                resources_str += \
                    '<a href="/users/%s/view">%s</a><br/>' % (user.id,
                                                              user.name)

            task_today_list.append({
                'task_id': task.id,
                'task_name': '%s (%s)' %
                             (task.name, ' | '.join([
                                 parent.name for parent in task.parents])),
                'resources': resources_str,
                'created_by_id': task.created_by.id,
                'created_by_name': task.created_by.name,
                'status': task.status.name,
                'status_color': task.status.html_class,
                'percent_complete': task.percent_complete
            })

    return task_today_list
