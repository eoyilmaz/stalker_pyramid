# -*- coding: utf-8 -*-
# Stalker a Production Shot Management System
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
from pyramid.view import view_config

from stalker.db import DBSession
from stalker import Sequence, StatusList, Status, Shot, Project

import logging
from stalker_pyramid.views import get_logged_in_user, milliseconds_since_epoch

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


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
        shot.sequence = sequence
        shot.status = status
        shot.updated_by = logged_in_user
        shot.date_updated = datetime.datetime.now()

        DBSession.add(shot)

    else:
        logger.debug('there are missing parameters')
        logger.debug('name      : %s' % name)
        logger.debug('status    : %s' % status)
        HTTPServerError()

    return HTTPOk()


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
    project_id = request.matchdict.get('id', -1)
    shots = []

    for shot in Shot.query.filter_by(project_id=project_id).all():
        sequence_str = ''

        for sequence in shot.sequences:
            sequence_str += \
                '<a href="/task/%s/view">%s</a><br/>' % (sequence.id,
                                                         sequence.name)
        shots.append({
            'id': shot.id,
            'name': shot.name,
            'sequences': sequence_str,
            'status': shot.status.name,
            'status_color': shot.status.html_class
            if shot.status.html_class else 'grey',
            'status_bg_color': shot.status.bg_color,
            'status_fg_color': shot.status.fg_color,
            'created_by_id': shot.created_by.id,
            'created_by_name': shot.created_by.name,
            'description': shot.description,
            'date_created': milliseconds_since_epoch(shot.date_created),
            'thumbnail_full_path': shot.thumbnail.full_path
            if shot.thumbnail else None,
            'percent_complete': shot.percent_complete
        })

    return shots
