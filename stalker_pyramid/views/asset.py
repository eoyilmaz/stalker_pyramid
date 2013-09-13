# -*- coding: utf-8 -*-
# Stalker Pyramid a Web Based Production Asset Management System
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
from stalker import Project, Type, StatusList, Status, Asset, Studio
from stalker.db import DBSession

import logging
import stalker_pyramid
from stalker_pyramid.views import PermissionChecker, get_logged_in_user, milliseconds_since_epoch

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@view_config(
    route_name='create_asset'
)
def create_asset(request):
    """creates a new Asset
    """
    logger.debug('***create_asset method starts ***')

    logged_in_user = get_logged_in_user(request)

    # get params
    name = request.params.get('name')
    code = request.params.get('code')
    description = request.params.get('description')
    type_name = request.params.get('type_name')

    status_id = request.params.get('status_id')
    status = Status.query.filter_by(id=status_id).first()

    project_id = request.params.get('project_id')
    project = Project.query.filter_by(id=project_id).first()
    logger.debug('project_id   : %s' % project_id)

    if name and code and type_name and status and  project:
        # get the type
        type_ = Type.query\
            .filter_by(target_entity_type='Asset')\
            .filter_by(name=type_name)\
            .first()

        if type_ is None:
            # create a new Type
            # TODO: should we check for permission here or will it be already done in the UI (ex. filteringSelect instead of comboBox)
            type_ = Type(
                name=type_name,
                code=type_name,
                target_entity_type='Asset'
            )

        # get the status_list
        status_list = StatusList.query.filter_by(
            target_entity_type='Asset'
        ).first()

        # there should be a status_list
        # TODO: you should think about how much possible this is
        if status_list is None:
            return HTTPServerError(detail='No StatusList found')

        # create the asset
        new_asset = Asset(
            name=name,
            code=code,
            description=description,
            project=project,
            type=type_,
            status_list=status_list,
            status=status,
            created_by=logged_in_user
        )

        DBSession.add(new_asset)
    else:
        logger.debug('there are missing parameters')
        logger.debug('name      : %s' % name)
        logger.debug('code      : %s' % code)
        logger.debug('type_name : %s' % type_name)
        logger.debug('status    : %s' % status)
        logger.debug('project   : %s' % project)
        HTTPServerError()

    return HTTPOk()


@view_config(
    route_name='update_asset'
)
def update_asset(request):
    """updates an Asset
    """

    logger.debug('***update_asset method starts ***')
    logged_in_user = get_logged_in_user(request)

    # get params
    asset_id = request.matchdict.get('id', -1)
    asset = Asset.query.filter_by(id=asset_id).first()

    name = request.params.get('name')
    code = request.params.get('code')
    description = request.params.get('description')
    type_name = request.params.get('type_name')

    status_id = request.params.get('status_id')
    status = Status.query.filter_by(id=status_id).first()

    if asset and name and code and type_name and status:
        # get the type
        type_ = Type.query\
            .filter_by(target_entity_type='Asset')\
            .filter_by(name=type_name)\
            .first()

        if type_ is None:
            # create a new Type
            type_ = Type(
                name=type_name,
                code=type_name,
                target_entity_type='Asset'
            )

        # update the asset
        logger.debug('code      : %s' % code)
        asset.name = name
        asset.code = code
        asset.description = description
        asset.type = type_
        asset.status = status
        asset.updated_by = logged_in_user
        asset.date_updated = datetime.datetime.now()

        DBSession.add(asset)

    return HTTPOk()




@view_config(
    route_name='get_entity_assets',
    renderer='json'
)
@view_config(
    route_name='get_project_assets',
    renderer='json'
)
def get_assets(request):
    """returns all the Assets of a given Project
    """
    # TODO: this should be paginated
    logger.debug('*** get_assets method starts ***')

    project_id = request.matchdict.get('id', -1)

    return [
        {
            'thumbnail_full_path': asset.thumbnail.full_path if asset.thumbnail else None,
            'id': asset.id,
            'name': asset.name,
            'code': asset.code,
            'type_name': asset.type.name,
            'type_id': asset.type.id,
            'status': asset.status.name,
            'status_bg_color': asset.status.bg_color,
            'status_fg_color': asset.status.fg_color,
            'created_by_id': asset.created_by.id,
            'created_by_name': asset.created_by.name,
            'description': asset.description,
            'date_created':milliseconds_since_epoch(asset.date_created),
            'percent_complete': asset.percent_complete
        }
        for asset in Asset.query.filter_by(project_id=project_id).all()
    ]


@view_config(
    route_name='get_asset_types',
    renderer='json'
)
def get_asset_types(request):
    """returns all the Assets of a given Project
    """
    logger.debug('*** get_asset_types method starts ***')
    return [
        {
            'id': asset_type.id,
            'name': asset_type.name
        }
        for asset_type in Type.query.filter_by(target_entity_type='Asset').all()
    ]
