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
import time
import datetime
import json

import transaction
from pyramid.response import Response
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPServerError, HTTPOk, HTTPForbidden
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message
from sqlalchemy.exc import IntegrityError
from stalker.db import DBSession
from stalker import (User, Task, Entity, Project, StatusList, Status,
                     TaskJugglerScheduler, Studio, Asset, Shot, Sequence,
                     Ticket, Type, Note)
from stalker.models.task import CircularDependencyError
from stalker import defaults

from stalker_pyramid.views import (PermissionChecker, get_logged_in_user,
                                   get_multi_integer, milliseconds_since_epoch,
                                   StdErrToHTMLConverter,
                                   multi_permission_checker,
                                   dummy_email_address, local_to_utc, get_user_os)
from stalker_pyramid.views.type import query_type


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@view_config(
    route_name='fix_task_statuses'
)
def fix_task_statuses(request):
    """the view correspondence of the update_task_statuses function
    """
    task_id = request.matchdict.get('id')
    task = Task.query.filter(Task.id == task_id).first()
    # check for children
    update_task_statuses(task)
    # check fo dependencies
    update_task_statuses_with_dependencies(task)
    return HTTPOk()


def update_task_statuses(task):
    """updates the task status according to its children statuses
    """
    if not task:
        # None is given
        return

    if not task.is_container:
        # do nothing
        return

    # first look to children statuses and if all of them are CMPL or HREV
    # then set this tasks status to CMPL
    # and update parents status

    status_new = Status.query.filter(Status.code == 'NEW').first()
    status_rts = Status.query.filter(Status.code == 'RTS').first()
    status_wip = Status.query.filter(Status.code == 'WIP').first()
    status_cmpl = Status.query.filter(Status.code == 'CMPL').first()

    # use pure sql
    sql_query = """select
        "Statuses".code,
        count(1)
    from "Tasks"
    join "Statuses" on "Tasks".status_id = "Statuses".id
    where "Tasks".parent_id = %s
    group by "Statuses".code
    """ % task.id

    result = DBSession.connection().execute(sql_query)

    status_codes = {
        'NEW': 0,
        'RTS': 0,
        'WIP': 0,
        'PREV': 0,
        'HREV': 0,
        'CMPL': 0
    }

    # update statuses
    for r in result.fetchall():
        if r[1]:
            status_codes[r[0]] = 1

    # convert it to a binary number (represented as string)
    binary_status = \
        '%(NEW)s%(RTS)s%(WIP)s%(PREV)s%(HREV)s%(CMPL)s' % status_codes

    status_lut = {
        '000000': status_new, # this will not happen
        '000001': status_cmpl,

        '000010': status_wip, # with the new implementation this could happen
        '000011': status_wip,

        '000100': status_wip,
        '000101': status_wip,
        '000110': status_wip,
        '000111': status_wip,

        '001000': status_wip,
        '001001': status_wip,
        '001010': status_wip,
        '001011': status_wip,
        '001100': status_wip,
        '001101': status_wip,
        '001110': status_wip,
        '001111': status_wip,

        # RTS extension
        '010000': status_rts,
        '010001': status_wip,
        '010010': status_wip,
        '010011': status_wip,
        '010100': status_wip,
        '010101': status_wip,
        '010110': status_wip,
        '010111': status_wip,
        '011000': status_wip,
        '011001': status_wip,
        '011010': status_wip,
        '011011': status_wip,
        '011100': status_wip,
        '011101': status_wip,
        '011110': status_wip,
        '011111': status_wip,

        '100000': status_new,
        '100001': status_wip,
        '100010': status_wip,
        '100011': status_wip,
        '100100': status_wip,
        '100101': status_wip,
        '100110': status_wip,
        '100111': status_wip,
        '101000': status_wip,
        '101001': status_wip,
        '101010': status_wip,
        '101011': status_wip,
        '101100': status_wip,
        '101101': status_wip,
        '101110': status_wip,
        '101111': status_wip,
        '110000': status_rts,
        '110001': status_wip,
        '110010': status_wip,
        '110011': status_wip,
        '110100': status_wip,
        '110101': status_wip,
        '110110': status_wip,
        '110111': status_wip,
        '111000': status_wip,
        '111001': status_wip,
        '111010': status_wip,
        '111011': status_wip,
        '111100': status_wip,
        '111101': status_wip,
        '111110': status_wip,
        '111111': status_wip
    }

    task.status = status_lut[binary_status]
    # go to parents
    update_task_statuses(task.parent)
    # commit the changes
    #DBSession.commit()
    # leave the commits to transaction.manager


def update_task_statuses_with_dependencies(task):
    """updates the task status according to its dependencies
    """
    if not task:
        # None is given
        return

    if task.is_container:
        # do nothing, its status will be decided by its children
        return

    status_new = Status.query.filter(Status.code == 'NEW').first()
    status_rts = Status.query.filter(Status.code == 'RTS').first()
    status_cmpl = Status.query.filter(Status.code == 'CMPL').first()

    if not task.depends:
        # doesn't have any dependency
        # convert its status from NEW to RTS if necessary
        if task.status == status_new:
            task.status = status_rts
        return

    if task.status == status_new:
        # check all of its dependencies
        # and decide if it is ready to start or not
        if all([dep.status == status_cmpl for dep in task.depends]):
            task.status = status_rts


@view_config(
    route_name='fix_task_schedule_info'
)
def fix_task_schedule_info(request):
    """fixes a tasks percent_complete value
    """
    task_id = request.matchdict.get('id')
    task = Task.query.filter(Task.id == task_id).first()

    if task:
        assert isinstance(task, Task)
        task.update_schedule_info()

    return HTTPOk()


def duplicate_task(task):
    """Duplicates the given task without children.

    :param task: a stalker.models.task.Task instance
    :return: stalker.models.task.Task
    """
    # create a new task and change its attributes
    class_ = Task
    extra_kwargs = {}
    if task.entity_type == 'Asset':
        class_ = Asset
        extra_kwargs = {
            'code': task.code
        }
    elif task.entity_type == 'Shot':
        class_ = Shot
        extra_kwargs = {
            'code': task.code + 'dup'
        }
    elif task.entity_type == 'Sequence':
        class_ = Sequence
        extra_kwargs = {
            'code': task.code
        }

    # all duplicated tasks are new tasks
    new = Status.query.filter(Status.code == 'NEW').first()

    dup_task = class_(
        name=task.name,
        project=task.project,
        bid_timing=task.bid_timing,
        bid_unit=task.bid_unit,
        computed_end=task.computed_end,
        computed_start=task.computed_start,
        created_by=task.created_by,
        description=task.description,
        is_milestone=task.is_milestone,
        resources=task.resources,
        priority=task.priority,
        schedule_constraint=task.schedule_constraint,
        schedule_model=task.schedule_model,
        schedule_timing=task.schedule_timing,
        schedule_unit=task.schedule_unit,
        status=new,
        status_list=task.status_list,
        notes=task.notes,
        tags=task.tags,
        responsible=task.responsible,
        #references=task.references,
        start=task.start,
        end=task.end,
        thumbnail=task.thumbnail,
        timing_resolution=task.timing_resolution,
        type=task.type,
        watchers=task.watchers,
        **extra_kwargs
    )
    dup_task.generic_data = task.generic_data
    dup_task.is_complete = task.is_complete

    return dup_task


def walk_hierarchy(task):
    """Walks the hierarchy of the given task

    :param task: The top most task instance
    :return:
    """
    tasks_to_visit = []
    tasks_to_visit.append(task)
    while len(tasks_to_visit):
        current_task = tasks_to_visit.pop(0)
        tasks_to_visit.extend(current_task.children)
        yield current_task


def find_leafs_in_hierarchy(task, leafs=None):
    """Walks through task hierarchy and finds all of the leaf tasks

    :param task: The starting task
    :return:
    """
    if not leafs:
        leafs = []

    # start from the given task
    logger.debug('walking on task : %s' % task)
    for child in task.children:
        if child.is_leaf:
            leafs.append(child)
        else:
            leafs.extend(find_leafs_in_hierarchy(child, leafs))
    return leafs


def walk_and_duplicate_task_hierarchy(task):
    """Walks through task hierarchy and creates duplicates of all the tasks
    it finds

    :param task: task
    :return:
    """
    # start from the given task
    logger.debug('duplicating task : %s' % task)
    logger.debug('task.children    : %s' % task.children)
    dup_task = duplicate_task(task)
    task.duplicate = dup_task
    for child in task.children:
        logger.debug('duplicating child : %s' % child)
        duplicated_child = walk_and_duplicate_task_hierarchy(child)
        duplicated_child.parent = dup_task
    return dup_task


def update_dependencies_in_duplicated_hierarchy(task):
    """Updates the dependencies in the given task. Uses the task.duplicate
    attribute to find the duplicate

    :param task: The top most task of the hierarchy
    :return: None
    """
    try:
        duplicated_task = task.duplicate
    except AttributeError:
        # not a duplicated task
        logger.debug('task has no duplicate: %s' % task)
        return

    for dependent_task in task.depends:
        if hasattr(dependent_task, 'duplicate'):
            logger.debug('there is a duplicate!')
            logger.debug('dependent_task.duplicate : %s' %
                         dependent_task.duplicate)
            duplicated_task.depends.append(dependent_task.duplicate)
        else:
            logger.debug('there is no duplicate!')
            duplicated_task.depends.append(dependent_task)

    for child in task.children:
        # check child dependencies
        # loop through children
        update_dependencies_in_duplicated_hierarchy(child)


def cleanup_duplicate_residuals(task):
    """Cleans the duplicate attributes in the hierarchy

    :param task: The top task in the hierarchy
    :return:
    """
    try:
        delattr(task, 'duplicate')
    except AttributeError:
        pass

    for child in task.children:
        cleanup_duplicate_residuals(child)


@view_config(
    route_name='duplicate_task_hierarchy'
)
def duplicate_task_hierarchy(request):
    """Duplicates the given task hierarchy.

    Walks through the hierarchy of the given task and duplicates every
    instance it finds in a new task.

    task: The task that wanted to be duplicated

    :return: A list of stalker.models.task.Task
    """
    task_id = request.matchdict.get('id')
    task = Task.query.filter_by(id=task_id).first()

    name = request.params.get('name', task.name + ' - Duplicate')
    description = request.params.get('description', task.description)

    if task:
        dup_task = walk_and_duplicate_task_hierarchy(task)
        update_dependencies_in_duplicated_hierarchy(task)

        cleanup_duplicate_residuals(task)
        # update the parent
        dup_task.parent = task.parent
        # just rename the dup_task

        dup_task.name = name
        dup_task.code = name
        dup_task.description = description

        DBSession.add(dup_task)

        #update_task_statuses_with_dependencies(dup_task)
        leafs = find_leafs_in_hierarchy(dup_task)
        for leaf in leafs:
            update_task_statuses_with_dependencies(leaf)

        for leaf in leafs:
            update_task_statuses(leaf)

            # check for children
        update_task_statuses(dup_task)
        # check fo dependencies
        update_task_statuses_with_dependencies(dup_task)
    else:
        transaction.abort()
        return Response(
            'No task can be found with the given id: %s' % task_id, 500)

    return Response('Task %s is duplicated successfully' % task.id)


