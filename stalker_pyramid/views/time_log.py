# -*- coding: utf-8 -*-


import time
import logging
import pytz
import datetime
import transaction

from pyramid.response import Response
from pyramid.view import view_config

from stalker import defaults, Task, User, Studio, TimeLog, Entity, Status
from stalker.db.session import DBSession
from stalker.exceptions import OverBookedError, DependencyViolationError

from stalker_pyramid.views import (get_logged_in_user,
                                   PermissionChecker, milliseconds_since_epoch,
                                   get_date, StdErrToHTMLConverter,
                                   get_multi_integer, to_seconds,
                                   from_milliseconds, seconds_since_epoch)
from stalker_pyramid.views.task import (get_task_full_path,
                                        fix_task_computed_time,
                                        auto_extend_time,
                                        get_schedule_information)

from stalker_pyramid import logger_name
logger = logging.getLogger(logger_name)


@view_config(
    route_name='user_general_time_log_dialog',
    renderer='templates/time_log/dialog/general_timelog_dialog.jinja2'
)
@view_config(
    route_name='task_time_log_dialog',
    renderer='templates/time_log/dialog/timelog_dialog.jinja2'
)
@view_config(
    route_name='user_time_log_dialog',
    renderer='templates/time_log/dialog/timelog_dialog.jinja2'
)
@view_config(
    route_name='entity_time_log_dialog',
    renderer='templates/time_log/dialog/timelog_dialog.jinja2'
)
def create_time_log_dialog(request):
    """creates a create_time_log_dialog by using the given task
    """
    logger.debug('inside timelog_dialog')

    came_from = request.params.get('came_from', '/')
    logger.debug('came_from %s: ' % came_from)

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
        'came_from': came_from,
        'milliseconds_since_epoch': milliseconds_since_epoch,
    }


@view_config(
    route_name='time_log_update_dialog',
    renderer='templates/time_log/dialog/timelog_dialog.jinja2',
)
def update_time_log_dialog(request):
    """updates a create_time_log_dialog by using the given task
    """
    logger.debug('inside updates_time_log_dialog')

    came_from = request.params.get('came_from', '/')
    logger.debug('came_from %s: ' % came_from)

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
        'entity': time_log.task,
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
    logger.debug('create_time_log method starts')

    # *************************************************************************
    # task

    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    task_id = request.params.get('task_id')
    task = Task.query.filter(Task.id == task_id).first()

    logger.debug('task_id     : %s' % task_id)
    logger.debug('task        : %s' % task)

    if not task:
        return Response('No task with id %s found' % task_id, 500)

    # *************************************************************************
    # resource
    resource_id = request.params.get('resource_id', None)
    resource = User.query.filter(User.id == resource_id).first()

    logger.debug('resource_id : %s' % resource_id)
    logger.debug('resource : %s' % resource)

    if not resource:
        return Response('No user with id %s found' % resource_id, 500)

    # **************************************************************************
    # collect data
    start_date = get_date(request, 'start')
    end_date = get_date(request, 'end')
    auto_split_working_hours = request.params.get('auto_split_wh', None)
    description = request.params.get('description', '')

    logger.debug('start_date  : %s' % start_date)
    logger.debug('end_date    : %s' % end_date)
    logger.debug('auto_split_working_hours  : %s' % auto_split_working_hours)
    logger.debug('description    : %s' % description)

    if task and resource and start_date and end_date:
        # we are ready to create the time log
        # TimeLog should handle the extension of the effort
        logger.debug('got all the data')
        try:
            logger.debug('creating time log through task')
            assert isinstance(task, Task)
            time_log = task.create_time_log(resource, start_date, end_date)
            time_log.description = description
            time_log.created_by = logged_in_user
            time_log.date_created = utc_now
            logger.debug('timelog created!')
        except (OverBookedError, TypeError, DependencyViolationError) as e:
            converter = StdErrToHTMLConverter(e)
            response = Response(converter.html(), 500)
            transaction.abort()
            return response
        else:
            request.session.flash(
                'success: Time log for <strong>%s</strong> is saved for '
                'resource <strong>%s</strong>.' % (task.name, resource.name)
            )
        logger.debug('no problem here!')
    else:
        response = Response(
            'There are missing parameters: '
            'task_id: %s, resource_id: %s' % (task_id, resource_id), 500
        )
        transaction.abort()
        return response
    task.update_schedule_info()
    fix_task_computed_time(task)

    if task.total_logged_seconds > task.schedule_seconds:
        logger.debug('EXTEND TIMING OF TASK!')
        revision_type = request.params.get('revision_type', 'Auto Extended Time')
        auto_extend_time(task,
                         description,
                         revision_type,
                         logged_in_user)

    logger.debug('successfully created time log!')
    response = Response(get_task_full_path(task.id))

    return response


