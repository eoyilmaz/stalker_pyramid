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
from pyramid.httpexceptions import HTTPOk, HTTPServerError
from pyramid.response import Response
from pyramid.view import view_config

from stalker.db import DBSession
from stalker import (User, ImageFormat, Repository, Structure, Status,
                     StatusList, Project, Entity)
from stalker_pyramid.views import (get_date, get_logged_in_user,
                                   PermissionChecker, milliseconds_since_epoch)

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


import colander 
from deform import Form, ValidationFailure


@view_config(
    route_name='deform_test',
    renderer='templates/index.jinja2'
)
def deform_test(request):
    """testing the deform library
    """
    class Person(colander.MappingSchema):
        name = colander.SchemaNode(colander.String())
        age = colander.SchemaNode(colander.Integer(),
                                  validator=colander.Range(0, 200))

    class People(colander.SequenceSchema):
        person = Person()

    class Schema(colander.MappingSchema):
        people = People()

    schema = Schema()
    myform = Form(schema=schema, buttons=('submit',))

    if 'submit' in request.POST:
        logger.debug('submit in POST')

        controls = request.POST.items()
        try:
            appstruct = myform.validate(controls)  # call validate
        except ValidationFailure, e: # catch the exception
            return {'form':e.render()} # re-render the form with an exception

        # the form submission succeeded, we have the data
        return {
            'form': None,
            'appstruct': appstruct
        }

    html = myform.render()

    return {
        'form': html
    }


@view_config(
    route_name='dialog_create_project',
    renderer='templates/project/dialog_create_project.jinja2',
)
def create_project_dialog(request):
    """called when the create project dialog is requested
    """
    logged_in_user = get_logged_in_user(request)

    return {
        'mode': 'CREATE',
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'milliseconds_since_epoch': milliseconds_since_epoch
    }


@view_config(
    route_name='dialog_update_project',
    renderer='templates/project/dialog_create_project.jinja2'
)
def update_project_dialog(request):
    """runs when updating a project
    """
    logged_in_user = get_logged_in_user(request)

    project_id = request.matchdict.get('id', -1)
    project = Project.query.filter_by(id=project_id).first()

    return {
        'mode': 'UPDATE',
        'has_permission': PermissionChecker(request),
        'project': project,
        'logged_in_user': logged_in_user,
        'milliseconds_since_epoch': milliseconds_since_epoch
    }


@view_config(
    route_name='create_project'
)
def create_project(request):
    """called when adding a new Project
    """
    logged_in_user = get_logged_in_user(request)

    # parameters
    name = request.params.get('name')
    code = request.params.get('code')
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

    if name and code and imf and repo and structure and lead_id and status:
        # lets create the project

        # status list
        status_list = StatusList.query \
            .filter_by(target_entity_type='Project').first()

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

    else:
        logger.debug('there are missing parameters')
        HTTPServerError()

    return HTTPOk()


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
    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    return [
        {
            'id': project.id,
            'name': project.name,
            'thumbnail_path': project.thumbnail.full_path
            if project.thumbnail else None
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