def convert_to_dgrid_gantt_project_format(projects):
    """Converts the given projects to the DGrid Gantt compatible json format.

    :param projects: List of Stalker Project.
    :return: json compatible dictionary
    """

    from sqlalchemy import func

    def hasChildren(project):
        return bool(
            DBSession.query(func.count(Task.id))
            .join(Task.project, Project.tasks)
            .filter(Project.id == project.id)
            .first()[0]
        )

    return [
        {
            'bid_timing': project.duration.days,
            'bid_unit': 'd',
            'completed': project.total_logged_seconds / project.schedule_seconds if project.schedule_seconds else 0,
            'description': project.description,
            'end': milliseconds_since_epoch(
                project.computed_end if project.computed_end else project.end),
            'id': project.id,
            'link': '/projects/%s/view' % project.id,
            'name': project.name,
            'hasChildren': hasChildren(project),
            'schedule_seconds': project.schedule_seconds,
            'start': milliseconds_since_epoch(
                project.computed_start if project.computed_start else project.start),
            'total_logged_seconds': project.total_logged_seconds,
            'type': project.entity_type,
            'status': project.status.code.lower()
        } for project in projects
    ]


def convert_to_dgrid_gantt_task_format(tasks):
    """Converts the given tasks to the DGrid Gantt compatible json format.

    :param tasks: List of Stalker Tasks.
    :return: json compatible dictionary
    """
    if not isinstance(tasks, list):
        response = HTTPServerError()
        response.text = u'This is a not a list of tasks'
        raise response

    return [
        {
            'bid_timing': task.bid_timing,
            'bid_unit': task.bid_unit,
            'completed': task.total_logged_seconds / task.schedule_seconds,
            'dependencies': [
                {
                    'id': dep.id,
                    'name': dep.name
                } for dep in task.depends],
            'description': task.description,
            'end': milliseconds_since_epoch(
                task.computed_end if task.computed_end else task.end),
            'hasChildren': task.is_container,
            'hierarchy_name': ' | '.join(
                [parent.name for parent in task.parents]),
            'id': task.id,
            'link': '/%ss/%s/view' % (task.entity_type.lower(), task.id),
            'name': task.name,
            'parent': task.parent.id if task.parent else task.project.id,
            'project_id': task.project.id,
            'priority': task.priority,
            'resources': [
                {'id': resource.id, 'name': resource.name} for resource in
                task.resources] if not task.is_container else [],
            'responsible': {
                'id': task.responsible.id,
                'name': task.responsible.name
            },
            'schedule_constraint': task.schedule_constraint,
            'schedule_model': task.schedule_model,
            'schedule_seconds': task.schedule_seconds,
            'schedule_timing': task.schedule_timing,
            'schedule_unit': task.schedule_unit,
            'start': milliseconds_since_epoch(
                task.computed_start if task.computed_start else task.start),
            'status': task.status.code.lower(),
            'total_logged_seconds': task.total_logged_seconds,
            'type': task.entity_type,
        } for task in tasks
    ]


@view_config(
    route_name='update_task'
)
def update_task(request):
    """Updates the given task with the data coming from the request
    """
    logged_in_user = get_logged_in_user(request)
    p_checker = PermissionChecker(request)

    # *************************************************************************
    # collect data
    parent_id = request.params.get('parent_id', None)
    if parent_id:
        parent = Task.query.filter(Task.id == parent_id).first()
    else:
        parent = None
    name = str(request.params.get('name', None))
    description = request.params.get('description', '')
    schedule_model = request.params.get('schedule_model') # there should be one
    schedule_timing = float(request.params.get('schedule_timing'))
    schedule_unit = request.params.get('schedule_unit')
    update_bid = 1 if request.params.get('update_bid') == 'on' else 0

    depend_ids = get_multi_integer(request, 'dependent_ids')
    depends = Task.query.filter(Task.id.in_(depend_ids)).all()

    resource_ids = get_multi_integer(request, 'resource_ids')
    resources = User.query.filter(User.id.in_(resource_ids)).all()

    # get responsible
    responsible_id = request.params.get('responsible_id', -1)
    responsible = User.query.filter(User.id == responsible_id).first()

    priority = request.params.get('priority', 500)

    entity_type = request.params.get('entity_type', None)
    code = request.params.get('code', None)
    asset_type = request.params.get('asset_type', None)
    task_type = request.params.get('task_type', None)
    shot_sequence_id = request.params.get('shot_sequence_id', None)

    cut_in = int(request.params.get('cut_in', 1))
    cut_out = int(request.params.get('cut_out', 1))

    logger.debug('entity_type         : %s' % entity_type)
    logger.debug('parent_id           : %s' % parent_id)
    logger.debug('parent              : %s' % parent)
    logger.debug('depend_ids          : %s' % depend_ids)
    logger.debug('depends             : %s' % depends)
    logger.debug('resource_ids        : %s' % resource_ids)
    logger.debug('resources           : %s' % resources)
    logger.debug('responsible         : %s' % responsible)
    logger.debug('name                : %s' % name)
    logger.debug('description         : %s' % description)
    logger.debug('schedule_model      : %s' % schedule_model)
    logger.debug('schedule_timing     : %s' % schedule_timing)
    logger.debug('schedule_unit       : %s' % schedule_unit)
    logger.debug('update_bid          : %s' % update_bid)
    logger.debug('priority            : %s' % priority)
    logger.debug('code                : %s' % code)

    logger.debug('shot_sequence_id              : %s' % shot_sequence_id)
    logger.debug('cut_in              : %s' % cut_in)
    logger.debug('cut_out             : %s' % cut_out)

    # before doing anything check permission
    if not p_checker('Update_' + entity_type):
        transaction.abort()
        return Response('You do not have enough permission to update a %s' %
                        entity_type, 500)

    # get task
    task_id = request.matchdict.get('id', -1)
    task = Task.query.filter(Task.id == task_id).first()

    # update the task
    if not task:
        transaction.abort()
        return Response("No task found with id : %s" % task_id, 500)

    task.name = name
    task.description = description

    prev_parent = task.parent

    try:
        task.parent = parent
        task.depends = depends
    except CircularDependencyError:
        transaction.abort()
        message = '</div>Parent item can not also be a dependent for the ' \
                  'updated item:<br><br>Parent: %s<br>Depends To: %s</div>' % \
                  (parent.name, map(lambda x: x.name, depends))
        transaction.abort()
        return Response(message, 500)
        # if the current parent and the previous parents are different
    # also update the previous parents status
    if parent != prev_parent:
        update_task_statuses(prev_parent)

    # also update parent status
    update_task_statuses(parent)

    # update status of this task according to its dependencies
    update_task_statuses_with_dependencies(task)
    # also update all task depends to this one
    for dep in task.dependent_of:
        update_task_statuses_with_dependencies(dep)

    task.schedule_model = schedule_model
    task.schedule_unit = schedule_unit
    task.schedule_timing = schedule_timing
    task.resources = resources
    task.priority = priority
    task.code = code
    task.updated_by = logged_in_user

    # update responsible
    if responsible:
        if task.parent:
            if task.parent.responsible == responsible:
                task.responsible = None
            else:
                task.responsible = responsible
        else:
            if task.responsible != responsible:
                task.responsible = responsible

    type_name = ''
    if entity_type == 'Asset':
        type_name = asset_type
    elif entity_type == 'Task':
        type_name = task_type

    task.type = query_type(entity_type, type_name)

    if entity_type == 'Shot':
        task.sequences = [
            Sequence.query.filter_by(id=shot_sequence_id).first()]
        # TODO: there is a bug in Stalker we can not set shot.cut_in because of _cut_duratioin attribute is absent
        # task.cut_in = cut_in
        # task.cut_out = cut_out

    task._reschedule(task.schedule_timing, task.schedule_unit)
    if update_bid:
        logger.debug('updating bid')
        task.bid_timing = task.schedule_timing
        task.bid_unit = task.schedule_unit
    else:
        logger.debug('not updating bid')
    return Response('Task updated successfully')




def depth_first_flatten(task, task_array=None):
    """Does a depth first flattening on the child tasks of the given task.
    :param task: start from this task
    :param task_array: previous flattened task array
    :return: list of flat tasks
    """

    if task_array is None:
        task_array = []

    if task:
        if task not in task_array:
            task_array.append(task)
            # take a tour in children
        for child_task in task.children:
            task_array.append(child_task)
            # recursive call
            task_array = depth_first_flatten(child_task, task_array)

    return task_array


def raw_data_to_array(raw_data):
    """converts the given string raw data in:

        '{"(string, string)"},{"(string, string)"}...{"(string, string)"}'

    format to a Python array of:

        [[int, string], [int, string] ... [int, string]]
    """
    data = []
    if len(raw_data) > 7:  # in which case it is not '{"(,)"}'
        json_data = json.loads(
            raw_data.replace('{', '[')
            .replace('}', ']')
            .replace('(', '[')
            .replace(')', ']')
        )  # it is an array of string
        for j in json_data:
            d = j[1:-1].split(',')
            data.append(
                {
                    'id': int(d[0]),
                    'name': d[1].replace('"', '')
                }
            )
    return data


