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
import logging
import time
import datetime
import json
import os


import transaction
from pyramid.response import Response
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPServerError, HTTPOk, HTTPForbidden
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message, Attachment

from sqlalchemy.exc import IntegrityError

from stalker.db import DBSession
from stalker import (defaults, User, Task, Entity, Project, StatusList,
                     Status, Studio, Asset, Shot, Sequence, Ticket, Type, Note,
                     Review, Version)
from stalker.exceptions import CircularDependencyError, StatusError

from stalker_pyramid.views import (PermissionChecker, get_logged_in_user,
                                   get_multi_integer, milliseconds_since_epoch,
                                   StdErrToHTMLConverter,
                                   multi_permission_checker,
                                   dummy_email_address, local_to_utc,
                                   get_path_converter)
from stalker_pyramid.views.link import (replace_img_data_with_links,
                                        MediaManager)
from stalker_pyramid.views.type import query_type


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def generate_recursive_task_query(ordered=True):
    """generates a query string that recursively gathers task information
    starting from the root tasks to the leaf tasks.
    """
    order_string = 'order by path' if ordered else ''

    query = """
    with recursive recursive_task(id, parent_id, path, path_names, responsible_id) as (
        select
            task.id,
            task.project_id,
            array[task.project_id] as path,
            ("Projects".code || '') as path_names,
            coalesce(
                (
                    select
                        array_agg(responsible_id)
                    from "Task_Responsible"
                    where "Task_Responsible".task_id = task.id
                    group by task_id
                ),
                (
                    select
                        array_agg(projects.lead_id) as responsible_id
                    from "Projects" as projects
                    where projects.id = "Projects".id
                    group by projects.id
                )
            ) as responsible_id
        from "Tasks" as task
        join "Projects" on task.project_id = "Projects".id
        where task.parent_id is NULL
    union all
        select
            task.id,
            task.parent_id,
            (parent.path || task.parent_id) as path,
            (parent.path_names || ' | ' || "Parent_SimpleEntities".name) as path_names,
            coalesce(
                (
                    select
                        array_agg(responsible_id)
                    from "Task_Responsible"
                    where "Task_Responsible".task_id = task.id
                    group by task_id
                ),
                parent.responsible_id
            ) as responsible_id
        from "Tasks" as task
        join recursive_task as parent on task.parent_id = parent.id
        join "SimpleEntities" as "Parent_SimpleEntities" on parent.id = "Parent_SimpleEntities".id
    ) select
        recursive_task.id,
        "SimpleEntities".name as name,
        recursive_task.parent_id,
        recursive_task.path,
        recursive_task.path_names,
        "SimpleEntities".name || ' (' || recursive_task.id || ') (' || recursive_task.path_names || ')' as full_path,
        "SimpleEntities".entity_type,
        recursive_task.responsible_id
    from recursive_task
    join "SimpleEntities" on recursive_task.id = "SimpleEntities".id
    %(order_string)s
    """ % {
        'order_string': order_string
    }
    return query


def get_task_full_path(task_id):
    """return full path of a task with given id
    """
    sql_query = """
        Select
            tasks.full_path as task_name
        from (
            %(generate_recursive_task_query)s
        ) as tasks
        where tasks.id = %(task_id)s
    """
    sql_query = sql_query % {
        'generate_recursive_task_query':
        generate_recursive_task_query(),
        'task_id': task_id
    }

    result = DBSession.connection().execute(sql_query).fetchone()

    return result[0]


def get_task_link_internal(request, task, task_full_path):
    """ TODO: add some doc string here
    """
    task_link_internal = \
        '<a href="%(url)s">%(name)s (%(task_entity_type)s)</a>' % {
            "url": request.route_path('view_task', id=task.id),
            "name": task_full_path,
            "task_entity_type": task.entity_type
        }
    return task_link_internal


def get_user_link_internal(request, user):
    """ TODO: add some doc string here
    """
    user_link_internal = \
        '<a href="%(url)s">%(name)s</a>' % {
            'url': request.route_path('view_user', id=user.id),
            'name': user.name
        }
    return user_link_internal


def get_description_text(description_temp,
                         user_name,
                         task_full_path,
                         note):
    """ TODO: add some doc string here
    """
    description_text = description_temp % {
        "user": user_name,
        "task_full_path": task_full_path,
        "note": note,
        "spacing": '\n\n'
    }
    return description_text


def get_description_html(description_temp,
                         user_name,
                         task_full_path,
                         note):
    """ TODO: add some doc string here
    """
    description_html = description_temp % {
        "user": '<strong>%s</strong>' % user_name,
        "task_full_path": '<strong>%s</strong>' % task_full_path,
        "note": '<br/><br/> %s ' % note.replace('\n', '<br>'),
        "spacing": '<br><br>'
    }
    return description_html


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
    route_name='fix_task_statuses'
)
def fix_task_statuses(request):
    """fixes task statuses
    """
    task_id = request.matchdict.get('id')
    task = Task.query.filter(Task.id == task_id).first()

    if task:
        assert isinstance(task, Task)
        task.update_status_with_dependent_statuses()
        task.update_status_with_children_statuses()
        task.update_schedule_info()

    request.session.flash('success: Task status is fixed!')

    return HTTPOk()


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
    new = Status.query.filter(Status.code == 'WFD').first()

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
        tags=task.tags,
        responsible=task.responsible,
        start=task.start,
        end=task.end,
        # thumbnail=task.thumbnail,
        type=task.type,
        watchers=task.watchers,
        date_created=local_to_utc(datetime.datetime.now()),
        **extra_kwargs
    )
    dup_task.generic_data = task.generic_data

    return dup_task


def walk_hierarchy(task):
    """Walks the hierarchy of the given task

    :param task: The top most task instance
    :return:
    """
    tasks_to_visit = [task]

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
    route_name='duplicate_task_hierarchy_dialog',
    renderer='templates/task/dialog/duplicate_task_hierarchy_dialog.jinja2'
)
def duplicate_task_hierarchy_dialog(request):
    """Dialog for duplicating task
    """

    logged_in_user = get_logged_in_user(request)
    came_from = request.params.get('came_from', request.url)

    entity_id = request.matchdict.get('id')
    entity = Entity.query.filter_by(id=entity_id).first()

    entity_type = entity.entity_type
    project = entity.project
    parent = entity.parent

    logger.debug('entity_id  : %s' % entity_id)
    logger.debug('entity     : %s' % entity)
    logger.debug('project    : %s' % project)
    logger.debug('parent     : %s' % parent)

    return {
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'entity': entity,
        'entity_type': entity_type,
        'project': project,
        'parent': parent,
        'came_from': came_from,
    }


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

    logger.debug('duplicate_task_hierarchy is running')

    task_id = request.matchdict.get('id')
    task = Task.query.filter_by(id=task_id).first()

    name = request.params.get('dup_task_name', task.name + ' - Duplicate')

    parent_id = request.params.get('parent_id', '-1')
    parent = Task.query.filter_by(id=parent_id).first()
    if not parent:
        parent = task.parent

    description = request.params.get('dup_task_description', '')

    if task:
        dup_task = walk_and_duplicate_task_hierarchy(task)
        update_dependencies_in_duplicated_hierarchy(task)

        cleanup_duplicate_residuals(task)
        # update the parent
        dup_task.parent = parent
        # just rename the dup_task

        dup_task.name = name
        dup_task.code = name
        dup_task.description = description

        DBSession.add(dup_task)

        #update_task_statuses_with_dependencies(dup_task)
        #leafs = find_leafs_in_hierarchy(dup_task)
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
    start = time.time()
    logger.debug('convert_to_dgrid_gantt_project_format is running')

    def has_children(proj):
        logger.debug('hasChildren is running')
        start_inner = time.time()

        sql_query = """select count(1)
        from "Tasks"
        where "Tasks".parent_id is NULL and "Tasks".project_id = %s
        """ % proj.id
        r = DBSession.connection().execute(sql_query).fetchone()[0]
        end_inner = time.time()

        logger.debug('hasChildren took: %s seconds' %
                     (end_inner - start_inner))
        return bool(r)

    return_data = [
        {
            'bid_timing': project.duration.days,
            'bid_unit': 'd',
            'completed':
            project.total_logged_seconds / project.schedule_seconds
            if project.schedule_seconds else 0,
            'description': project.description,
            'end': milliseconds_since_epoch(
                project.computed_end if project.computed_end else project.end),
            'id': project.id,
            'link': '/projects/%s/view' % project.id,
            'name': project.name,
            'hasChildren': has_children(project),
            'schedule_seconds': project.schedule_seconds,
            'start': milliseconds_since_epoch(
                project.computed_start
                if project.computed_start else project.start
            ),
            'total_logged_seconds': project.total_logged_seconds,
            'type': project.entity_type,
            'status': project.status.code.lower()
        } for project in projects
    ]
    end = time.time()
    logger.debug('convert_to_dgrid_gantt_project_format took: %s seconds' %
                 (end - start))
    return return_data


def convert_to_dgrid_gantt_task_format(tasks):
    """Converts the given tasks to the DGrid Gantt compatible json format.

    :param tasks: List of Stalker Tasks.
    :return: json compatible dictionary
    """
    # This should use pure SQL
    if not isinstance(tasks, list):
        response = HTTPServerError()
        response.text = 'This is a not a list of tasks'
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
            'responsible': [{
                'id': responsible.id,
                'name': responsible.name
            } for responsible in task.responsible],
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
            'date_created': milliseconds_since_epoch(task.date_created),
            'date_updated': milliseconds_since_epoch(task.date_updated)
        } for task in tasks
    ]


@view_config(
    route_name='update_task_schedule_timing_dialog',
    renderer='templates/task/dialog/update_task_schedule_timing_dialog.jinja2'
)
def update_task_schedule_timing_dialog(request):
    """called when creating tasks
    """
    logger.debug('update_task_schedule_timing_dialog is starts')

    task_id = request.matchdict.get('id')
    task = Task.query.get(task_id)

    return {
        'entity': task
    }


@view_config(
    route_name='update_task_schedule_timing'
)
def update_task_schedule_timing(request):
    """Inline updates the given task with the data coming from the request
    """
    logger.debug('update_task_schedule_timing IS RUNNING')

    logged_in_user = get_logged_in_user(request)
    utc_now = local_to_utc(datetime.datetime.now())

    # *************************************************************************
    # collect data
    schedule_model = request.params.get('schedule_model')
    schedule_timing = float(request.params.get('schedule_timing'))
    schedule_unit = request.params.get('schedule_unit')
    update_bid = 1 if request.params.get('update_bid') == 'on' else 0

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
        if schedule_unit not in ['min', 'h', 'd', 'w', 'm', 'y']:
            transaction.abort()
            return Response(
                "schedule_unit parameter should be one of ['min','h', 'd', "
                "'w', 'm', 'y']", 500
            )

    if not schedule_model:
        transaction.abort()
        return Response('There are missing parameters: schedule_model', 500)
    else:
        if schedule_model not in ['effort', 'duration', 'length']:
            transaction.abort()
            return Response("schedule_model parameter should be on of "
                            "['effort', 'duration', 'length']", 500)

    logger.debug('schedule_model      : %s' % schedule_model)
    logger.debug('schedule_timing     : %s' % schedule_timing)
    logger.debug('schedule_unit       : %s' % schedule_unit)
    logger.debug('update_bid          : %s' % update_bid)

    # get task
    task_id = request.matchdict.get('id', -1)
    task = Task.query.filter(Task.id == task_id).first()

    # update the task
    if not task:
        transaction.abort()
        return Response("No task found with id : %s" % task_id, 500)

    if task.status.code in ['CMPL', 'PREV', 'WIP', 'HREV', 'DREV']:
        transaction.abort()
        return Response(
            "You can not update %s status task" % task.status.name, 500
        )

    task.schedule_model = schedule_model
    task.schedule_unit = schedule_unit
    task.schedule_timing = schedule_timing

    task.updated_by = logged_in_user
    task.date_updated = utc_now

    if update_bid:
        logger.debug('updating bid')
        task.bid_timing = task.schedule_timing
        task.bid_unit = task.schedule_unit

    return Response('Task updated successfully')


