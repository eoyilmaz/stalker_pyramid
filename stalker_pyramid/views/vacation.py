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
import logging

from pyramid.httpexceptions import HTTPOk, HTTPServerError
from pyramid.view import view_config
from stalker import User, Studio, Vacation, Type, Entity

from stalker import defaults

from stalker.db import DBSession
from stalker_pyramid.views import (get_logged_in_user, PermissionChecker,
                                   milliseconds_since_epoch, get_date)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@view_config(
    route_name='dialog_create_vacation',
    renderer='templates/vacation/dialog_create_vacation.jinja2',
)
def create_vacation_dialog(request):
    """creates a create_vacation_dialog by using the given user
    """
    logger.debug('inside create_vacation_dialog')

    # get logged in user
    logged_in_user = get_logged_in_user(request)

    user_id = int(request.matchdict.get('id', -1))
    user = User.query.filter(User.user_id == user_id).first()

    vacation_types = Type.query.filter(
        Type.target_entity_type == 'Vacation').all()

    studio = Studio.query.first()

    if not studio:
        studio = defaults

    if not user:
        user = studio
        vacation_types = []

    return {
        'mode': 'CREATE',
        'has_permission': PermissionChecker(request),
        'studio': studio,
        'logged_in_user': logged_in_user,
        'user': user,
        'types': vacation_types,
        'milliseconds_since_epoch': milliseconds_since_epoch
    }


@view_config(
    route_name='dialog_update_vacation',
    renderer='templates/vacation/dialog_create_vacation.jinja2',
)
def update_vacation_dialog(request):
    """updates a create_vacation_dialog by using the given user
    """
    logger.debug('inside updates_vacation_dialog')

    # get logged in user
    logged_in_user = get_logged_in_user(request)

    vacation_id = request.matchdict.get('id', -1)
    vacation = Vacation.query.filter_by(id=vacation_id).first()

    vacation_types = Type.query.filter(
        Type.target_entity_type == 'Vacation').all()

    studio = Studio.query.first()

    if not studio:
        studio = defaults

    user = vacation.user
    if not vacation.user:
        user = studio
        vacation_types = []

    return {
        'mode': 'UPDATE',
        'has_permission': PermissionChecker(request),
        'studio': studio,
        'logged_in_user': logged_in_user,
        'user': user,
        'vacation': vacation,
        'types': vacation_types,
        'milliseconds_since_epoch': milliseconds_since_epoch
    }


@view_config(
    route_name='create_vacation'
)
def create_vacation(request):
    """runs when creating a vacation
    """

    logger.debug('inside create_vacation')
    user_id = int(request.params.get('user_id'))
    user = User.query.filter(User.id == user_id).first()

    #**************************************************************************
    # collect data
    logged_in_user = get_logged_in_user(request)

    type_name = request.params.get('type_name')
    start_date = get_date(request, 'start')
    end_date = get_date(request, 'end')

    logger.debug('user_id     : %s' % user_id)
    logger.debug('user        : %s' % user)
    logger.debug('start_date  : %s' % start_date)
    logger.debug('end_date    : %s' % end_date)

    if start_date and end_date:
        # we are ready to create the time log
        # Vacation should handle the extension of the effort

        type_ = Type.query \
            .filter_by(target_entity_type='Vacation') \
            .filter_by(name=type_name) \
            .first()

        if type_ is None:
            # create a new Type
            # TODO: should we check for permission here or will it be already done in the UI (ex. filteringSelect instead of comboBox)
            type_ = Type(
                name=type_name,
                code=type_name,
                target_entity_type='Vacation'
            )

        if not user:
            logger.debug('its a studio vacation')

            vacation = Vacation(
                created_by=logged_in_user,
                type=type_,
                start=start_date,
                end=end_date
            )
            DBSession.add(vacation)
        else:
            logger.debug('its a personal vacation')
            vacation = Vacation(
                user=user,
                created_by=logged_in_user,
                type=type_,
                start=start_date,
                end=end_date
            )
            DBSession.add(vacation)
        logger.debug('end of creating vacation')

    else:
        HTTPServerError()

    return HTTPOk()


@view_config(
    route_name='update_vacation'
)
def update_vacation(request):
    """runs when updating a vacation
    """

    vacation_id = request.params.get('vacation_id')
    vacation = Vacation.query.filter_by(id=vacation_id).first()


    #**************************************************************************
    # collect data
    logged_in_user = get_logged_in_user(request)

    type_name = request.params.get('type_name')
    start_date = get_date(request, 'start')
    end_date = get_date(request, 'end')

    logger.debug('start_date  : %s' % start_date)
    logger.debug('end_date    : %s' % end_date)

    if vacation and start_date and end_date:
        # we are ready to create the time log
        # Vacation should handle the extension of the effort
        type_ = Type.query \
            .filter_by(target_entity_type='Vacation') \
            .filter_by(name=type_name) \
            .first()

        if type_ is None:
            # create a new Type
            # TODO: should we check for permission here or will it be already done in the UI (ex. filteringSelect instead of comboBox)
            type_ = Type(
                name=type_name,
                code=type_name,
                target_entity_type='Vacation'
            )

        vacation.updated_by = logged_in_user
        vacation.type = type_
        vacation.start = start_date
        vacation.end = end_date
        DBSession.add(vacation)


    else:
        HTTPServerError()

    return HTTPOk()


@view_config(
    route_name='get_entity_vacations',
    renderer='json'
)
@view_config(
    route_name='get_studio_vacations',
    renderer='json'
)
@view_config(
    route_name='get_user_vacations',
    renderer='json'
)
def get_vacations(request):
    """returns all the Shots of the given Project
    """
    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter(Entity.id==entity_id).first()

    vacations = []
    if isinstance(entity, Studio):
        vacations = Vacation.query.filter(Vacation.user==None).all()
    elif isinstance(entity, User):
        vacations = entity.vacations

    return [{
            'id': vacation.id,
            'type': vacation.type.name,
            'created_by_id': vacation.created_by_id,
            'created_by_name': vacation.created_by.name,
            'start_date': milliseconds_since_epoch(vacation.start),
            'end_date': milliseconds_since_epoch(vacation.end)
        } for vacation in vacations]