@view_config(
    route_name='get_tasks',
    renderer='json'
)
def get_tasks(request):
    """RESTful version of getting all tasks
    """
    logger.debug('using raw sql query')
    start = time.time()

    parent_id = request.params.get('parent_id')
    task_id = request.params.get('task_id')

    sql_query = """select
        "Tasks".bid_timing as bid_timing,
        "Tasks".bid_unit as bid_unit,
                coalesce(
            -- for parent tasks
            (case "Tasks"._schedule_seconds
                when 0 then 0
                else "Tasks"._total_logged_seconds::float / "Tasks"._schedule_seconds * 100
             end
            ),
            -- for child tasks we need to count the total seconds of related TimeLogs
            (coalesce("Task_TimeLogs".duration, 0.0))::float /
                ("Tasks".schedule_timing * (case "Tasks".schedule_unit
                    when 'h' then 3600
                    when 'd' then 32400
                    when 'w' then 147600
                    when 'm' then 590400
                    when 'y' then 7696277
                    else 0
                end)) * 100.0
        ) as percent_complete,
        array_agg(
            distinct(
                "Task_Dependencies".id,
                "Task_Dependencies".name
            )
        ) as dependencies,
        "SimpleEntities".description,
        extract(epoch from coalesce("Tasks".computed_end::timestamp AT TIME ZONE 'UTC', "Tasks".end::timestamp AT TIME ZONE 'UTC')) * 1000 as end,
        exists (
           select 1
            from "Tasks" as "Child_Tasks"
            where "Child_Tasks".parent_id = "Tasks".id
        ) as hasChildren,
        "Task_Hierarchy".parent_names as hierarchy_name,
        "Tasks".id as id,
        '/' || lower("SimpleEntities".entity_type) || 's/' || "Tasks".id || '/view' as link,
        "SimpleEntities".name,
        coalesce("Parent_Tasks".id, "Tasks".project_id) as parent_id,
        "Tasks".priority as priority,
        array_agg(
            distinct(
                "Task_Resources".resource_id,
                "Task_Resources".resource_name
            )
        ) as resources,
        "Tasks".schedule_model,
        coalesce("Tasks"._schedule_seconds,
            "Tasks".schedule_timing * (case "Tasks".schedule_unit
                when 'h' then 3600
                when 'd' then 32400
                when 'w' then 147600
                when 'm' then 590400
                when 'y' then 7696277
                else 0
            end)
        ) as schedule_seconds,
        "Tasks".schedule_timing,
        "Tasks".schedule_unit,
        extract(epoch from coalesce("Tasks".computed_start::timestamp AT TIME ZONE 'UTC', "Tasks".start::timestamp AT TIME ZONE 'UTC')) * 1000 as start,
        lower("Task_Status".code) as status,
        coalesce(
            -- for parent tasks
            "Tasks"._total_logged_seconds,
            -- for child tasks we need to count the total seconds of related TimeLogs
            coalesce("Task_TimeLogs".duration, 0.0)
        ) as total_logged_seconds,
        "SimpleEntities".entity_type
    from "Tasks"
        left outer join "Tasks" as "Parent_Tasks" on "Tasks".parent_id = "Parent_Tasks".id
        -- TimeLogs for Leaf Tasks
        left outer join (
            select
                "TimeLogs".task_id,
                extract(epoch from sum("TimeLogs".end::timestamp AT TIME ZONE 'UTC' - "TimeLogs".start::timestamp AT TIME ZONE 'UTC')) as duration
            from "TimeLogs"
            group by task_id
        ) as "Task_TimeLogs" on "Task_TimeLogs".task_id = "Tasks".id
        -- Dependencies
        left outer join (
            select
                "SimpleEntities".id as id,
                "SimpleEntities".name as name,
                "Task_Dependencies".task_id
            from "Task_Dependencies"
                join "SimpleEntities" on "Task_Dependencies".depends_to_task_id = "SimpleEntities".id
        ) as "Task_Dependencies" on "Tasks".id = "Task_Dependencies".task_id
        join "SimpleEntities" on "Tasks".id = "SimpleEntities".id
        -- hierarcy name
        join (
            select
                parent_data.id as id,
                "SimpleEntities".name || '(' || "SimpleEntities".id || ') (' ||
                array_to_string(array_agg(
                    case
                        when "SimpleEntities_parent".entity_type = 'Project'
                        then "Projects".code
                        else "SimpleEntities_parent".name
                    end),
                    ' | '
                ) || ')'
                as parent_names
                from (
                    with recursive parent_ids(id, parent_id, n) as (
                            select task.id, coalesce(task.parent_id, task.project_id), 0
                            from "Tasks" task
                        union all
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
                group by parent_data.id, "SimpleEntities".name, "SimpleEntities".id
        ) as "Task_Hierarchy" on "Tasks".id = "Task_Hierarchy".id
        -- resources
        left outer join (
            select
                "SimpleEntities".id as resource_id,
                "SimpleEntities".name as resource_name,
                "Task_Resources".task_id as task_id
            from "Task_Resources"
            join "SimpleEntities" on "Task_Resources".resource_id = "SimpleEntities".id
        ) as "Task_Resources" on "Tasks".id = "Task_Resources".task_id
        -- status
        join "Statuses" as "Task_Status" on "Tasks".status_id = "Task_Status".id
    where %(where_condition)s
    group by
        "Tasks".bid_timing,
        "Tasks".bid_unit,
        "Tasks"._total_logged_seconds,
        "Tasks"._schedule_seconds,
        "Tasks".id,
        "Task_TimeLogs".duration,
        "Tasks".schedule_timing,
        "Tasks".schedule_unit,
        "SimpleEntities".description,
        "Tasks".computed_end,
        "Tasks".end,
        "Task_Hierarchy".parent_names,
        "SimpleEntities".entity_type,
        "SimpleEntities".name,
        "Tasks".id,
        "Tasks".priority,
        "Tasks".responsible_id,
        "Tasks".schedule_model,
        "Tasks".computed_start,
        "Tasks".start,
        "Task_Status".code,
        "Parent_Tasks".id,
        "Tasks".project_id
    order by "SimpleEntities".name
    """

    # set the content range to prevent JSONRest Store to query the data twice
    content_range = '%s-%s/%s'
    where_condition = ''
    if task_id:
        task = Entity.query.filter(Entity.id == task_id).first()
        if isinstance(task, (Project, Studio)):
            # no where condition
            if isinstance(task, Project):
                return_data = convert_to_dgrid_gantt_project_format([task])
                # just return here to avoid any further error
                content_range = content_range % (0, 1, 1)
            else:
                convert_data = Project.query.all()
                return_data = convert_to_dgrid_gantt_project_format(
                    convert_data)
                # just return here to avoid any further error
                content_range = content_range % (
                    0, len(convert_data) - 1, len(convert_data))
            resp = Response(
                json_body=return_data
            )
            resp.content_range = content_range
            end = time.time()
            logger.debug('%s rows retrieved in %s seconds' % (len(return_data),
                                                              (end - start)))
            return resp

        elif isinstance(task, Task):
            where_condition = '"Tasks".id = %s' % task_id

    elif parent_id:
        parent = Entity.query.filter(Entity.id == parent_id).first()
        if isinstance(parent, Project):
            where_condition = '"Parent_Tasks".id is NULL and "Tasks".project_id = %s' % parent_id
        elif isinstance(parent, Task):
            where_condition = '"Parent_Tasks".id = %s' % parent_id

    sql_query = sql_query % {'where_condition': where_condition}

    logger.debug('sql_query : %s' % sql_query)

    # convert to dgrid format right here in place
    result = DBSession.connection().execute(sql_query)

    # use local functions to speed things up
    local_raw_data_to_array = raw_data_to_array
    return_data = [
        {
            'bid_timing': r[0],
            'bid_unit': r[1],
            'completed': r[2],
            'dependencies': local_raw_data_to_array(r[3]),
            'description': r[4],
            'end': r[5],
            'hasChildren': r[6],
            'hierarchy_name': r[7],
            'id': r[8],
            'link': r[9],
            'name': r[10],
            'parent_id': r[11],
            'priority': r[12],
            'resources': local_raw_data_to_array(r[13]),
            'schedule_model': r[14],
            'schedule_seconds': r[15],
            'schedule_timing': r[16],
            'schedule_unit': r[17],
            'start': r[18],
            'status': r[19],
            'total_logged_seconds': r[20],
            'type': r[21],
        }
        for r in result.fetchall()
    ]

    task_count = len(return_data)
    content_range = content_range % (0, task_count - 1, task_count)

    # logger.debug('return_data: %s' % return_data)
    end = time.time()
    logger.debug('%s rows retrieved in %s seconds' % (len(return_data),
                                                      (end - start)))

    resp = Response(
        json_body=return_data
    )
    resp.content_range = content_range
    return resp


@view_config(
    route_name='get_entity_tasks',
    renderer='json'
)

@view_config(
    route_name='get_studio_tasks',
    renderer='json'
)
def get_entity_tasks(request):
    """RESTful version of getting all tasks of an entity
    """
    logger.debug('get_entity_tasks is running')
    entity_id = request.matchdict.get('id', -1)
    start = time.time()
    entity = Entity.query.filter(Entity.id == entity_id).first()

    parent_id = request.params.get('parent_id')
    parent = Entity.query.filter_by(id=parent_id).first()

    return_data = []
    # set the content range to prevent JSONRest Store to query the data twice
    content_range = '%s-%s/%s'

    if entity:
        if parent:
            #logger.debug('there is a parent')
            tasks = []
            if isinstance(entity, User):
                # get user tasks
                entity_tasks = entity.tasks

                # add all parents
                entity_tasks_and_parents = []
                for task in entity_tasks:
                    entity_tasks_and_parents.extend(task.parents)
                entity_tasks_and_parents.extend(entity_tasks)

                if isinstance(parent, Task):
                    parents_children = parent.children
                elif isinstance(parent, Project):
                    parents_children = parent.root_tasks

                for child in parents_children:
                    if child in entity_tasks_and_parents:
                        tasks.append(child)

                if not tasks:
                    # there are no children
                    tasks = parents_children

            elif isinstance(entity, Studio):
                if isinstance(parent, Task):
                    tasks = parent.children
                elif isinstance(parent, Project):
                    tasks = parent.root_tasks

            return_data = convert_to_dgrid_gantt_task_format(tasks)
        else:
            #logger.debug('no parent')
            # no parent,
            # just return projects of the entity
            entity_projects = []
            if isinstance(entity, User):
                entity_projects = entity.projects
            elif isinstance(entity, Studio):
                entity_projects = Project.query.all()

            return_data = \
                convert_to_dgrid_gantt_project_format(entity_projects)

        content_range = content_range % (0,
                                         len(return_data) - 1,
                                         len(return_data))
    end = time.time()
    logger.debug('%s rows retrieved in %s seconds' % (len(return_data),
                                                      (end - start)))

    resp = Response(
        json_body=return_data
    )
    resp.content_range = content_range
    return resp

@view_config(
    route_name='get_user_tasks',
    renderer='json'
)
def get_user_tasks(request):
    """returns all the tasks in the database related to the given entity in
    flat json format
    """
    logged_in_user = get_logged_in_user(request)
    # get all the tasks related in the given project
    user_id = request.matchdict.get('id', -1)
    user = User.query.filter_by(id=user_id).first()

    statuses = []
    status_codes = request.GET.getall('status')
    if status_codes:
        statuses = Status.query.filter(Status.code.in_(status_codes)).all()

    if statuses:
        tasks = [task for task in user.tasks if task.status in statuses]
    else:
        tasks = user.tasks

    return [
        {
            'id': task.id,
            'responsible_name': task.responsible.name,
            'responsible_id': task.responsible.id,
            'percent_complete': task.percent_complete,
            'type': task.type.name if task.type else '',
            'request_review': '1' if ((
                                          logged_in_user in task.resources or logged_in_user == task.responsible) and task.status.code == 'WIP' and task.is_leaf) else None,
            'status': task.status.name,
            'status_color': task.status.html_class,
            'name': '%s (%s)' % (
                task.name,
                ' | '.join([parent.name for parent in task.parents])
            )
        } for task in tasks
    ]


@view_config(
    route_name='get_task',
    renderer='json'
)
def get_task(request):
    """RESTful version of getting a task or project
    """
    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    return_data = []
    if isinstance(entity, Task):
        return_data = convert_to_dgrid_gantt_task_format([entity])
    elif isinstance(entity, Project):
        return_data = convert_to_dgrid_gantt_project_format([entity])

    #logger.debug('return_data: %s' % return_data)

    return return_data


@view_config(
    route_name='get_task_children',
    renderer='json'
)
def get_task_children(request):
    """RESTful version of getting task children
    """
    task_id = request.matchdict.get('id', -1)
    task = Task.query.filter_by(id=task_id).first()
    return convert_to_dgrid_gantt_task_format(task.children)


@view_config(
    route_name='get_gantt_tasks',
    renderer='json'
)
def get_gantt_tasks(request):
    """returns all the tasks in the database related to the given entity in
    jQueryGantt compatible json format
    """
    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    #logger.debug('entity : %s' % entity)

    tasks = []
    if entity:
        if isinstance(entity, Project):
            # return both the project and the root tasks of its
            project = entity
            dgrid_data = convert_to_dgrid_gantt_project_format([project])
            dgrid_data.extend(
                convert_to_dgrid_gantt_task_format(project.root_tasks))
            return dgrid_data
        elif isinstance(entity, User):
            user = entity
            # sort the tasks with the project.id
            if user is not None:
                # TODO: just return root tasks to make it fast
                # get the user projects and then tasks of the user
                dgrid_data = convert_to_dgrid_gantt_project_format(
                    user.projects)

                user_tasks_with_parents = []
                for task in user.tasks:
                    user_tasks_with_parents.append(task)
                    user_tasks_with_parents.extend(task.parents)

                tasks = list(set(user_tasks_with_parents))
                dgrid_data.extend(convert_to_dgrid_gantt_task_format(tasks))
                return dgrid_data
        elif entity.entity_type == 'Studio':
            projects = Project.query.all()
            for project in projects:
                # get the tasks who is a root task
                root_tasks = Task.query \
                    .filter(Task.project == project) \
                    .filter(Task.parent == None).all()

                # do a depth first search for child tasks
                for root_task in root_tasks:
                    # logger.debug('root_task: %s, parent: %s' % (root_task, root_task.parent))
                    tasks.extend(depth_first_flatten(root_task))

        else:  # Task, Asset, Shot, Sequence
            tasks.append(entity)
            tasks.extend(entity.parents)
            tasks.extend(depth_first_flatten(entity))
            tasks = list(set(tasks))

    tasks.sort(key=lambda x: x.start)

    # logger.debug('tasks count: %i' % len(tasks))
    # for task in tasks:
    #     logger.debug('------------------------------')
    #     logger.debug('task name: %s' % task.name)
    #     logger.debug('start date: %s' % task.start)
    #     logger.debug('end date: %s' % task.end)

    return convert_to_dgrid_gantt_task_format(tasks)