@view_config(
    route_name='update_task_dependencies_dialog',
    renderer='templates/task/dialog/update_task_dependencies_dialog.jinja2'
)
def update_task_dependencies_dialog(request):
    """called when creating tasks
    """
    logger.debug('update_task_dependencies_dialog is starts')

    task_id = request.matchdict.get('id')
    task = Task.query.get(task_id)

    return {
        'entity': task
    }


@view_config(
    route_name='update_task_dependencies'
)
def update_task_dependencies(request):
    """Inline updates the given task with the data coming from the request
    """

    logger.debug('update_task_dependencies IS RUNNING')

    logged_in_user = get_logged_in_user(request)
    utc_now = local_to_utc(datetime.datetime.now())

    depend_ids = get_multi_integer(request, 'dependent_ids')
    depends = Task.query.filter(Task.id.in_(depend_ids)).all()

    # get task
    task_id = request.matchdict.get('id', -1)
    task = Task.query.filter(Task.id == task_id).first()

    # update the task
    if not task:
        transaction.abort()
        return Response("No task found with id : %s" % task_id, 500)

    if task.status.code in ['CMPL', 'PREV', 'WIP', 'HREV', 'DREV']:
        transaction.abort()
        return Response(
            "You can not update %s status task" % task.status.name, 500
        )

    try:
        task.depends = depends
    except CircularDependencyError:
        transaction.abort()
        message = \
            '</div>Parent item can not also be a dependent for the ' \
            'updated item:<br><br>Parent: %s<br>Depends To: %s</div>' % (
                task.parent.name, map(lambda x: x.name, depends)
            )
        transaction.abort()
        return Response(message, 500)

    task.updated_by = logged_in_user
    task.date_updated = utc_now

    return Response('Task updated successfully')


@view_config(
    route_name='inline_update_task'
)
def inline_update_task(request):
    """Inline updates the given task with the data coming from the request
    """

    logger.debug('INLINE UPDATE TASK IS RUNNING')

    logged_in_user = get_logged_in_user(request)

    # *************************************************************************
    # collect data
    attr_name = request.params.get('attr_name', None)
    attr_value = request.params.get('attr_value', None)

    logger.debug('attr_name %s', attr_name)
    logger.debug('attr_value %s', attr_value)

    # get task
    task_id = request.matchdict.get('id', -1)
    task = Task.query.filter(Task.id == task_id).first()

    # update the task
    if not task:
        transaction.abort()
        return Response("No task found with id : %s" % task_id, 500)

    if attr_name and attr_value:

        logger.debug('attr_name %s', attr_name)

        if attr_name == 'type':

            type_query = Type.query.filter_by(
                target_entity_type=task.entity_type
            )
            type_ = type_query.filter_by(id=attr_value).first()

            if not type_:
                transaction.abort()
                return Response("No type found with id : %s" % attr_value, 500)

            task.type = type_

        elif attr_name == 'description':

            # convert images to Links
            attachments = []
            description, links = replace_img_data_with_links(attr_value)

            task.description = description

            if links:
                # update created_by attributes of links
                for link in links:
                    link.created_by = logged_in_user

                    # manage attachments
                    link_full_path = \
                        MediaManager.convert_file_link_to_full_path(
                            link.full_path
                        )

                    link_data = open(link_full_path, "rb").read()

                    link_extension = os.path.splitext(link.filename)[1].lower()
                    mime_type = ''
                    if link_extension in ['.jpeg', '.jpg']:
                        mime_type = 'image/jpg'
                    elif link_extension in ['.png']:
                        mime_type = 'image/png'

                    attachment = Attachment(
                        link.filename,
                        mime_type,
                        link_data
                    )
                    attachments.append(attachment)
                DBSession.add_all(links)
        else:
            setattr(task, attr_name, attr_value)

        task.updated_by = logged_in_user
        utc_now = local_to_utc(datetime.datetime.now())
        task.date_updated = utc_now

    else:
        logger.debug('not updating')
        return Response("MISSING PARAMETERS", 500)

    return Response(
        'Task updated successfully %s %s' % (attr_name, attr_value)
    )


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
    schedule_model = request.params.get('schedule_model')
    schedule_timing = float(request.params.get('schedule_timing'))
    schedule_unit = request.params.get('schedule_unit')
    update_bid = 1 if request.params.get('update_bid') == 'on' else 0

    depend_ids = get_multi_integer(request, 'dependent_ids[]')
    depends = Task.query.filter(Task.id.in_(depend_ids)).all()

    resource_ids = get_multi_integer(request, 'resource_ids[]')
    resources = User.query.filter(User.id.in_(resource_ids)).all()

    responsible_ids = get_multi_integer(request, 'responsible_ids[]')
    responsible = User.query.filter(User.id.in_(responsible_ids)).all()

    priority = int(request.params.get('priority', 500))

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

    logger.debug('shot_sequence_id    : %s' % shot_sequence_id)
    logger.debug('cut_in              : %s' % cut_in)
    logger.debug('cut_out             : %s' % cut_out)

    # before doing anything check permission
    if not p_checker('Update_' + entity_type):
        transaction.abort()
        return Response(
            'You do not have enough permission to update a %s' %
            entity_type, 500
        )

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
    updated_parent = False
    try:
        task.parent = parent
    except CircularDependencyError as e:
        transaction.abort()
        message = StdErrToHTMLConverter(e)
        return Response(message.html(), 500)

    if prev_parent != parent:
        updated_parent = True

    if task.status.code in ['RTS', 'WFD']:
        try:
            task.depends = depends
        except CircularDependencyError:
            transaction.abort()
            message = \
                '</div>Parent item can not also be a dependent for the ' \
                'updated item:<br><br>Parent: %s<br>Depends To: %s</div>' % (
                    parent.name, map(lambda x: x.name, depends)
                )
            transaction.abort()
            return Response(message, 500)
    logger.debug('task in DBSession: %s' % (task in DBSession))

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
                task.responsible = []
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
        logger.debug('entity_type is Shot')
        task.sequences = [
            Sequence.query.filter_by(id=shot_sequence_id).first()
        ]
        task.cut_in = cut_in
        task.cut_out = cut_out

    task._reschedule(task.schedule_timing, task.schedule_unit)
    if update_bid:
        logger.debug('updating bid')
        task.bid_timing = task.schedule_timing
        task.bid_unit = task.schedule_unit
    else:
        logger.debug('not updating bid')

    if updated_parent:
        # update parent statuses
        if prev_parent:
            prev_parent.update_status_with_children_statuses()

        if task.parent:
            task.parent.update_status_with_children_statuses()

    task.date_updated = local_to_utc(datetime.datetime.now())

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
    if raw_data is not None and len(raw_data) > 7:  # in which case it is not '{"(,)"}'
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


def generate_where_clause(params):
    """Generates where clause strings from the given dictionary

    :param dict params: A dictionary of search strings where the keys are
      the field name and the values are the desired values. So a dictionary
      like this::

        params = {
            'id': [23],
            'name': ['Lighting'],
            'entity_type': ['Task'],
            'task_type': ['Lighting'],
            'resource': ['Ozgur']
        }

      will result a search string like::

        where (
            tasks.id = 23
            or tasks.name ilike '%Lighting%'
            or tasks.full_path ilike '%Lighting%'
            or tasks.entity_type ilike '%Task%'
            or task_types.name ilike '%Lighting%'
            or exists (
                select * from (
                    select unnest(resource_info.resource_name)
                ) x(resource_name)
                where x.resource_name like '%Ozgur%'
            )
        )

      It will use only the available keys, so giving a dictionary like::

        params = {
            'id': 23,
            'resource': 'Ozgur'
        }

      will result::

        where (
            tasks.id = 23
            or exists (
                select * from (
                    select unnest(resource_info.resource_name)
                ) x(resource_name)
                where x.resource_name like '%Ozgur%'
            )
        )
    """

    where_string = ''
    where_string_buffer = []

    for id_ in params.get('id[]', params.get('id', [])):
        where_string_buffer.append(
            'tasks.id = {id}'.format(id=id_)
        )

    for parent_id in params.get('parent_id[]',
                                params.get('parent_id', [])):
        where_string_buffer.append(
            "tasks.parent_id = {parent_id}".format(parent_id=parent_id)
        )

    for name in params.get('name[]', params.get('name', [])):
        where_string_buffer.append(
            "tasks.name ilike '%{name}%' ".format(name=name)
        )

    for name in params.get('path[]', params.get('path', [])):
        where_string_buffer.append(
            "tasks.full_path ilike '%{name}%'".format(name=name)
        )

    for entity_type in params.get('entity_type[]',
                                  params.get('entity_type', [])):
        where_string_buffer.append(
            "tasks.entity_type = '{entity_type}'".format(
                entity_type=entity_type
            )
        )

    for task_type in params.get('task_type[]',
                                params.get('task_type', [])):
        where_string_buffer.append(
            "task_types.name ilike '%{task_type}%'".format(task_type=task_type)
        )

    for project_id in params.get('project_id[]',
                                 params.get('project_id', [])):
        where_string_buffer.append(
            """"Tasks".project_id = {project_id}""".format(
                project_id=project_id
            )
        )

    for resource_id in params.get('resource_id[]',
                                  params.get('resource_id', [])):
        where_string_buffer.append(
            """exists (
        select * from (
            select unnest(resource_info.resource_id)
        ) x(resource_id)
        where x.resource_id = {resource_id}
    )""".format(resource_id=resource_id))

    for resource_name in \
        params.get('resource_name[]',
                   params.get('resource_name', [])):
        where_string_buffer.append(
            """exists (
        select * from (
            select unnest(resource_info.resource_name)
        ) x(resource_name)
        where x.resource_name like '%{resource_name}%'
    )""".format(resource_name=resource_name))

    for responsible_id in params.get('responsible_id[]',
                                     params.get('responsible_id', [])):
        where_string_buffer.append(
            """{responsible_id} = any (tasks.responsible_id)""".format(
                responsible_id=responsible_id
            )
        )

    for resource_name in \
        params.get('resource_name[]',
                   params.get('resource_name', [])):
        where_string_buffer.append(
            """exists (
        select * from (
            select unnest(resource_info.resource_name)
        ) x(resource_name)
        where x.resource_name like '%{resource_name}%'
    )""".format(resource_name=resource_name))

    for status in params.get('status[]', params.get('status', [])):
        where_string_buffer.append(
            """"Statuses".code ilike '%{status}%'""".format(status=status)
        )

    if 'leaf_only' in params:
        where_string_buffer.append(
            """not exists (
        select 1 from "Tasks"
        where "Tasks".parent_id = tasks.id
    )""")

    if 'has_resource' in params:
        where_string_buffer.append(
            "resource_info.info is not NULL"
        )

    if 'has_no_resource' in params:
        where_string_buffer.append(
            "resource_info.info is NULL"
        )

    if len(where_string_buffer):
        # need to indent the first element by hand
        where_string_buffer[0] = '{indent}%s' % where_string_buffer[0]
        where_string = \
            'where (\n%s\n)' % '\n{indent}and '.join(where_string_buffer)
        where_string = where_string.format(indent=' ' * 4)

    return where_string


