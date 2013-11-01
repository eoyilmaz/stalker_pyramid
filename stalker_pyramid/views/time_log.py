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
from pyramid.response import Response
from pyramid.view import view_config

from stalker import defaults, Task, User, Studio, TimeLog, Entity, Status

from stalker.db import DBSession
from stalker.exceptions import OverBookedError
from stalker_pyramid.views import (get_logged_in_user,
                                   PermissionChecker, milliseconds_since_epoch,
                                   get_date, StdErrToHTMLConverter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@view_config(
    route_name='task_time_log_dialog',
    renderer='templates/time_log/dialog/time_log_dialog.jinja2',
)
@view_config(
    route_name='user_time_log_dialog',
    renderer='templates/time_log/dialog/time_log_dialog.jinja2',
)
@view_config(
    route_name='entity_time_log_dialog',
    renderer='templates/time_log/dialog/time_log_dialog.jinja2',
)
def create_time_log_dialog(request):
    """creates a create_time_log_dialog by using the given task
    """
    logger.debug('inside time_log_dialog')

    came_from = request.params.get('came_from','/')
    logger.debug('came_from %s: '% came_from)

    # get logged in user
    logged_in_user = get_logged_in_user(request)

    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    studio = Studio.query.first()
    if not studio:
        studio = defaults

    return {
        'mode': 'create',
        'has_permission': PermissionChecker(request),
        'studio': studio,
        'logged_in_user': logged_in_user,
        'entity': entity,
        'came_from':came_from,
        'milliseconds_since_epoch': milliseconds_since_epoch,
    }


@view_config(
    route_name='time_log_update_dialog',
    renderer='templates/time_log/dialog/time_log_dialog.jinja2',
)
def update_time_log_dialog(request):
    """updates a create_time_log_dialog by using the given task
    """
    logger.debug('inside updates_time_log_dialog')

    came_from = request.params.get('came_from','/')
    logger.debug('came_from %s: '% came_from)

    # get logged in user
    logged_in_user = get_logged_in_user(request)

    time_log_id = request.matchdict.get('id', -1)
    time_log = TimeLog.query.filter_by(id=time_log_id).first()

    studio = Studio.query.first()
    if not studio:
        studio = defaults

    return {
        'mode': 'update',
        'has_permission': PermissionChecker(request),
        'studio': studio,
        'logged_in_user': logged_in_user,
        'task': time_log.task,
        'came_from': came_from,
        'time_log': time_log,
        'milliseconds_since_epoch': milliseconds_since_epoch
    }


@view_config(
    route_name='create_time_log'
)
def create_time_log(request):
    """runs when creating a time_log
    """

    logger.debug('inside create_time_log')
    task_id = request.params.get('task_id')
    task = Task.query.filter(Task.id == task_id).first()

    #**************************************************************************
    # collect data
    resource_id = request.params.get('resource_id', None)
    resource = User.query.filter(User.id == resource_id).first()

    start_date = get_date(request, 'start')
    end_date = get_date(request, 'end')

    logger.debug('task_id     : %s' % task_id)
    logger.debug('task        : %s' % task)
    logger.debug('resource_id : %s' % resource_id)
    logger.debug('start_date  : %s' % start_date)
    logger.debug('end_date    : %s' % end_date)

    if task and resource and start_date and end_date:
        # we are ready to create the time log
        # TimeLog should handle the extension of the effort
        logger.debug('got all the data')
        try:
            time_log = TimeLog(
                task=task,
                resource=resource,
                start=start_date,
                end=end_date
            )

            # check the dependent tasks has finished
            compl = Status.query.filter(Status.code == "CMPL").first()
            for dep_task in task.depends:
                if dep_task.status != compl:
                    response = Response(
                        'Because one of the dependencies (Task: %s (%s)) has '
                        'not finished, \n'
                        'You can not create time logs for this task yet!'
                        '\n\nPlease, inform %s to finish this task!' %
                        (dep_task.name, dep_task.id,
                         [r.name for r in dep_task.resources])
                    )
                    response.status_int = 500
                    return response

            # check the depending tasks
            for dep_task in task.dependent_of:
                if len(dep_task.time_logs) > 0:
                    response = Response(
                        'Because one of the depending (Task: %s (%s)) has '
                        'already started, \n'
                        'You can not create any more time logs for this task!'
                        '\n\nPlease, inform %s about this situation!' %
                        (dep_task.name, dep_task.id,
                         task.responsible.name)
                    )
                    response.status_int = 500
                    return response

            # set the status to wip for this task
            logger.debug('Updating Task (%s) status to WIP!' % task_id)
            wip = Status.query.filter(Status.code == "WIP").first()
            task.status = wip
            DBSession.add(task)
        except OverBookedError as e:
            converter = StdErrToHTMLConverter(e)
            response = Response(converter.html())
            response.status_int = 500
            return response
        else:
            DBSession.add(time_log)
            request.session.flash(
                'success:Time log for <strong>%s</strong> is saved for resource <strong>%s</strong>.' % (task.name,resource.name)
            )
        logger.debug('no problem here!')
    else:
        response = Response(
            'There are missing parameters: '
            'task_id: %s, resource_id: %s' % (task_id, resource_id)
        )
        response.status_int = 500
        return response
    logger.debug('successfully created time log!')
    response = Response('successfully created time log!')
    response.status_int = 200
    return response


@view_config(
    route_name='update_time_log'
)
def update_time_log(request):
    """runs when updating a time_log
    """
    logger.debug('inside update_time_log')
    # time_log_id = int(request.params.get('time_log_id'))
    time_log_id = request.matchdict.get('id', -1)
    time_log = TimeLog.query.filter_by(id=time_log_id).first()

    #**************************************************************************
    # collect data
    resource_id = int(request.params.get('resource_id', None))
    resource = User.query.filter(User.id == resource_id).first()

    start_date = get_date(request, 'start')
    end_date = get_date(request, 'end')

    logger.debug('time_log_id : %s' % time_log_id)
    logger.debug('resource_id : %s' % resource_id)
    logger.debug('start         : %s' % start_date)
    logger.debug('end           : %s' % end_date)

    if time_log and resource and start_date and end_date:
        # we are ready to create the time log
        # TimeLog should handle the extension of the effort

        try:
            time_log.resource = resource
            time_log.start = start_date
            time_log.end = end_date
        except OverBookedError:
            return HTTPServerError()
        else:
            DBSession.add(time_log)
            request.session.flash(
                'success:Time log for <strong>%s</strong> is updated..' % (time_log.task.name)
            )
            logger.debug('successfully updated time log!')

    return HTTPOk()


@view_config(
    route_name='get_entity_time_logs',
    renderer='json'
)
@view_config(
    route_name='get_task_time_logs',
    renderer='json'
)
def get_time_logs(request):
    """returns all the Shots of the given Project
    """
    logger.debug('get_time_logs is running')
    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    logger.debug('entity_id : %s' % entity_id)

    time_log_data = []

    # if entity.time_logs:
    for time_log in entity.time_logs:
        # logger.debug('time_log.task.id : %s' % time_log.task.id)
        # assert isinstance(time_log, TimeLog)
        time_log_data.append({
            'id': time_log.id,
            'entity_type':time_log.plural_class_name.lower(),
            'task_id': time_log.task.id,
            'task_name': time_log.task.name,
            'task_status': time_log.task.status.name,
            'parent_name': ' | '.join(
                [parent.name for parent in time_log.task.parents]),
            'resource_id': time_log.resource_id,
            'resource_name': time_log.resource.name,
            'duration': time_log.total_seconds,
            'start': milliseconds_since_epoch(time_log.start),
            'end': milliseconds_since_epoch(time_log.end),
            'className': 'label-important',
            'allDay': '0'

            # 'hours_to_complete': time_log.hours_to_complete,
            # 'notes': time_log.notes
        })

    return time_log_data