@view_config(
    route_name='get_gantt_task_children',
    renderer='json'
)
def get_gantt_task_children(request):
    """returns the children tasks of the given task
    """
    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    # return all user tasks with their parents
    # TODO: check if there is a user id in the query to just return the
    #       parents of the user tasks

    if isinstance(entity, Project):
        return convert_to_dgrid_gantt_task_format(entity.root_tasks)
    if isinstance(entity, Task):
        return convert_to_dgrid_gantt_task_format(entity.children)
    return []


@view_config(
    route_name='get_project_tasks_count',
    renderer='json'
)
def get_project_tasks_count(request):
    """returns all the tasks in the database related to the given entity in
    flat json format
    """
    project_id = request.matchdict.get('id', -1)

    sql_query = """select
        count(1)
    from "Tasks"
    where "Tasks".project_id = %s
    """ % project_id

    return DBSession.connection().execute(sql_query).fetchone()[0]


@view_config(
    route_name='get_project_tasks',
    renderer='json'
)
def get_project_tasks(request):
    """returns all the tasks in the database related to the given entity in
    flat json format
    """
    # get all the tasks related in the given project
    project_id = request.matchdict.get('id', -1)

    start = time.time()

    sql_query = """
    (
        SELECT
            task_parents.id,
            "Task_SimpleEntities".name || ' (' || "Task_SimpleEntities".id || ') (' || "Projects".code || ' | ' || task_parents.parent_names || ')' as parent_names 
        FROM (
            SELECT
                task_parents.id,
                array_agg(task_parents.parent_id) as parent_ids,
                array_agg(task_parents.n) as n,
                array_to_string(
                    array_agg(task_parents.parent_name),
                    ' | '
                ) as parent_names
            FROM (
                WITH RECURSIVE parent_ids(id, parent_id, n) as (
                        SELECT task.id, task.parent_id, 0
                        FROM "Tasks" AS task
                        WHERE task.parent_id IS NOT NULL
                    UNION ALL
                        SELECT task.id, parent.parent_id, parent.n + 1
                        FROM "Tasks" task, parent_ids parent
                        WHERE task.parent_id = parent.id
                )
                SELECT
                    parent_ids.id as id,
                    parent_ids.n as n,
                    parent_ids.parent_id AS parent_id,
                    "ParentTask_SimpleEntities".name as parent_name
                FROM parent_ids
                JOIN "SimpleEntities" as "ParentTask_SimpleEntities" ON parent_ids.parent_id = "ParentTask_SimpleEntities".id
                ORDER BY id, parent_ids.n DESC
            ) as task_parents
            GROUP BY task_parents.id
        ) as task_parents
        JOIN "Tasks" ON task_parents.id = "Tasks".id
        JOIN "Projects" ON "Tasks".project_id = "Projects".id
        JOIN "SimpleEntities" as "Task_SimpleEntities" ON "Tasks".id = "Task_SimpleEntities".id
        WHERE "Tasks".project_id = %(p_id)s
    )
    UNION
    (
        SELECT
            "Tasks".id,
            "Task_SimpleEntities".name || '(' || "Task_SimpleEntities".id || ') (' || "Projects".code || ')' as parent_names
        FROM "Tasks"
        JOIN "Projects" ON "Tasks".project_id = "Projects".id
        JOIN "SimpleEntities" as "Task_SimpleEntities" on "Tasks".id = "Task_SimpleEntities".id
        WHERE "Tasks".parent_id IS NULL AND "Tasks".project_id = %(p_id)s
    )
    """ % {'p_id': project_id}

    result = DBSession.connection().execute(sql_query)

    data = [
        {
            'id': r[0],
            'name': r[1]
        } for r in result.fetchall()
    ]
    end = time.time()

    logger.debug('get_project_task took : %s seconds' % (end - start))
    return data


@view_config(
    route_name='get_user_tasks_count',
    renderer='json'
)
def get_user_tasks_count(request):
    """returns all the tasks in the database related to the given entity in
    flat json format
    """
    # get all the tasks related in the given project
    user_id = request.matchdict.get('id', -1)
    user = User.query.filter_by(id=user_id).first()

    statuses = []
    status_codes = request.GET.getall('status')
    if status_codes:
        statuses = Status.query.filter(Status.code.in_(status_codes)).all()

    tasks = []
    if statuses:
        tasks = [task for task in user.tasks if task.status in statuses]
    else:
        tasks = user.tasks

    return len(tasks)

@view_config(
    route_name='get_entity_tasks_stats',
    renderer='json'
)
def get_entity_tasks_stats(request):
    """runs when viewing an task
    """
    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    #logger.debug('user_id : %s' % entity_id)

    status_list = StatusList.query.filter_by(
        target_entity_type='Task'
    ).first()

    join_attr = None

    if entity.entity_type == 'User':
        join_attr = Task.resources
    elif entity.entity_type == 'Project':
        join_attr = Task.project

    __class__ = entity.__class__

    status_count_task = []

    #TODO find the correct solution to filter leaf tasks. This does not work.
    for status in status_list.statuses:
        status_count_task.append({
            'name': status.name,
            'id': status.id,
            'code': status.code,
            'color': status.html_class,
            'icon': 'icon-folder-close-alt',
            'count': Task.query.join(entity.__class__, join_attr) \
                .filter(__class__.id == entity_id) \
                .filter(Task.status_id == status.id) \
                .filter(Task.children == None) \
                .count()
        })

    return status_count_task



@view_config(
    route_name='get_entity_tasks_by_filter',
    renderer='json'
)
def get_entity_tasks_by_filter(request):
    """returns all the tasks in the database related to the given entity in
    flat json format
    """

    logged_in_user = get_logged_in_user(request)

     # get all the tasks related in the given project
    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    logger.debug('entity_id: %s'% entity_id)

    filter_id = request.matchdict.get('f_id', -1)
    filter = Entity.query.filter_by(id=filter_id).first()


    sql_query = """select
    "Task_Resources".task_id as task_id,
    "ParentTasks".parent_names as task_name,
    "Responsible_SimpleEntities".id as responsible_id,
    "Responsible_SimpleEntities".name as responsible_name,
    coalesce("Type_SimpleEntities".name,'') as type_name,
         array_agg(coalesce(
            -- for parent tasks
            (case "Tasks"._schedule_seconds
                when 0 then 0
                else "Tasks"._total_logged_seconds::float / "Tasks"._schedule_seconds * 100
             end
            ),
            -- for child tasks we need to count the total seconds of related TimeLogs
            (coalesce("Task_TimeLogs".duration, 0.0))::float /
                ("Tasks".schedule_timing * (case "Tasks".schedule_unit
                    when 'h' then 3600
                    when 'd' then 32400
                    when 'w' then 147600
                    when 'm' then 590400
                    when 'y' then 7696277
                    else 0
                end)) * 100.0
        )) as percent_complete,
        array_agg("Resource_SimpleEntities".id) as resource_id,
        array_agg("Resource_SimpleEntities".name) as resource_name,
        "Statuses_SimpleEntities".name as status_name,
        "Statuses".code as status_code,
        "Statuses_SimpleEntities".html_class as status_color,
        "Project_SimpleEntities".id as project_id,
        "Project_SimpleEntities".name as project_name

    from "Tasks"
    join "Task_Resources" on "Task_Resources".task_id = "Tasks".id
    join "SimpleEntities" as "Project_SimpleEntities"on "Project_SimpleEntities".id = "Tasks".project_id
    join "Statuses" on "Statuses".id = "Tasks".status_id
    join "SimpleEntities" as "Statuses_SimpleEntities" on "Statuses_SimpleEntities".id = "Statuses".id
    left outer join (
                select
                    "TimeLogs".task_id,
                    extract(epoch from sum("TimeLogs".end::timestamp AT TIME ZONE 'UTC' - "TimeLogs".start::timestamp AT TIME ZONE 'UTC')) as duration
                from "TimeLogs"
                group by task_id
            ) as "Task_TimeLogs" on "Task_TimeLogs".task_id = "Tasks".id
    join "SimpleEntities" as "Task_SimpleEntities" on "Task_SimpleEntities".id = "Task_Resources".task_id

    join "SimpleEntities" as "Resource_SimpleEntities" on "Resource_SimpleEntities".id = "Task_Resources".resource_id
    join ((
        -- get tasks responsible from parents
        -- so find all the tasks that doesn't have a responsible but one of their parents has
        with recursive go_to_parent(id, parent_id) as (
                select task.id, task.parent_id
                from "Tasks" as task
                where task.responsible_id is NULL
            union all
                select g.id, task.parent_id
                from go_to_parent as g
                join "Tasks" as task on g.parent_id = task.id
                where task.parent_id is not NULL and task.responsible_id is NULL
        )
        select
            g.id, "Tasks".responsible_id
        from go_to_parent as g
        join "Tasks" on "Tasks".id = g.parent_id
        where "Tasks".responsible_id is not NULL
        order by g.id
    )
    union
    (
        -- select all the tasks that has a responsible
        select
            id, responsible_id
        from "Tasks"
        where responsible_id is not NULL
    )
    union
    (
        -- select all the residual tasks that are not in the previous union
        select
            "Tasks".id,
            "Projects".lead_id
        from "Tasks"
        join "Projects" on "Tasks".project_id = "Projects".id
        left outer join (
            (
                -- get tasks responsible from parents
                -- so find all the tasks that doesn't have a responsible but one of their parents has
                with recursive go_to_parent(id, parent_id) as (
                        select task.id, task.parent_id
                        from "Tasks" as task
                        where task.responsible_id is NULL
                    union all
                        select g.id, task.parent_id
                        from go_to_parent as g
                        join "Tasks" as task on g.parent_id = task.id
                        where task.parent_id is not NULL and task.responsible_id is NULL
                )
                select
                    g.id
                from go_to_parent as g
                join "Tasks" on "Tasks".id = g.parent_id
                where "Tasks".responsible_id is not NULL
                order by g.id
            )
            union
            (
                -- select all the tasks that has a responsible
                select
                    id
                from "Tasks"
                where responsible_id is not NULL
            )
        ) as prev_query on "Tasks".id = prev_query.id
        where prev_query.id is NULL
    )) as "Tasks_Responsible" on "Tasks_Responsible".id = "Tasks".id
    left join "SimpleEntities" as "Responsible_SimpleEntities" on "Responsible_SimpleEntities".id = "Tasks_Responsible".responsible_id
    left join "SimpleEntities" as "Type_SimpleEntities" on "Task_SimpleEntities".type_id = "Type_SimpleEntities".id
    left join (
    (
        SELECT
            task_parents.id,
            "Task_SimpleEntities".name || '(' || "Task_SimpleEntities".id || ') (' || "Projects".code || ' | ' || task_parents.parent_names || ')' as parent_names 
        FROM (
            SELECT
                task_parents.id,
                array_agg(task_parents.parent_id) as parent_ids,
                array_agg(task_parents.n) as n,
                array_to_string(
                    array_agg(task_parents.parent_name),
                    ' | '
                ) as parent_names
            FROM (
                WITH RECURSIVE parent_ids(id, parent_id, n) as (
                        SELECT task.id, task.parent_id, 0
                        FROM "Tasks" AS task
                        WHERE task.parent_id IS NOT NULL
                    UNION ALL
                        SELECT task.id, parent.parent_id, parent.n + 1
                        FROM "Tasks" task, parent_ids parent
                        WHERE task.parent_id = parent.id
                )
                SELECT
                    parent_ids.id as id,
                    parent_ids.n as n,
                    parent_ids.parent_id AS parent_id,
                    "ParentTask_SimpleEntities".name as parent_name
                FROM parent_ids
                JOIN "SimpleEntities" as "ParentTask_SimpleEntities" ON parent_ids.parent_id = "ParentTask_SimpleEntities".id
                ORDER BY id, parent_ids.n DESC
            ) as task_parents
            GROUP BY task_parents.id
        ) as task_parents
        JOIN "Tasks" ON task_parents.id = "Tasks".id
        JOIN "Projects" ON "Tasks".project_id = "Projects".id
        JOIN "SimpleEntities" as "Task_SimpleEntities" ON "Tasks".id = "Task_SimpleEntities".id
    )
    UNION
    (
        SELECT
            "Tasks".id,
            "Task_SimpleEntities".name || '(' || "Task_SimpleEntities".id || ') (' || "Projects".code || ')' as parent_names
        FROM "Tasks"
        JOIN "Projects" ON "Tasks".project_id = "Projects".id
        JOIN "SimpleEntities" as "Task_SimpleEntities" on "Tasks".id = "Task_SimpleEntities".id
        WHERE "Tasks".parent_id IS NULL
    )
    ) as "ParentTasks" on "Tasks".id = "ParentTasks".id

    where %(where_condition_for_entity)s%(where_condition_for_filter)s

    group by "Task_Resources".task_id,
        "ParentTasks".parent_names,
        "Responsible_SimpleEntities".id ,
        "Responsible_SimpleEntities".name,
        "Type_SimpleEntities".name,
        "Statuses_SimpleEntities".name,
        "Statuses".code,
        "Statuses_SimpleEntities".html_class,
        "Project_SimpleEntities".id,
        "Project_SimpleEntities".name"""

    where_condition_for_entity = ''



    if isinstance(entity, User):
         where_condition_for_entity = '"Task_Resources".resource_id=%s' % entity_id


    elif isinstance(entity, Project):
        where_condition_for_entity = '"Tasks".project_id =%s' % entity_id

    where_condition_for_filter = ''

    if isinstance(filter, User):
         where_condition_for_entity = ''
         where_condition_for_filter = '"Tasks_Responsible".responsible_id=%s' % filter_id
    elif isinstance(filter, Status):
        where_condition_for_filter = ' and "Statuses_SimpleEntities".id =%s' % filter_id


    sql_query = sql_query % {'where_condition_for_entity': where_condition_for_entity, 'where_condition_for_filter':where_condition_for_filter}


    # convert to dgrid format right here in place
    result = DBSession.connection().execute(sql_query)

    return_data = [
        {
            'id': r[0],
            'name': r[1],
            'responsible_id': r[2],
            'responsible_name': r[3],
            'type': r[4],
            'percent_complete': r[5][0],
            'resource_id':r[6],
            'resource_name':r[7],
            'status':r[8],
            'status_code':r[9],
            'status_color':r[10],
            'project_id':r[11],
            'project_name':r[12],
            'request_review':'1' if (logged_in_user.id in r[6] or r[2]==logged_in_user.id) and r[9]=='WIP' else None,
            'review':'1' if r[2]==logged_in_user.id and r[9]=='PREV' else None

        }
        for r in result.fetchall()
    ]



    resp = Response(
        json_body=return_data
    )
    # resp.content_range = content_range
    return resp