def generate_order_by_clause(params):
    """Generates order_by clause strings from the given list.

    :param list params: A list of column names to sort the result to::

        params = [
            'id', 'name', 'full_path', 'parent_id',
            'resource', 'status', 'project_id',
            'task_type', 'entity_type', 'percent_complete'
        ]

      will result a search string like::

        order by
            tasks.id, tasks.name, tasks.full_path,
            tasks.parent_id, , resource_info.info,
            "Statuses".code, "Tasks".project_id, task_types.name,
            tasks.entity_type
    """

    order_by_string = ''
    order_by_string_buffer = []

    column_dict = {
        'id': 'tasks.id',
        'parent_id': "tasks.parent_id",
        'name': "tasks.name",
        'path': "tasks.full_path",
        'full_path': "tasks.full_path",
        'entity_type': "tasks.entity_type",
        'task_type': "task_types.name",
        'project_id': '"Tasks".project_id',
        'date_created': 'date_created',
        'date_updated': 'date_updated',
        'has_children': 'has_children',
        'link': 'link',
        'priority': 'priority',
        'depends_to': 'dep_info',
        'resource': "resource_info.info",
        'responsible': 'responsible_id',
        'bid_timing': '"Tasks".bid_timing',
        'bid_unit': '"Tasks".bid_unit',
        'schedule_timing': '"Tasks".schedule_timing',
        'schedule_unit': '"Tasks".schedule_unit',
        'schedule_model': '"Tasks".schedule_model',
        'schedule_seconds': 'schedule_seconds',
        'total_logged_seconds': 'total_logged_seconds',
        'percent_complete': 'percent_complete',
        'start': 'start',
        'end': '"end"',
        'status': '"Statuses".code',
    }
    for column_name in params:
        order_by_string_buffer.append(column_dict[column_name])

    if len(order_by_string_buffer):
        # need to indent the first element by hand
        order_by_string = 'order by %s' % ', '.join(order_by_string_buffer)

    return order_by_string


