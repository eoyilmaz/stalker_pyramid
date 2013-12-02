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
import time
import transaction
from stalker_pyramid.views import (get_logged_in_user,
                                   PermissionChecker, milliseconds_since_epoch,
                                   get_date, StdErrToHTMLConverter)
from stalker_pyramid.views.task import update_task_statuses

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

    logger.debug('task_id : %s' % task_id)

    task = Task.query.filter(Task.id == task_id).first()

    if not task:
        return Response('No task with id %s found' % task_id, 500)

    #**************************************************************************
    # collect data
    resource_id = request.params.get('resource_id', None)
    resource = User.query.filter(User.id == resource_id).first()

    start_date = get_date(request, 'start')
    end_date = get_date(request, 'end')

    description = request.params.get('description', '')

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
                end=end_date,
                description=description
            )

            status_new = Status.query.filter(Status.code == "NEW").first()
            status_wip = Status.query.filter(Status.code == "WIP").first()
            status_cmpl = \
                Status.query.filter(Status.code == "CMPL").first()
            status_has_revision = \
                Status.query.filter(Status.code == "HREV").first()

            # check if the task status is not completed
            if task.status not in [status_new, status_wip]:
                DBSession.rollback()
                # it is not possible to create a time log for completed tasks
                response = Response('It is only possible to create time log '
                                    'for a task with status is set to '
                                    '"NEW" or "WIP"', 500)
                transaction.abort()
                return response

            # check the dependent tasks has finished
            for dep_task in task.depends:
                if dep_task.status not in [status_cmpl,
                                           status_has_revision]:
                    response = Response(
                        'Because one of the dependencies (Task: %s (%s)) has '
                        'not finished, \n'
                        'You can not create time logs for this task yet!'
                        '\n\nPlease, inform %s to finish this task!' %
                        (dep_task.name, dep_task.id,
                         [r.name for r in dep_task.resources]), 500
                    )
                    transaction.abort()
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
                         task.responsible.name), 500
                    )
                    transaction.abort()
                    return response

            # set the status to wip for this task
            logger.debug('Updating Task (%s) status to WIP!' % task_id)
            wip = Status.query.filter(Status.code == "WIP").first()
            task.status = wip
            DBSession.add(task)
        except (OverBookedError, TypeError) as e:
            converter = StdErrToHTMLConverter(e)
            response = Response(converter.html(), 500)
            transaction.abort()
            return response
        else:
            DBSession.add(time_log)
            # check parent task statuses
            update_task_statuses(task.parent)
            request.session.flash(
                'success:Time log for <strong>%s</strong> is saved for resource <strong>%s</strong>.' % (task.name,resource.name)
            )
        logger.debug('no problem here!')
    else:
        response = Response(
            'There are missing parameters: '
            'task_id: %s, resource_id: %s' % (task_id, resource_id), 500
        )
        transaction.abort()
        return response
    logger.debug('successfully created time log!')
    response = Response('successfully created time log!')
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

    description = request.params.get('description', '')

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
            time_log.description = description
        except OverBookedError as e:
            response = Response(e.message, 500)
            transaction.abort()
            return response
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
    logger.debug('entity_id : %s' % entity_id)

    data = DBSession.connection().execute(
        'select entity_type from "SimpleEntities" where id=%s' % entity_id
    ).fetchone()

    entity_type = None
    if len(data):
        entity_type = data[0]

    logger.debug('entity_type : %s' % entity_type)

    sql_query = """select
        "TimeLogs".id,
        "TimeLogs".task_id,
        "SimpleEntities_Task".name,
        "SimpleEntities_Status".name,
        parent_names.parent_name,
        "TimeLogs".resource_id,
        "SimpleEntities_Resource".name,
        extract(epoch from "TimeLogs".end::timestamp AT TIME ZONE 'UTC' - "TimeLogs".start::timestamp AT TIME ZONE 'UTC') as total_seconds,
        extract(epoch from "TimeLogs".start::timestamp AT TIME ZONE 'UTC') * 1000 as start,
        extract(epoch from "TimeLogs".end::timestamp AT TIME ZONE 'UTC') * 1000 as end
    from "TimeLogs"
    join "Tasks" on "TimeLogs".task_id = "Tasks".id
    join "SimpleEntities" as "SimpleEntities_Task" on "Tasks".id = "SimpleEntities_Task".id
    join "SimpleEntities" as "SimpleEntities_Status" on "Tasks".status_id = "SimpleEntities_Status".id
    join "SimpleEntities" as "SimpleEntities_Resource" on "TimeLogs".resource_id = "SimpleEntities_Resource".id
    join (
        select
            parent_data.id,
            "SimpleEntities".name,
            array_to_string(array_agg(
                case
                    when "SimpleEntities_parent".entity_type = 'Project'
                    then "Projects".code
                    else "SimpleEntities_parent".name
                end),
                ' | '
            ) as parent_name
            from (
                with recursive parent_ids(id, parent_id, n) as (
                        select task.id, coalesce(task.parent_id, task.project_id), 0
                        from "Tasks" task
                    union
                        select task.id, parent.parent_id, parent.n + 1
                        from "Tasks" task, parent_ids parent
                        where task.parent_id = parent.id
                )
                select
                    parent_ids.id, parent_id as parent_id, parent_ids.n
                    from parent_ids
                    order by id, parent_ids.n desc
            ) as parent_data
            join "SimpleEntities" on "SimpleEntities".id = parent_data.id
            join "SimpleEntities" as "SimpleEntities_parent" on "SimpleEntities_parent".id = parent_data.parent_id
            left outer join "Projects" on parent_data.parent_id = "Projects".id
            group by parent_data.id, "SimpleEntities".name
    ) as parent_names on "TimeLogs".task_id = parent_names.id
    """

    if entity_type == u'User':
        sql_query += 'where "TimeLogs".resource_id = %s' % entity_id
    elif entity_type == u'Task':
        sql_query += 'where "TimeLogs".task_id = %s' % entity_id
    elif entity_type is None:
        return []

    result = DBSession.connection().execute(sql_query)

    start = time.time()
    data = [
        {
            'id': r[0],
            'entity_type': 'timelogs',
            'task_id': r[1],
            'task_name': r[2],
            'task_status': r[3],
            'parent_name': r[4],
            'resource_id': r[5],
            'resource_name': r[6],
            'duration': r[7],
            'start': r[8],
            'end': r[9],
            'className': 'label-important',
            'allDay': '0'
        } for r in result.fetchall()
    ]
    end = time.time()
    logger.debug('get_entity_time_logs took: %s seconds' % (end - start))
    return data

@view_config(
    route_name='delete_time_log',
    permission='Delete_TimeLog'
)
def delete_time_log(request):
    """deletes the time_log with the given id
    """
    time_log_id = request.matchdict.get('id')
    time_log = TimeLog.query.get(time_log_id)

    logger.debug('delete_time_log: %s' % time_log_id)

    if not time_log:
        transaction.abort()
        return Response('Can not find a Time_log with id: %s' % time_log_id, 500)

    try:
        DBSession.delete(time_log)
        transaction.commit()
    except Exception as e:
        transaction.abort()
        c = StdErrToHTMLConverter(e)
        transaction.abort()
        return Response(c.html(), 500)

    return Response('Successfully deleted time_log: %s' % time_log_id)


