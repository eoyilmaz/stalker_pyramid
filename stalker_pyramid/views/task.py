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

import transaction

from pyramid.response import Response
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPServerError, HTTPOk

from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message

from sqlalchemy.exc import IntegrityError

from stalker.db import DBSession
from stalker import (User, Task, Entity, Project, StatusList, Status,
                     TaskJugglerScheduler, Studio, Asset, Shot, Sequence, Type, Ticket)
from stalker.models.task import CircularDependencyError
from stalker import defaults
import stalker_pyramid
from stalker_pyramid.views import (PermissionChecker, get_logged_in_user,
                                   get_multi_integer, milliseconds_since_epoch,
                                   get_date)


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# def walk_task_hierarchy(starting_task):
#     """
#     """

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
        status=task.status,
        status_list=task.status_list,
        notes=task.notes,
        tags=task.tags,
        references=task.references,
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
    start_task = task
    i = 0
    yield task
    while True:
        try:
            task = task.children[i]
            yield task
            i += 1
        except IndexError: # no more child
            if task != start_task:
                # go to parent of the current task
                parent = task.parent
                # go to the next child
                index = parent.children.index(task)
                i = index + 1
                task = parent
            else:
                break


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

    :param task: The task that wanted to be duplicated
    :return: A list of stalker.models.task.Task
    """
    task_id = request.params.get('task_id')
    task = Task.query.filter_by(id=task_id).first()
    if task:
        dup_task = walk_and_duplicate_task_hierarchy(task)
        update_dependencies_in_duplicated_hierarchy(task)
        cleanup_duplicate_residuals(task)
        # update the parent
        dup_task.parent = task.parent
        # just rename the dup_task
        dup_task.name += ' - Duplicate'
        DBSession.add(dup_task)
    else:
        raise HTTPServerError()

    return HTTPOk()


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
            'completed': project.total_logged_seconds / project.schedule_seconds,
            'description': project.description,
            'end': milliseconds_since_epoch(
                project.computed_end if project.computed_end else project.end),
            'id': project.id,
            'name': project.name,
            'hasChildren': hasChildren(project),
            'schedule_seconds': project.schedule_seconds,
            'start': milliseconds_since_epoch(
                project.computed_start if project.computed_start else project.start),
            'total_logged_seconds': project.total_logged_seconds,
            'type': project.entity_type
            # 'children': [{'$ref': task.id} for task in project.root_tasks]
        } for project in projects
    ]


def convert_to_dgrid_gantt_task_format(tasks):
    """Converts the given tasks to the DGrid Gantt compatible json format.

    :param tasks: List of Stalker Tasks.
    :return: json compatible dictionary
    """
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
            'hierarchy_name': ' | '.join([parent.name for parent in task.parents]),
            'id': task.id,
            'name': task.name,
            'parent': task.parent.id if task.parent else task.project.id,
            'priority': task.priority,
            'responsible': {
                'id': task.responsible.id,
                'name': task.responsible.name
            },
            'resources': [
                {'id': resource.id, 'name': resource.name} for resource in task.resources] if not task.is_container else [],
            'schedule_constraint': task.schedule_constraint,
            'schedule_model': task.schedule_model,
            'schedule_seconds': task.schedule_seconds,
            'schedule_timing': task.schedule_timing,
            'schedule_unit': task.schedule_unit,
            'start': milliseconds_since_epoch(
                task.computed_start if task.computed_start else task.start),
            'total_logged_seconds': task.total_logged_seconds,
            'type': task.entity_type,
            # 'children': [{'$ref': task.id} for task in task.children]
        } for task in tasks
    ]


@view_config(
    route_name='dialog_update_task',
    renderer='templates/task/dialog_create_task.jinja2'
)
def update_task_dialog(request):
    """runs when updating a task
    """
    task_id = request.matchdict.get('id', -1)
    task = Task.query.filter(Task.id == task_id).first()

    return {
        'mode': 'UPDATE',
        'has_permission': PermissionChecker(request),
        'project': task.project,
        'task': task,
        'parent': task.parent,
        'schedule_models': defaults.task_schedule_models,
        'milliseconds_since_epoch': milliseconds_since_epoch
    }


@view_config(
    route_name='update_task'
)
def update_task(request):
    """Updates the given task with the data coming from the request
    """
    logged_in_user = get_logged_in_user(request)
    if not logged_in_user:
        import auth
        return auth.logout(request)

    # *************************************************************************
    # collect data
    parent_id = request.params.get('parent_id', None)
    if parent_id:
        parent = Task.query.filter(Task.id == parent_id).first()
    else:
        parent = None
    name = str(request.params.get('name', None))
    description = request.params.get('description', '')
    is_milestone = int(request.params.get('is_milestone', None))
    status_id = int(request.params.get('status_id', None))
    status = Status.query.filter_by(id=status_id).first()
    schedule_model = request.params.get('schedule_model') # there should be one
    schedule_timing = float(request.params.get('schedule_timing'))
    schedule_unit = request.params.get('schedule_unit')
    schedule_constraint = int(request.params.get('schedule_constraint', 0))
    start = get_date(request, 'start')
    end = get_date(request, 'end')
    update_bid = int(request.params.get('update_bid'))

    depend_ids = get_multi_integer(request, 'depend_ids')
    depends = Task.query.filter(Task.id.in_(depend_ids)).all()

    resource_ids = get_multi_integer(request, 'resource_ids')
    resources = User.query.filter(User.id.in_(resource_ids)).all()

    # get responsible
    responsible_id = request.params.get('responsible_id', -1)
    responsible = User.query.filter(User.id==responsible_id).first()

    priority = request.params.get('priority', 500)

    entity_type = request.params.get('entity_type', None)
    code = request.params.get('code', None)
    asset_type = request.params.get('asset_type_name', None)
    shot_sequence_id = request.params.get('shot_sequence_id', None)

    logger.debug('parent_id           : %s' % parent_id)
    logger.debug('parent              : %s' % parent)
    logger.debug('depend_ids          : %s' % depend_ids)
    logger.debug('depends             : %s' % depends)
    logger.debug('resource_ids        : %s' % resource_ids)
    logger.debug('resources           : %s' % resources)
    logger.debug('responsible         : %s' % responsible)
    logger.debug('name                : %s' % name)
    logger.debug('description         : %s' % description)
    logger.debug('is_milestone        : %s' % is_milestone)
    logger.debug('status_id           : %s' % status_id)
    logger.debug('status              : %s' % status)
    logger.debug('schedule_model      : %s' % schedule_model)
    logger.debug('schedule_timing     : %s' % schedule_timing)
    logger.debug('schedule_unit       : %s' % schedule_unit)
    logger.debug('schedule_constraint : %s' % schedule_constraint)
    logger.debug('start               : %s' % start)
    logger.debug('end                 : %s' % end)
    logger.debug('update_bid          : %s' % update_bid)
    logger.debug('priority            : %s' % priority)
    logger.debug('code                : %s' % code)

    # get task
    task_id = request.matchdict.get('id', -1)
    task = Task.query.filter(Task.id == task_id).first()

    # update the task
    if not task:
        return HTTPOk(detail='Task not updated')

    task.name = name
    task.description = description

    try:
        task.parent = parent
        task.depends = depends
    except CircularDependencyError:
        transaction.abort()
        return HTTPServerError()

    task.start = start
    task.end = end
    task.is_milestone = is_milestone
    task.status = status
    task.schedule_model = schedule_model
    task.schedule_unit = schedule_unit
    task.schedule_timing = schedule_timing
    task.schedule_constraint = schedule_constraint
    task.resources = resources
    task.priority = priority
    task.code = code
    task.updated_by = logged_in_user

    # update responsible
    if responsible:
        if task.responsible != responsible:
            task.responsible = responsible

    if entity_type == 'Asset':
        type_ = Type.query \
            .filter_by(target_entity_type='Asset') \
            .filter_by(name=asset_type) \
            .first()

        if type_ is None:
            # create a new Type
            # TODO: should we check for permission here or will it be already done in the UI (ex. filteringSelect instead of comboBox)
            type_ = Type(
                name=asset_type,
                code=asset_type,
                target_entity_type='Asset'
            )

        task.type = type_

    if entity_type == 'Shot':
        task.sequence = Sequence.query.filter_by(id=shot_sequence_id).first()

    task._reschedule(task.schedule_timing, task.schedule_unit)
    if update_bid:
        logger.debug('updating bid')
        task.bid_timing = task.schedule_timing
        task.bid_unit = task.schedule_unit
    else:
        logger.debug('not updating bid')
    return HTTPOk(detail='Task updated successfully')


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


@view_config(
    route_name='get_tasks',
    renderer='json'
)
def get_tasks(request):
    """RESTful version of getting all tasks
    """
    # logger.debug('request.GET: %s' % request.GET)
    parent_id = request.GET.get('parent_id')
    task_id = request.GET.get('task_id')

    return_data = None
    # set the content range to prevent JSONRest Store to query the data twice
    content_range = '%s-%s/%s'
    if task_id:
        task = Entity.query.filter(Entity.id == task_id).first()
        if isinstance(task, Project):
            return_data = convert_to_dgrid_gantt_project_format([task])
            content_range = content_range % (0, 0, 1)
        elif isinstance(task, Task):
            return_data = convert_to_dgrid_gantt_task_format([task])
            content_range = content_range % (0, 0, 1)
    elif parent_id:
        parent = Entity.query.filter(Entity.id == parent_id).first()

        if isinstance(parent, Project):
            tasks = parent.root_tasks
        elif isinstance(parent, Task):
            tasks = Task.query.filter(Task.parent_id == parent_id).order_by(Task.name).all()

        content_range = content_range % (0, len(tasks) - 1, len(tasks))
        # logger.debug(tasks)
        return_data = convert_to_dgrid_gantt_task_format(tasks)

    # logger.debug('return_data: %s' % return_data)

    resp = Response(
        json_body=return_data
    )
    resp.content_range = content_range
    return resp


@view_config(
    route_name='get_user_tasks',
    renderer='json'
)
@view_config(
    route_name='get_studio_tasks',
    renderer='json'
)
def get_entity_tasks(request):
    """RESTful version of getting all tasks of an entity
    """
    # logger.debug('request.GET: %s' % request.GET)
    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter(Entity.id == entity_id).first()

    parent_id = request.GET.get('parent_id')
    parent = Entity.query.filter_by(id=parent_id).first()

    # logger.debug('parent_id : %s' % parent_id)
    # logger.debug('parent    : %s' % parent)

    return_data = None
    # set the content range to prevent JSONRest Store to query the data twice
    content_range = '%s-%s/%s'

    if entity:
        if parent:
            logger.debug('there is a parent')
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
            logger.debug('no parent')
            # no parent,
            # just return projects of the entity
            entity_projects = []
            if isinstance(entity, User):
                entity_projects = entity.projects
            elif isinstance(entity, Studio):
                entity_projects = Project.query.all()

            return_data = convert_to_dgrid_gantt_project_format(entity_projects)

        content_range = content_range % (0,
                                         len(return_data) - 1,
                                         len(return_data))

    # logger.debug('return_data: %s' % return_data)

    resp = Response(
        json_body=return_data
    )
    resp.content_range = content_range
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

    # logger.debug('return_data: %s' % return_data)

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

    logger.debug('entity : %s' % entity)

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
                    .filter(Task._project == project) \
                    .filter(Task.parent == None).all()

                # do a depth first search for child tasks
                for root_task in root_tasks:
                    # logger.debug('root_task: %s, parent: %s' % (root_task, root_task.parent))
                    tasks.extend(depth_first_flatten(root_task))

        else: # Asset, Shot, Sequence
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
    route_name='get_project_tasks',
    renderer='json'
)
def get_project_tasks(request):
    """returns all the tasks in the database related to the given entity in
    flat json format
    """
    # get all the tasks related in the given project
    project_id = request.matchdict.get('id', -1)
    project = Project.query.filter_by(id=project_id).first()

    return [
        {
            'id': task.id,
            'name': '%s (%s)' % (
                task.name,
                ' | '.join(reversed([parent.name for parent in task.parents]))
            )
        } for task in Task.query.filter(Task._project == project).all()
    ]




@view_config(
    route_name='dialog_create_project_task',
    renderer='templates/task/dialog_create_task.jinja2'
)
def create_task_dialog(request):
    """only project information is present
    """
    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    parent = None
    if entity.entity_type == 'Project':
        project = entity
    else:
        project = entity.project
        parent = entity

    return {
        'mode': 'CREATE',
        'has_permission': PermissionChecker(request),
        'project': project,
        'parent': parent,
        'schedule_models': defaults.task_schedule_models,
        'milliseconds_since_epoch': milliseconds_since_epoch
    }


@view_config(
    route_name='dialog_create_child_task',
    renderer='templates/task/dialog_create_task.jinja2'
)
def create_child_task_dialog(request):
    """generates the info from the given parent task
    """
    parent_task_id = request.matchdict.get('id', -1)
    parent_task = Task.query.filter_by(id=parent_task_id).first()

    project = parent_task.project if parent_task else None

    return {
        'mode': 'CREATE',
        'has_permission': PermissionChecker(request),
        'project': project,
        'parent': parent_task,
        'schedule_models': defaults.task_schedule_models,
        'milliseconds_since_epoch': milliseconds_since_epoch
    }


@view_config(
    route_name='dialog_create_dependent_task',
    renderer='templates/task/dialog_create_task.jinja2'
)
def create_dependent_task_dialog(request):
    """runs when adding a dependent task
    """
    # get the dependee task
    depends_to_task_id = request.matchdict.get('id', -1)
    depends_to_task = Task.query.filter_by(id=depends_to_task_id).first()

    project = depends_to_task.project if depends_to_task else None

    return {
        'mode': 'CREATE',
        'has_permission': PermissionChecker(request),
        'project': project,
        'depends_to': depends_to_task,
        'schedule_models': defaults.task_schedule_models,
        'milliseconds_since_epoch': milliseconds_since_epoch
    }


@view_config(
    route_name='create_task'
)
def create_task(request):
    """runs when adding a new task
    """
    logged_in_user = get_logged_in_user(request)
    if not logged_in_user:
        import auth
        return auth.logout(request)

    # ***********************************************************************
    # collect params
    project_id = request.params.get('project_id', None)
    parent_id = request.params.get('parent_id', None)
    name = request.params.get('name', None)
    description = request.params.get('description', '')
    is_milestone = request.params.get('is_milestone', None)
    status_id = request.params.get('status_id', None)
    if status_id:
        status_id = int(status_id)

    schedule_model = request.params.get('schedule_model') # there should be one
    schedule_timing = float(request.params.get('schedule_timing'))
    schedule_unit = request.params.get('schedule_unit')
    schedule_constraint = int(request.params.get('schedule_constraint', 0))

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
        responsible = User.query.filter(User.id==responsible_id).first()

    priority = request.params.get('priority', 500)

    entity_type = request.params.get('entity_type', None)
    code = request.params.get('code', None)
    asset_type = request.params.get('asset_type_name', None)
    shot_sequence_id = request.params.get('shot_sequence_id', None)

    logger.debug('project_id          : %s' % project_id)
    logger.debug('parent_id           : %s' % parent_id)
    logger.debug('name                : %s' % name)
    logger.debug('description         : %s' % description)
    logger.debug('is_milestone        : %s' % is_milestone)
    logger.debug('status_id           : %s' % status_id)
    logger.debug('schedule_model      : %s' % schedule_model)
    logger.debug('schedule_timing     : %s' % schedule_timing)
    logger.debug('schedule_unit       : %s' % schedule_unit)
    logger.debug('resource_ids        : %s' % resource_ids)
    logger.debug('resources           : %s' % resources)
    logger.debug('responsible         : %s' % responsible)
    logger.debug('priority            : %s' % priority)
    logger.debug('schedule_constraint : %s' % schedule_constraint)
    logger.debug('entity_type         : %s' % entity_type)
    logger.debug('code                : %s' % code)

    kwargs = {}

    if project_id and name and status_id:
        # get the project
        project = Project.query.filter_by(id=project_id).first()
        kwargs['project'] = project

        # get the parent if exists
        parent = None
        if parent_id:
            parent = Task.query.filter_by(id=parent_id).first()

        kwargs['parent'] = parent

        # get the status_list
        status_list = StatusList.query.filter_by(
            target_entity_type=entity_type
        ).first()

        logger.debug('status_list: %s' % status_list)

        # there should be a status_list
        if status_list is None:
            return HTTPServerError(
                detail='No StatusList found'
            )

        status = Status.query.filter_by(id=status_id).first()
        logger.debug('status: %s' % status)

        # get the dates
        start = get_date(request, 'start')
        end = get_date(request, 'end')

        logger.debug('start : %s' % start)
        logger.debug('end : %s' % end)

        # get the dependencies
        depend_ids = get_multi_integer(request, 'depend_ids')
        depends = Task.query.filter(Task.id.in_(depend_ids)).all()
        logger.debug('depends: %s' % depends)

        kwargs['name'] = name
        kwargs['description'] = description
        kwargs['status_list'] = status_list
        kwargs['status'] = status
        kwargs['created_by'] = logged_in_user

        kwargs['start'] = start
        kwargs['end'] = end

        kwargs['schedule_model'] = schedule_model
        kwargs['schedule_timing'] = schedule_timing
        kwargs['schedule_unit'] = schedule_unit
        kwargs['schedule_constraint'] = schedule_constraint

        kwargs['resources'] = resources
        kwargs['depends'] = depends

        kwargs['priority'] = priority

        kwargs['code'] = code

        if entity_type == 'Asset':
            type_ = Type.query \
                .filter_by(target_entity_type='Asset') \
                .filter_by(name=asset_type) \
                .first()

            if type_ is None:
                # create a new Type
                # TODO: should we check for permission here or will it be already done in the UI (ex. filteringSelect instead of comboBox)
                type_ = Type(
                    name=asset_type,
                    code=asset_type,
                    target_entity_type='Asset'
                )

            kwargs['type'] = type_

        if entity_type == 'Shot':
            sequence = Sequence.query.filter_by(id=shot_sequence_id).first()
            kwargs['sequence'] = sequence

        try:

            if entity_type == 'Task':
                new_entity = Task(**kwargs)
                logger.debug('new_task.name %s' % new_entity.name)
                # logger.debug('new_task.status: %s' % new_entity.status)
                DBSession.add(new_entity)
            elif entity_type == 'Asset':
                new_entity = Asset(**kwargs)
                logger.debug('new_asset.name %s' % new_entity.name)
                # logger.debug('new_asset.status: %s' % new_entity.status)
                DBSession.add(new_entity)
            elif entity_type == 'Shot':
                new_entity = Shot(**kwargs)
                logger.debug('new_shot.name %s' % new_entity.name)
                # logger.debug('new_shot.status: %s' % new_entity.status)
                DBSession.add(new_entity)
            elif entity_type == 'Sequence':
                new_entity = Sequence(**kwargs)
                logger.debug('new_shot.name %s' % new_entity.name)
                # logger.debug('new_shot.status: %s' % new_entity.status)
                DBSession.add(new_entity)

            if responsible:
                # check if the responsible is different than
                # the parents responsible
                if new_entity.responsible != responsible:
                    new_entity.responsible = responsible

        except (AttributeError, TypeError, CircularDependencyError) as e:
            logger.debug(e.message)
            error = HTTPServerError()
            error.title = str(type(e))
            error.detail = e.message
            return error
        else:
            DBSession.add(new_entity)
            try:
                transaction.commit()
            except IntegrityError as e:
                logger.debug(e.message)
                transaction.abort()
                return HTTPServerError(detail=e.message)
            else:
                logger.debug('flushing the DBSession, no problem here!')
                DBSession.flush()
                logger.debug('finished adding Task')
    else:
        logger.debug('there are missing parameters')

        def get_param(param):
            if param in request.params:
                logger.debug('%s: %s' % (param, request.params[param]))
            else:
                logger.debug('%s not in params' % param)

        get_param('project_id')
        get_param('name')
        get_param('description')
        get_param('is_milestone')
        get_param('resource_ids')
        get_param('status_id')

        param_list = ['project_id', 'name', 'description',
                      'is_milestone', 'resource_ids', 'status_id']

        params = [param for param in param_list if param not in request.params]

        error = HTTPServerError()
        error.explanation = 'There are missing parameters: %s' % params
        return error

    return HTTPOk(detail='Task created successfully')


@view_config(
    route_name='auto_schedule_tasks',
)
def auto_schedule_tasks(request):
    """schedules all the tasks of active projects
    """
    # get the studio
    studio = Studio.query.first()

    if studio:
        tj_scheduler = TaskJugglerScheduler()
        studio.scheduler = tj_scheduler

        # logger.debug('studio.name: %s' % studio.name)
        # logger.debug('studio.working_hours[0]: %s' % studio.working_hours[0])
        # logger.debug('studio.daily_working_hours: %s' % studio.daily_working_hours)
        # logger.debug('studio.to_tjp: %s' % studio.to_tjp)

        try:
            studio.schedule()
        except RuntimeError:
            return HTTPServerError()

    return HTTPOk()


@view_config(
    route_name='request_task_review',
)
def request_task_review(request):
    """creates a new ticket and sends an email to the responsible
    """
    # get logged in user as he review requester
    logged_in_user = get_logged_in_user(request)
    if not logged_in_user:
        import auth
        return auth.logout(request)

    task_id = request.matchdict.get('id', -1)
    task = Task.query.filter(Task.id==task_id).first()

    if task:
        # get the project that the ticket belongs to
        project = task.project

        summary_text = 'Review Request: "%s"' % task.name
        description_text = '%s has requested you to do a review for ' \
                           '"%s (%s) - (%s)"' % (
            logged_in_user.name,
            task.name,
            task.entity_type,
            "|".join(map(lambda x: x.name, task.parents))
        )

        responsible = task.responsible

        # create a Ticket with the owner set to the responsible
        review_ticket = Ticket(
            project=project,
            summary=summary_text,
            description=description_text,
            created_by=logged_in_user
        )
        review_ticket.set_owner(responsible)

        # link the task to the review
        review_ticket.links.append(task)

        DBSession.add(review_ticket)

        # send email to responsible and resources of the task
        mailer = get_mailer(request)

        recipients = [logged_in_user.email, responsible.email]
        # recipients.extend(task.resources)

        message = Message(
            subject=summary_text,
            sender="Anima Stalker <anima.stalker.pyramid@stalker.com>",
            recipients=recipients,
            body=description_text)
        mailer.send(message)

    return HTTPOk()



@view_config(
    route_name='view_project_asset',
    renderer='templates/task/view_project_task.jinja2'
)
@view_config(
    route_name='view_project_sequence',
    renderer='templates/task/view_project_task.jinja2'
)
@view_config(
    route_name='view_project_shot',
    renderer='templates/task/view_project_task.jinja2'
)
@view_config(
    route_name='view_project_task',
    renderer='templates/task/view_project_task.jinja2'
)
def view_project_task(request):
    """runs when viewing an task
    """
    logged_in_user = get_logged_in_user(request)
    if not logged_in_user:
        import auth
        return auth.logout(request)

    project_id = request.matchdict['pid']
    project = Project.query.filter_by(id=project_id).first()

    task_id = request.matchdict['id']
    task = Task.query.filter_by(id=task_id).first()

    studio = Studio.query.first()
    projects = Project.query.all()

    return {
        'entity':project,
        'task': task,
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'milliseconds_since_epoch': milliseconds_since_epoch,
        'stalker_pyramid': stalker_pyramid,
        'projects': projects,
        'studio': studio
    }
