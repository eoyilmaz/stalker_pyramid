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

from pyramid.httpexceptions import HTTPServerError, HTTPOk
from pyramid.security import authenticated_userid
from pyramid.view import view_config


from stalker.db import DBSession
from stalker import User, Project, StatusList, Status, Sequence, Entity

import logging
from stalker_pyramid.views import PermissionChecker, get_logged_in_user

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


@view_config(
    route_name='dialog_create_sequence',
    renderer='templates/sequence/dialog_create_sequence.jinja2'
)
def create_sequence_dialog(request):
    """fills the create sequence dialog
    """
    project_id = request.matchdict.get('id', -1)
    project = Project.query.filter_by(id=project_id).first()

    return {
        'mode': 'CREATE',
        'has_permission': PermissionChecker(request),
        'project': project
    }


@view_config(
    route_name='dialog_update_sequence',
    renderer='templates/sequence/dialog_create_sequence.jinja2'
)
def update_sequence_dialog(request):
    """fills the create sequence dialog
    """
    sequence_id = request.matchdict.get('id', -1)
    sequence = Sequence.query.filter_by(id=sequence_id).first()

    return {
        'mode': 'UPDATE',
        'sequence': sequence,
        'has_permission': PermissionChecker(request),
        'project': sequence.project
    }

@view_config(
    route_name='create_sequence'
)
def create_sequence(request):
    """runs when adding a new sequence
    """
    logged_in_user = get_logged_in_user(request)

    name = request.params.get('name')
    code = request.params.get('code')

    status_id = request.params.get('status_id')
    status = Status.query.filter_by(id=status_id).first()

    project_id = request.params.get('project_id')
    project = Project.query.filter_by(id=project_id).first()

    logger.debug('project_id   : %s' % project_id)

    if name and code  and status and  project:
        # get descriptions
        description = request.params.get('description')

        # get the status_list
        status_list = StatusList.query.filter_by(
            target_entity_type='Sequence'
        ).first()

        # there should be a status_list
        # TODO: you should think about how much possible this is
        if status_list is None:
            return HTTPServerError(detail='No StatusList found')


        new_sequence = Sequence(
                        name=name,
                        code=code,
                        description=description,
                        status_list=status_list,
                        status=status,
                        created_by=logged_in_user,
                        project=project
                    )

        DBSession.add(new_sequence)

    else:
        logger.debug('there are missing parameters')
        logger.debug('name      : %s' % name)
        logger.debug('code      : %s' % code)
        logger.debug('status    : %s' % status)
        logger.debug('project   : %s' % project)
        HTTPServerError()

    return HTTPOk()

@view_config(
    route_name='update_sequence'
)
def update_sequence(request):
    """runs when adding a new sequence
    """
    logged_in_user = get_logged_in_user(request)

    sequence_id = request.params.get('sequence_id')
    sequence = Sequence.query.filter_by(id=sequence_id).first()

    name = request.params.get('name')
    code = request.params.get('code')

    status_id = request.params.get('status_id')
    status = Status.query.filter_by(id=status_id).first()


    if sequence and code and name  and status:
        # get descriptions
        description = request.params.get('description')

        #update the sequence
        sequence.name = name
        sequence.code = code
        sequence.description = description
        sequence.status = status
        sequence.updated_by = logged_in_user
        sequence.date_updated = datetime.datetime.now()

        DBSession.add(sequence)

    else:
        logger.debug('there are missing parameters')
        logger.debug('name      : %s' % name)
        logger.debug('status    : %s' % status)
        HTTPServerError()

    return HTTPOk()



@view_config(
    route_name='view_sequence',
    renderer='templates/sequence/page_view_sequence.jinja2'
)
def view_sequence(request):
    """runs when viewing an sequence
    """

    login = authenticated_userid(request)
    logged_in_user = User.query.filter_by(login=login).first()

    sequence_id = request.matchdict.get('id', -1)
    sequence = Sequence.query.filter_by(id=sequence_id).first()

    return {
        'user': logged_in_user,
        'sequence': sequence,
        'has_permission': PermissionChecker(request)
    }


@view_config(
    route_name='get_sequences',
    renderer='json'
)
def get_sequences(request):
    """returns all sequences as a json data
    """
    return [
        {
            'id': sequence.id,
            'name': sequence.name,
            'status': sequence.status.name,
            'status_bg_color': sequence.status.bg_color,
            'status_fg_color': sequence.status.fg_color,
            'user_id': sequence.created_by.id,
            'user_name': sequence.created_by.name,
            'thumbnail_path': sequence.thumbnail.full_path if sequence.thumbnail else None
        }
        for sequence in Sequence.query.all()
    ]


@view_config(
    route_name='get_project_sequences',
    renderer='json'
)
@view_config(
    route_name='get_entity_sequences',
    renderer='json'
)
def get_project_sequences(request):
    """returns the related sequences of the given project as a json data
    """
    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    return [
        {
            'id': sequence.id,
            'name': sequence.name,
            'status': sequence.status.name,
            'status_bg_color': sequence.status.bg_color,
            'status_fg_color': sequence.status.fg_color,
            'user_id': sequence.created_by.id,
            'user_name': sequence.created_by.name,
            'thumbnail_path': sequence.thumbnail.full_path if sequence.thumbnail else None
        }
        for sequence in entity.sequences
    ]
