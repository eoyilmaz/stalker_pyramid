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

import time
import datetime

from pyramid.httpexceptions import HTTPOk
from pyramid.view import view_config
from stalker import Type, Status, Asset
from stalker.db import DBSession

import logging
from stalker_pyramid.views import get_logged_in_user

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@view_config(
    route_name='update_asset',
    permission='Update_Asset'
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
    route_name='get_entity_assets_count',
    renderer='json',
    permission='List_Asset'
)
@view_config(
    route_name='get_project_assets_count',
    renderer='json',
    permission='List_Asset'
)
def get_assets_count(request):
    """returns the count of assets in a project
    """
    project_id = request.matchdict.get('id', -1)

    sql_query = """select count(1)
    from "Assets"
        join "Tasks" on "Assets".id = "Tasks".id
    where "Tasks".project_id = %s
    """ % project_id

    return DBSession.connection().execute(sql_query).fetchone()[0]


@view_config(
    route_name='get_entity_assets',
    renderer='json',
    permission='List_Asset'
)
@view_config(
    route_name='get_project_assets',
    renderer='json',
    permission='List_Asset'
)
def get_assets(request):
    """returns all the Assets of a given Project
    """
    logger.debug('*** get_assets method starts ***')

    project_id = request.matchdict.get('id', -1)

    start = time.time()
    sql_query = """select
        "Assets".id,
        "SimpleEntities".name,
        "Assets".code,
        "SimpleEntities".description,
        "Types".id as type_id,
        "SimpleEntities_Types".name as type_name,
        extract(epoch from "SimpleEntities".date_created) * 1000,
        "SimpleEntities".created_by_id,
        "SimpleEntities_CreatedBy".name as created_by_name,
        "Links".full_path as thumbnail_full_path,
        "SimpleEntities_Statuses".name as status_name,
        "SimpleEntities_Statuses".html_class as status_html_class,
        "Tasks"._total_logged_seconds::float / "Tasks"._schedule_seconds * 100 as percent_complete
    from "Assets"
        join "Tasks" on "Assets".id = "Tasks".id
        join "SimpleEntities" on "Assets".id = "SimpleEntities".id
        left outer join "Links" on "SimpleEntities".thumbnail_id = "Links".id
        join "Statuses" on "Tasks".status_id = "Statuses".id
        left outer join "SimpleEntities" as "SimpleEntities_Statuses" on "Statuses".id = "SimpleEntities_Statuses".id
        left outer join "Types" on "SimpleEntities".type_id = "Types".id
        join "SimpleEntities" as "SimpleEntities_Types" on "Types".id = "SimpleEntities_Types".id
        left outer join "SimpleEntities" as "SimpleEntities_CreatedBy" on "SimpleEntities".created_by_id = "SimpleEntities_CreatedBy".id
    where "Tasks".project_id = %(project_id)s
    order by type_name, name
    """ % {'project_id': project_id}

    result = DBSession.connection().execute(sql_query)

    data = [
        {
            'id': r[0],
            'name': r[1],
            'code': r[2],
            'description': r[3],
            'type_id': r[4],
            'type_name': r[5],
            'date_created': r[6],
            'created_by_id': r[7],
            'created_by_name': r[8],
            'thumbnail_full_path': r[9],
            'status': r[10],
            'status_color': r[11],
            'percent_complete': r[12]
        } for r in result.fetchall()
    ]

    end = time.time()
    logger.debug(
        '%s rows retrieved in : %s seconds' % (len(data), (end - start))
    )

    return data