def data_dialog(request, mode='create', entity_type='Task'):
    """a generic function which will create a dictionary with enough data
    """
    logged_in_user = get_logged_in_user(request)
    came_from = request.params.get('came_from', request.url)

    entity_id = request.matchdict.get('id')
    entity = Entity.query.filter_by(id=entity_id).first()

    if mode == 'create':
        project_id = request.params.get('project_id')
        project = Project.query.filter_by(id=project_id).first()

        parent_id = request.params.get('parent_id')
        parent = Task.query.filter_by(id=parent_id).first()

        if not project and parent:
            project = parent.project

        dependent_ids = get_multi_integer(request, 'dependent_ids', 'GET')
        depends_to = Task.query.filter(Task.id.in_(dependent_ids)).all()

        if not project and depends_to:
            project = depends_to[0].project
    elif mode in ['update', 'review']:
        entity_type = entity.entity_type
        project = entity.project
        parent = entity.parent
        depends_to = entity.depends

    logger.debug('entity_id  : %s' % entity_id)
    logger.debug('entity     : %s' % entity)
    logger.debug('project    : %s' % project)
    logger.debug('parent     : %s' % parent)
    logger.debug('depends_to : %s' % depends_to)

    return {
        'mode': mode,
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'entity': entity,
        'entity_type': entity_type,
        'project': project,
        'parent': parent,
        'depends_to': depends_to,
        'schedule_models': defaults.task_schedule_models,
        'milliseconds_since_epoch': milliseconds_since_epoch,
        'came_from': came_from,
    }


@view_config(
    route_name='create_task_dialog',
    renderer='templates/task/dialog/task_dialog.jinja2'
)
def create_task_dialog(request):
    """called when creating tasks
    """
    return data_dialog(request, mode='create', entity_type='Task')


@view_config(
    route_name='update_task_dialog',
    renderer='templates/task/dialog/task_dialog.jinja2'
)
def update_task_dialog(request):
    """called when updating tasks
    """
    return data_dialog(request, mode='update', entity_type='Task')


@view_config(
    route_name='create_asset_dialog',
    renderer='templates/task/dialog/task_dialog.jinja2'
)
def create_asset_dialog(request):
    """called when creating assets
    """
    return data_dialog(request, mode='create', entity_type='Asset')


@view_config(
    route_name='update_asset_dialog',
    renderer='templates/task/dialog/task_dialog.jinja2'
)
def update_asset_dialog(request):
    """called when updating assets
    """
    return data_dialog(request, mode='update', entity_type='Asset')


@view_config(
    route_name='review_asset_dialog',
    renderer='templates/task/dialog/review_task_dialog.jinja2'
)
def review_asset_dialog(request):
    """called when reviewing assets
    """
    return data_dialog(request, mode='review', entity_type='Asset')


@view_config(
    route_name='create_shot_dialog',
    renderer='templates/task/dialog/task_dialog.jinja2'
)
def create_shot_dialog(request):
    """called when creating shots
    """
    return data_dialog(request, mode='create', entity_type='Shot')


@view_config(
    route_name='update_shot_dialog',
    renderer='templates/task/dialog/task_dialog.jinja2'
)
def update_shot_dialog(request):
    """called when updating shots
    """
    return data_dialog(request, mode='update', entity_type='Shot')


@view_config(
    route_name='review_shot_dialog',
    renderer='templates/task/dialog/review_task_dialog.jinja2'
)
def review_shot_dialog(request):
    """called when reviewing shots
    """
    return data_dialog(request, mode='review', entity_type='Shot')


@view_config(
    route_name='create_sequence_dialog',
    renderer='templates/task/dialog/task_dialog.jinja2'
)
def create_sequence_dialog(request):
    """called when creating sequences
    """
    return data_dialog(request, mode='create', entity_type='Sequence')


@view_config(
    route_name='update_sequence_dialog',
    renderer='templates/task/dialog/task_dialog.jinja2'
)
def update_sequence_dialog(request):
    """called when updating sequences
    """
    return data_dialog(request, mode='update', entity_type='Sequence')


@view_config(
    route_name='review_sequence_dialog',
    renderer='templates/task/dialog/review_task_dialog.jinja2'
)
def review_sequence_dialog(request):
    """called when reviewing sequences
    """
    return data_dialog(request, mode='review', entity_type='Sequence')


@view_config(route_name='create_task')
def create_task(request):
    """runs when adding a new task
    """
    logged_in_user = get_logged_in_user(request)

    # ***********************************************************************
    # collect params
    project_id = request.params.get('project_id', None)
    parent_id = request.params.get('parent_id', None)
    name = request.params.get('name', None)
    description = request.params.get('description', '')
    # is_milestone = request.params.get('is_milestone', None)

    schedule_model = request.params.get('schedule_model') # there should be one
    schedule_timing = float(request.params.get('schedule_timing'))
    schedule_unit = request.params.get('schedule_unit')

    # get the resources
    resources = []
    resource_ids = []
    if 'resource_ids' in request.params:
        resource_ids = get_multi_integer(request, 'resource_ids')
        resources = User.query.filter(User.id.in_(resource_ids)).all()

    # get responsible
    responsible_id = request.params.get('responsible_id', None)
    responsible = None
    if responsible_id:
        responsible = User.query.filter(User.id == responsible_id).first()

    priority = request.params.get('priority', 500)

    code = request.params.get('code', '')
    entity_type = request.params.get('entity_type')
    asset_type = request.params.get('asset_type')
    task_type = request.params.get('task_type')
    shot_sequence_id = request.params.get('shot_sequence_id')

    cut_in = request.params.get('cut_in')
    cut_out = request.params.get('cut_out')

    logger.debug('entity_type         : %s' % entity_type)
    logger.debug('asset_type          : %s' % asset_type)
    logger.debug('task_type           : %s' % task_type)
    logger.debug('code                : %s' % code)
    logger.debug('project_id          : %s' % project_id)
    logger.debug('parent_id           : %s' % parent_id)
    logger.debug('name                : %s' % name)
    logger.debug('description         : %s' % description)
    logger.debug('schedule_model      : %s' % schedule_model)
    logger.debug('schedule_timing     : %s' % schedule_timing)
    logger.debug('schedule_unit       : %s' % schedule_unit)
    logger.debug('resource_ids        : %s' % resource_ids)
    logger.debug('resources           : %s' % resources)
    logger.debug('responsible         : %s' % responsible)
    logger.debug('priority            : %s' % priority)
    logger.debug('shot_sequence_id    : %s' % shot_sequence_id)
    logger.debug('cut_in              : %s' % cut_in)
    logger.debug('cut_out             : %s' % cut_out)

    kwargs = {}

    if not project_id or not name:
        logger.debug('there are missing parameters')

        def get_param(param):
            if param in request.params:
                logger.debug('%s: %s' % (param, request.params[param]))
            else:
                logger.debug('%s not in params' % param)

        get_param('project_id')
        get_param('name')
        get_param('description')

        param_list = ['project_id', 'name', 'description']
        params = [param for param in param_list if param not in request.params]
        transaction.abort()
        return Response('There are missing parameters: %s' % params, 500)

    # get the project
    project = Project.query.filter_by(id=project_id).first()
    kwargs['project'] = project

    # get the parent if parent_id exists
    parent = Task.query.filter_by(id=parent_id).first() if parent_id else None

    kwargs['parent'] = parent

    # get the status_list
    status_list = StatusList.query \
        .filter_by(target_entity_type=entity_type) \
        .first()

    logger.debug('status_list: %s' % status_list)

    # get the dependencies
    logger.debug('request.POST: %s' % request.POST)
    depends_to_ids = get_multi_integer(request, 'dependent_ids')

    depends = Task.query.filter(
        Task.id.in_(depends_to_ids)).all() if depends_to_ids else []
    logger.debug('depends: %s' % depends)
    # TODO: check if any of the dependent tasks are in HREV status,
    #       then prevent depending to those tasks and ask the user to remove
    #       that dependency

    # there should be a status_list
    if status_list is None:
        transaction.abort()
        return Response(
            'No StatusList found suitable for %s' % entity_type, 500)

    # check the statuses of the dependencies to decide the newly created task
    # status
    status_new = Status.query.filter_by(code='NEW').first()
    status_rts = Status.query.filter_by(code='RTS').first()
    status_cmpl = Status.query.filter_by(code='CMPL').first()
    status = status_rts
    if depends:
        for dependent_task in depends:
            if dependent_task.status != status_cmpl:
                # TODO: use update_task_statuses_with_dependencies()
                status = status_new

    logger.debug('status: %s' % status)

    if not schedule_timing:
        return Response('schedule_timing can not be 0', 500)

    kwargs['name'] = name
    kwargs['code'] = code
    kwargs['description'] = description
    kwargs['created_by'] = logged_in_user
    kwargs['date_created'] = local_to_utc(datetime.datetime.now())


    kwargs['status_list'] = status_list
    kwargs['status'] = status

    kwargs['schedule_model'] = schedule_model
    kwargs['schedule_timing'] = schedule_timing
    kwargs['schedule_unit'] = schedule_unit

    kwargs['resources'] = resources
    kwargs['depends'] = depends

    kwargs['priority'] = priority

    type_name = ''
    if entity_type == 'Asset':
        type_name = asset_type
    elif entity_type == 'Task':
        type_name = task_type
    kwargs['type'] = query_type(entity_type, type_name)

    if entity_type == 'Shot':
        sequence = Sequence.query.filter_by(id=shot_sequence_id).first()
        kwargs['sequence'] = sequence
        kwargs['cut_in'] = cut_in
        kwargs['cut_out'] = cut_out

    try:
        if entity_type == 'Asset':
            logger.debug('creating a new Asset')
            new_entity = Asset(**kwargs)
            logger.debug('new_asset.name %s' % new_entity.name)
        elif entity_type == 'Shot':
            new_entity = Shot(**kwargs)
            logger.debug('new_shot.name %s' % new_entity.name)
        elif entity_type == 'Sequence':
            new_entity = Sequence(**kwargs)
            logger.debug('new_shot.name %s' % new_entity.name)
        else:  # entity_type == 'Task'
            new_entity = Task(**kwargs)
            logger.debug('new_task.name %s' % new_entity.name)
        DBSession.add(new_entity)

        if responsible:
            # check if the responsible is different than
            # the parents responsible
            if new_entity.responsible != responsible:
                new_entity.responsible = responsible

    except (AttributeError, TypeError, CircularDependencyError) as e:
        logger.debug('The Error Message: %s' % e.message)
        response = Response('%s' % e.message, 500)
        transaction.abort()
        return response
    else:
        DBSession.add(new_entity)
        try:
            transaction.commit()
        except IntegrityError as e:
            logger.debug(e.message)
            transaction.abort()
            return Response(e.message, 500)
        else:
            logger.debug('flushing the DBSession, no problem here!')
            DBSession.flush()
            logger.debug('finished adding Task')

    return Response('Task created successfully')