@view_config(
    route_name='get_tasks',
    renderer='json'
)
def get_tasks(request):
    """RESTful version of getting all tasks
    """
    logger.debug('get_tasks is running')
    start = time.time()

    # set the content range to prevent JSONRest Store to query the data twice
    content_range = '%s-%s/%s'

    entity_type = "Task"
    task_id = -1
    if 'id' in request.params:
        # check if this is a Task or Project
        task_id = int(request.params.get('id', -1))

        # get the entity_type of this data
        entity_type = DBSession.connection().execute(
            """select entity_type from "SimpleEntities" where id=%s""" %
            task_id
        ).fetchone()[0]

    logger.debug('entity_type: %s' % entity_type)

    order_by_params = request.GET.getall('order_by')
    logger.debug('order_by_params: %s' % order_by_params)

    order_by = generate_order_by_clause(order_by_params)
    if order_by == '':
        # use default
        order_by = 'order by tasks.name'

    if entity_type not in ['Project', 'Studio']:
        where_condition = generate_where_clause(request.params.dict_of_lists())

        logger.debug('where_condition: %s' % where_condition)

        sql_query = """
        select
            tasks.id,
            tasks.entity_type,
            task_types.name as task_type,
            tasks.name,
            tasks.full_path,
            "Tasks".project_id,
            "Tasks".parent_id,
            "Task_SimpleEntities".description,

            -- audit info
            (extract(epoch from "Task_SimpleEntities".date_created::timestamp at time zone 'UTC') * 1000)::bigint as date_created,
            (extract(epoch from "Task_SimpleEntities".date_updated::timestamp at time zone 'UTC') * 1000)::bigint as date_updated,

            exists (
                select 1
                from "Tasks" as "Child_Tasks"
                where "Child_Tasks".parent_id = "Tasks".id
            ) as has_children,

            '/' || lower("Task_SimpleEntities".entity_type) || 's/' || "Tasks".id || '/view' as link,

            "Tasks".priority as priority,

            dep_info.info as dep_info,
            resource_info.info as resource_info,
            tasks.responsible_id,

            "Tasks".bid_timing,
            "Tasks".bid_unit,

            "Tasks".schedule_timing,
            "Tasks".schedule_unit,
            "Tasks".schedule_model,
            coalesce("Tasks".schedule_seconds,
                "Tasks".schedule_timing * (case "Tasks".schedule_unit
                    when 'min' then 60
                    when 'h' then 3600
                    when 'd' then 32400
                    when 'w' then 147600
                    when 'm' then 590400
                    when 'y' then 7696277
                    else 0
                end)
            ) as schedule_seconds,

            coalesce(
                -- for parent tasks
                "Tasks".total_logged_seconds,
                -- for child tasks we need to count the total seconds of related TimeLogs
                coalesce("Task_TimeLogs".duration, 0.0)
            ) as total_logged_seconds,

            coalesce(
                -- for parent tasks
                (case "Tasks".schedule_seconds
                    when 0 then 0
                    else "Tasks".total_logged_seconds::float / "Tasks".schedule_seconds * 100
                 end
                ),
                -- for child tasks we need to count the total seconds of related TimeLogs
                (coalesce("Task_TimeLogs".duration, 0.0))::float /
                    ("Tasks".schedule_timing * (case "Tasks".schedule_unit
                        when 'min' then 60
                        when 'h' then 3600
                        when 'd' then 32400
                        when 'w' then 147600
                        when 'm' then 590400
                        when 'y' then 7696277
                        else 0
                    end)) * 100.0
            ) as percent_complete,

            (extract(epoch from coalesce("Tasks".computed_start::timestamp AT TIME ZONE 'UTC', "Tasks".end::timestamp AT TIME ZONE 'UTC')) * 1000)::bigint as "start",
            (extract(epoch from coalesce("Tasks".computed_end::timestamp AT TIME ZONE 'UTC', "Tasks".end::timestamp AT TIME ZONE 'UTC')) * 1000)::bigint as "end",

            lower("Statuses".code) as status

        from (
            %(tasks_hierarchical_name)s
        ) as tasks
        join "Tasks" on tasks.id = "Tasks".id
        join "SimpleEntities" as "Task_SimpleEntities" on tasks.id = "Task_SimpleEntities".id
        -- Dependencies
        left outer join (
            select
                task_id,
                array_agg((depends_to_id, "SimpleEntities".name)) as info
            from "Task_Dependencies"
            join "SimpleEntities" on "Task_Dependencies".depends_to_id = "SimpleEntities".id
            group by task_id
        ) as dep_info on tasks.id = dep_info.task_id
        -- Resources
        left outer join (
            select
                "Tasks".id as task_id,
                array_agg(("Resource_SimpleEntities".id, "Resource_SimpleEntities".name)) as info,
                array_agg("Resource_SimpleEntities".id) as resource_id,
                array_agg("Resource_SimpleEntities".name) as resource_name
            from "Tasks"
            join "Task_Resources" on "Tasks".id = "Task_Resources".task_id
            join "SimpleEntities" as "Resource_SimpleEntities" on "Task_Resources".resource_id = "Resource_SimpleEntities".id
            group by "Tasks".id
        ) as resource_info on "Tasks".id = resource_info.task_id

        -- TimeLogs for Leaf Tasks
        left outer join (
            select
                "TimeLogs".task_id,
                extract(epoch from sum("TimeLogs".end::timestamp AT TIME ZONE 'UTC' - "TimeLogs".start::timestamp AT TIME ZONE 'UTC')) as duration
            from "TimeLogs"
            group by task_id
        ) as "Task_TimeLogs" on "Task_TimeLogs".task_id = tasks.id

        -- Task Status
        join "Statuses" on "Tasks".status_id = "Statuses".id

        -- Task Type
        left join (
            select
                "Tasks".id,
                "Type_SimpleEntities".name
            from "Tasks"
            join "SimpleEntities" as "Task_SimpleEntities" on "Tasks".id = "Task_SimpleEntities".id
            join "Types" on "Task_SimpleEntities".type_id = "Types".id
            join "SimpleEntities" as "Type_SimpleEntities" on "Types".id = "Type_SimpleEntities".id
        ) as task_types on tasks.id = task_types.id

        %(where_condition)s

        %(order_by)s
        """

        sql_query = sql_query % {
            'where_condition': where_condition,
            'order_by': order_by,
            'tasks_hierarchical_name':
            generate_recursive_task_query(ordered=False)
        }

    else:
        sql_query = """
        -- Projects Part
        select
            "Projects".id as id,
            'Project' as entity_type,
            '' as task_type,
            "Project_SimpleEntities".name as name,
            "Project_SimpleEntities".name as full_path,
            NULL,
            NULL as parent_id,
            "Project_SimpleEntities".description,

            -- audit info
            (extract(epoch from "Project_SimpleEntities".date_created::timestamp at time zone 'UTC') * 1000)::bigint as date_created,
            (extract(epoch from "Project_SimpleEntities".date_updated::timestamp at time zone 'UTC') * 1000)::bigint as date_updated,

            exists (
                select 1
                from "Tasks" as "Child_Tasks"
                where "Child_Tasks".project_id = "Projects".id
            ) as has_children,

            '/projects/' || "Projects".id || '/view' as link,

            500,

            NULL,--array_agg((NULL, NULL)),
            NULL,--array_agg((NULL, NULL)),
            NULL,--array_agg((NULL, NULL)),

            0 as bid_timing,
            'min' as bid_unit,

            0 as schedule_timing,
            'min' as schedule_unit,
            'effort' as schedule_model,
            total_schedule_seconds as schedule_seconds,

            project_schedule_info.total_logged_seconds as total_logged_seconds,

            project_schedule_info.total_logged_seconds / total_schedule_seconds  * 100 as percent_complete,

            (extract(epoch from coalesce("Projects".computed_start::timestamp AT TIME ZONE 'UTC', "Projects".end::timestamp AT TIME ZONE 'UTC')) * 1000)::bigint as "start",
            (extract(epoch from coalesce("Projects".computed_end::timestamp AT TIME ZONE 'UTC', "Projects".end::timestamp AT TIME ZONE 'UTC')) * 1000)::bigint as "end",

            lower("Statuses".code) as status

        from "Projects"
        join "SimpleEntities" as "Project_SimpleEntities" on "Projects".id = "Project_SimpleEntities".id
        join "Statuses" on "Projects".status_id = "Statuses".id
        join (
            select
                "Tasks".project_id as project_id,
                sum(coalesce("Tasks".total_logged_seconds, coalesce("Task_TimeLogs".duration, 0.0))::float) as total_logged_seconds, 
                sum(coalesce(
                    "Tasks".schedule_seconds,
                    (
                        "Tasks".schedule_timing * (
                            case "Tasks".schedule_unit
                                when 'min' then 60
                                when 'h' then 3600
                                when 'd' then 32400
                                when 'w' then 147600
                                when 'm' then 590400
                                when 'y' then 7696277
                                else 0
                            end
                        )
                    )
                )) as total_schedule_seconds
            from "Tasks"
            -- TimeLogs for Leaf Tasks
            left outer join (
                select
                    "TimeLogs".task_id,
                    extract(epoch from sum("TimeLogs".end::timestamp AT TIME ZONE 'UTC' - "TimeLogs".start::timestamp AT TIME ZONE 'UTC')) as duration
                from "TimeLogs"
                group by task_id
            ) as "Task_TimeLogs" on "Task_TimeLogs".task_id = "Tasks".id

            where "Tasks".parent_id is NULL
            group by "Tasks".project_id
        ) as project_schedule_info on "Projects".id = project_schedule_info.project_id
        """

        if entity_type == 'Project':
            sql_query = '%s %s' % (
                sql_query,
                'where "Projects".id = %s' % task_id
            )

    from sqlalchemy import text  # to be able to use "%" sign use this function
    result = DBSession.connection().execute(text(sql_query))

    # use local functions to speed things up
    local_raw_data_to_array = raw_data_to_array
    return_data = [
        {
            'id': r[0],
            'entity_type': r[1],
            'task_type': r[2],
            'name': r[3],
            'full_path': r[4],
            'project_id': r[5],
            'parent_id': r[6],
            'description': r[7],
            'date_created': r[8],
            'date_updated': r[9],
            'hasChildren': r[10],
            'link': r[11],
            'priority': r[12],
            'dependencies': local_raw_data_to_array(r[13]),
            'resources': local_raw_data_to_array(r[14]),
            'responsible': r[15],
            'bid_timing': r[16],
            'bid_unit': r[17],
            'schedule_timing': r[18],
            'schedule_unit': r[19],
            'schedule_model': r[20],
            'schedule_seconds': r[21],
            'total_logged_seconds': r[22],
            'completed': r[23],
            'start': r[24],
            'end': r[25],
            'status': r[26],
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

                parents_children = []
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
    logger.debug('get_user_tasks starts')

    # get all the tasks related in the given project
    user_id = request.matchdict.get('id', -1)

    sql_query = """select
        "Tasks".id  as task_id,
        "ParentTasks".full_path as task_name
    from "Tasks"
        join "Task_Resources" on "Task_Resources".task_id = "Tasks".id
        join "Statuses" as "Task_Statuses" on "Task_Statuses".id = "Tasks".status_id
        left join (
            %(generate_recursive_task_query)s
        ) as "ParentTasks" on "Tasks".id = "ParentTasks".id
        %(where_condition)s
    """

    where_condition = 'where "Task_Resources".resource_id = %s' % user_id

    statuses = []
    status_codes = request.GET.getall('status')
    if status_codes:
        statuses = Status.query.filter(Status.code.in_(status_codes)).all()

    if statuses:
        temp_buffer = [where_condition, """ and ("""]
        for i, status in enumerate(statuses):
            if i > 0:
                temp_buffer.append(' or')
            temp_buffer.append(""" "Task_Statuses".code='%s'""" % status.code)
        temp_buffer.append(' )')
        where_condition = ''.join(temp_buffer)

    logger.debug('where_condition: %s' % where_condition)

    sql_query = sql_query % {
        'generate_recursive_task_query':
        generate_recursive_task_query(),
        'where_condition': where_condition
    }

    result = DBSession.connection().execute(sql_query)

    return_data = [
        {
            'id': r[0],
            'name': r[1]
        }
        for r in result.fetchall()
    ]

    resp = Response(
        json_body=return_data
    )
    # resp.content_range = content_range
    return resp


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
    is_leaf = request.params.get('leaf', 0)

    if is_leaf:
        sql_query = """select
            count(1)
        from "Tasks"
        where not exists (
            select 1 from "Tasks" as "All_Tasks"
            where "All_Tasks".parent_id = "Tasks".id
            ) and "Tasks".project_id = %s
        """ % project_id
    else:
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
            "Task_SimpleEntities".name || ' (' || "Task_SimpleEntities".id || ') (' || "Projects".code || ')' as parent_names
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

    logger.debug('get_entity_tasks_stats is starts')

    sql_query = """
        select
            count("Tasks".id) as count,
            "Statuses".id as status_id,
            "Statuses".code as status_code,
            "Statuses_SimpleEntities".name as status_name,
            "Statuses_SimpleEntities".html_class as status_color

        from "Statuses"
            join "Tasks" on "Statuses".id = "Tasks".status_id
            join "SimpleEntities" as "Statuses_SimpleEntities" on "Statuses_SimpleEntities".id = "Statuses".id

        %(where_condition_for_entity)s

        and not (
            exists (
                select 1
                from (
                    select "Tasks".parent_id from "Tasks"
                ) AS all_tasks
                where all_tasks.parent_id = "Tasks".id
            )
        )

        group by
           "Statuses".code,
           "Statuses".id,
           "Statuses_SimpleEntities".name,
           "Statuses_SimpleEntities".html_class
    """
    where_condition_for_entity = ''

    if isinstance(entity, User):
        where_condition_for_entity = \
            'join "Task_Resources" on "Task_Resources".task_id = "Tasks".id ' \
            'where "Task_Resources".resource_id =%s' % entity_id
    elif isinstance(entity, Project):
        where_condition_for_entity = 'where "Tasks".project_id =%s' % entity_id

    sql_query = sql_query % {
        'where_condition_for_entity': where_condition_for_entity
    }

    # convert to dgrid format right here in place
    result = DBSession.connection().execute(sql_query)

    return_data = [
        {
            'tasks_count': r[0],
            'status_id': r[1],
            'status_code': r[2],
            'status_name': r[3],
            'status_color': r[4],
            'status_icon':''
        }
        for r in result.fetchall()
    ]

    resp = Response(
        json_body=return_data
    )
    # resp.content_range = content_range
    return resp


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

    logger.debug('entity_id: %s' % entity_id)

    filter_id = request.matchdict.get('f_id', -1)
    filter_ = Entity.query.filter_by(id=filter_id).first()

    sql_query = """select
    "Task_Resources".task_id as task_id,
    "ParentTasks".full_path as task_name,
    array_agg("Responsible_SimpleEntities".id) as responsible_id,
    array_agg("Responsible_SimpleEntities".name) as responsible_name,
    coalesce("Type_SimpleEntities".name,'') as type_name,
    (coalesce("Task_TimeLogs".duration, 0.0))::float /
            ("Tasks".schedule_timing * (case "Tasks".schedule_unit
                when 'min' then 60
                when 'h' then 3600
                when 'd' then 32400
                when 'w' then 147600
                when 'm' then 590400
                when 'y' then 7696277
                else 0
            end)
            ) * 100.0
    as percent_complete,
    array_agg("Resource_SimpleEntities".id) as resource_id,
    array_agg("Resource_SimpleEntities".name) as resource_name,
    "Statuses_SimpleEntities".name as status_name,
    "Statuses".code,
    "Statuses_SimpleEntities".html_class as status_color,
    "Project_SimpleEntities".id as project_id,
    "Project_SimpleEntities".name as project_name,
    array_agg("Reviewers".reviewer_id) as reviewer_id,
    ((("Tasks".schedule_timing * (case "Tasks".schedule_unit
                when 'min' then 60
                when 'h' then 3600
                when 'd' then 32400
                when 'w' then 147600
                when 'm' then 590400
                when 'y' then 7696277
                else 0
            end))-coalesce("Task_TimeLogs".duration, 0.0))/3600

    ) as hour_to_complete,
    coalesce("Tasks".computed_start,"Tasks".start) as start_date,
    "Tasks".priority as priority,
    ((("Tasks".bid_timing * (case "Tasks".bid_unit
                when 'min' then 60
                when 'h' then 3600
                when 'd' then 32400
                when 'w' then 147600
                when 'm' then 590400
                when 'y' then 7696277
                else 0
            end))-coalesce("Task_TimeLogs".duration, 0.0))/3600

    ) as hour_based_on_bid


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
    join "SimpleEntities" as "Tasks_SimpleEntities" on "Tasks_SimpleEntities".id = "Task_Resources".task_id

    join "SimpleEntities" as "Resource_SimpleEntities" on "Resource_SimpleEntities".id = "Task_Resources".resource_id
    join ((
        -- get tasks responsible from parents
        -- so find all the tasks that doesn't have a responsible but one of their parents has
        with recursive go_to_parent(id, parent_id) as (
                select task.id, task.parent_id
                from "Tasks" as task
                left outer join "Task_Responsible" on task.id = "Task_Responsible".task_id
                where "Task_Responsible".responsible_id is NULL
            union all
                select g.id, task.parent_id
                from go_to_parent as g
                join "Tasks" as task on g.parent_id = task.id
                join "Task_Responsible" on task.id = "Task_Responsible".task_id
                where task.parent_id is not NULL and "Task_Responsible".responsible_id is NULL
        )
    select
        g.id,
        "Task_Responsible".responsible_id
    from go_to_parent as g
    join "Tasks" as parent_task on g.parent_id = parent_task.id
    join "Task_Responsible" on parent_task.id = "Task_Responsible".task_id
    where "Task_Responsible".responsible_id is not NULL
    order by g.id
    )
    union
    (
        -- select all the tasks that has a responsible
        select
            id,
            responsible_id
        from "Tasks"
        join "Task_Responsible" on "Tasks".id = "Task_Responsible".task_id
        where "Task_Responsible".responsible_id is not NULL
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
                        left outer join "Task_Responsible" on task.id = "Task_Responsible".task_id
                        where "Task_Responsible".responsible_id is NULL
                    union all
                        select g.id, task.parent_id
                        from go_to_parent as g
                        join "Tasks" as task on g.parent_id = task.id
                        join "Task_Responsible" on task.id = "Task_Responsible".task_id
                        where task.parent_id is not NULL and "Task_Responsible".responsible_id is NULL
                )
                select
                    g.id
                from go_to_parent as g
                join "Tasks" as parent_task on g.parent_id = parent_task.id
                join "Task_Responsible" on parent_task.id = "Task_Responsible".task_id
                where "Task_Responsible".responsible_id is not NULL
                order by g.id
            )
            union
            (
                -- select all the tasks that has a responsible
                select
                    id
                from "Tasks"
                join "Task_Responsible" on "Tasks".id = "Task_Responsible".task_id
                where responsible_id is not NULL
            )
        ) as prev_query on "Tasks".id = prev_query.id
        where prev_query.id is NULL
    )) as "Tasks_Responsible" on "Tasks_Responsible".id = "Tasks".id
    left join "SimpleEntities" as "Responsible_SimpleEntities" on "Responsible_SimpleEntities".id = "Tasks_Responsible".responsible_id
    left join "SimpleEntities" as "Type_SimpleEntities" on "Tasks_SimpleEntities".type_id = "Type_SimpleEntities".id
    left join (
        %(generate_recursive_task_query)s
    ) as "ParentTasks" on "Tasks".id = "ParentTasks".id

    left outer join (
        select
            "Reviews_Tasks".id as task_id,
            "Reviews".reviewer_id as reviewer_id

            from "Reviews"
            join "Tasks" as "Reviews_Tasks" on "Reviews_Tasks".id = "Reviews".task_id
            join "Statuses" as "Reviews_Statuses" on "Reviews_Statuses".id = "Reviews".status_id

            where "Reviews_Statuses".code = 'NEW') as "Reviewers" on "Reviewers".task_id = "Tasks".id

    where %(where_condition_for_entity)s %(where_condition_for_filter)s

    group by
        "Task_Resources".task_id,
        "ParentTasks".full_path,
        percent_complete,
        "Statuses_SimpleEntities".name,
        "Statuses".code,
        "Statuses_SimpleEntities".html_class,
        "Project_SimpleEntities".id,
        "Project_SimpleEntities".name,
        start_date,
        hour_based_on_bid,
        hour_to_complete,
        type_name,
        priority
    """
    where_condition_for_entity = ''

    if isinstance(entity, User):
        where_condition_for_entity = \
            '"Task_Resources".resource_id = %s' % entity_id
    elif isinstance(entity, Project):
        where_condition_for_entity = '"Tasks".project_id =%s' % entity_id

    where_condition_for_filter = ''

    if isinstance(filter_, User):
        where_condition_for_entity = ''
        where_condition_for_filter = \
            '"Tasks_Responsible".responsible_id = %s' % filter_id
    elif isinstance(filter_, Status):
        where_condition_for_filter = \
            'and "Statuses_SimpleEntities".id = %s' % filter_id

    sql_query = sql_query % {
        'generate_recursive_task_query':
        generate_recursive_task_query(),
        'where_condition_for_entity': where_condition_for_entity,
        'where_condition_for_filter': where_condition_for_filter
    }

    # convert to dgrid format right here in place
    result = DBSession.connection().execute(sql_query)

    return_data = [
        {
            'id': r[0],
            'name': r[1],
            'responsible_id': r[2],
            'responsible_name': r[3],
            'type': r[4],
            'percent_complete': r[5],
            'resource_id': r[6],
            'resource_name': r[7],
            'status': r[8],
            'status_code': r[9],
            'status_color': r[10],
            'project_id': r[11],
            'project_name': r[12],
            'request_review': '1' if (logged_in_user.id in r[6] or r[2] == logged_in_user.id) and r[9] == 'WIP' else None,
            'review': '1' if logged_in_user.id in r[13] and r[9] == 'PREV' else None,
            'hour_to_complete':r[14],
            'hour_based_on_bid':r[17],
            'start_date':milliseconds_since_epoch(r[15]),
            'priority':r[16]
        }
        for r in result.fetchall()
    ]

    #task_count = len(return_data)
    # content_range = content_range % (0, task_count - 1, task_count)

    # logger.debug('return_data: %s' % return_data)
    #end = time.time()

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

    project = None
    parent = None
    depends_to = None

    logger.debug('mode    : %s' % mode)
    if mode == 'create':
        project_id = request.params.get('project_id')
        project = Project.query.filter_by(id=project_id).first()

        logger.debug('project_id    : %s' % project_id)

        parent_id = request.params.get('parent_id')
        parent = Task.query.filter_by(id=parent_id).first()

        logger.debug('parent_id    : %s' % parent_id)

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

    schedule_model = request.params.get('schedule_model')
    schedule_timing = float(request.params.get('schedule_timing'))
    schedule_unit = request.params.get('schedule_unit')

    # get the resources
    resources = []
    resource_ids = []
    if 'resource_ids[]' in request.params:
        resource_ids = get_multi_integer(request, 'resource_ids[]')
        resources = User.query.filter(User.id.in_(resource_ids)).all()

    # get responsible

    responsible = []
    responsible_ids = []
    if 'responsible_ids[]' in request.params:
        responsible_ids = get_multi_integer(request, 'responsible_ids[]')
        responsible = User.query.filter(User.id.in_(responsible_ids)).all()

    priority = int(request.params.get('priority', 500))

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

        def get_param(p):
            if p in request.params:
                logger.debug('%s: %s' % (p, request.params[p]))
            else:
                logger.debug('%s not in params' % p)

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
    depends_to_ids = get_multi_integer(request, 'dependent_ids[]')

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
    # status_wfd = Status.query.filter_by(code='WFD').first()
    status_rts = Status.query.filter_by(code='RTS').first()
    # status_cmpl = Status.query.filter_by(code='CMPL').first()
    status = status_rts

    #if depends:
    #    for dependent_task in depends:
    #        if dependent_task.status != status_cmpl:
    #            # TODO: use update_task_statuses_with_dependencies()
    #            status = status_wfd

    logger.debug('status: %s' % status)

    if not schedule_timing:
        return Response('schedule_timing can not be 0', 500)

    kwargs['name'] = name
    kwargs['code'] = code
    kwargs['description'] = description
    kwargs['created_by'] = logged_in_user
    kwargs['date_created'] = local_to_utc(datetime.datetime.now())

    kwargs['status_list'] = status_list

    kwargs['schedule_model'] = schedule_model
    kwargs['schedule_timing'] = schedule_timing
    kwargs['schedule_unit'] = schedule_unit

    kwargs['responsible'] = responsible
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
        kwargs['sequences'] = [sequence]
        kwargs['cut_in'] = int(cut_in or 1)
        kwargs['cut_out'] = int(cut_out or 1)

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

        # if responsible:
        #     # check if the responsible is different than
        #     # the parents responsible
        #     if new_entity.responsible != responsible:
        #         new_entity.responsible = responsible

    except (AttributeError, TypeError, CircularDependencyError) as e:
        logger.debug('The Error Message: %s' % e)
        response = Response('%s' % e, 500)
        transaction.abort()
        return response
    else:
        DBSession.add(new_entity)
        try:
            transaction.commit()
        except IntegrityError as e:
            logger.debug(str(e))
            transaction.abort()
            return Response(str(e), 500)
        else:
            logger.debug('flushing the DBSession, no problem here!')
            DBSession.flush()
            logger.debug('finished adding Task')

    return Response('Task created successfully')


def get_last_version_of_task(request, is_published=''):
    """finds last published version of task
    """
    version = None

    task_id = request.matchdict.get('id')
    task = Task.query.filter_by(id=task_id).first()

    sql_query = """
       select
           "Versions".id as version_id,
           "Version_SimpleEntities".date_updated as date_updated

       from "Versions"
           join "Tasks" as "Version_Tasks" on "Version_Tasks".id = "Versions".task_id
           join "SimpleEntities" as "Version_SimpleEntities" on "Version_SimpleEntities".id = "Versions".id

       where "Version_Tasks".id = %(task_id)s and "Versions".take_name = 'Main' %(is_published_condition)s

       order by date_updated desc
       limit 1
       """

    is_published_condition = ''

    if is_published != '':
        is_published_condition = \
            """ and "Versions".is_published = '%s'""" % is_published

    logger.debug('%s' % is_published_condition)

    sql_query = sql_query % {
        'task_id': task_id,
        'is_published_condition': is_published_condition
    }

    result = DBSession.connection().execute(sql_query).fetchone()
    version = None
    if result:
        version = Version.query.filter(Version.id == result[0]).first()

    return version


@view_config(
    route_name='cleanup_task_new_reviews_dialog',
    renderer='templates/modals/confirm_dialog.jinja2'
)
def cleanup_task_new_reviews_dialog(request):
    """works when task has at least one answered review
    """
    logger.debug('cleanup_task_new_reviews_dialog is starts')

    task_id = request.matchdict.get('id')

    action = '/tasks/%s/cleanup_new_reviews' % task_id
    came_from = request.params.get('came_from', '/')

    message = 'All unanswered reviews will be deleted and review set will ' \
              'be finalized.<br><br>Are you sure?'

    logger.debug('action: %s' % action)

    return {
        'message': message,
        'came_from': came_from,
        'action': action
    }


def get_answered_reviews(task, review_set_number):
    """deletes reviews object which status is NEW
    """
    logger.debug('get_answered_reviews starts')
    reviews = task.review_set(review_set_number)

    answered_reviews = []

    for review in reviews:
        status_new = Status.query.filter_by(code='NEW').first()
        if review.status is not status_new:
            answered_reviews.append(review)

    logger.debug('get_answered_reviews ends')

    return answered_reviews


@view_config(
    route_name='cleanup_task_new_reviews'
)
def cleanup_task_new_reviews(request):

    """works when task has at least one answered review
    """
    logger.debug('cleanup_task_new_reviews is starts')

    logged_in_user = get_logged_in_user(request)

    utc_now = local_to_utc(datetime.datetime.now())

    task_id = request.matchdict.get('id')
    task = Task.query.filter(Task.id == task_id).first()

    if not task:
        transaction.abort()
        return Response('There is no task with id: %s' % task_id, 500)

    status_prev = Status.query.filter(Status.code == 'PREV').first()

    if task.status is not status_prev:
        transaction.abort()
        return Response('Task status is not pending review', 500)

    answered_reviews = get_answered_reviews(task, task.review_number + 1)
    if len(answered_reviews) == 0:
        transaction.abort()
        return Response(
            "There is no answered review. You have to make a review. Ask "
            "admin if you don't see farce review button", 500
        )

    cleanup_unanswered_reviews(task, task.review_number + 1)

    answered_reviews = get_answered_reviews(task, task.review_number + 1)

    a_review = answered_reviews[0]
    try:
        a_review.finalize_review_set()
    except Exception as e:
        transaction.abort()
        c = StdErrToHTMLConverter(e)
        transaction.abort()
        return Response(c.html(), 500)

    note_type = query_type('Note', 'Cleanup Reviews')
    note_type.html_class = 'red'
    note_type.code = 'cleanedup_reviews'

    note = Note(
        content='%s has cleaned all unanswered reviews' % logged_in_user.name,
        created_by=logged_in_user,
        date_created=utc_now,
        date_updated=utc_now,
        type=note_type
    )
    DBSession.add(note)

    task.notes.append(note)

    task.updated_by = logged_in_user
    task.date_updated = utc_now

    request.session.flash('success:Unanswered reviews are cleaned!')
    return Response('Successfully Unanswered reviews are cleaned!')


@view_config(
    route_name='review_sequence_dialog',
    renderer='templates/task/dialog/review_task_dialog.jinja2'
)
@view_config(
    route_name='review_asset_dialog',
    renderer='templates/task/dialog/review_task_dialog.jinja2'
)
@view_config(
    route_name='review_shot_dialog',
    renderer='templates/task/dialog/review_task_dialog.jinja2'
)
@view_config(
    route_name='review_task_dialog',
    renderer='templates/task/dialog/review_task_dialog.jinja2'
)
def review_task_dialog(request):
    """called when reviewing tasks
    """
    entity_id = request.matchdict.get('id')
    entity = Entity.query.filter_by(id=entity_id).first()

    logged_in_user = get_logged_in_user(request)

    came_from = request.params.get('came_from', request.url)
    review_mode = request.params.get('review_mode', 'approve')
    forced = request.params.get('forced', None)

    version = get_last_version_of_task(request, is_published='')

    status_new = Status.query.filter_by(code='NEW').first()
    review = Review.query\
        .filter(Review.reviewer_id == logged_in_user.id)\
        .filter(Review.task_id == entity.id)\
        .filter(Review.status == status_new)\
        .first()

    if forced:
        review = Review.query\
            .filter(Review.task_id == entity.id)\
            .filter(Review.status == status_new)\
            .first()

    review_description = 'No Comment'

    if review:
        review_description = review.description

    project = entity.project
    version_path = ''
    if version:
        path_converter = get_path_converter(request, entity)
        version_path = path_converter(version.absolute_full_path)

    return {
        'review_description': review_description,
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'task': entity,
        'project': project,
        'came_from': came_from,
        'version': version,
        'version_path': version_path,
        'review_mode': review_mode,
        'forced': forced
    }


@view_config(
    route_name='review_task'
)
def review_task(request):
    """review task
    """
    # get logged in user as he review requester
    task_id = request.matchdict.get('id')
    task = Task.query.filter(Task.id == task_id).first()

    if not task:
        transaction.abort()
        return Response('There is no task with id: %s' % task_id, 500)

    review_mode = request.params.get('review')

    if not review_mode:
        transaction.abort()
        return Response('No revision is specified', 500)

    if review_mode == 'Approve':
        return approve_task(request)
    elif review_mode == 'Request Revision':
        return request_revision(request)


def cleanup_unanswered_reviews(task, review_set_number):
    """deletes reviews object which status is NEW
    """
    logger.debug('cleanup_unanswered_reviews starts')
    reviews = task.review_set(review_set_number)

    for review in reviews:
        status_new = Status.query.filter_by(code='NEW').first()
        if review.status == status_new:

            try:
                review.task = None
                DBSession.delete(review)
            except Exception as e:
                transaction.abort()
                c = StdErrToHTMLConverter(e)
                transaction.abort()
                return Response(c.html(), 500)

    logger.debug('cleanup_unanswered_reviews ends')


def forced_review(reviewer, task):
    """deletes all new reviews and creates a review with approved status
    """
    logger.debug('forced_review starts')

    cleanup_unanswered_reviews(task, task.review_number + 1)
    review = Review(reviewer=reviewer, task=task)

    return review


@view_config(
    route_name='approve_task'
)
def approve_task(request):
    """ TODO: add doc string
    """
    logged_in_user = get_logged_in_user(request)

    task_id = request.matchdict.get('id', -1)
    task = Task.query.filter(Task.id == task_id).first()

    if not task:
        transaction.abort()
        return Response('There is no task with id: %s' % task_id, 500)

    send_email = request.params.get('send_email', 1)  # for testing purposes
    description = request.params.get('description', 1)
    forced = request.params.get('forced', None)

    logger.debug('forced: %s' % forced)

    utc_now = local_to_utc(datetime.datetime.now())

    note_type = query_type('Note', 'Approved')
    note_type.html_class = 'green'
    note_type.code = 'approved'

    note = Note(
        content=description,
        created_by=logged_in_user,
        date_created=utc_now,
        date_updated=utc_now,
        type=note_type
    )
    DBSession.add(note)

    if forced:
        has_permission = PermissionChecker(request)
        if has_permission('Create_Review'):
            review = forced_review(logged_in_user, task)
            review.date_created = utc_now
        else:
            return Response('You dont have permission', 500)
    else:

        status_new = Status.query.filter_by(code='NEW').first()

        review = Review.query\
            .filter(Review.reviewer_id == logged_in_user.id)\
            .filter(Review.task_id == task.id)\
            .filter(Review.status == status_new)\
            .first()

    logger.debug('review %s' % review)

    if not review:
        transaction.abort()
        return Response('There is no review', 500)

    try:
        review.approve()

        review.description = \
            '%(resource_note)s <br/> <b>%(reviewer_name)s</b>: ' \
            '%(reviewer_note)s' % {
                'resource_note': review.description,
                'reviewer_name': logged_in_user.name,
                'reviewer_note': note.content
            }

        review.date_updated = utc_now

        task.notes.append(note)
    except StatusError as e:
        return Response('StatusError: %s' % e, 500)

    task.updated_by = logged_in_user
    task.date_updated = utc_now

    if send_email:
         # send email to resources of the task

        mailer = get_mailer(request)

        recipients = []
        for resource in task.resources:
            recipients.append(resource.email)

        for responsible in task.responsible:
            recipients.append(responsible.email)

        task_full_path = get_task_full_path(task.id)

        description_temp = \
            '%(user)s has approved ' \
            '%(task_full_path)s with the following ' \
            'comment:%(spacing)s' \
            '%(note)s'

        message = Message(
            subject='Task Reviewed: "%(task_full_path)s" has been '
                    'approved by %(user)s!' %
            {
                'task_full_path': task_full_path,
                'user': logged_in_user
            },
            sender=dummy_email_address,
            recipients=recipients,
            body=get_description_text(
                description_temp,
                logged_in_user.name,
                task_full_path,
                note.content if note.content else '-- no notes --'
            ),
            html=get_description_html(
                description_temp,
                logged_in_user.name,
                task_full_path,
                note.content if note.content else '-- no notes --'
            )
        )

        try:
            mailer.send_to_queue(message)
        except ValueError:  # no internet connection
            pass

    request.session.flash('success:Approved task')
    return Response('Successfully approved task')


@view_config(
    route_name='request_revision'
)
def request_revision(request):
    """updates task timing and status and sends an email to the task resources
    """
    logged_in_user = get_logged_in_user(request)

    task_id = request.matchdict.get('id', -1)
    task = Task.query.filter(Task.id == task_id).first()

    if not task:
        transaction.abort()
        return Response('There is no task with id: %s' % task_id, 500)

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
        if schedule_unit not in ['min', 'h', 'd', 'w', 'm', 'y']:
            transaction.abort()
            return Response(
                "schedule_unit parameter should be one of ['min','h', 'd', "
                "'w', 'm', 'y']", 500
            )

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

    send_email = request.params.get('send_email', 1)  # for testing purposes
    description = request.params.get('description', 1)
    forced = request.params.get('forced', None)

    utc_now = local_to_utc(datetime.datetime.now())

    unit_word = {
        'h': 'hours',
        'd': 'days',
        'w': 'weeks',
        'm': 'months',
        'y': 'years'
    }[schedule_unit]

    note_type = query_type('Note', 'Request Revision')
    note_type.html_class = 'purple'
    note_type.code = 'requested_revision'

    note = Note(
        content='Expanded the timing of the task by <b>'
                '%(schedule_timing)s %(schedule_unit)s</b>.<br/>'
                '%(description)s' % {
                    'schedule_timing': schedule_timing,
                    'schedule_unit': schedule_unit,
                    'description': description
                },
        created_by=logged_in_user,
        date_created=utc_now,
        date_updated=utc_now,
        type=note_type
    )
    DBSession.add(note)

    if forced:
        has_permission = PermissionChecker(request)
        if has_permission('Create_Review') \
           or logged_in_user in task.responsible:
           # review = forced_review(logged_in_user, task);
           # review.date_created = utc_now

            task.request_revision(
                logged_in_user,
                note.content,
                schedule_timing,
                schedule_unit
            )
        else:
            return Response("You don't have permission", 500)
    else:

        status_new = Status.query.filter_by(code='NEW').first()

        review = Review.query\
            .filter(Review.reviewer_id == logged_in_user.id)\
            .filter(Review.task_id == task.id)\
            .filter(Review.status == status_new)\
            .first()

        logger.debug('review %s' % review)

        if not review:
            transaction.abort()
            return Response('There is no review', 500)

        try:
            review.request_revision(
                schedule_timing,
                schedule_unit,
                '%(resource_note)s <br/> <b>%(reviewer_name)s</b>: '
                '%(reviewer_note)s' % {
                    'resource_note': review.description,
                    'reviewer_name': logged_in_user.name,
                    'reviewer_note': note.content
                }
            )
            review.date_updated = utc_now

        except StatusError as e:
                return Response('StatusError: %s' % e, 500)

    task.notes.append(note)
    task.updated_by = logged_in_user
    task.date_updated = utc_now

    if send_email:
        # and send emails to the resources

        # send email to responsible and resources of the task
        mailer = get_mailer(request)

        recipients = []
        for responsible in task.responsible:
            recipients.append(responsible.email)

        for resource in task.resources:
            recipients.append(resource.email)

        task_full_path = get_task_full_path(task.id)

        description_temp = \
            '%(user)s has requested a revision to ' \
            '%(task_full_path)s' \
            '. The following description is supplied for the ' \
            'revision request:%(spacing)s' \
            '%(note)s'

        message = Message(
            subject='Task Reviewed: "%(task_full_path)s" has been '
                    'requested revision by %(user)s!' % {
                        'task_full_path': task_full_path,
                        'user': logged_in_user
                    },
            sender=dummy_email_address,
            recipients=recipients,
            body=get_description_text(
                description_temp,
                logged_in_user.name,
                task_full_path,
                note.content if note.content else '-- no notes --'
            ),
            html=get_description_html(
                description_temp,
                logged_in_user.name,
                task_full_path,
                note.content if note.content else '-- no notes --'
            )
        )

        # try:
        mailer.send_to_queue(message)
        # except ValueError:  # no internet connection
        #     pass

    request.session.flash('success:Requested revision for the task')
    return Response('Successfully requested revision for the task')


@view_config(
    route_name='request_review_task_dialog',
    renderer='templates/task/dialog/request_review_task_dialog.jinja2'
)
def request_review_task_dialog(request):
    """ TODO: add doc string
    """
    logger.debug('request_review_task_dialog starts')

    task_id = request.matchdict.get('id')
    task = Task.query.filter_by(id=task_id).first()

    action = '/tasks/%s/request_review' % task_id

    request_review_mode = request.params.get('request_review_mode', 'Progress')

    selected_responsible_id = \
        request.params.get('selected_responsible_id', '-1')
    selected_responsible = \
        User.query.filter_by(id=selected_responsible_id).first()

    version_path = ''
    version = None

    if request_review_mode == 'Progress':
        version = get_last_version_of_task(request, is_published='')
    else:
        version = get_last_version_of_task(request, is_published='t')

    if not version:
        if task.type:
            # TODO: Add this to the config file
            forced_publish_types = [
                'Look Development', 'Character Design', 'Model', 'Rig',
                'Previs', 'Layout', 'Lighting', 'Environment Design',
                'Matte Painting', 'Animation','Animation Bible',  'Camera', 'Simulation',
                'Postvis', 'Scene Assembly', 'Schematic', 'Comp', 'FX', 'Sketch',
                'Color Sketch', 'Groom'
            ]
            if task.type.name in forced_publish_types:
                action = ''
        else:
            action = ''
    else:
        path_converter = get_path_converter(request, task)
        version_path = path_converter(version.absolute_full_path)

    came_from = request.params.get('came_from', '/')


    return {
        'request_review_mode': request_review_mode,
        'came_from': came_from,
        'action': action,
        'version': version,
        'version_path': version_path,
        'task': task,
        'selected_responsible': selected_responsible,
        'task_type': task.type.name if task.type else "No"
    }


@view_config(
    route_name='request_review',
)
def request_review(request):
    """creates a new ticket and sends an email to the responsible
    """
    logger.debug('request_review method starts')
    # get logged in user as he review requester
    logged_in_user = get_logged_in_user(request)

    task_id = request.matchdict.get('id', -1)
    task = Task.query.filter(Task.id == task_id).first()

    request_review_mode = request.params.get('request_review_mode', 'Progress')

    if not task:
        transaction.abort()
        return Response('There is no task with id: %s' % task_id, 500)

    # check if the user is one of the resources of this task or the responsible
    if logged_in_user not in task.resources and \
       logged_in_user not in task.responsible:
        transaction.abort()
        return Response('You are not one of the resources nor the '
                        'responsible of this task, so you can not request a '
                        'review for this task', 500)

    if request_review_mode == 'Final':
        return request_final_review(request)
    elif request_review_mode == 'Progress':
        return request_progress_review(request)


def request_progress_review(request):
    """runs when resource request final review"""

    logger.debug('request_progress_review starts')

    selected_responsible_ids = \
        get_multi_integer(request, 'selected_responsible_ids')
    selected_responsible_list = \
        User.query.filter(User.id.in_(selected_responsible_ids)).all()

    if not selected_responsible_list:
        transaction.abort()
        return Response('You did not select any responsible', 500)

    logged_in_user = get_logged_in_user(request)

    task_id = request.matchdict.get('id', -1)
    task = Task.query.filter(Task.id == task_id).first()

    note = request.params.get('note', 'No note')

    utc_now = local_to_utc(datetime.datetime.now())

    # Create ticket_type if it does not exist
    ticket_type_name = 'In Progress-Review'
    ticket_type = query_type('Ticket', ticket_type_name)

    recipients = []

    # Create tickets for selected responsible
    user_link_internal = get_user_link_internal(request, logged_in_user)
    task_full_path = get_task_full_path(task.id)
    task_link_internal = get_task_link_internal(request, task,
                                                task_full_path)

    for responsible in selected_responsible_list:
        logger.debug('responsible: %s' % responsible)
        recipients.append(responsible.email)

        request_review_ticket = Ticket(
            project=task.project,
            summary='In Progress Review Request: %s' % task_full_path,
            description='%(sender)s has requested you to do <b>a progress '
                        'review</b> for %(task)s' % {
                            'sender': user_link_internal,
                            'task': task_link_internal
                        },
            type=ticket_type,
            created_by=logged_in_user,
            date_created=utc_now,
            date_updated=utc_now
        )

        request_review_ticket.reassign(logged_in_user, responsible)

        # link the task to the review
        request_review_ticket.links.append(task)
        DBSession.add(request_review_ticket)

        note_type = query_type('Note', 'Ticket Comment')
        note_type.html_class = 'pink'
        note_type.code = 'ticket_comment'

        ticket_comment = Note(
            content=note,
            created_by=logged_in_user,
            date_created=utc_now,
            date_updated=utc_now,
            type=note_type
        )

        DBSession.add(ticket_comment)

        request_review_ticket.comments.append(ticket_comment)
        task.notes.append(ticket_comment)
        task.updated_by = logged_in_user
        task.date_updated = utc_now

    # Send mail to
    send_email = request.params.get('send_email', 1)  # for testing purposes

    if send_email:
        recipients.append(logged_in_user.email)
        # recipients.extend(task.responsible)

        description_temp = \
            '%(user)s has requested you to do a progress review for ' \
            '%(task_full_path)s with the following note:' \
            '%(spacing)s%(note)s '

        mailer = get_mailer(request)

        message = Message(
            subject='Review Request: "%(task_full_path)s)' % {
                'task_full_path': task_full_path
            },
            sender=dummy_email_address,
            recipients=recipients,
            body=get_description_text(
                description_temp,
                logged_in_user.name,
                task_full_path,
                note if note else '-- no notes --'
            ),
            html=get_description_html(
                description_temp,
                logged_in_user.name,
                task_full_path,
                note if note else '-- no notes --'
            )
        )

        logger.debug('mailer send')
        mailer.send_to_queue(message)

    logger.debug(
        'success:Your progress review request has been sent to responsible'
    )

    request.session.flash(
        'success:Your progress review request has been sent to responsible'
    )

    return Response(
        'Your progress review request has been sent to responsible'
    )


def request_final_review(request):
    """runs when resource request final review
    """

    logger.debug('request_final_review starts')

    logged_in_user = get_logged_in_user(request)

    task_id = request.matchdict.get('id', -1)
    task = Task.query.filter(Task.id == task_id).first()

    note_str = request.params.get('note', 'No note')
    send_email = request.params.get('send_email', 1)  # for testing purposes

    utc_now = local_to_utc(datetime.datetime.now())

    note_type = query_type('Note', 'Request Review')
    note_type.html_class = 'orange'
    note_type.code = 'requested_review'

    note = Note(
        content=note_str,
        created_by=logged_in_user,
        date_created=utc_now,
        date_updated=utc_now,
        type=note_type
    )

    task.notes.append(note)
    reviews = task.request_review()
    for review in reviews:
        review.created_by = logged_in_user
        review.date_created = utc_now
        review.date_updated = utc_now
        review.description = "<br/><b>%(resource_name)s :<b> %(note)s" % {
            'resource_name': logged_in_user.name,
            'note': note.content
        }

    if send_email:
        #*******************************************************************
        # info message for responsible
        recipients = []

        for responsible in task.responsible:
            recipients.append(responsible.email)

        task_full_path = get_task_full_path(task.id)
        description_temp = \
            '%(user)s has requested you to do a final review for ' \
            '%(task_full_path)s with the following note:%(note)s'

        mailer = get_mailer(request)

        message = Message(
            subject='Review Request: "%(task_full_path)s)' % {
                'task_full_path': task_full_path
            },
            sender=dummy_email_address,
            recipients=recipients,
            body=get_description_text(
                description_temp,
                logged_in_user.name,
                task_full_path,
                note.content if note.content else '-- no notes --'
            ),
            html=get_description_html(
                description_temp,
                logged_in_user.name,
                task_full_path,
                note.content if note.content else '-- no notes --'
            )
        )

        try:
            mailer.send_to_queue(message)
        except ValueError:
            pass

        #*******************************************************************
        # info message for resources and logged in user
        recipients = [logged_in_user.email]
        for resource in task.resources:
            recipients.append(resource.email)

        description_temp = \
            'Your final review request from %(responsible)s for ' \
            '%(task_full_path)s with the following note has been ' \
            'sent:%(note)s'

        mailer = get_mailer(request)

        responsible_names = ', '.join(map(lambda x: x.name, task.responsible))
        responsible_names_html = ', '.join(
            map(lambda x: '<strong>%s</strong>' % x.name, task.responsible)
        )
        message = Message(
            subject='Review Request: "%(task_full_path)s)' % {
                'task_full_path': task_full_path
            },
            sender=dummy_email_address,
            recipients=recipients,
            body=description_temp % {
                "user": logged_in_user.name,
                'responsible': responsible_names,
                "task_full_path": task_full_path,
                "note": note.content,
                "spacing": '\n\n'
            },
            html=description_temp % {
                "user": '<strong>%s</strong>' % logged_in_user.name,
                'responsible': responsible_names_html,
                "task_full_path": '<strong>%s</strong>' %
                                          task_full_path,
                "note": '<br/><br/> %s ' % note.content,
                "spacing": '<br><br>'
            }
        )

        try:
            mailer.send_to_queue(message)
        except ValueError:
            pass

    logger.debug(
        'success:Your final review request has been sent to responsible'
    )

    request.session.flash(
        'success:Your final review request has been sent to responsible'
    )

    return Response('Your final review request has been sent to responsible')


@view_config(
    route_name='request_extra_time_dialog',
    renderer='templates/task/dialog/request_extra_time_dialog.jinja2'
)
def request_extra_time_dialog(request):
    """ TODO: add doc string
    """
    logger.debug('request_extra_time_dialog starts')

    task_id = request.matchdict.get('id')
    task = Task.query.filter_by(id=task_id).first()

    action = '/tasks/%s/request_extra_time' % task_id

    came_from = request.params.get('came_from', '/')

    return {
        'came_from': came_from,
        'action': action,
        'task': task
    }


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

    if not task:
        transaction.abort()
        return Response('There is no task with id: %s' % task_id, 500)

    if task.is_container:
            transaction.abort()
            return Response('Can not request extra time for a container '
                            'task', 500)

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

    send_email = request.params.get('send_email', 1)  # for testing purposes
    description = request.params.get('description', 'No comments')

    utc_now = local_to_utc(datetime.datetime.now())

    note_type = query_type('Note', 'Request Extra Time')
    note_type.html_class = 'red2'
    note_type.code = 'requested_extra_time'

    note = Note(
        content='<i class="icon-heart"></i> Requesting extra time <b>'
                '%(schedule_timing)s %(schedule_unit)s</b>.<br/>'
                '%(description)s' % {
                    'schedule_timing': schedule_timing,
                    'schedule_unit': schedule_unit,
                    'description': description
                },
        created_by=logged_in_user,
        date_created=utc_now,
        date_updated=utc_now,
        type=note_type
    )
    DBSession.add(note)

    task.notes.append(note)

    reviews = task.request_review()
    for review in reviews:
        review.created_by = logged_in_user
        review.date_created = utc_now
        review.date_updated = utc_now
        review.description = "<b>%(resource_name)s</b>: %(note)s " % {
            'resource_name': logged_in_user.name,
            'note': note.content
        }

    if send_email:
        #*******************************************************************
        # info message for responsible
        recipients = []

        for responsible in task.responsible:
            recipients.append(responsible.email)

        task_full_path = get_task_full_path(task.id)

        description_temp = \
            '%(user)s has requested extra time for ' \
            '%(task_full_path)s with the following note:%(note)s'

        mailer = get_mailer(request)

        message = Message(
            subject='Extra Time Request: "%(task_full_path)s)' % {
                'task_full_path': task_full_path
            },
            sender=dummy_email_address,
            recipients=recipients,
            body=get_description_text(
                description_temp,
                logged_in_user.name,
                task_full_path,
                note.content if note.content else '-- no notes --'
            ),
            html=get_description_html(
                description_temp,
                logged_in_user.name,
                task_full_path,
                note.content if note.content else '-- no notes --'
            )
        )

        try:
            mailer.send_to_queue(message)
        except ValueError:
            pass

    logger.debug(
        'success:Your extra time request has been sent to responsible'
    )

    request.session.flash(
        'success:Your extra time request has been sent to responsible'
    )

    return Response('Your extra time request has been sent to responsible')


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


def unbind_task_hierarchy_relations(task):
    """unbinds the given task and any child of it from any ticket
    """
    # TODO: the following is a recursive call to this function which is bound
    #       to raise a RuntimeError with the increasing number of task
    #       hierarchy.
    for child_task in task.children:
        unbind_task_hierarchy_relations(child_task)
    unbind_task_relations(task)


def unbind_task_relations(task):
    """unbinds the given task from any tickets related to it
    """
    tickets = Ticket.query.filter(Ticket.links.contains(task)).all()
    for ticket in tickets:
        ticket.links.remove(task)

    from stalker import Version
    with DBSession.no_autoflush:
        task.references = []
        for v in task.versions:
            v.inputs = []
            for tv in Version.query.filter(Version.inputs.contains(v)):
                tv.inputs.remove(v)


@view_config(
    route_name='delete_task_dialog',
    renderer='templates/modals/confirm_dialog.jinja2'
)
def delete_task_dialog(request):
    """deletes the department with the given id
    """
    logger.debug('delete_department_dialog is starts')

    task_id = request.matchdict.get('id')
    #task = Task.query.get(task_id)

    action = '/tasks/%s/delete' % task_id
    came_from = request.params.get('came_from', '/')
    message = 'All the selected tasks and their child tasks and all the ' \
              'TimeLogs entered and all the Versions created for those ' \
              'tasks are going to be deleted.<br><br>Are you sure?'

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
        unbind_task_hierarchy_relations(task)
        unbind_task_relations(task)

        DBSession.delete(task)
        #transaction.commit()
        logger.debug(
            'Successfully deleted task: %s (%s)' % (task.name, task_id)
        )
    except Exception as e:
        transaction.abort()
        c = StdErrToHTMLConverter(e)
        transaction.abort()
        return Response(c.html(), 500)

    return Response('Successfully deleted task: %s' % task_id)




@view_config(
    route_name='get_task_related_entities',
    renderer='json'
)
def get_task_related_entity(request):

    task_id = request.matchdict.get('id')
    task = Task.query.get(task_id)

    entity_type = request.matchdict.get('e_type')

    if not task:
        transaction.abort()
        return Response('Can not find a Task with id: %s' % task_id, 500)


    task_related_assets = []
    task_related_assets.extend(get_task_related_entities(task, entity_type))
    return task_related_assets


def get_task_related_entities(task, entity_type):

    task_related_assets = []
    if task.children:
        for child in task.children:
            task_related_assets.extend(get_task_related_entities(child, entity_type))
    else:
        for dep_task in task.depends:
            asset = get_task_parent(dep_task, entity_type)
            if asset:
                if asset not in task_related_assets:
                    task_related_assets.append({
                                'id': asset.id,
                                'name': asset.name,
                                'thumbnail_full_path': asset.thumbnail.full_path if asset.thumbnail else None
                                })

    return task_related_assets

def get_task_parent(task, entity_type):
    if task.parent:
        if task.parent.entity_type == entity_type:
            return task.parent
        else:
            get_task_parent(task.parent, entity_type)
    else:
        return task


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
            'schedule_seconds': task.schedule_seconds,
            'schedule_unit': task.schedule_unit

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
            # logger.debug('resource_id %s' % time_log.resource.id)
            # logger.debug('resource_name %s' % time_log.resource.name)

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

    type_ = request.matchdict.get('type', -1)

    list_of_dep_tasks_json = []
    list_of_dep_tasks = []

    if type_ == 'depends':
        list_of_dep_tasks = task.depends
    elif type_ == 'dependent_of':
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
                'schedule_unit': dep_task.schedule_unit,
                'resources': resources
            }
        )

    return list_of_dep_tasks_json