@view_config(
    route_name='update_time_log'
)
def update_time_log(request):
    """runs when updating a time_log
    """
    logger.debug('inside update_time_log')

    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    # time_log_id = int(request.params.get('time_log_id'))
    time_log_id = request.matchdict.get('id', -1)
    time_log = TimeLog.query.filter_by(id=time_log_id).first()

    # **************************************************************************
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

        previous_duration = time_log.duration

        try:
            time_log.start = start_date
            time_log.end = end_date
            time_log.description = description
            time_log.resource = resource
            time_log.updated_by = logged_in_user
            time_log.date_updated = utc_now

            with DBSession.no_autoflush:
                if time_log.duration > previous_duration\
                   and time_log.task.status == 'HREV':
                    # update the task status to WIP
                    wip = Status.query.filter(Status.code == 'WIP').first()
                    time_log.task.status = wip

        except OverBookedError as e:
            logger.debug('e: %s' % str(e))
            response = Response(str(e), 500)
            transaction.abort()
            return response
        else:
            DBSession.add(time_log)
            request.session.flash(
                'success:Time log for <strong>%s</strong> is updated..'
                % time_log.task.name
            )
            logger.debug('successfully updated time log!')

    time_log.task.update_schedule_info()
    fix_task_computed_time(time_log.task)

    if time_log.task.total_logged_seconds > time_log.task.schedule_seconds:

        revision_type = request.params.get('revision_type', 'Auto Extended Time')
        auto_extend_time(time_log.task,
                         description,
                         revision_type,
                         logged_in_user)

    return Response('TimeLog has been updated successfully')


@view_config(
    route_name='user_multi_timelog_dialog',
    renderer='templates/time_log/dialog/multi_timelog_dialog.jinja2'
)
def user_multi_timelog_dialog(request):
    """creates a create_time_log_dialog by using the given task
    """
    logger.debug('inside timelog_dialog')

    came_from = request.params.get('came_from', '/')
    logger.debug('came_from %s: ' % came_from)

    # get logged in user
    logged_in_user = get_logged_in_user(request)

    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    selected_task_list = get_multi_integer(request, 'task_ids', 'GET')
    tasks = Task.query.filter(Task.id.in_(selected_task_list)).all()

    studio = Studio.query.first()
    if not studio:
        studio = defaults

    return {
        'mode': 'create',
        'has_permission': PermissionChecker(request),
        'studio': studio,
        'logged_in_user': logged_in_user,
        'entity': entity,
        'came_from': came_from,
        'tasks': tasks,
        'milliseconds_since_epoch': milliseconds_since_epoch,
    }