@view_config(route_name='auto_schedule_tasks')
def auto_schedule_tasks(request):
    """schedules all the tasks of active projects
    """
    # get the studio
    studio = Studio.query.first()

    if not studio:
        transaction.abort()
        return Response("There is no Studio instance\n"
                        "Please create a studio first", 500)

    tj_scheduler = TaskJugglerScheduler()
    studio.scheduler = tj_scheduler

    try:
        stderr = studio.schedule()
        c = StdErrToHTMLConverter(stderr)
        return Response(c.html(replace_links=True))
    except RuntimeError as e:
        c = StdErrToHTMLConverter(e)
        transaction.abort()
        return Response(c.html(replace_links=True), 500)



def get_last_version_of_task(request, is_published=''):
     """finds last published version of task
     """

     version = None

     task_id = request.matchdict.get('id')
     task = Task.query.filter_by(id=task_id).first()

     sql_query = """select
            "Versions".id as version_id,
            "Versions".parent_id as parent_id,
            "Version_Tasks".id as task_id,
            "Version_SimpleEntities".date_updated,
            "Version_SimpleEntities".created_by_id as created_by_id,
            "Created_by_SimpleEntities".name as created_by_name,
            "Version_Links".full_path as absolute_full_path,
            "Version_SimpleEntities".description as description
                from "Versions"
                join "Tasks" as "Version_Tasks" on "Version_Tasks".id = "Versions".task_id
                join "Links" as "Version_Links" on "Version_Links".id = "Versions".id
                join "SimpleEntities" as "Version_SimpleEntities" on "Version_SimpleEntities".id = "Versions".id
                join "SimpleEntities" as "Created_by_SimpleEntities" on "Created_by_SimpleEntities".id = "Version_SimpleEntities".created_by_id
                where "Version_Tasks".id = %(task_id)s and "Versions".take_name = 'Main' %(is_published_condition)s

                order by date_updated desc
                limit 1"""

     is_published_condition = ''

     if is_published !='':

         is_published_condition = ' and "Versions".is_published = \'%s\'' % is_published


     logger.debug('%s' % is_published_condition)

     sql_query = sql_query % {'task_id': task_id, 'is_published_condition':is_published_condition}

     result = DBSession.connection().execute(sql_query).fetchone()

     if result:

            user_os = get_user_os(request)
            repo = task.project.repository

            path_converter = lambda x: x
            if repo:
                if user_os == 'windows':
                    path_converter = repo.to_windows_path
                elif user_os == 'linux':
                    path_converter = repo.to_linux_path
                elif user_os == 'osx':
                    path_converter = repo.to_osx_path

            file_name_split = result[6].split('/')

            version = {
                            'id': result[0],
                            'parent_id': result[1],
                            'task_id': result[2],
                            'task_name':task.name,
                            'date_updated': result[3],
                            'created_by_id': result[4],
                            'created_by_name': result[5],
                            'path':path_converter(result[6]),
                            'description':result[7] if result[7] else 'No description',
                            'file_name':'.../%s'% file_name_split[len(file_name_split)-1]
                     }

     return version

@view_config(
    route_name='review_task_dialog',
    renderer='templates/task/dialog/review_task_dialog.jinja2'
)
def review_task_dialog(request):
    """called when reviewing tasks
    """

    logged_in_user = get_logged_in_user(request)
    came_from = request.params.get('came_from', request.url)

    entity_id = request.matchdict.get('id')
    entity = Entity.query.filter_by(id=entity_id).first()

    version = get_last_version_of_task(request, is_published='t')

    project = entity.project


    return {

        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'entity': entity,
        'project': project,
        'came_from': came_from,
        'version':version
    }

@view_config(
    route_name='review_task'
)
def review_task(request):
    """review task
    """

     # get logged in user as he review requester
    logged_in_user = get_logged_in_user(request)


    task_id = request.matchdict.get('id')
    task = Task.query.filter(Task.id == task_id).first()

    if not task:
        transaction.abort()
        return Response('There is no task with id: %s' % task_id, 500)

    send_email = request.params.get('send_email', 1)
    description = request.params.get('description', '')

    review = request.params.get('review')

    if not review:
        transaction.abort()
        return Response('No revision is specified', 500)

    if review == 'Approve':
        # change the task status to complete
        status_cmpl = Status.query.filter(Status.code == 'CMPL').first()
        if not status_cmpl:
            transaction.abort()
            return Response('There is no status with code CMPL, please inform '
                            'your Stalker admin to create a task with code '
                            'CMPL and assign it to Task', 500)
        try:
            task.status = status_cmpl
        except ValueError as e:
            transaction.abort()
            return Response(e.message, 500)

        # update parent statuses
        update_task_statuses(task.parent)

        # update dependent_of statuses
        for dep in task.dependent_of:
            update_task_statuses_with_dependencies(dep)

        utc_now = local_to_utc(datetime.datetime.now())
        logger.debug("utc_now: %s" % utc_now)
        logger.debug("task.date_created: %s" % task.date_created)

        task.updated_by = logged_in_user
        task.date_updated = utc_now

        task_full_name = '%s (%s)' % (
                task.name,
                '|'.join(map(lambda x: x.name, task.parents))
            )

        summary_text = \
                'Task Reviewed: "%(task_full_name)s" has been approved!' % {
                    'task_full_name': task_full_name
                }



        description_body = \
                '%(requester_name)s has approved ' \
                '%(task)s with the following ' \
                'comment:%(spacing)s' \
                '%(description)s'

        if description == "":
                description_body = \
                '%(requester_name)s has approved ' \
                '%(task)s  ' \
                '%(spacing)s' \
                '%(description)s'



        description_text = description_body % {
                "requester_name": logged_in_user.name,
                "task": task_full_name,
                "spacing": '\n\n',
                "description": description
                if description else "(No Description)"
            }

        description_html = description_body % {
                "requester_name": '<strong>%s</strong>' % logged_in_user.name,
                "task": '<strong>%s</strong>' % task_full_name,
                "spacing": '<br><br>',
                "description": description.replace('\n', '<br>')
                if description else "(No Description)"
            }


        # find the related revision Ticket and add the comment
        review_type = Type.query.filter(Type.name == "Review").first()
        tickets = Ticket.query \
            .filter(Ticket.links.contains(task)) \
            .filter(Ticket.type == review_type).all()
        logger.debug("tickets: %s" % tickets)



        if tickets:

            note = Note(
                content=description_text,
                created_by=logged_in_user,
                date_created=utc_now,
                date_updated=utc_now
            )
            for ticket in tickets:
                ticket.comments.append(note)
                ticket.date_updated = utc_now
                ticket.updated_by = logged_in_user
                ticket.resolve(logged_in_user,'fixed')
            DBSession.add(note)

        transaction.commit()
        DBSession.add_all([task, logged_in_user])



        if send_email:
            # send email to resources of the task
            mailer = get_mailer(request)
            recipients = []
            for resource in task.resources:
                recipients.append(resource.email)


            message = Message(
                subject=summary_text,
                sender=dummy_email_address,
                recipients=recipients,
                body=description_text,
                html=description_html
            )
            mailer.send(message)

    elif review == 'Request Revision':
        # so request a revision
        request_revision(request)
        # no need to update the child and dependent_of statuses,
        # they will not change

    return Response('Successfully reviewed task')