@view_config(
    route_name='force_task_status_dialog',
    renderer='templates/modals/confirm_dialog.jinja2'
)
def force_task_status_dialog(request):
    """deletes the department with the given id
    """
    logger.debug('delete_department_dialog is starts')

    task_id = request.matchdict.get('id')
    status_code = request.matchdict.get('status_code')

    came_from = request.params.get('came_from', '/')
    action = '/tasks/%s/force_status/%s' % (task_id, status_code)
    message = 'Task will be set as %s' \
                  '<br><br>Are you sure?' % status_code

    logger.debug('action: %s' % action)

    return {
        'message': message,
        'came_from': came_from,
        'action': action
    }


@view_config(
    route_name='force_task_status',
    permission='Create_Review'
)
def force_task_status(request):
    """Forces the task status to the status given with the status_code parameter.

    It needs task_id and status_code as a parameter in the request, with out
    them it will return a response with status_code of 500.

    It will work only for tasks with 'WIP' and 'HREV' statuses.
    """

    status_code = request.matchdict.get('status_code')
    logger.debug('status_code: %s' % status_code)
    status = Status.query.filter(Status.code == status_code).first()
    if not status:
        transaction.abort()
        return Response('Can not find a status with code: %s' % status_code, 500)

    if status.code not in ['CMPL','STOP','OH']:
        transaction.abort()
        return Response('Can not set status to: %s' % status_code, 500)

    task_id = request.matchdict.get('id')
    task = Task.query.get(task_id)

    if not task:
        transaction.abort()
        return Response('Can not find a Task with id: %s' % task_id, 500)

    if task.status.code not in ['WIP','HREV']:
        transaction.abort()
        return Response('Cannot force %s tasks' % task.status.code, 500)

    if status.code == 'STOP':
        task.stop()
    elif status.code =='OH':
        task.hold()
    elif status.code == 'CMPL':
        timing, unit = task.least_meaningful_time_unit(task.total_logged_seconds)
        task.schedule_timing = timing
        task.schedule_unit = unit
        task.status = status

        task.update_parent_statuses()
        for tdep in task.task_dependent_of:
            dep = tdep.task
            dep.update_status_with_dependent_statuses()
            if dep.status.code in ['HREV', 'PREV', 'DREV', 'OH', 'STOP']:
                # for tasks that are still be able to continue to work,
                # change the dependency_target to "onstart" to allow
                # the two of the tasks to work together and still let the
                # TJ to be able to schedule the tasks correctly
                tdep.dependency_target = 'onstart'
            # also update the status of parents of dependencies
            dep.update_parent_statuses()

    logged_in_user = get_logged_in_user(request)
    utc_now = local_to_utc(datetime.datetime.now())

    note_type = query_type('Note', 'Forced Status')
    note_type.html_class = 'red'
    note_type.code = 'forced_status'

    note = Note(
        content='%s has changed this task status to %s' % (logged_in_user.name, status.name),
        created_by=logged_in_user,
        date_created=utc_now,
        date_updated=utc_now,
        type=note_type
    )
    DBSession.add(note)

    task.notes.append(note)
    task.updated_by = logged_in_user
    task.date_updated = utc_now

    return Response('Success: %s status is set to %s' % (task.name, status.name))

