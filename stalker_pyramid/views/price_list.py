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
from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config
from pyramid.response import Response

from stalker import (defaults, Good, Project, Studio, PriceList)
from stalker.db import DBSession
import transaction

import stalker_pyramid
from stalker_pyramid.views import (log_param, get_logged_in_user,
                                   PermissionChecker, milliseconds_since_epoch,
                                   StdErrToHTMLConverter)

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def query_price_list(price_list_name):
    """returns a Type instance either it creates a new one or gets it from DB
    """
    if not price_list_name:
        return None

    price_list_ = PriceList.filter_by(name=price_list_name).first()

    if price_list_name and price_list_ is None:
        # create a new PriceList
        logger.debug('creating new price_list: %s' % (
            price_list_name)
        )
        price_list_ = PriceList(
            name=price_list_name
        )
        DBSession.add(price_list_)

    return price_list_

@view_config(
    route_name='get_studio_goods',
    renderer='json'
)
@view_config(
    route_name='get_goods',
    renderer='json'
)
def get_goods(request):
    """
        give all define goods in a list
    """
    logger.debug('***get_studio_goods method starts ***')

    return [
        {
            'id': good.id,
            'name': good.name,
            'cost': good.cost,
            'msrp': good.msrp,
            'unit': good.unit,
            'price_list': good.price_list
        }
        for good in Good.query.order_by(Good.name.asc()).all()
    ]


@view_config(
    route_name='create_good'
)
def create_group(request):
    """creates a new Good
    """

    logger.debug('***create good method starts ***')

    logged_in_user = get_logged_in_user(request)


    came_from = request.params.get('came_from', '/')
    name = request.params.get('name', None)
    msrp = request.params.get('msrp', None)
    unit = request.params.get('unit', None)
    cost = request.params.get('cost', None)
    price_list_name = request.params.get('price_list_name', None)

    logger.debug('came_from : %s' % came_from)
    logger.debug('name : %s' % name)
    logger.debug('msrp : %s' % msrp)
    logger.debug('unit : %s' % unit)
    logger.debug('cost : %s' % cost)
    logger.debug('price_list_name : %s' % price_list_name)

    # create and add a new good
    if name and msrp and unit and cost and price_list_name:

        price_list = query_price_list(price_list_name)
        try:
            # create the new group
            new_good = Good(
                name=name,
                msrp=msrp,
                unit=unit,
                cost=cost,
                price_list = price_list
            )

            new_good.created_by = logged_in_user
            new_good.date_created = datetime.datetime.now()

            DBSession.add(new_good)

            logger.debug('added new good successfully')

            request.session.flash(
                'success:Good <strong>%s</strong> is '
                'created successfully' % name
            )

            logger.debug('***create good method ends ***')

        except BaseException as e:
            request.session.flash('error: %s' % e)
            HTTPFound(location=came_from)
    else:
        logger.debug('not all parameters are in request.params')
        transaction.abort()
        return Response(
            'There are missing parameters: '
            'name: %s' % name, 500
        )

    return Response('successfully created %s!' % name)


@view_config(
    route_name='update_good'
)
def update_good(request):
    """updates the good with data from request
    """

    logger.debug('***update group method starts ***')

    logged_in_user = get_logged_in_user(request)

    came_from = request.params.get('came_from', '/')
    good_id = request.matchdict.get('id')
    good = Good.query.filter_by(id=good_id).first()

    if not good:
        transaction.abort()
        return Response('There is no task with id: %s' % good_id, 500)

    name = request.params.get('name', None)
    msrp = request.params.get('msrp', None)
    unit = request.params.get('unit', None)
    cost = request.params.get('cost', None)
    price_list_name = request.params.get('price_list_name', None)

    if name and msrp and unit and cost and price_list_name:

        price_list = query_price_list(price_list_name)
         # update the group
        good.name = name
        good.msrp = msrp
        good.unit = unit
        good.cost = cost
        good.price_list = price_list
        good.updated_by = logged_in_user
        good.date_updated = datetime.datetime.now()

        DBSession.add(good)

        logger.debug('good is updated successfully')

        request.session.flash(
                'success:Good <strong>%s</strong> is updated successfully' % name
        )

        logger.debug('***update group method ends ***')
    else:
        logger.debug('not all parameters are in request.params')
        log_param(request, 'group_id')
        log_param(request, 'name')
        response = Response(
            'There are missing parameters: '
            'good_id: %s, name: %s' % (good_id, name), 500
        )
        transaction.abort()
        return response

    response = Response('successfully updated %s good!' % name)
    return response