@view_config(
    route_name='request_revision'
)
def request_revision(request):
    """updates task timing and status and sends an email to the task resources
    """
    # get logged in user as he review requester
    logged_in_user = get_logged_in_user(request)

    task_id = request.matchdict.get('id', -1)
    task = Task.query.filter(Task.id == task_id).first()

    # check if we have a task
    if not task:
        transaction.abort()
        return Response('There is no task with id: %s' % task_id, 500)

    send_email = request.params.get('send_email', 1)
    description = request.params.get('description', '')

    schedule_timing = request.params.get('schedule_timing')
    schedule_unit = request.params.get('schedule_unit')
    schedule_model = request.params.get('schedule_model')

    if not schedule_timing:
        transaction.abort()
        return Response('There are missing parameters: schedule_timing', 500)
    else:
        try:
            schedule_timing = float(schedule_timing)
        except ValueError:
            transaction.abort()
            return Response('Please supply a float or integer value for '
                            'schedule_timing parameter', 500)

    if not schedule_unit:
        transaction.abort()
        return Response('There are missing parameters: schedule_unit', 500)
    else:
        if schedule_unit not in ['h', 'd', 'w', 'm', 'y']:
            transaction.abort()
            return Response("schedule_unit parameter should be one of ['h', "
                            "'d', 'w', 'm', 'y']", 500)

    if not schedule_model:
        transaction.abort()
        return Response('There are missing parameters: schedule_model', 500)
    else:
        if schedule_model not in ['effort', 'duration', 'length']:
            transaction.abort()
            return Response("schedule_model parameter should be on of "
                            "['effort', 'duration', 'length']", 500)

    logger.debug('schedule_timing: %s' % schedule_timing)
    logger.debug('schedule_unit  : %s' % schedule_unit)
    logger.debug('schedule_model : %s' % schedule_model)

    # get statuses
    status_prev = Status.query.filter(Status.code == 'PREV').first()

    # check if the task has some time logs
    if task.status != status_prev:
        transaction.abort()
        return Response('You can not request a revision for a task with '
                        'status is set to "%s"' % task.status.name, 500)

    # set task status to Has Revision (HREV)
    status_hrev = Status.query.filter(Status.code == 'HREV').first()
    if not status_hrev:
        transaction.abort()
        return Response('There is no status with name "Has Revision" and code '
                        '"HREV" please inform your Stalker admin to create '
                        'this status and include it to Task status list.', 500)

    task.status = status_hrev
    # first set its effort to its time logs
    task.schedule_timing = task.total_logged_seconds / 3600
    task.schedule_unit = 'h'

    # and expand it with the given revision timing
    # convert the given revision unit to hours
    studio = Studio.query.first()
    if not studio:
        studio = defaults

    #assert isinstance(studio, Studio)
    if schedule_unit == 'h':
        # do nothing just add the timing
        task.schedule_timing += schedule_timing
    elif schedule_unit == 'd':
        task.schedule_timing += schedule_timing * studio.daily_working_hours
    elif schedule_unit == 'w':
        task.schedule_timing += schedule_timing * studio.weekly_working_hours
    elif schedule_unit == 'm':
        task.schedule_timing += schedule_timing * 4 * \
                                studio.weekly_working_hours
    elif schedule_unit == 'y':
        task.schedule_timing += \
            int(schedule_timing * studio.yearly_working_days *
                studio.weekly_working_hours)

    utc_now = local_to_utc(datetime.datetime.now())

    task.updated_by = logged_in_user
    task.date_updated = utc_now

    resource = task.resources[0]

    # find the related revision Ticket and add the comment
    review_type = Type.query.filter(Type.name == "Review").first()
    tickets = Ticket.query \
        .filter(Ticket.links.contains(task)) \
        .filter(Ticket.type == review_type).all()


    if tickets:
        for ticket in tickets:
            ticket.date_updated = utc_now
            ticket.updated_by = logged_in_user
            resource = ticket.created_by
            ticket.resolve(logged_in_user,'fixed')


    # get the project that the ticket belongs to
    project = task.project

    user_link_internal = '<a href="%(url)s">%(name)s</a>' % {
        'url': request.route_path('view_user', id=logged_in_user.id),
        'name': logged_in_user.name
    }

    task_parent_names = "|".join(map(lambda x: x.name, task.parents))

    task_name_as_text = "%(name)s (%(entity_type)s) - (%(parents)s)" % {
        "name": task.name,
        "entity_type": task.entity_type,
        "parents": task_parent_names
    }

    task_link_internal = \
        '<a href="%(url)s">%(name)s ' \
        '(%(task_entity_type)s) - (%(task_parent_names)s)</a>' % {
            "url": request.route_path('view_task', id=task.id),
            "name": task.name,
            "task_entity_type": task.entity_type,
            "task_parent_names": task_parent_names
        }


    summary_text = 'Revision Request: "%(name)s" (%(parent_names)s)' % {
        'name': task.name,
        'parent_names': task_parent_names
    }

    description_body = \
            '%(requester_name)s has requested a revision to ' \
            '%(task)s and expanded the timing of the task by %(timing)s ' \
            '%(unit)s. The following description is supplied for the ' \
            'revision request:%(spacing)s' \
            '%(description)s'

    unit_word = {
            'h': 'hours',
            'd': 'days',
            'w': 'weeks',
            'm': 'months',
            'y': 'years'
        }[schedule_unit]

    description_text = description_body % {
            "requester_name": logged_in_user.name,
            "task": task_name_as_text,
            "timing": schedule_timing,
            "unit": unit_word,
            "spacing": '\n\n',
            "description": description
            if description else "(No Description)"
        }

    description_html = description_body % {
            "requester_name": '<strong>%s</strong>' % logged_in_user.name,
            "task": '<strong>%s</strong>' % task_name_as_text,
            "timing": '<strong>%s' % schedule_timing,
            "unit": '%s</strong>' % unit_word,
            "spacing": '<br><br>',
            "description": description.replace('\n', '<br>')
            if description else "(No Description)"
        }

    ticket_description = description_body % {
            "requester_name": user_link_internal,
            "task": task_link_internal,
            "timing": schedule_timing,
            "unit": unit_word,
            "spacing": '\n\n',
            "description": description
            if description else "(No Description)"
        }

    revision_type = Type.query.filter_by(name='Revision').first()

    if revision_type is None:
            # create a new Type
            revision_type = Type(
                name='Revision',
                code='Revision',
                target_entity_type='Ticket'
            )

    revision_tickets = Ticket.query \
        .filter(Ticket.links.contains(task)) \
        .filter(Ticket.type == revision_type).all()


    if revision_tickets:

        note = Note(
            content=ticket_description,
            created_by=logged_in_user,
            date_created=utc_now,
            date_updated=utc_now
        )

        for hr_ticket in revision_tickets:
            hr_ticket.comments.append(note)
            hr_ticket.date_updated = utc_now
            hr_ticket.updated_by = logged_in_user
            # reopen if closed
            hr_ticket.reopen(logged_in_user)
        DBSession.add(note)
    else:

        revision_ticket = Ticket(
                project=project,
                summary=summary_text,
                description=ticket_description,
                type=revision_type,
                created_by=logged_in_user,
                date_created=utc_now,
                date_updated=utc_now
        )
        revision_ticket.reassign(logged_in_user, resource)

        # link the task to the review
        revision_ticket.links.append(task)
        DBSession.add(revision_ticket)

    transaction.commit()
    DBSession.add_all([task, logged_in_user])

    if send_email:
        # and send emails to the resources

        responsible = task.responsible
        # send email to responsible and resources of the task
        mailer = get_mailer(request)

        recipients = [logged_in_user.email]
        if responsible.email not in recipients:
            recipients.append(responsible.email)
        for resource in task.resources:
            recipients.append(resource.email)

        message = Message(
            subject=summary_text,
            sender=dummy_email_address,
            recipients=recipients,
            body=description_text,
            html=description_html
        )
        mailer.send(message)

    return HTTPOk()



@view_config(
    route_name='request_review_task_dialog',
    renderer='templates/task/dialog/request_review_task_dialog.jinja2'
)
def request_review_task_dialog(request):


    task_id = request.matchdict.get('id')
    task = Task.query.filter_by(id=task_id).first()

    action = '/tasks/%s/request_review' % task_id


    version = get_last_version_of_task(request, is_published='t')

    if version is None:
        if task.type:
            if task.type.name in ['Look Development', 'Character Design', 'Model', 'Rig', 'Previs', 'Layout', 'Lighting', 'Environment Design', 'Matte Painting', 'Animation', 'Camera', 'Simulation', 'Postvis', 'Scene Assembly', 'Comp', 'FX', 'Concept', 'Groom']:
                action = ''
            else:
                version = {
                                'date_updated': '',
                                'created_by_id': '',
                                'created_by_name': '',
                                'path':'',
                                'description':'',
                                'file_name':''
                         }
        else:
            action = ''



    came_from = request.params.get('came_from', '/')


    return {
        'came_from': came_from,
        'action': action,
        'version': version,
        'task_type':task.type.name if task.type else "No"
    }


@view_config(
    route_name='request_review',
)
def request_review(request):
    """creates a new ticket and sends an email to the responsible
    """
    # get logged in user as he review requester
    logged_in_user = get_logged_in_user(request)

    task_id = request.matchdict.get('id', -1)
    task = Task.query.filter(Task.id == task_id).first()

    note = request.params.get('note', 'No note')
    request_review_mode = request.params.get('request_review_mode', 'Progress')
    send_email = request.params.get('send_email', 1)  # for testing purposes
    utc_now = local_to_utc(datetime.datetime.now())

    if not task:
        transaction.abort()
        return Response('There is no task with id: %s' % task_id, 500)

    if task.is_container:
        transaction.abort()
        return Response('Can not request review for a container task', 500)

    # check if the task status is wip
    status_wip = Status.query.filter(Status.code == 'WIP').first()
    if task.status != status_wip:
        transaction.abort()
        return Response('You can not request a review for a task with status '
                        'is set to "%s"' % task.status.name, 500)

    # check if the user is one of the resources of this task or the responsible
    if logged_in_user not in task.resources and \
                    logged_in_user != task.responsible:
        transaction.abort()
        return Response('You are not one of the resources nor the '
                        'responsible of this task, so you can not request a '
                        'review for this task', 500)

    ticket_type_name=''

    if request_review_mode == 'Final':

        ticket_type_name ='Review'

        # set task status to Pending Review
        status_prev = Status.query.filter(Status.code == "PREV").first()
        task.status = status_prev

        # set task effort to the total_logged_seconds
        task.schedule_timing = task.total_logged_seconds / 3600
        task.schedule_unit = 'h'

        revision_type = Type.query.filter_by(name='Revision').first()

        revision_tickets = Ticket.query \
            .filter(Ticket.links.contains(task)) \
            .filter(Ticket.type == revision_type).all()


        if revision_tickets:

            for hr_ticket in revision_tickets:
                hr_ticket.date_updated = utc_now
                hr_ticket.updated_by = logged_in_user
                # reopen if closed
                hr_ticket.resolve(logged_in_user,'fixed')

    elif request_review_mode == 'Progress':
        ticket_type_name ='In Progress-Review'


    # get the project that the ticket belongs to
    project = task.project

    user_link_internal = '<a href="%(url)s">%(name)s</a>' % {
        'url': request.route_path('view_user', id=logged_in_user.id),
        'name': logged_in_user.name
    }

    task_parent_names = "|".join(map(lambda x: x.name, task.parents))

    task_name_as_text = "%(name)s (%(entity_type)s) - (%(parents)s)" % {
        "name": task.name,
        "entity_type": task.entity_type,
        "parents": task_parent_names
    }

    task_link_internal = \
        '<a href="%(url)s">%(name)s ' \
        '(%(task_entity_type)s) - (%(task_parent_names)s)</a>' % {
            "url": request.route_path('view_task', id=task.id),
            "name": task.name,
            "task_entity_type": task.entity_type,
            "task_parent_names": task_parent_names
        }

    summary_text = '%(request_review_mode)s Review Request: "%(name)s" (%(parent_names)s)' % {
        'request_review_mode':request_review_mode,
        'name': task.name,
        'parent_names': task_parent_names
    }

    description_template = \
        '%(user)s has requested you to do a %(request_review_mode)s review for %(task)s'

    description_text = description_template % {
        "request_review_mode":request_review_mode,
        "user": logged_in_user.name,
        "task": task_name_as_text
    }

    description_html = description_template % {
        "request_review_mode":request_review_mode,
        "user": '<strong>%s</strong>' % logged_in_user.name,
        "task": '<strong>%s</strong>' % task_name_as_text
    }



    responsible = task.responsible


    ticket_type = Type.query.filter_by(name=ticket_type_name).first()
    if ticket_type is None:
            # create a new Type
            ticket_type = Type(
                name=ticket_type_name,
                code=ticket_type_name,
                target_entity_type='Ticket'
            )

    tickets = Ticket.query \
        .filter(Ticket.links.contains(task)) \
        .filter(Ticket.type == ticket_type).all()
    if tickets:
        note = Note(
            content=note,
            created_by=logged_in_user,
            date_created=utc_now,
            date_updated=utc_now
        )
        for ticket in tickets:
            ticket.comments.append(note)
            ticket.date_updated = utc_now
            ticket.updated_by = logged_in_user
            # reopen if closed
            ticket.reopen(logged_in_user)
        DBSession.add(note)
    else:
        request_review_ticket = Ticket(
            project=project,
            summary=summary_text,
            description=note,
            type=ticket_type,
            created_by=logged_in_user,
            date_created=utc_now,
            date_updated=utc_now
        )
        request_review_ticket.reassign(logged_in_user, responsible)

        # link the task to the review
        request_review_ticket.links.append(task)
        DBSession.add(request_review_ticket)

    if send_email:
        # send email to responsible and resources of the task
        mailer = get_mailer(request)

        recipients = [logged_in_user.email]
        if responsible.email not in recipients:
            recipients.append(responsible.email)

        for resource in task.resources:
            recipients.append(resource.email)

        message = Message(
            subject=summary_text,
            sender=dummy_email_address,
            recipients=recipients,
            body=description_text,
            html=description_html)
        mailer.send(message)

    request.session.flash(
        'success:Your review request has been sent to %s' % responsible.name)

    return Response('Your review request has been sent to %s' %
                    responsible.name)