@view_config(
    route_name='resume_task_dialog',
    renderer='templates/modals/confirm_dialog.jinja2'
)
def resume_task_dialog(request):
    """resume task dialog for Stopped and Holt tasks
    """
    logger.debug('delete_department_dialog is starts')

    task_id = request.matchdict.get('id')

    came_from = request.params.get('came_from', '/')
    action = '/tasks/%s/resume' % task_id
    message = 'Task will be resumed' \
                  '<br><br>Are you sure?'

    logger.debug('action: %s' % action)

    return {
        'message': message,
        'came_from': came_from,
        'action': action
    }


@view_config(
    route_name='resume_task',
    permission='Create_Review'
)
def resume_task(request):
    """resume task method for Stopped and Holt tasks
    """

    task_id = request.matchdict.get('id')
    task = Task.query.get(task_id)

    if not task:
        transaction.abort()
        return Response('Can not find a Task with id: %s' % task_id, 500)

    if task.status.code not in ['OH','STOP']:
        transaction.abort()
        return Response('Cannot resume %s tasks' % task.status.code, 500)

    task.resume()


    logged_in_user = get_logged_in_user(request)
    utc_now = local_to_utc(datetime.datetime.now())

    note_type = query_type('Note', 'Resumed')
    note_type.html_class = 'red'
    note_type.code = 'resumed'

    note = Note(
        content='%s has changed this task status to %s' % (logged_in_user.name, task.status.name),
        created_by=logged_in_user,
        date_created=utc_now,
        date_updated=utc_now,
        type=note_type
    )
    DBSession.add(note)

    task.notes.append(note)
    task.updated_by = logged_in_user
    task.date_updated = utc_now

    return Response('Success: %s is resumed' % task.name)