@view_config(
    route_name='create_multi_timelog'
)
def create_multi_timelog(request):
    """runs when creating a time_log
    """
    logger.debug('create_multi_timelog method starts')

    # **************************************************************************
    # task

    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    selected_task_list = get_multi_integer(request, 'task_ids')
    tasks = Task.query.filter(Task.id.in_(selected_task_list)).all()

    if not tasks:
        return Response('No task id found', 500)

    # **************************************************************************
    # resource
    resource_id = request.params.get('resource_id', None)
    resource = User.query.filter(User.id == resource_id).first()

    logger.debug('resource_id : %s' % resource_id)
    logger.debug('resource : %s' % resource)

    if not resource:
        return Response('No user with id %s found' % resource_id, 500)

    # **************************************************************************
    # collect data
    start_date = get_date(request, 'start')
    description = request.params.get('description', '')

    logger.debug('start_date  : %s' % start_date)
    logger.debug('description    : %s' % description)

    schedule_info = get_schedule_information(request)
    if not schedule_info:
        transaction.abort()
        return schedule_info

    schedule_timing = schedule_info[0]
    schedule_unit = schedule_info[1]

    duration = to_seconds(schedule_timing, schedule_unit)

    logger.debug('schedule_timing: %s' % schedule_timing)
    logger.debug('schedule_unit  : %s' % schedule_unit)
    logger.debug('duration  : %s' % duration)

    if resource and start_date and duration:

        for task in tasks:
            start_as_seconds = seconds_since_epoch(start_date)
            end_as_seconds = start_as_seconds + duration
            end_date = from_milliseconds(end_as_seconds*1000)

            try:
                logger.debug('recursive_create_timelog_action')
                logger.debug('start_date  : %s' % start_date)
                logger.debug('end_date  : %s' % end_date)
                logger.debug('resource  : %s' % resource)

                time_log = task.create_time_log(resource, start_date, end_date)
                time_log.description = description
                time_log.created_by = logged_in_user
                time_log.date_created = utc_now
                logger.debug('timelog created!')

            except (OverBookedError, TypeError, DependencyViolationError) as e:
                converter = StdErrToHTMLConverter(e)
                response = Response(converter.html(), 500)
                transaction.abort()
                return response
            else:

                start_date = end_date

                request.session.flash(
                    'success: Time log for <strong>%s</strong> is saved for '
                    'resource <strong>%s</strong>.' % (task.name, resource.name)
                )
                task.update_schedule_info()
                fix_task_computed_time(task)

                if task.total_logged_seconds > task.schedule_seconds:

                    revision_type = request.params.get('revision_type', 'Auto Extended Time')
                    auto_extend_time(task,
                                     description,
                                     revision_type,
                                     logged_in_user)
    else:
        response = Response(
            'There are missing parameters: ', 500
        )
        transaction.abort()
        return response

    logger.debug('successfully created time log!')
    response = Response('successfully created time log!')

    return response


def recursive_create_timelog_action(t, s_date, d, r, desc, l_in_user, u_now):

    logger.debug('recursive_create_timelog_action is starts')

    task = t
    start_date = s_date
    duration = d
    resource = r
    description = desc
    logged_in_user = l_in_user
    utc_now = u_now

    start_as_seconds = seconds_since_epoch(start_date)
    end_as_seconds = start_as_seconds + duration
    end_date = from_milliseconds(end_as_seconds*1000)

    try:
        logger.debug('recursive_create_timelog_action')
        logger.debug('start_date  : %s' % start_date)
        logger.debug('end_date  : %s' % end_date)
        logger.debug('resource  : %s' % resource)

        time_log = task.create_time_log(resource, start_date, end_date)
        time_log.description = description
        time_log.created_by = logged_in_user
        time_log.date_created = utc_now
        logger.debug('timelog created!')

    except (OverBookedError, TypeError, DependencyViolationError) as e:
        converter = StdErrToHTMLConverter(e)
        response = Response(converter.html(), 500)
        transaction.abort()
        return response
    else:
        return end_date