@view_config(
    route_name='request_extra_time',
)
def request_extra_time(request):
    """creates sends an email to the responsible about the user has requested
    extra time
    """
    # get logged in user as he review requester
    logged_in_user = get_logged_in_user(request)

    task_id = request.matchdict.get('id', -1)
    task = Task.query.filter(Task.id == task_id).first()

    send_email = request.params.get('send_email', 1)

    extra_time = request.params.get('extra_time', -1)

    if task and extra_time:
        # no extra hours for a container task
        if task.is_container:
            transaction.abort()
            return Response('Can not request extra time for a container '
                            'task', 500)

        # TODO: increase task extra time request counter

        if send_email:
            # get the project that the ticket belongs to
            summary_text = 'Extra Time Request: "%s"' % task.name
            description_text = \
                """%(user_name)s has requested %(extra_time)s extra hours for
                %(task_name)s (%(task_link)s)" """ % {
                    "user_name": logged_in_user.name,
                    "extra_time": extra_time,
                    "task_name": task.name,
                    "task_link": request.route_url('view_task', id=task.id)
                }

            description_html = \
                """%(user_name)s has requested %(extra_time)s extra hours for
                %(task_name)s (%(task_link)s)" """ % {
                    "user_name": logged_in_user.name,
                    "extra_time": extra_time,
                    "task_name": task.name,
                    "task_link": request.route_url('view_task', id=task.id)
                }

            responsible = task.responsible

            # send email to responsible and resources of the task
            mailer = get_mailer(request)

            recipients = [logged_in_user.email]
            if responsible.email not in recipients:
                recipients.append(responsible.email)
            for resource in task.resources:
                recipients.append(resource.email)

            message = Message(
                subject=summary_text,
                sender=dummy_email_address,
                recipients=recipients,
                body=description_text,
                html=description_html,
            )
            mailer.send(message)

        return Response('You have successfully requested extra time for '
                        'your task')
    transaction.abort()
    return Response('There is no task with id : %s' % task_id, 500)




@view_config(
    route_name='get_entity_versions_used_by_tasks',
    renderer='json'
)
def get_entity_versions_used_by_tasks(request):
    """returns all the Shots of the given Project
    """
    logger.debug('get_versions is running')

    entity_id = request.matchdict.get('id', -1)

    logger.debug('entity_id : %s' % entity_id)

    sql_query = """select
    "Input_Version_Task_SimpleEntities".id,
    "Input_Version_Task_SimpleEntities".name,
    "Task_Resources_SimpleEntities".id as resource_id,
    "Task_Resources_SimpleEntities".name as resource_name,
    "Input_Version_Task_Statuses_SimpleEntities".html_class as status_color
    
from "Tasks"
    join "Versions" on "Tasks".id = "Versions".task_id
join "Version_Inputs" on "Versions".id = "Version_Inputs".link_id
join "Versions" as "Input_Versions" on "Version_Inputs".version_id = "Input_Versions".id
join "Tasks" as "Input_Version_Tasks" on "Input_Versions".task_id = "Input_Version_Tasks".id
join "SimpleEntities" as "Input_Version_Task_SimpleEntities" on "Input_Version_Tasks".id = "Input_Version_Task_SimpleEntities".id
join "SimpleEntities" as "Tasks_SimpleEntities" on "Tasks_SimpleEntities".id = "Tasks".id
    join "SimpleEntities" as "Input_Version_Task_Statuses_SimpleEntities" on "Input_Version_Task_Statuses_SimpleEntities".id = "Input_Version_Tasks".status_id
join "Task_Resources"  on "Task_Resources".task_id = "Input_Version_Tasks".id
join "SimpleEntities" as "Task_Resources_SimpleEntities" on "Task_Resources_SimpleEntities".id = "Task_Resources".resource_id

where "Tasks".id = %(task_id)s
group by "Input_Version_Task_SimpleEntities".id, 
"Tasks_SimpleEntities".name,
"Task_Resources_SimpleEntities".id,
"Task_Resources_SimpleEntities".name,
"Input_Version_Task_Statuses_SimpleEntities".html_class
    
    """

    # set the content range to prevent JSONRest Store to query the data twice
    content_range = '%s-%s/%s'
    task_id = entity_id

    sql_query = sql_query % {'task_id': task_id}

    logger.debug('sql_query : %s' % sql_query)

    result = DBSession.connection().execute(sql_query)

    return_data = [
        {
            'id': r[0],
            'name': r[1],
            'resource_id': r[2],
            'resource_name': r[3],
            'status_color':r[4]
        }
        for r in result.fetchall()

    ]

    task_count = len(return_data)
    content_range = content_range % (0, task_count - 1, task_count)

    resp = Response(
        json_body=return_data
    )
    resp.content_range = content_range
    return resp




def unbind_task_hierarchy_from_tickets(task):
    """unbinds the given task and any child of it from any ticket
    """
    for child_task in task.children:
        unbind_task_hierarchy_from_tickets(child_task)
    unbind_task_from_tickets(task)


def unbind_task_from_tickets(task):
    """unbinds the given task from any tickets related to it
    """
    tickets = Ticket.query.filter(Ticket.links.contains(task)).all()
    for ticket in tickets:
        ticket.links.remove(task)


@view_config(
    route_name='delete_task_dialog',
    renderer='templates/modals/confirm_dialog.jinja2'
)
def delete_department_dialog(request):
    """deletes the department with the given id
    """
    logger.debug('delete_department_dialog is starts')

    task_id = request.matchdict.get('id')
    task = Task.query.get(task_id)

    action = '/tasks/%s/delete' % task_id

    came_from = request.params.get('came_from', '/')

    message = 'All the selected tasks and their child tasks and all the TimeLogs entered and all the Versions created for those tasks are going to be deleted.<br><br>Are you sure?'

    logger.debug('action: %s' % action)

    return {
        'message': message,
        'came_from': came_from,
        'action': action
    }


@view_config(
    route_name='delete_task',
    permission='Delete_Task'
)
def delete_task(request):
    """deletes the task with the given id
    """
    task_id = request.matchdict.get('id')
    task = Task.query.get(task_id)

    if not task:
        transaction.abort()
        return Response('Can not find a Task with id: %s' % task_id, 500)

    try:
        unbind_task_hierarchy_from_tickets(task)

        DBSession.delete(task)
        transaction.commit()
    except Exception as e:
        transaction.abort()
        c = StdErrToHTMLConverter(e)
        transaction.abort()
        return Response(c.html(), 500)

    return Response('Successfully deleted task: %s' % task_id)


def get_child_task_events(task):
    task_events = []

    if task.children:
        for child in task.children:
            task_events.extend(get_child_task_events(child))
    else:
        resources = []
        for resource in task.resources:
            resources.append({'name': resource.name, 'id': resource.id})

        # logger.debug('resources %s' % resources)
        task_events.append({
            'id': task.id,
            'entity_type': task.plural_class_name.lower(),
            # 'title': '%s (%s)' % (
            #     task.name,
            #     ' | '.join([parent.name for parent in task.parents])),
            'title': task.name,
            'start': milliseconds_since_epoch(task.start),
            'end': milliseconds_since_epoch(task.end),
            'className': 'label',
            'allDay': False,
            'status': task.status.name,
            'status_color': task.status.html_class,
            'resources': resources,
            'percent_complete': task.percent_complete,
            'total_logged_seconds': task.total_logged_seconds,
            'schedule_seconds': task.schedule_seconds
            # 'hours_to_complete': time_log.hours_to_complete,
            # 'notes': time_log.notes
        })

        for time_log in task.time_logs:
        # logger.debug('time_log.task.id : %s' % time_log.task.id)
        # assert isinstance(time_log, TimeLog)
            task_events.append({
                'id': time_log.id,
                'entity_type': time_log.plural_class_name.lower(),
                'resource_name': time_log.resource.name,
                'title': time_log.task.name,
                'start': milliseconds_since_epoch(time_log.start),
                'end': milliseconds_since_epoch(time_log.end),
                'className': 'label-success',
                'allDay': False,
                'status': time_log.task.status.name,
                'status_color': time_log.task.status.html_class
            })
            logger.debug('resource_id %s' % time_log.resource.id)
            logger.debug('resource_name %s' % time_log.resource.name)

    return task_events


@view_config(
    route_name='get_task_events',
    renderer='json'
)
def get_task_events(request):
    if not multi_permission_checker(
            request, ['Read_User', 'Read_TimeLog', 'Read_Vacation']):
        return HTTPForbidden(headers=request)

    logger.debug('get_task_events is running')

    task_id = request.matchdict.get('id', -1)
    task = Task.query.filter_by(id=task_id).first()

    logger.debug('task_id : %s' % task_id)

    events = []
    events.extend(get_child_task_events(task))
    return events


@view_config(
    route_name='get_task_dependency',
    renderer='json'
)
def get_task_dependency(request):
    if not multi_permission_checker(
            request, ['Read_User', 'Read_Task']):
        return HTTPForbidden(headers=request)

    logger.debug('get_task_dependent_of is running')

    task_id = request.matchdict.get('id', -1)
    task = Task.query.filter_by(id=task_id).first()

    type = request.matchdict.get('type', -1)

    list_of_dep_tasks_json = []
    list_of_dep_tasks = []

    if type == 'depends':
        list_of_dep_tasks = task.depends
    elif type == 'dependent_of':
        list_of_dep_tasks = task.dependent_of

    for dep_task in list_of_dep_tasks:
        resources = []

        for resource in dep_task.resources:
            resources.append({'name': resource.name, 'id': resource.id})

        list_of_dep_tasks_json.append(
            {
                'id': dep_task.id,
                'name': dep_task.name,
                'status': dep_task.status.name,
                'status_color': dep_task.status.html_class,
                'percent_complete': dep_task.percent_complete,
                'total_logged_seconds': dep_task.total_logged_seconds,
                'schedule_seconds': dep_task.schedule_seconds,
                'resources': resources
            }
        )

    return list_of_dep_tasks_json