@view_config(
    route_name='get_task_resources',
    renderer='json'
)
def get_task_resources(request):
    """
    """

    logger.debug('***get_task_resources method starts ***')

    task_id = request.matchdict.get('id')
    task = Task.query.get(task_id)

    if not task:
        transaction.abort()
        return Response('Can not find a Task with id: %s' % task_id, 500)

    logger.debug(task.resources)

    return [
        {
            'id': resource.id,
            'name': resource.name,
            'thumbnail_full_path': resource.thumbnail.full_path if resource.thumbnail else None,
            'description': '',
            'item_view_link': '/users/%s/view' % resource.id,
            'item_remove_link':'/tasks/%s/remove/resources/%s/dialog?came_from=%s'%( task.id, resource.id, request.current_route_path())
            if PermissionChecker(request)('Update_Task') else None
        }
        for resource in task.resources
    ]



@view_config(
    route_name='remove_task_user_dialog',
    renderer='templates/modals/confirm_dialog.jinja2'
)
def remove_task_user_dialog(request):
    """deletes the department with the given id
    """
    logger.debug('remove_task_resource_dialog is starts')

    task_id = request.matchdict.get('id')
    user_id = request.matchdict.get('user_id')
    user_type = request.matchdict.get('user_type')

    task = Task.query.get(task_id)
    user = User.query.filter(User.id == user_id).first()

    came_from = request.params.get('came_from', '/')
    action = '/tasks/%s/remove/%s/%s' % (task.id, user_type, user.id)
    message = '%s will be removed from %s resources' \
                  '<br><br>Are you sure?' % (user.name, task.name)

    logger.debug('action: %s' % action)

    return {
        'message': message,
        'came_from': came_from,
        'action': action
    }