@view_config(
    route_name='get_entity_time_logs',
    renderer='json'
)
@view_config(
    route_name='get_task_time_logs',
    renderer='json'
)
@view_config(
    route_name='get_project_time_logs',
    renderer='json'
)
def get_time_logs(request):
    """returns all the time logs of the given entity
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
        extract(epoch from "TimeLogs".end - "TimeLogs".start) as total_seconds,
        extract(epoch from "TimeLogs".start) * 1000 as start,
        extract(epoch from "TimeLogs".end) * 1000 as end,
        "SimpleEntities_Created_By".id,
        "SimpleEntities_Created_By".name,
        "SimpleEntities_TimeLog".description
    from "TimeLogs"
    join "Tasks" on "TimeLogs".task_id = "Tasks".id
    join "SimpleEntities" as "SimpleEntities_TimeLog" on "SimpleEntities_TimeLog".id = "TimeLogs".id
    join "SimpleEntities" as "SimpleEntities_Created_By" on "SimpleEntities_Created_By".id = "SimpleEntities_TimeLog".created_by_id
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

    if entity_type == 'User':
        sql_query += 'where "TimeLogs".resource_id = %s' % entity_id
    elif entity_type == 'Task':
        sql_query += 'where "TimeLogs".task_id = %s' % entity_id
    elif entity_type == 'Project':
        sql_query += 'where "Tasks".project_id = %s' % entity_id
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
            'duration': r[7]/3600,
            'start': r[8],
            'end': r[9],
            'created_by_id': r[10],
            'created_by_name': r[11],
            'description': r[12],
            'className': 'label-important',
            'allDay': '0',
            'update_timelog_action':'timelogs/{id}/update/dialog'
        } for r in result.fetchall()
    ]
    end = time.time()
    logger.debug('get_entity_time_logs took: %s seconds' % (end - start))
    return data


@view_config(
    route_name='get_monthly_time_logs',
    renderer='json'
)
def get_monthly_time_logs(request):
    """returns project monthly time logs as a json
    """

    resource_ids = get_multi_integer(request, 'resource_id', 'GET')
    project_id = request.params.get('project_id', None)

    sql_query = """select
        sum(extract(epoch from "TimeLogs".end - "TimeLogs".start)) / 3600 as total_hours,
        min(extract(epoch from "TimeLogs".start)) as start,
        max(extract(epoch from "TimeLogs".end)) as end
    from "TimeLogs"
    join "Tasks" on "Tasks".id = "TimeLogs".task_id

    %(where_conditions)s

    group by date_trunc('month', "TimeLogs".start)
    order by start
    """
    where_conditions = ''
    if resource_ids:
        temp_buffer = ["""where ("""]
        for i, resource_id in enumerate(resource_ids):
            if i > 0:
                temp_buffer.append(' or')
            temp_buffer.append(""" "TimeLogs".resource_id='%s'""" % resource_id)
        temp_buffer.append(' )')
        where_conditions = ''.join(temp_buffer)

    if project_id:
        where_conditions = """where "Tasks".project_id=%s """ % project_id

    sql_query = sql_query % {
        'where_conditions': where_conditions
    }

    result = DBSession.connection().execute(sql_query).fetchall()

    logger.debug('get_project_total_schedule_seconds: %s' % result[0])
    return [{
        'total_hours': r[0],
        'start_date': r[1],
        'end_date': r[2]
    } for r in result]


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
        return Response(
            'Can not find a Time_log with id: %s' % time_log_id, 500
        )

    status_cmpl = Status.query.filter(Status.code == 'CMPL').first()

    if time_log.task.status in [status_cmpl]:
        transaction.abort()
        return Response(
            'Error: You can not delete a TimeLog of a Task with status CMPL',
            500
        )

    task_id = time_log.task.id

    try:
        DBSession.delete(time_log)
        transaction.commit()
    except Exception as e:
        transaction.abort()
        c = StdErrToHTMLConverter(e)
        transaction.abort()
        return Response(c.html(), 500)
    else:
        # update the status of the task if there is no time log any more
        task = Task.query.get(task_id)
        assert isinstance(task, Task)
        if not task.time_logs:
            status_new = Status.query.filter(Status.code == 'NEW').first()
            task.status = status_new

    return Response('Successfully deleted time_log: %s' % time_log_id)
