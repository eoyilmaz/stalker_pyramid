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
import transaction
from webob import Response
from stalker_pyramid.views import (get_logged_in_user, PermissionChecker,
                                   milliseconds_since_epoch, get_date, StdErrToHTMLConverter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@view_config(
    route_name='entity_vacation_dialog',
    renderer='templates/vacation/dialog/vacation_dialog.jinja2',
)
@view_config(
    route_name='studio_vacation_dialog',
    renderer='templates/vacation/dialog/vacation_dialog.jinja2',
)
@view_config(
    route_name='user_vacation_dialog',
    renderer='templates/vacation/dialog/vacation_dialog.jinja2',
)
def create_vacation_dialog(request):
    """creates a create_vacation_dialog by using the given user
    """
    logger.debug('***create_vacation_dialog method starts ***')

    came_from = request.params.get('came_from','/')
    logger.debug('came_from %s '% came_from)

    # get logged in user
    logged_in_user = get_logged_in_user(request)

    entity_id = int(request.matchdict.get('id', -1))
    entity = Entity.query.filter(Entity.entity_id == entity_id).first()

    logger.debug('entity %s '% entity)

    vacation_types = Type.query.filter(
        Type.target_entity_type == 'Vacation').filter(Type.name !='StudioWide').all()


    studio = Studio.query.first()

    if not studio:
        studio = defaults

    if entity.entity_type == 'Studio':
        # user = studio
        vacation_types = Type.query.filter(
        Type.target_entity_type == 'Vacation').filter(Type.name =='StudioWide').all()

    return {
        'mode': 'create',
        'has_permission': PermissionChecker(request),
        'studio': studio,
        'logged_in_user': logged_in_user,
        'entity': entity,
        'came_from':came_from,
        'types': vacation_types,
        'milliseconds_since_epoch': milliseconds_since_epoch
    }


@view_config(
    route_name='vacation_update_dialog',
    renderer='templates/vacation/dialog/vacation_dialog.jinja2',
)
def update_vacation_dialog(request):
    """updates a create_vacation_dialog by using the given user
    """
    logger.debug('***update_vacation_dialog method starts ***')

    came_from = request.params.get('came_from','/')
    logger.debug('came_from %s: '% came_from)

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
        vacation_types = Type.query.filter(
        Type.target_entity_type == 'Vacation').filter(Type.name =='StudioWide').all()

    return {
        'mode': 'update',
        'has_permission': PermissionChecker(request),
        'studio': studio,
        'logged_in_user': logged_in_user,
        'entity': user,
        'vacation': vacation,
        'came_from':came_from,
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

    logger.debug('type_name     : %s' % type_name)
    logger.debug('user        : %s' % user)
    logger.debug('start_date  : %s' % start_date)
    logger.debug('end_date    : %s' % end_date)
    logger.debug('user_id     : %s' % user_id)

    if start_date and end_date and type_name:
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

            # request.session.flash(
            #     'success:<strong>%s</strong> vacation is created for <strong>%s</strong>.' % (type_.name, Studio.query.first().name)
            # )

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

            request.session.flash(
                'success:<strong>%s</strong> vacation is created for <strong>%s</strong>.' % (type_.name, user.name)
            )
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
    logged_in_user = get_logged_in_user(request)

    #**************************************************************************
    # collect data

    vacation_id = request.matchdict.get('id', -1)
    vacation = Vacation.query.filter_by(id=vacation_id).first()


    type_name = request.params.get('type_name')
    start_date = get_date(request, 'start')
    end_date = get_date(request, 'end')

    logger.debug('start_date  : %s' % start_date)
    logger.debug('end_date    : %s' % end_date)
    logger.debug('vacation    : %s' % vacation)
    logger.debug('vacation_id    : %s' % vacation_id)

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

        request.session.flash(
           'success: <strong>%s</strong> vacation is updated for %s.' % (type_.name,(vacation.user.name if vacation.user else Studio.query.first().name ))
        )

        logger.debug('vacation_id    : %s is updated! ' % vacation_id)

    else:
        HTTPServerError()

    return HTTPOk()


@view_config(
    route_name='get_entity_vacations_count',
    renderer='json'
)
@view_config(
    route_name='get_studio_vacations_count',
    renderer='json'
)
@view_config(
    route_name='get_user_vacations_count',
    renderer='json'
)
def get_vacations_count(request):
    """returns the count of vacations of the given entity
    """
    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter(Entity.id == entity_id).first()

    vacations = Vacation.query.filter(Vacation.user == None).all()
    if isinstance(entity, User):
        vacations.extend(entity.vacations)

    return len(vacations)


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

    vacations = Vacation.query.filter(Vacation.user==None).all()
    if isinstance(entity, User):
        vacations.extend(entity.vacations)

    return [{
            'id': vacation.id,
            'entity_type':vacation.plural_class_name.lower(),
            'title': vacation.type.name,
            'start': milliseconds_since_epoch(vacation.start),
            'end': milliseconds_since_epoch(vacation.end),
            'className': 'label-yellow',
            'allDay': True,
            'status': ''
        } for vacation in vacations]


@view_config(
    route_name='delete_vacation',
    permission='Delete_TimeLog'
)
def delete_vacation(request):
    """deletes the vacation with the given id
    """
    vacation_id = request.matchdict.get('id')
    vacation = Vacation.query.get(vacation_id)

    logger.debug('delete_vacation: %s' % vacation_id)

    if not vacation:
        transaction.abort()
        return Response('Can not find a Vacation with id: %s' % vacation_id, 500)

    try:
        DBSession.delete(vacation)
        transaction.commit()
    except Exception as e:
        transaction.abort()
        c = StdErrToHTMLConverter(e)
        transaction.abort()
        return Response(c.html(), 500)

    return Response('Successfully deleted vacation: %s' % vacation_id)