@view_config(
    route_name='remove_task_user',
    permission='Update_Task'
)
def remove_task_user(request):
    """deletes the task with the given id
    """

    user_id = request.matchdict.get('user_id')
    user = User.query.filter(User.id == user_id).first()
    user_type = request.matchdict.get('user_type')

    if not user:
        transaction.abort()
        return Response('Can not find a user with id: %s' % user_id, 500)

    task_id = request.matchdict.get('id')
    task = Task.query.get(task_id)

    if not task:
        transaction.abort()
        return Response('Can not find a Task with id: %s' % task_id, 500)

    if not user_type:
        transaction.abort()
        return Response('Missing parameters', 500)

    if user_type=='resources':
        task.resources.remove(user)
    elif user_type=='responsible':
        task.responsible.remove(user)

    logged_in_user = get_logged_in_user(request)
    utc_now = local_to_utc(datetime.datetime.now())

    task.updated_by = logged_in_user
    task.date_updated = utc_now

    return Response('Success: %s is removed from %s resources' % (user.name, task.name))

@view_config(
    route_name='change_tasks_users_dialog',
    renderer='templates/task/dialog/change_tasks_users_dialog.jinja2'
)
def change_tasks_users_dialog(request):
    """changes task users with the given users dialog
    """
    logger.debug('change_tasks_users_dialog is starts')

    selected_task_list = get_multi_integer(request, 'task_ids', 'GET')
    logger.debug('selected_task_list : %s' % selected_task_list)

    tasks = Task.query.filter(Task.id.in_(selected_task_list)).all()
    logger.debug('tasks : %s' % tasks)

    project_id = request.params.get('project_id', '-1')
    logger.debug('project_id : %s' % project_id)

    came_from = request.params.get('came_from', '/')
    user_type = request.matchdict.get('user_type')

    return {
        'tasks': tasks,
        'user_type':user_type,
        'came_from': came_from,
        'project_id':project_id
    }

@view_config(
    route_name='change_tasks_users',
    permission='Update_Task'
)
def change_tasks_users(request):
    """changes task users with the given users
    """

    selected_list = get_multi_integer(request, 'user_ids')
    users = User.query\
            .filter(User.id.in_(selected_list)).all()

    if not users:
        transaction.abort()
        return Response('Missing parameters', 500)

    selected_task_list = get_multi_integer(request, 'task_ids[]')
    logger.debug('selected_task_list : %s' % selected_task_list)

    tasks = Task.query.filter(Task.id.in_(selected_task_list)).all()
    logger.debug('tasks : %s' % tasks)

    if not tasks:
        transaction.abort()
        return Response('Can not find any Task', 500)

    user_type = request.matchdict.get('user_type')

    if not user_type:
        transaction.abort()
        return Response('Missing parameters', 500)

    if user_type=='resources':
        for task in tasks:
            task.resources = users
    elif user_type=='responsible':
        for task in tasks:
            task.responsible = users

    logged_in_user = get_logged_in_user(request)
    utc_now = local_to_utc(datetime.datetime.now())

    task.updated_by = logged_in_user
    task.date_updated = utc_now

    return Response('Success: %s are added to selected tasks' % user_type)



@view_config(
    route_name='change_task_users_dialog',
    renderer='templates/task/dialog/change_task_users_dialog.jinja2'
)
def change_task_users_dialog(request):
    """changes task users with the given users dialog
    """
    logger.debug('change_task_users_dialog is starts')

    task_id = request.matchdict.get('id')
    task = Task.query.get(task_id)

    came_from = request.params.get('came_from', '/')
    user_type = request.matchdict.get('user_type')

    return {
        'task': task,
        'user_type':user_type,
        'came_from': came_from
    }

@view_config(
    route_name='change_task_users',
    permission='Update_Task'
)
def change_task_users(request):
    """changes task users with the given users
    """

    selected_list = get_multi_integer(request, 'user_ids')
    users = User.query\
            .filter(User.id.in_(selected_list)).all()

    if not users:
        transaction.abort()
        return Response('Missing parameters', 500)

    task_id = request.matchdict.get('id')
    task = Task.query.get(task_id)

    if not task:
        transaction.abort()
        return Response('Can not find a Task with id: %s' % task_id, 500)

    user_type = request.matchdict.get('user_type')

    if not user_type:
        transaction.abort()
        return Response('Missing parameters', 500)
    # for resource in resources:
    #     if resource  not in task.resources:
    #         task.resources.append(resource)
    if user_type=='resources':
        task.resources = users
    elif user_type=='responsible':
        task.responsible = users

    logged_in_user = get_logged_in_user(request)
    utc_now = local_to_utc(datetime.datetime.now())

    task.updated_by = logged_in_user
    task.date_updated = utc_now

    return Response('Success: %s are added to %s resources' % (user_type, task.name))

