# -*- coding: utf-8 -*-

import logging
import time
import pytz
import datetime
import json
import os


import transaction
from pyramid.response import Response
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPServerError, HTTPOk, HTTPForbidden
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message, Attachment
from beaker.cache import cache_region

from sqlalchemy.exc import IntegrityError

from stalker import (db, defaults, User, Task, Entity, Project, StatusList,
                     Status, Studio, Asset, Shot, Sequence, Ticket, Type, Note,
                     Review, Version, TimeLog, Good)
from stalker.db.session import DBSession
from stalker.exceptions import CircularDependencyError, StatusError
from stalker.models import walk_hierarchy

from stalker_pyramid.views import (PermissionChecker, get_logged_in_user,
                                   get_multi_integer, milliseconds_since_epoch,
                                   StdErrToHTMLConverter,
                                   multi_permission_checker,
                                   convert_seconds_to_time_range,
                                   dummy_email_address,
                                   get_path_converter, invalidate_all_caches,
                                   measure_time, get_date, get_user_os)
from stalker_pyramid.views.link import (replace_img_data_with_links,
                                        MediaManager)
from stalker_pyramid.views.note import create_simple_note
from stalker_pyramid.views.type import query_type


#logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)
from stalker_pyramid import logger_name
logger = logging.getLogger(logger_name)


def generate_recursive_task_query(ordered=True):
    """generates a query string that recursively gathers task information
    starting from the root tasks to the leaf tasks.
    """
    order_string = 'order by path' if ordered else ''

    query = """
    with recursive recursive_task(id, parent_id, path, path_names, type_names, responsible_id) as (
        select
            task.id,
            task.project_id,
            task.project_id::text as path,
            ("Projects".code || '') as path_names,
            'Project ' as type_names,
            (
                select
                    array_agg(responsible_id)
                from "Task_Responsible"
                where "Task_Responsible".task_id = task.id
                group by task_id
            ) as responsible_id,
            "Task_Thumbnail".full_path as thumbnail_full_path
        from "Tasks" as task

        join "SimpleEntities" as "Task_SimpleEntities" on task.id = "Task_SimpleEntities".id
        left outer join "Links" as "Task_Thumbnail" on "Task_SimpleEntities".thumbnail_id = "Task_Thumbnail".id 

        join "Projects" on task.project_id = "Projects".id
        where task.parent_id is NULL
    union all
        select
            task.id,
            task.parent_id,
            (parent.path || '|' || task.parent_id::text) as path,
            (parent.path_names || ' | ' || "Parent_SimpleEntities".name) as path_names,
            (
                coalesce(
                    (parent.type_names || ' | ' || "Type_SimpleEntities".name),
                    (parent.type_names || ' | None' )
                ) || ' | '
            )  as type_names,
            coalesce(
                (
                    select
                        array_agg(responsible_id)
                    from "Task_Responsible"
                    where "Task_Responsible".task_id = task.id
                    group by task_id
                ),
                parent.responsible_id
            ) as responsible_id,
            coalesce(
                thumbnail_full_path,
                "Parent_Task_Thumbnail".full_path
            ) as thumbnail_full_path
        from "Tasks" as task
        join recursive_task as parent on task.parent_id = parent.id
        join "SimpleEntities" as "Parent_SimpleEntities" on parent.id = "Parent_SimpleEntities".id
        left outer join "Links" as "Parent_Task_Thumbnail" on "Parent_SimpleEntities".thumbnail_id = "Parent_Task_Thumbnail".id
        left outer join "Types" as "Parent_Types" on "Parent_SimpleEntities".type_id = "Parent_Types".id
        left outer join "SimpleEntities" as "Type_SimpleEntities" on "Parent_Types".id = "Type_SimpleEntities".id
    ) select
        recursive_task.id,
        "SimpleEntities".name as name,
        recursive_task.parent_id,
        recursive_task.path || '|' || recursive_task.id as path,
        recursive_task.path_names,
        "SimpleEntities".name || ' (' || recursive_task.path_names || ')(' || recursive_task.id || ')' as full_path,
        "SimpleEntities".entity_type,
        recursive_task.responsible_id,
        task_watchers.watcher_id,
        recursive_task.type_names,
        recursive_task.thumbnail_full_path as thumbnail_full_path
    from recursive_task
    join "SimpleEntities" on recursive_task.id = "SimpleEntities".id
    left join (
        select
            "Task_Watchers".task_id,
            array_agg("Task_Watchers".watcher_id) as watcher_id
        from "Task_Watchers"
        group by "Task_Watchers".task_id
    ) as task_watchers on recursive_task.id = task_watchers.task_id
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
        'generate_recursive_task_query': generate_recursive_task_query(),
        'task_id': task_id
    }

    result = DBSession.connection().execute(sql_query).fetchone()

    return result[0]


def get_task_internal_link(task_id):
    """returns an internal link for the given task
    """
    task_full_path = get_task_full_path(task_id)
    from stalker_pyramid import stalker_server_internal_url
    internal_link = '%s/tasks/%s/view' % (stalker_server_internal_url, task_id)
    return '<a href="%(internal_link)s">%(task_full_path)s</a>' % {
        'internal_link': internal_link,
        'task_full_path': task_full_path
    }


def get_task_external_link(task_id):
    """returns an external link for the given task
    """
    task_full_path = get_task_full_path(task_id)
    from stalker_pyramid import stalker_server_external_url
    external_link = '%s/tasks/%s/view' % (stalker_server_external_url, task_id)
    return '<a href="%(external_link)s">%(task_full_path)s</a>' % {
        'external_link': external_link,
        'task_full_path': task_full_path
    }


@view_config(
    route_name='get_task_internal_link',
    renderer='json'
)
def get_task_internal_link_view(request):
    """returns an internal url for the given task
    """
    task_id = request.matchdict.get('id')
    return get_task_internal_link(task_id)


@view_config(
    route_name='get_task_external_link',
    renderer='json'
)
def get_task_external_link_view(request):
    """returns an external url for the given task
    """
    task_id = request.matchdict.get('id')
    return get_task_external_link(task_id)


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


def check_all_tasks_status_by_schedule_model(projects):
    """after scheduling project checks the task statuses
    """

    logger.debug('check_task_status_by_schedule_model starts')

    utc_now = datetime.datetime.now(pytz.utc)

    tasks = Task.query.filter(Task.schedule_model == 'duration').filter(Task.project in projects).all()
    status_cmpl = Status.query.filter(Status.code == 'CMPL').first()
    status_wip = Status.query.filter(Status.code == 'WIP').first()
    if tasks:
        for task in tasks:
            if task.is_leaf:
                if task.computed_end < utc_now:
                    task.status = status_cmpl
                elif task.computed_start < utc_now < task.computed_end:
                    task.status = status_wip
                else:
                    continue


def check_task_status_by_schedule_model(task):
    """after scheduling project checks the task statuses
    """

    logger.debug('check_task_status_by_schedule_model starts')

    utc_now = datetime.datetime.now(pytz.utc)

    status_cmpl = Status.query.filter(Status.code == 'CMPL').first()
    status_wip = Status.query.filter(Status.code == 'WIP').first()

    if task.is_leaf and task.schedule_model == 'duration':
        depends_tasks_cmpl = True
        for dependent_task in task.depends:
            if dependent_task.status is not status_cmpl:
                depends_tasks_cmpl = False

        if depends_tasks_cmpl:
            task.status = status_cmpl
            # if task.computed_end < utc_now:
            #     task.status = status_cmpl
            # elif task.computed_start < utc_now and task.computed_end > utc_now:
            #     task.status = status_wip


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
    route_name='fix_tasks_statuses'
)
def fix_tasks_statuses(request):
    """ request revision for selected tasks
    """

    selected_task_list = get_multi_integer(request, 'task_ids', 'GET')
    tasks = Task.query.filter(Task.id.in_(selected_task_list)).all()

    if not tasks:
        transaction.abort()
        return Response('Can not find any Task', 500)

    for task in tasks:
        task.update_status_with_dependent_statuses()
        task.update_status_with_children_statuses()
        task.update_schedule_info()
        check_task_status_by_schedule_model(task)
        fix_task_computed_time(task)

    request.session.flash('success: Task status is fixed!')
    invalidate_all_caches()

    return HTTPOk()


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

        check_task_status_by_schedule_model(task)
        fix_task_computed_time(task)

    request.session.flash('success: Task status is fixed!')

    # invalidate all caches
    invalidate_all_caches()

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

    # invalidate all caches
    invalidate_all_caches()

    return HTTPOk()


def generate_unique_shot_name(base_name, shot_name_increment=10):
    """generates a unique shot name and code based of the base_name

    :param base_name: The base shot name
    :param int shot_name_increment: The increment amount
    """
    logger.debug('generating unique shot number based on: %s' % base_name)
    logger.debug('shot_name_increment is: %s' % shot_name_increment)
    import re
    from stalker.db.session import DBSession
    from stalker import Shot

    regex = re.compile('[0-9]+')

    # base_name: Ep001_001_0010
    name_parts = base_name.split('_')

    # find the shot number
    shot_number_as_string = regex.findall(name_parts[-1])[-1]
    padding = len(shot_number_as_string)
    shot_number = int(shot_number_as_string)

    # initialize from the given shot_number
    i = shot_number

    logger.debug('start shot_number: %s' % shot_number)

    # initialize existing_shot variable with base_name
    while True and i < 10000:
        name_parts[-1] = str(i).zfill(padding)
        shot_name = '_'.join(name_parts)
        with DBSession.no_autoflush:
            existing_shot = DBSession.query(Shot.name).filter(Shot.name==shot_name).first()
        if not existing_shot:
            logger.debug('generated unique shot name: %s' % shot_name)
            return shot_name
        i += shot_name_increment

    raise RuntimeError("Can not generate a unique shot name!!!")


def duplicate_task(task, user):
    """Duplicates the given task without children.

    :param task: a stalker.models.task.Task instance
    :param user:
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

        # generate a unique shot name based on task.name
        logger.debug('generating unique shot name!')
        shot_name = generate_unique_shot_name(task.name)

        extra_kwargs = {
            'name': shot_name,
            'code': shot_name
        }
    elif task.entity_type == 'Sequence':
        class_ = Sequence
        extra_kwargs = {
            'code': task.code
        }

    # all duplicated tasks are new tasks
    from stalker.db.session import DBSession
    with DBSession.no_autoflush:
        wfd = Status.query.filter(Status.code == 'WFD').first()

    utc_now = datetime.datetime.now(pytz.utc)

    kwargs = {
        'name': task.name,
        'project': task.project,
        'bid_timing': task.bid_timing,
        'bid_unit': task.bid_unit,
        'computed_end': task.computed_end,
        'computed_start': task.computed_start,
        'created_by': user,
        'description': task.description,
        'is_milestone': task.is_milestone,
        'priority': task.priority,
        'schedule_constraint': task.schedule_constraint,
        'schedule_model': task.schedule_model,
        'schedule_timing': task.schedule_timing,
        'schedule_unit': task.schedule_unit,
        'status': wfd,
        'status_list': task.status_list,
        'tags': task.tags,
        'responsible': task.responsible,
        'start': task.start,
        'end': task.end,
        'type': task.type,
        'watchers': task.watchers,
        'date_created': utc_now,
    }

    kwargs.update(extra_kwargs)

    dup_task = class_(**kwargs)
    dup_task.generic_data = task.generic_data

    return dup_task


# def walk_hierarchy(task):
#     """Walks the hierarchy of the given task
#
#     :param task: The top most task instance
#     :return:
#     """
#     tasks_to_visit = [task]
#
#     while len(tasks_to_visit):
#         current_task = tasks_to_visit.pop(0)
#         tasks_to_visit.extend(current_task.children)
#         yield current_task


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


def walk_and_duplicate_task_hierarchy(task, user):
    """Walks through task hierarchy and creates duplicates of all the tasks
    it finds

    :param task: task
    :param user: The user who is calling this function
    :return:
    """
    import re
    regex = re.compile('[0-9]+')
    # start from the given task
    logger.debug('duplicating task : %s' % task)
    logger.debug('task.children    : %s' % task.children)
    dup_task = duplicate_task(task, user)
    task.duplicate = dup_task
    for child in task.children:
        logger.debug('duplicating child : %s' % child)
        duplicated_child = walk_and_duplicate_task_hierarchy(child, user)
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


def duplicate_task_hierarchy_action(task, parent, name, description, user):
    """Duplicates the given task hierarchy.

    Walks through the hierarchy of the given task and duplicates every
    instance it finds in a new task.

    task: The task that wanted to be duplicated

    :return: A list of stalker.models.task.Task
    """
    dup_task = walk_and_duplicate_task_hierarchy(task, user)
    update_dependencies_in_duplicated_hierarchy(task)

    cleanup_duplicate_residuals(task)
    # update the parent
    dup_task.parent = parent
    # just rename the dup_task

    dup_task.name = name
    dup_task.code = name
    dup_task.description = description

    DBSession.add(dup_task)

    return dup_task


@view_config(
    route_name='duplicate_asset_hierarchy'
)
def duplicate_asset_hierarchy(request):
    """Duplicates the given asset hierarchy.

    Walks through the hierarchy of the given asset and duplicates every
    instance it finds in a new task.

    task: The task that wanted to be duplicated

    :return: A list of stalker.models.task.Task
    """

    logger.debug('duplicate_asset_hierarchy is running')
    logged_in_user = get_logged_in_user(request)

    asset_id = request.params.get('temp_asset_id')
    asset = Asset.query.filter_by(id=asset_id).first()

    logger.debug('asset_id %s ' % asset_id)

    name = request.params.get('name', asset.name + ' - Duplicate')

    parent_id = request.params.get('parent_id', -1)
    parent = Task.query.filter_by(id=parent_id).first()

    if not parent:
        parent = asset.parent

    description = request.params.get('description', '')

    responsible = []
    responsible_ids = []
    if 'responsible_ids[]' in request.params:
        responsible_ids = get_multi_integer(request, 'responsible_ids[]')
        responsible = User.query.filter(User.id.in_(responsible_ids)).all()

    if asset:
        dup_asset = duplicate_task_hierarchy_action(
            asset,
            parent,
            name,
            description,
            logged_in_user
        )

        dup_asset.responsible = responsible
        DBSession.add(dup_asset)

        #update_task_statuses_with_dependencies(dup_task)
        #leafs = find_leafs_in_hierarchy(dup_task)
    else:
        transaction.abort()
        return Response(
            'No task can be found with the given id: %s' % asset_id, 500)

    # invalidate all caches
    invalidate_all_caches()

    request.session.flash('success:Task %s is duplicated successfully' % asset.name)

    return Response('Task %s is duplicated successfully' % asset.id)


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
    logged_in_user = get_logged_in_user(request)

    task_id = request.matchdict.get('id')
    task = Task.query.filter_by(id=task_id).first()

    logger.debug('task_id %s ' % task_id)

    name = request.params.get('dup_task_name', task.name + ' - Duplicate')

    parent_id = request.params.get('parent_id', -1)
    parent = Task.query.filter_by(id=parent_id).first()

    if not parent:
        parent = task.parent

    description = request.params.get('dup_task_description', '')

    if task:
        duplicate_task_hierarchy_action(task,
                                        parent,
                                        name,
                                        description,
                                        logged_in_user)

        #update_task_statuses_with_dependencies(dup_task)
        #leafs = find_leafs_in_hierarchy(dup_task)
    else:
        transaction.abort()
        return Response(
            'No task can be found with the given id: %s' % task_id, 500)

    # invalidate all caches
    invalidate_all_caches()

    request.session.flash('success:Task %s is duplicated successfully' % task.name)

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

        logger.debug('hasChildren took: %s seconds' % (end_inner - start_inner))
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
            'entity_type': project.entity_type,
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
            'completed': task.percent_complete / 100,
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
            'status_name': task.status.name,
            'total_logged_seconds': task.total_logged_seconds,
            'type': task.entity_type,
            'entity_type': task.entity_type,
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
    utc_now = datetime.datetime.now(pytz.utc)

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

    # invalidate all caches
    invalidate_all_caches()

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
    utc_now = datetime.datetime.now(pytz.utc)

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
                task.parent.name, list(map(lambda x: x.name, depends))
            )
        transaction.abort()
        return Response(message, 500)

    task.updated_by = logged_in_user
    task.date_updated = utc_now

    # invalidate all caches
    invalidate_all_caches()

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
            if attr_name == 'cut_in' \
               or attr_name == 'cut_out' \
               or attr_name == 'fps' \
               or attr_name == 'priority':
                attr_value = int(attr_value)

            setattr(task, attr_name, attr_value)

            if attr_name == 'priority':
                for ct in task.walk_hierarchy():
                    ct.priority = attr_value

        task.updated_by = logged_in_user
        utc_now = datetime.datetime.now(pytz.utc)
        task.date_updated = utc_now

    else:
        logger.debug('not updating')
        return Response("MISSING PARAMETERS", 500)

    # invalidate all caches
    invalidate_all_caches()

    return Response(
        'Task updated successfully %s %s' % (attr_name, attr_value)
    )


@view_config(
    route_name='update_task',
    permission='Update_Task'
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
    good_id = request.params.get('good_id', None)

    cut_in = int(request.params.get('cut_in', 1))
    cut_out = int(request.params.get('cut_out', 1))
    fps = int(request.params.get('fps', 1))

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
    logger.debug('good_id             : %s' % good_id)
    logger.debug('code                : %s' % code)

    logger.debug('shot_sequence_id    : %s' % shot_sequence_id)
    logger.debug('cut_in              : %s' % cut_in)
    logger.debug('cut_out             : %s' % cut_out)
    logger.debug('fps                 : %s' % fps)

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
                    parent.name, list(map(lambda x: x.name, depends))
                )
            transaction.abort()
            return Response(message, 500)
    logger.debug('task in DBSession: %s' % (task in DBSession))

    task.schedule_model = schedule_model
    task.schedule_unit = schedule_unit
    task.schedule_timing = schedule_timing
    task.resources = resources
    task.priority = priority
    # also update all child task priorities
    if priority != task.priority:
        for ct in task.walk_hierarchy():
            ct.priority = priority

    task.code = code
    task.updated_by = logged_in_user

    # update responsible
    if responsible != task.responsible:
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
        sequence = Sequence.query.filter_by(id=shot_sequence_id).first()
        if sequence:
            task.sequences = [sequence]
        task.cut_in = cut_in
        task.cut_out = cut_out
        task.fps = fps

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

    if good_id:
        good = Good.query.filter_by(id=good_id).first()
        if good:
            logger.debug('Good is found with name : %s' % good.name)
            task.good = good

    utc_now = datetime.datetime.now(pytz.utc)
    task.date_updated = utc_now

    # invalidate all caches
    invalidate_all_caches()

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
            'resource': ['Ozgur'],
            'resource_id': [23, 45, 58],
            'responsible_id': [25, 26],
            'path': ['108', '108|26']
        }

      will result a search string like::

        where (
            tasks.id = 23
            and tasks.name ilike '%Lighting%'
            and tasks.full_path ilike '%Lighting%'
            and tasks.entity_type ilike '%Task%'
            and task_types.name ilike '%Lighting%'
            and exists (
                select * from (
                    select unnest(resource_info.resource_name)
                ) x(resource_name)
                where x.resource_name like '%Ozgur%'
            )
            and (tasks.path ilike '%108%' or tasks.path ilike '%108|26%')
        )

      It will use only the available keys, so giving a dictionary like::

        params = {
            'id': 23,
            'resource': 'Ozgur'
        }

      will result::

        where (
            tasks.id = 23
            and exists (
                select * from (
                    select unnest(resource_info.resource_name)
                ) x(resource_name)
                where x.resource_name like '%Ozgur%'
            )
        )
    """

    where_string = ''
    where_string_buffer = []

    def compress_buffer(buff=None, conditional='or'):
        """returns a compressed buffer
        :param list buff: a list of strings to be compressed
        :param str conditional: 'or' or 'and' will be placed in between each
          compressed buffer element
        """
        if buff is None:
            buff = []

        template = '(%s)'  # for multiple conditions of same kind we need
                           # parentheses
        if len(buff) == 1:
            template = '%s'  # we have only 1 condition
                             # no need to have parentheses

        return template % (' %s ' % conditional).join(buff)

    # id
    temp_buffer = []
    for id_ in params.get('id[]', params.get('id', [])):
        temp_buffer.append(
            'tasks.id = {id}'.format(id=id_)
        )
    if len(temp_buffer):
        where_string_buffer.append(
            compress_buffer(temp_buffer, 'or')
        )

    # parent_id
    temp_buffer = []
    for parent_id in params.get('parent_id[]',
                                params.get('parent_id', [])):
        temp_buffer.append(
            "tasks.parent_id = {parent_id}".format(parent_id=parent_id)
        )
    if len(temp_buffer):
        where_string_buffer.append(
            compress_buffer(temp_buffer, 'or')
        )

    # name
    temp_buffer = []
    for name in params.get('name[]', params.get('name', [])):
        temp_buffer.append(
            "tasks.name ilike '%{name}%'".format(name=name)
        )
    if len(temp_buffer):
        where_string_buffer.append(
            compress_buffer(temp_buffer, 'or')
        )

    # path
    temp_buffer = []
    for name in params.get('path[]', params.get('path', [])):
        # name = "|%s|" % name
        temp_buffer.append(
            "tasks.path ilike '%{name}%'".format(name=name)
        )
    if len(temp_buffer):
        where_string_buffer.append(
            compress_buffer(temp_buffer, 'or')
        )

    # path
    temp_buffer = []
    for name in params.get('type_names[]', params.get('type_names', [])):
        name = "| %s |" % name
        temp_buffer.append(
            "tasks.type_names ilike '%{name}%'".format(name=name)
        )
    if len(temp_buffer):
        where_string_buffer.append(
            compress_buffer(temp_buffer, 'or')
        )

    # full_path
    temp_buffer = []
    for name in params.get('full_path[]', params.get('full_path', [])):
        temp_buffer.append(
            "tasks.full_path ilike '%{name}%'".format(name=name)
        )
    if len(temp_buffer):
        where_string_buffer.append(
            compress_buffer(temp_buffer, 'or')
        )

    # type_names
    # temp_buffer = []
    # for name in params.get('type_names[]', params.get('type_names', [])):
    #     temp_buffer.append(
    #         "tasks.type_names ilike '%{name}%'".format(name=name)
    #     )
    # if len(temp_buffer):
    #     where_string_buffer.append(
    #         compress_buffer(temp_buffer, 'or')
    #     )

    # entity_type
    temp_buffer = []
    for entity_type in params.get('entity_type[]',
                                  params.get('entity_type', [])):
        temp_buffer.append(
            "tasks.entity_type = '{entity_type}'".format(
                entity_type=entity_type
            )
        )
    if len(temp_buffer):
        where_string_buffer.append(
            compress_buffer(temp_buffer, 'or')
        )

    # task_type
    temp_buffer = []
    for task_type in params.get('task_type[]',
                                params.get('task_type', [])):
        temp_buffer.append(
            "task_types.name ilike '%{task_type}%'".format(task_type=task_type)
        )
    if len(temp_buffer):
        where_string_buffer.append(
            compress_buffer(temp_buffer, 'or')
        )

    # task_type_id
    temp_buffer = []
    for task_type_id in params.get('task_type_id[]',
                                params.get('task_type_id', [])):
        temp_buffer.append(
            "task_types.type_id = {task_type_id}".format(task_type_id=task_type_id)
        )
    if len(temp_buffer):
        where_string_buffer.append(
            compress_buffer(temp_buffer, 'or')
        )

    # project_id
    temp_buffer = []
    for project_id in params.get('project_id[]',
                                 params.get('project_id', [])):
        temp_buffer.append(
            """"Tasks".project_id = {project_id}""".format(
                project_id=project_id
            )
        )
    if len(temp_buffer):
        where_string_buffer.append(
            compress_buffer(temp_buffer, 'or')
        )

    # project_statuses
    temp_buffer = []
    for project_status in params.get('project_status[]', params.get('project_status', [])):
        temp_buffer.append(
            """"Project_Statuses".code = '{project_status}'""".format(
                project_status=project_status
            )
        )
    if len(temp_buffer):
        where_string_buffer.append(
            compress_buffer(temp_buffer, 'or')
        )

    # resource_id
    temp_buffer = []
    for resource_id in params.get('resource_id[]',
                                  params.get('resource_id', [])):
        temp_buffer.append(
            """exists (
        select * from (
            select unnest(resource_info.resource_id)
        ) x(resource_id)
        where x.resource_id = {resource_id}
    )""".format(resource_id=resource_id))
    if len(temp_buffer):
        where_string_buffer.append(
            compress_buffer(temp_buffer, 'or')
        )

    # resource_name
    temp_buffer = []
    for resource_name in \
        params.get('resource_name[]',
                   params.get('resource_name', [])):
        temp_buffer.append(
            """exists (
        select * from (
            select unnest(resource_info.resource_name)
        ) x(resource_name)
        where x.resource_name like '%{resource_name}%'
    )""".format(resource_name=resource_name))
    if len(temp_buffer):
        where_string_buffer.append(
            compress_buffer(temp_buffer, 'or')
        )

    # responsible_id
    temp_buffer = []
    for responsible_id in params.get('responsible_id[]',
                                     params.get('responsible_id', [])):
        temp_buffer.append(
            """{responsible_id} = any (tasks.responsible_id)""".format(
                responsible_id=responsible_id
            )
        )
    if len(temp_buffer):
        where_string_buffer.append(
            compress_buffer(temp_buffer, 'or')
        )

    # watcher_id
    temp_buffer = []
    for watcher_id in params.get('watcher_id[]',
                                 params.get('watcher_id', [])):
        temp_buffer.append(
            """{watcher_id} = any (tasks.watcher_id)""".format(
                watcher_id=watcher_id
            )
        )
    if len(temp_buffer):
        where_string_buffer.append(
            compress_buffer(temp_buffer, 'or')
        )

    statuses = params.get('status[]', params.get('status', []))
    if statuses:
        where_string_status = """("""
        where_string_status += \
            """\n{indent}"Statuses".code ilike '%{status}%'""".format(
                status=statuses[0],
                indent=' ' * 4
            )
        if len(statuses) > 1:
            for i in range(1, len(statuses)):
                where_string_status += \
                    """\n{indent}or "Statuses".code ilike '%{status}%'""".format(status=statuses[i], indent=' ' * 4)

        where_string_status += """\n    )"""

        where_string_buffer.append(where_string_status)

    if 'leaf_only' in params:
        where_string_buffer.append(
            """not exists (
        select 1 from "Tasks"
        where "Tasks".parent_id = tasks.id
    )""")

    if 'has_resource' in params:
        where_string_buffer.append(
            "resource_info.resource_id is not NULL"
        )

    if 'has_no_resource' in params:
        where_string_buffer.append(
            "resource_info.resource_id is NULL"
        )

    if len(where_string_buffer):
        # need to indent the first element by hand
        where_string_buffer[0] = '{indent}%s' % where_string_buffer[0]
        where_string = \
            'where (\n%s\n)' % '\n{indent}and '.join(where_string_buffer)
        where_string = where_string.format(indent=' ' * 4)

    # logger.debug("WHERE STRING: %s" % where_string)

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
        'id': 'id',
        'parent_id': "parent_id",
        'name': "name",
        'path': "full_path",
        'full_path': "full_path",
        'entity_type': "entity_type",
        'task_type': "task_types.name",
        'project_id': 'project_id',
        'date_created': 'date_created',
        'date_updated': 'date_updated',
        'has_children': 'has_children',
        'link': 'link',
        'priority': 'priority',
        'depends_to': 'dep_info',
        'resource': "resource_info.resource_id",
        'responsible': 'responsible_id',
        'watcher': 'watcher_id',
        'bid_timing': 'bid_timing',
        'bid_unit': 'bid_unit',
        'schedule_timing': 'schedule_timing',
        'schedule_unit': 'schedule_unit',
        'schedule_model': 'schedule_model',
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


def query_tasks(
        limit=None,
        offset=None,
        order_by_params=None,
        where_clause=None,
        task_id=None):
    """an intermediate function to make caching work flawlessly
    """
    return cached_query_tasks(
        limit,
        offset,
        order_by_params,
        where_clause,
        task_id)


@cache_region('long_term', 'load_tasks')
def cached_query_tasks(limit, offset, order_by_params, where_clause, task_id):
    """Query for tasks. Does some pretty amazing things.

    :param limit:
    :param offset:
    :param order_by_params:
    :param where_clause:
    :param task_id:
    :return:
    """
    start_time = time.time()

    entity_type = "Task"
    if task_id:
        # check if this is a Task or Project
        # get the entity_type of this data
        entity_type = DBSession.connection().execute(
            """select entity_type from "SimpleEntities" where id=%s""" %
            task_id
        ).fetchone()[0]
    else:
        task_id = -1

    logger.debug('entity_type: %s' % entity_type)

    if order_by_params is None:
        order_by_params = []

    order_by = generate_order_by_clause(order_by_params)
    if order_by == '':
        # use default
        order_by = 'order by tasks.name'

    if entity_type not in ['Project', 'Studio']:

        # logger.debug('where_clause: %s' % where_clause)

        sql_query = """
        select
            tasks.id as id,
            tasks.entity_type as entity_type,
            task_types.name as task_type,
            tasks.name as name,
            tasks.path as path,
            tasks.full_path as full_path,
            tasks.thumbnail_full_path,
            "Tasks".project_id as project_id,
            "Tasks".parent_id as parent_id,
            "Task_SimpleEntities".description as description,

            -- audit info
            (extract(epoch from "Task_SimpleEntities".date_created) * 1000)::bigint as date_created,
            (extract(epoch from "Task_SimpleEntities".date_updated) * 1000)::bigint as date_updated,

            exists (
                select 1
                from "Tasks" as "Child_Tasks"
                where "Child_Tasks".parent_id = "Tasks".id
            ) as "hasChildren",

            '/' || lower("Task_SimpleEntities".entity_type) || 's/' || "Tasks".id || '/view' as link,

            "Tasks".priority as priority,

            -- dep_info.info as dependencies,
            coalesce(dep_info.depends_to_id, '{}') as depends_to_ids,
            coalesce(dep_info.depends_to_name, '{}') as depends_to_names,

            -- resource_info.info as resources,
            coalesce(resource_info.resource_id, '{}') as resource_ids,
            coalesce(resource_info.resource_name, '{}') as resource_names,

            tasks.responsible_id as responsible,
            tasks.watcher_id as watcher,

            "Tasks".bid_timing as bid_timing,
            "Tasks".bid_unit as bid_unit,

            "Tasks".schedule_timing as schedule_timing,
            "Tasks".schedule_unit as schedule_unit,
            "Tasks".schedule_model as schedule_model,
            coalesce("Tasks".schedule_seconds,
                "Tasks".schedule_timing * (case "Tasks".schedule_unit
                    when 'min' then 60
                    when 'h' then 3600
                    when 'd' then 32400
                    when 'w' then 183600
                    when 'm' then 734400
                    when 'y' then 9573418
                    else 0
                end)
            ) as schedule_seconds,

            coalesce(
                -- for parent tasks
                "Tasks".total_logged_seconds,
                -- for child tasks we need to count the total seconds of related TimeLogs
                coalesce("Task_TimeLogs".duration, 0.0)
            )::int as total_logged_seconds,

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
                        when 'w' then 183600
                        when 'm' then 734400
                        when 'y' then 9573418
                        else 0
                    end)) * 100.0
            )::float as percent_complete,

            (extract(epoch from coalesce("Tasks".computed_start, "Tasks".end)) * 1000)::bigint as "start",
            (extract(epoch from coalesce("Tasks".computed_end, "Tasks".end)) * 1000)::bigint as "end",

            lower("Statuses".code) as status,
            "Status_SimpleEntities".name as status_name,
            tasks.type_names as type_names

        from (
            %(tasks_hierarchical_name)s
        ) as tasks
        join "Tasks" on tasks.id = "Tasks".id
        join "SimpleEntities" as "Task_SimpleEntities" on tasks.id = "Task_SimpleEntities".id

        -- Dependencies
        left outer join (
            select
                task_id,
                array_agg(depends_to_id) as depends_to_id,
                array_agg("SimpleEntities".name) as depends_to_name
            from "Task_Dependencies"
            join "SimpleEntities" on "Task_Dependencies".depends_to_id = "SimpleEntities".id
            group by task_id
        ) as dep_info on tasks.id = dep_info.task_id

        -- Resources
        left outer join (
            select
                "Tasks".id as task_id,
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
                extract(epoch from sum("TimeLogs".end - "TimeLogs".start)) as duration
            from "TimeLogs"
            group by task_id
        ) as "Task_TimeLogs" on "Task_TimeLogs".task_id = tasks.id

        -- Task Status
        join "Statuses" on "Tasks".status_id = "Statuses".id
        join "SimpleEntities" as "Status_SimpleEntities" on "Statuses".id = "Status_SimpleEntities".id

        -- Task Type
        left join (
            select
                "Tasks".id,
                "Type_SimpleEntities".name,
                "Type_SimpleEntities".id as type_id
            from "Tasks"
            join "SimpleEntities" as "Task_SimpleEntities" on "Tasks".id = "Task_SimpleEntities".id
            join "Types" on "Task_SimpleEntities".type_id = "Types".id
            join "SimpleEntities" as "Type_SimpleEntities" on "Types".id = "Type_SimpleEntities".id
        ) as task_types on tasks.id = task_types.id

        -- Project related data
        join "Projects" on "Tasks".project_id = "Projects".id
        join "Statuses" as "Project_Statuses" on "Projects".status_id = "Project_Statuses".id

        %(where_clause)s

        %(order_by)s
        """

        sql_query = sql_query % {
            'where_clause': where_clause,
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
            "Projects".id as path,
            "Project_SimpleEntities".name as full_path,
            coalesce("Project_Thumbnail".full_path) as thumbnail_full_path,

            NULL as project_id,
            NULL as parent_id,
            "Project_SimpleEntities".description as description,

            -- audit info
            (extract(epoch from "Project_SimpleEntities".date_created) * 1000)::bigint as date_created,
            (extract(epoch from "Project_SimpleEntities".date_updated) * 1000)::bigint as date_updated,

            exists (
                select 1
                from "Tasks" as "Child_Tasks"
                where "Child_Tasks".project_id = "Projects".id
            ) as "hasChildren",

            '/projects/' || "Projects".id || '/view' as link,

            500 as priority,

            '{}' as depends_to_ids,--array_agg((NULL, NULL)),
            '{}' as depends_to_names,--array_agg((NULL, NULL)),

            '{}' as resource_ids,--array_agg((NULL, NULL)),
            '{}' as resource_names,--array_agg((NULL, NULL)),

            '{}' as responsible,--array_agg((NULL, NULL)),
            '{}' as watcher,--array_agg((NULL, NULL)),

            0 as bid_timing,
            'min' as bid_unit,

            0 as schedule_timing,
            'min' as schedule_unit,
            'effort' as schedule_model,
            total_schedule_seconds as schedule_seconds,

            project_schedule_info.total_logged_seconds as total_logged_seconds,

            (project_schedule_info.total_logged_seconds / total_schedule_seconds * 100)::float as percent_complete,

            (extract(epoch from coalesce("Projects".computed_start, "Projects".end)) * 1000)::bigint as "start",
            (extract(epoch from coalesce("Projects".computed_end, "Projects".end)) * 1000)::bigint as "end",

            lower("Statuses".code) as status,
            "Status_SimpleEntities".name as status_name,
            '' as type_names

        from "Projects"
        join "SimpleEntities" as "Project_SimpleEntities" on "Projects".id = "Project_SimpleEntities".id
        left outer join "Links" as "Project_Thumbnail" on "Project_SimpleEntities".thumbnail_id = "Project_Thumbnail".id
        join "Statuses" on "Projects".status_id = "Statuses".id
        join "SimpleEntities" as "Status_SimpleEntities" on "Statuses".id = "Status_SimpleEntities".id
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
                                when 'w' then 183600
                                when 'm' then 734400
                                when 'y' then 9573418
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
                    extract(epoch from sum("TimeLogs".end - "TimeLogs".start))::bigint as duration
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

    if offset:
        sql_query = '%s offset %s' % (sql_query, offset)

    if limit and int(limit) > 0:
        sql_query = '%s limit %s' % (sql_query, limit)

    from sqlalchemy import text  # to be able to use "%" sign use this function

    result = DBSession.connection().execute(text(sql_query))

    return_data = [
        {
            'id': r['id'],
            'entity_type': r['entity_type'],
            'task_type': r['task_type'],
            'name': r['name'],
            'path': r['path'],
            'full_path': r['full_path'],
            'thumbnail_full_path': r['thumbnail_full_path'],
            'project_id': r['project_id'],
            'parent_id': r['parent_id'],
            'description': r['description'],
            'date_created': r['date_created'],
            'date_updated': r['date_updated'],
            'hasChildren': r['hasChildren'],
            'link': r['link'],
            'priority': r['priority'],
            'dependencies': list(map(lambda x, y: {'id': x, 'name': y}, r['depends_to_ids'], r['depends_to_names'])),
            'resources': list(map(lambda x, y: {'id': x, 'name': y}, r['resource_ids'], r['resource_names'])),
            'responsible': r['responsible'],
            'watcher': r['watcher'],
            'bid_timing': r['bid_timing'],
            'bid_unit': r['bid_unit'],
            'schedule_timing': r['schedule_timing'],
            'schedule_unit': r['schedule_unit'],
            'schedule_model': r['schedule_model'],
            'schedule_seconds': r['schedule_seconds'],
            'total_logged_seconds': r['total_logged_seconds'],
            'completed': r['percent_complete'],
            'start': r['start'],
            'end': r['end'],
            'status': r['status'],
            'status_name': r['status_name'],
            'type_names': r['type_names']
        }
        for r in result.fetchall()
    ]

    # logger.debug('return_data: %s' % return_data)
    end_time = time.time()
    logger.debug('%s rows retrieved in %s seconds' % (len(return_data),
                                                      (end_time - start_time)))
    return return_data


@view_config(
    route_name='get_tasks',
    renderer='json'
)
def get_tasks(request):
    """RESTful version of getting all tasks
    """
    logger.debug('get_tasks is running')
    global_start_time = start_time = time.time()
    # set the content range to prevent JSONRest Store to query the data twice

    offset = int(request.params.get('offset', 0))
    limit = request.params.get('limit')

    logger.debug('offset: %s' % offset)
    logger.debug('limit: %s' % limit)

    order_by_params = request.GET.getall('order_by')
    logger.debug('order_by_params: %s' % order_by_params)

    where_clause = generate_where_clause(request.params.dict_of_lists())
    end_time = time.time()
    logger.debug('generate_where_clause: %s seconds' % (end_time - start_time))

    start_time = time.time()
    task_id = None
    if 'id' in request.params:
        # check if this is a Task or Project
        task_id = int(request.params.get('id', -1))

    return_data = query_tasks(
        limit=limit,
        offset=offset,
        order_by_params=order_by_params,
        where_clause=where_clause,
        task_id=task_id,
    )
    end_time = time.time()
    logger.debug(
        'query_tasks: %s seconds' % (end_time - start_time)
    )

    task_count = len(return_data)
    content_range = '%s-%s/%s' % (offset, offset + task_count - 1, task_count)

    # print(return_data)

    resp = Response(
        json_body=return_data
    )
    resp.content_range = content_range
    global_end = time.time()
    logger.debug(
        'GET_TASKS: %s rows retrieved in %s seconds' % (
            len(return_data), (global_end - global_start_time)
        )
    )

    return resp


@cache_region('long_term', 'load_tasks')
def get_entity_type(entity_id):
    """returns entity_type of the given entity with the given entity_id
    """
    return DBSession.connection().execute(
        """select entity_type from "SimpleEntities" where id=%s""" %
        entity_id
    ).fetchone()[0]


@cache_region('long_term', 'load_tasks')
def get_cached_tasks_count(entity_type, where_clause, task_id):
    """returns a cached value of tasks count
    """
    logger.debug('entity_type: %s' % entity_type)

    if entity_type not in ['Project', 'Studio']:

        # logger.debug('where_clause: %s' % where_clause)

        sql_query = """select count(result.id) from (
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
            (extract(epoch from "Task_SimpleEntities".date_created) * 1000)::bigint as date_created,
            (extract(epoch from "Task_SimpleEntities".date_updated) * 1000)::bigint as date_updated,

            exists (
                select 1
                from "Tasks" as "Child_Tasks"
                where "Child_Tasks".parent_id = "Tasks".id
            ) as has_children,

            '/' || lower("Task_SimpleEntities".entity_type) || 's/' || "Tasks".id || '/view' as link,

            "Tasks".priority as priority,

            coalesce(dep_info.depends_to_id, '{}') as depends_to_ids,
            coalesce(dep_info.depends_to_name, '{}') as depends_to_names,
            coalesce(resource_info.resource_id, '{}') as resource_ids,
            coalesce(resource_info.resource_name, '{}') as resource_names,

            tasks.responsible_id,
            tasks.watcher_id,

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
                    when 'w' then 183600
                    when 'm' then 734400
                    when 'y' then 9573418
                    else 0
                end)
            ) as schedule_seconds,

            coalesce(
                -- for parent tasks
                "Tasks".total_logged_seconds::int,
                -- for child tasks we need to count the total seconds of related TimeLogs
                coalesce("Task_TimeLogs".duration, 0.0)
            ) as total_logged_seconds,

            coalesce(
                -- for parent tasks
                (case "Tasks".schedule_seconds
                    when 0 then 0
                    else "Tasks".total_logged_seconds / "Tasks".schedule_seconds * 100
                 end
                ),
                -- for child tasks we need to count the total seconds of related TimeLogs
                (coalesce("Task_TimeLogs".duration, 0.0)) /
                    ("Tasks".schedule_timing * (case "Tasks".schedule_unit
                        when 'min' then 60
                        when 'h' then 3600
                        when 'd' then 32400
                        when 'w' then 183600
                        when 'm' then 734400
                        when 'y' then 9573418
                        else 0
                    end)) * 100.0
            )::float as percent_complete,

            (extract(epoch from coalesce("Tasks".computed_start, "Tasks".end)) * 1000)::bigint as "start",
            (extract(epoch from coalesce("Tasks".computed_end, "Tasks".end)) * 1000)::bigint as "end",

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
                array_agg(depends_to_id) as depends_to_id,
                array_agg("SimpleEntities".name) as depends_to_name
            from "Task_Dependencies"
            join "SimpleEntities" on "Task_Dependencies".depends_to_id = "SimpleEntities".id
            group by task_id
        ) as dep_info on tasks.id = dep_info.task_id
        -- Resources
        left outer join (
            select
                "Tasks".id as task_id,
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
                extract(epoch from sum("TimeLogs".end - "TimeLogs".start)) as duration
            from "TimeLogs"
            group by task_id
        ) as "Task_TimeLogs" on "Task_TimeLogs".task_id = tasks.id

        -- Task Status
        join "Statuses" on "Tasks".status_id = "Statuses".id

        -- Task Type
        left join (
            select
                "Tasks".id,
                "Type_SimpleEntities".name,
                "Type_SimpleEntities".id as type_id
            from "Tasks"
            join "SimpleEntities" as "Task_SimpleEntities" on "Tasks".id = "Task_SimpleEntities".id
            join "Types" on "Task_SimpleEntities".type_id = "Types".id
            join "SimpleEntities" as "Type_SimpleEntities" on "Types".id = "Type_SimpleEntities".id
        ) as task_types on tasks.id = task_types.id

        -- Project related data
        join "Projects" on "Tasks".project_id = "Projects".id
        join "Statuses" as "Project_Statuses" on "Projects".status_id = "Project_Statuses".id

        %(where_clause)s
        ) as result
        """

        sql_query = sql_query % {
            'where_clause': where_clause,
            'tasks_hierarchical_name':
                generate_recursive_task_query(ordered=False)
        }

    else:
        sql_query = """
        -- Projects Part
        select count(result.id) from (
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
            (extract(epoch from "Project_SimpleEntities".date_created) * 1000)::bigint as date_created,
            (extract(epoch from "Project_SimpleEntities".date_updated) * 1000)::bigint as date_updated,

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
            NULL,--array_agg((NULL, NULL)),

            0 as bid_timing,
            'min' as bid_unit,

            0 as schedule_timing,
            'min' as schedule_unit,
            'effort' as schedule_model,
            total_schedule_seconds as schedule_seconds,

            project_schedule_info.total_logged_seconds as total_logged_seconds,

            project_schedule_info.total_logged_seconds / total_schedule_seconds  * 100 as percent_complete,

            (extract(epoch from coalesce("Projects".computed_start, "Projects".end)) * 1000)::bigint as "start",
            (extract(epoch from coalesce("Projects".computed_end, "Projects".end)) * 1000)::bigint as "end",

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
                                when 'w' then 183600
                                when 'm' then 734400
                                when 'y' then 9573418
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
                    extract(epoch from sum("TimeLogs".end - "TimeLogs".start)) as duration
                from "TimeLogs"
                group by task_id
            ) as "Task_TimeLogs" on "Task_TimeLogs".task_id = "Tasks".id

            where "Tasks".parent_id is NULL
            group by "Tasks".project_id
        ) as project_schedule_info on "Projects".id = project_schedule_info.project_id
        ) as result
        """

        if entity_type == 'Project':
            sql_query = '%s %s' % (
                sql_query,
                'where "Projects".id = %s' % task_id
            )
    from sqlalchemy import text  # to be able to use "%" sign use this function

    result = DBSession.connection().execute(text(sql_query))

    tasks_count = result.fetchone()

    if tasks_count:
        return tasks_count[0]
    else:
        return 0


@view_config(
    route_name='get_tasks_count',
    renderer='json'
)
def get_tasks_count(request):
    """RESTful version of getting all tasks
    """
    logger.debug('get_tasks_count is running')

    # set the content range to prevent JSONRest Store to query the data twice
    content_range = '%s-%s/%s'

    entity_type = "Task"
    task_id = -1
    if 'id' in request.params:
        # check if this is a Task or Project
        task_id = int(request.params.get('id', -1))

        # get the entity_type of this data
        entity_type = get_entity_type(task_id)

    where_clause = ''
    if entity_type not in ['Project', 'Studio']:
        where_clause = generate_where_clause(request.params.dict_of_lists())

    return get_cached_tasks_count(entity_type, where_clause, task_id)


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

    open_projects = request.params.get('open_projects')

    return_data = []
    # set the content range to prevent JSONRest Store to query the data twice
    content_range = '%s-%s/%s'

    if entity:
        if parent:
            # logger.debug('there is a parent')
            tasks = []
            if isinstance(entity, User):
                # get user tasks
                # only include open_projects
                if open_projects:
                    entity_tasks = Task.query.join(Project).filter(Task.resources.contain(entity)).filter()
                else:
                    rts = Status.query.filter(Status.code == 'RTS').first()
                    wip = Status.query.filter(Status.code == 'WIP').first()
                    entity_tasks = DBSession.query(Task).join(Task.project).filter(Task.resources.contains(entity)).filter(Project.status_id.in_([rts.id, wip.id])).all()

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
            # logger.debug('no parent')
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


@cache_region('long_term', 'load_tasks')
def get_cached_user_tasks(statuses, user_id, project_statuses=None):
    """it is an intermediate function to make caching work
    """

    sql_query = """select
        "Tasks".id  as task_id,
        "ParentTasks".full_path as task_name,
        "Task_SimpleEntities".name as short_name

    from "Tasks"
        join "Task_Resources" on "Task_Resources".task_id = "Tasks".id
        join "Statuses" as "Task_Statuses" on "Task_Statuses".id = "Tasks".status_id
        join "SimpleEntities" as "Task_SimpleEntities" on "Task_SimpleEntities".id = "Tasks".id
        join "Projects" on "Tasks".project_id = "Projects".id
        join "Statuses" as "Project_Statuses" on "Projects".status_id = "Project_Statuses".id
        left join (
            %(generate_recursive_task_query)s
        ) as "ParentTasks" on "Tasks".id = "ParentTasks".id
        %(where_clause)s
    """
    where_clause = 'where "Task_Resources".resource_id = %s' % user_id
    if statuses:
        temp_buffer = [where_clause, """ and ("""]
        for i, status in enumerate(statuses):
            if i > 0:
                temp_buffer.append(' or')
            temp_buffer.append(""" "Task_Statuses".code='%s'""" % status.code)
        temp_buffer.append(' )')
        where_clause = ''.join(temp_buffer)

    if project_statuses:
        temp_buffer = [where_clause, """ and ("""]
        for i, status in enumerate(project_statuses):
            if i > 0:
                temp_buffer.append(' or')
            temp_buffer.append(""" "Project_Statuses".code='%s'""" % status.code)
        temp_buffer.append(' )')
        where_clause = ''.join(temp_buffer)

    logger.debug('where_clause: %s' % where_clause)
    sql_query = sql_query % {
        'generate_recursive_task_query': generate_recursive_task_query(),
        'where_clause': where_clause
    }
    result = DBSession.connection().execute(sql_query)
    return_data = [
        {
            'id': r[0],
            'name': r[1],
            'short_name': r[2]
        }
        for r in result.fetchall()
    ]
    return return_data


@view_config(
    route_name='get_user_tasks_simple',
    renderer='json'
)
def get_user_tasks_simple(request):
    """return user's task with a simple methot for view user page
    """
    logger.debug("get_user_tasks_simple")

    user_id = request.matchdict.get('id', -1)
    user = User.query.filter(User.id == user_id).first()

    logger.debug("user_id: %s" % user_id)

    if not user:
        transaction.abort()
        return Response("No user found by the id: %s" % user_id)

    status_code = request.params.get('status_code', None)
    status = Status.query.filter(Status.code == status_code.upper()).first()

    logger.debug("status_code: %s" % status_code)

    if not status:
        transaction.abort()
        return Response("No status found by the code: %s" % status_code)

    project_id = request.params.get('project_id', None)
    project = Project.query.filter(Project.id == project_id).first()

    logger.debug("project_id: %s" % project_id)

    if not project:
        transaction.abort()
        return Response("No project found by the id: %s" % project_id)

    sql_query = """select
        "Tasks".id,
        tasks.name,
        tasks.full_path,

        tasks.thumbnail_full_path,

        "Tasks".project_id,
        "Tasks".parent_id,
        "Tasks".priority as priority,

        "Tasks".bid_timing,
        "Tasks".bid_unit,

        "Tasks".schedule_timing,
        "Tasks".schedule_unit,
        "Tasks".schedule_model,

        coalesce(
            "Tasks".total_logged_seconds::int,
            coalesce("Task_TimeLogs".duration, 0)::int
        ) as total_logged_seconds,

        "Tasks".start,
        "Tasks".end

        from (

    with recursive recursive_task(id, path_names) as (
        select
            task.id,
            ("Projects".code || '') as path_names,
            "Task_Thumbnail".full_path as thumbnail_full_path
        from "Tasks" as task
        join "SimpleEntities" as "Task_SimpleEntities" on task.id = "Task_SimpleEntities".id
        left outer join "Links" as "Task_Thumbnail" on "Task_SimpleEntities".thumbnail_id = "Task_Thumbnail".id 
        join "Projects" on task.project_id = "Projects".id
        where task.parent_id is NULL
    union all
        select
            task.id,
            (parent.path_names || ' | ' || "Parent_SimpleEntities".name) as path_names,
            coalesce(
                thumbnail_full_path,
                "Parent_Task_Thumbnail".full_path
            ) as thumbnail_full_path
        from "Tasks" as task
        join recursive_task as parent on task.parent_id = parent.id
        join "SimpleEntities" as "Parent_SimpleEntities" on parent.id = "Parent_SimpleEntities".id
        left outer join "Links" as "Parent_Task_Thumbnail" on "Parent_SimpleEntities".thumbnail_id = "Parent_Task_Thumbnail".id
    ) select
        recursive_task.id,
        "SimpleEntities".name as name,
        recursive_task.path_names,
        "SimpleEntities".name || ' (' || recursive_task.path_names || ')(' || recursive_task.id || ')' as full_path,
        recursive_task.thumbnail_full_path as thumbnail_full_path
    from recursive_task
    join "SimpleEntities" on recursive_task.id = "SimpleEntities".id

        ) as tasks
        join "Tasks" on tasks.id = "Tasks".id

        -- Resources
        left outer join (
            select
                "Tasks".id as task_id,
                array_agg("Task_Resources".resource_id) as resource_id
            from "Tasks"
            join "Task_Resources" on "Tasks".id = "Task_Resources".task_id
            group by "Tasks".id
        ) as resource_info on "Tasks".id = resource_info.task_id

        -- TimeLogs for Leaf Tasks
        left outer join (
            select
                "TimeLogs".task_id,
                extract(epoch from sum("TimeLogs".end - "TimeLogs".start)) as duration
            from "TimeLogs"
            group by task_id
        ) as "Task_TimeLogs" on "Task_TimeLogs".task_id = tasks.id

        -- Task Status
        join "Statuses" on "Tasks".status_id = "Statuses".id

        where (
                "Tasks".project_id = %(project_id)s
                and exists (
                    select * from (
                        select unnest(resource_info.resource_id)
                    ) x(resource_id)
                    where x.resource_id = %(user_id)s
                )
                and (
                "Statuses".code ilike '%%%(status_code)s%%'
                )
                and not exists (
                    select 1 from "Tasks"
                    where "Tasks".parent_id = tasks.id
                )
            )

    order by tasks.name"""

    sql_query = sql_query % {
        'project_id': project.id,
        'status_code': status.code,
        'user_id': user.id
    }

    # logger.debug("sql_query %s" % sql_query)

    start = time.time()
    from sqlalchemy import text
    result = DBSession.connection().execute(text(sql_query))

    return_data = [
        {
            'id': r['id'],
            'name': r['name'],
            'full_path': r["full_path"],
            'thumbnail_full_path': r["thumbnail_full_path"],
            'project_id': r["project_id"],
            'parent_id': r["parent_id"],
            'priority': r["priority"],
            'bid_timing': r["bid_timing"],
            'bid_unit': r["bid_unit"],
            'schedule_timing': r["schedule_timing"],
            'schedule_unit': r["schedule_unit"],
            'schedule_model': r["schedule_model"],
            'total_logged_seconds': r["total_logged_seconds"],
            'start': milliseconds_since_epoch(r["start"]),
            'end': milliseconds_since_epoch(r["end"])
        }
        for r in result.fetchall()
    ]
    end = time.time()
    logger.debug('get_user_task_simple took: %s seconds' %
                 (end - start))
    return return_data


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
    statuses = []
    status_codes = request.GET.getall('status')
    if status_codes:
        statuses = Status.query.filter(Status.code.in_(status_codes)).all()

    project_statuses = []
    project_status_codes = request.GET.getall('project_status')
    logger.debug("project_status_codes: %s" % project_status_codes)
    if project_status_codes:
        project_statuses = Status.query.filter(Status.code.in_(project_status_codes)).all()

    return_data = get_cached_user_tasks(statuses, user_id, project_statuses)

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

    # logger.debug('entity : %s' % entity)

    tasks = []
    if entity:
        if isinstance(entity, Project):
            # return both the project and the root tasks of its
            project = entity
            dgrid_data = convert_to_dgrid_gantt_project_format([project])
            dgrid_data.extend(convert_to_dgrid_gantt_task_format(project.root_tasks))
            return dgrid_data
        elif isinstance(entity, User):
            user = entity
            # sort the tasks with the project.id
            if user is not None:
                # TODO: just return root tasks to make it fast
                # get the user projects and then tasks of the user
                dgrid_data = convert_to_dgrid_gantt_project_format(user.projects)

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

    # get open_projects parameter
    open_projects = request.GET.get("open_projects")

    if not open_projects:
        sql_query = """select count(task_id)
from "Task_Resources"
where "Task_Resources".resource_id = %s
""" % user_id
    else:
        sql_query = """select count(task_id)
from "Task_Resources"
join "Tasks" on "Task_Resources".task_id = "Tasks".id
join "Projects" on "Tasks".project_id = "Projects".id
join "Statuses" on "Projects".status_id = "Statuses".id
where "Task_Resources".resource_id = %s and ("Statuses".code = 'RTS' or "Statuses".code = 'WIP')
""" % user_id

    return DBSession.connection().execute(sql_query).fetchone()[0]


@cache_region('long_term', 'load_tasks')
def get_cached_entity_tasks_stats(entity, entity_id, project):
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

        %(where_clause_for_entity)s

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
    where_clause_for_entity = ''
    if isinstance(entity, User):
        where_clause_for_entity = \
            'join "Task_Resources" on "Task_Resources".task_id = "Tasks".id ' \
            'where "Task_Resources".resource_id =%s' % entity_id
        if project:
            where_clause_for_entity += ' and "Tasks".project_id = %s' % project.id
    elif isinstance(entity, Project):
        where_clause_for_entity = 'where "Tasks".project_id =%s' % entity_id
    sql_query = sql_query % {
        'where_clause_for_entity': where_clause_for_entity
    }

    #logger.debug("sql_query: %s" % sql_query)
    # convert to dgrid format right here in place
    result = DBSession.connection().execute(sql_query)
    return_data = [
        {
            'tasks_count': r[0],
            'status_id': r[1],
            'status_code': r[2],
            'status_name': r[3],
            'status_color': r[4],
            'status_icon': ''
        }
        for r in result.fetchall()
    ]
    return return_data


@view_config(
    route_name='get_entity_tasks_stats',
    renderer='json'
)
def get_entity_tasks_stats(request):
    """runs when viewing an task
    """
    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    project_id = request.params.get('project_id', -1)
    project = Project.query.filter_by(id=project_id).first()

    logger.debug('get_entity_tasks_stats is starts')

    return_data = get_cached_entity_tasks_stats(entity, entity_id, project)

    resp = Response(
        json_body=return_data
    )
    # resp.content_range = content_range
    return resp


@cache_region('long_term', 'load_tasks')
def get_cached_tasks_stats(entity, entity_id, project):
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

        %(where_clause_for_entity)s

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
    where_clause_for_entity = ''
    if isinstance(entity, User):
        where_clause_for_entity = \
            'join "Task_Resources" on "Task_Resources".task_id = "Tasks".id ' \
            'where "Task_Resources".resource_id = %s' % entity_id
        if project:
            where_clause_for_entity += ' and "Tasks".project_id = %s' % project.id
    elif isinstance(entity, Project):
        where_clause_for_entity = 'where "Tasks".project_id =%s' % entity_id
    sql_query = sql_query % {
        'where_clause_for_entity': where_clause_for_entity
    }

    logger.debug("sql_query: %s" % sql_query)
    # convert to dgrid format right here in place
    result = DBSession.connection().execute(sql_query)
    return_data = [
        {
            'tasks_count': r['count'],
            'status_id': r['status_id'],
            'status_code': r['status_code'],
            'status_name': r['status_name'],
            'status_color': r['status_color'],
            'status_icon': ''
        }
        for r in result.fetchall()
    ]
    return return_data


@view_config(
    route_name='get_tasks_stats',
    renderer='json'
)
def get_tasks_stats(request):
    """runs when viewing an task
    """
    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    project_id = request.params.get('project_id', -1)
    project = Project.query.filter_by(id=project_id).first()

    logger.debug('get_cached_tasks_stats is starts')

    return_data = get_cached_tasks_stats(entity, entity_id, project)

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

    sql_query = """
select
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
            when 'w' then 183600
            when 'm' then 734400
            when 'y' then 9573418
            else 0
        end)
        ) * 100.0 as percent_complete,
    array_agg("Resource_SimpleEntities".id) as resource_id,
    array_agg("Resource_SimpleEntities".name) as resource_name,
    "Statuses_SimpleEntities".name as status_name,
    "Statuses".code as status_code,
    "Statuses_SimpleEntities".html_class as status_color,
    "Project_SimpleEntities".id as project_id,
    "Project_SimpleEntities".name as project_name,
    array_agg("Reviewers".reviewer_id) as reviewer_id,
    ((("Tasks".schedule_timing * (case "Tasks".schedule_unit
            when 'min' then 60
            when 'h' then 3600
            when 'd' then 32400
            when 'w' then 183600
            when 'm' then 734400
            when 'y' then 9573418
            else 0
        end)) - coalesce("Task_TimeLogs".duration, 0.0)) / 3600
    ) as hour_to_complete,
    coalesce("Tasks".computed_start,"Tasks".start) as start_date,
    "Tasks".priority as priority,

    (
        (
            ("Tasks".bid_timing * (
                case "Tasks".bid_unit
                    when 'min' then 60
                    when 'h' then 3600
                    when 'd' then 32400
                    when 'w' then 183600
                    when 'm' then 734400
                    when 'y' then 9573418
                else 0
                end
            )
        ) - coalesce("Task_TimeLogs".duration, 0.0)) / 3600.0
    ) as hour_based_on_bid

from "Tasks"
    join "Task_Resources" on "Task_Resources".task_id = "Tasks".id
    join "SimpleEntities" as "Project_SimpleEntities"on "Project_SimpleEntities".id = "Tasks".project_id
    join "Statuses" on "Statuses".id = "Tasks".status_id
    join "SimpleEntities" as "Statuses_SimpleEntities" on "Statuses_SimpleEntities".id = "Statuses".id
    left outer join (
        select
            "TimeLogs".task_id,
            extract(epoch from sum("TimeLogs".end - "TimeLogs".start)) as duration
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
            -1 --"Projects".lead_id
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

    where %(where_clause_for_entity)s %(where_clause_for_filter)s

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
    where_clause_for_entity = ''

    if isinstance(entity, User):
        where_clause_for_entity = '"Task_Resources".resource_id = %s' % entity_id
    elif isinstance(entity, Project):
        where_clause_for_entity = '"Tasks".project_id =%s' % entity_id

    where_clause_for_filter = ''
    if isinstance(filter_, User):
        where_clause_for_entity = ''
        where_clause_for_filter = '"Tasks_Responsible".responsible_id = %s' % filter_id
    elif isinstance(filter_, Status):
        where_clause_for_filter = 'and "Statuses_SimpleEntities".id = %s' % filter_id

    sql_query = sql_query % {
        'generate_recursive_task_query': generate_recursive_task_query(),
        'where_clause_for_entity': where_clause_for_entity,
        'where_clause_for_filter': where_clause_for_filter
    }

    # convert to dgrid format right here in place
    result = DBSession.connection().execute(sql_query)

    return_data = [
        {
            'id': r["task_id"],
            'name': r["task_name"],
            'responsible_id': r["responsible_id"],
            'responsible_name': r["responsible_name"],
            'type': r["type_name"],
            'percent_complete': r["percent_complete"],
            'resource_id': r["resource_id"],
            'resource_name': r["resource_name"],
            'status': r["status_name"],
            'status_code': r["status_code"],
            'status_color': r["status_color"],
            'project_id': r["project_id"],
            'project_name': r["project_name"],
            'request_review': '1' if (logged_in_user.id in r["resource_id"] or r["responsible_id"] == logged_in_user.id) and r["reviewer_id"] == 'WIP' else None,
            'review': '1' if logged_in_user.id in r["reviewer_id"] and r["reviewer_id"] == 'PREV' else None,
            'hour_to_complete':r["hour_to_complete"],
            'hour_based_on_bid':r["hour_based_on_bid"],
            'start_date':milliseconds_since_epoch(r["start_date"]),
            'priority':r["priority"]
        }
        for r in result.fetchall()
    ]

    # task_count = len(return_data)
    # content_range = content_range % (0, task_count - 1, task_count)

    # logger.debug('return_data: %s' % return_data)
    # end = time.time()

    resp = Response(
        json_body=return_data
    )
    # resp.content_range = content_range
    return resp


@view_config(
    route_name='get_task_leafs_in_hierarchy',
    renderer='json'
)
def get_task_leafs_in_hierarchy(request):
    """finds last leaf tasks under a parent task
    """
    logger.debug('get_task_leafs_in_hierarchy is running!')
    task_id = request.matchdict.get('id', -1)
    task = Task.query.filter(Task.id == task_id).first()

    sql_query = """
        Select
            "Tasks".id,
            "Task_SimpleEntities".name,
            "Type_SimpleEntities".name as type_name,
            "Tasks".bid_timing,
            "Tasks".bid_unit,
            "Tasks".schedule_timing,
            "Tasks".schedule_unit,
            coalesce( extract(epoch from sum("TimeLogs".end - "TimeLogs".start))::int, 0) as total_logged_seconds,
            "Statuses".code
        from (
            %(generate_recursive_task_query)s
        ) as tasks
        join "Tasks" on tasks.id = "Tasks".id
        join "SimpleEntities" as "Task_SimpleEntities" on "Task_SimpleEntities".id = "Tasks".id
        join "SimpleEntities" as "Type_SimpleEntities" on "Type_SimpleEntities".id = "Task_SimpleEntities".type_id
        left join "TimeLogs" on "TimeLogs".task_id = "Tasks".id
        join "Statuses" on "Statuses".id = "Tasks".status_id
        where tasks.path ilike '%%|%(task_id)s|%%' and not exists (
        select 1 from "Tasks"
        where "Tasks".parent_id = tasks.id)
        group by "Tasks".id,
            "Task_SimpleEntities".name,
            "Type_SimpleEntities".name,
            "Tasks".bid_timing,
            "Tasks".bid_unit,
            "Tasks".schedule_timing,
            "Tasks".schedule_unit,
            "Statuses".code
    """
    sql_query = sql_query % {
        'generate_recursive_task_query': generate_recursive_task_query(),
        'task_id': task.id
    }

    # logger.debug(sql_query)

    from sqlalchemy import text  # to be able to use "%" sign use this function
    result = DBSession.connection().execute(text(sql_query))

    return [
        {
            'id': r[0],
            'name': r[1],
            'type': r[2],
            'bid_timing': r[3],
            'bid_unit': r[4],
            'schedule_timing': r[5],
            'schedule_unit': r[6],
            'total_logged_seconds': r[7],
            'status_code':r[8]
        }
        for r in result.fetchall()
    ]


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
    renderer='templates/task/dialog/task_dialog.jinja2',
    permission='Create_Task'
)
def create_task_dialog(request):
    """called when creating tasks
    """
    return data_dialog(request, mode='create', entity_type='Task')


@view_config(
    route_name='update_task_dialog',
    renderer='templates/task/dialog/task_dialog.jinja2',
    permission='Update_Task'
)
def update_task_dialog(request):
    """called when updating tasks
    """
    return data_dialog(request, mode='update', entity_type='Task')


@view_config(
    route_name='create_asset_dialog',
    renderer='templates/task/dialog/task_dialog.jinja2',
    permission='Create_Task'
)
def create_asset_dialog(request):
    """called when creating assets
    """
    return data_dialog(request, mode='create', entity_type='Asset')


@view_config(
    route_name='update_asset_dialog',
    renderer='templates/task/dialog/task_dialog.jinja2',
    permission='Update_Task'
)
def update_asset_dialog(request):
    """called when updating assets
    """
    return data_dialog(request, mode='update', entity_type='Asset')


@view_config(
    route_name='create_shot_dialog',
    renderer='templates/task/dialog/task_dialog.jinja2',
    permission='Create_Task'
)
def create_shot_dialog(request):
    """called when creating shots
    """
    return data_dialog(request, mode='create', entity_type='Shot')


@view_config(
    route_name='update_shot_dialog',
    renderer='templates/task/dialog/task_dialog.jinja2',
    permission='Update_Task'
)
def update_shot_dialog(request):
    """called when updating shots
    """
    return data_dialog(request, mode='update', entity_type='Shot')


@view_config(
    route_name='create_sequence_dialog',
    renderer='templates/task/dialog/task_dialog.jinja2',
    permission='Create_Task'
)
def create_sequence_dialog(request):
    """called when creating sequences
    """
    return data_dialog(request, mode='create', entity_type='Sequence')


@view_config(
    route_name='update_sequence_dialog',
    renderer='templates/task/dialog/task_dialog.jinja2',
    permission='Update_Task'
)
def update_sequence_dialog(request):
    """called when updating sequences
    """
    return data_dialog(request, mode='update', entity_type='Sequence')


@view_config(
    route_name='create_task',
    permission='Create_Task',
)
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
    good_id = request.params.get('good_id')

    code = request.params.get('code', '')
    entity_type = request.params.get('entity_type')
    asset_type = request.params.get('asset_type')
    task_type = request.params.get('task_type')
    shot_sequence_id = request.params.get('shot_sequence_id')

    cut_in = request.params.get('cut_in')
    cut_out = request.params.get('cut_out')
    fps = request.params.get('fps')

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
    logger.debug('good_id            : %s' % good_id)
    logger.debug('shot_sequence_id    : %s' % shot_sequence_id)
    logger.debug('cut_in              : %s' % cut_in)
    logger.debug('cut_out             : %s' % cut_out)
    logger.debug('fps                 : %s' % fps)

    kwargs = {}
    if not all(ord(c) < 128 for c in name):
        transaction.abort()
        return Response('Turkce Karakter Kullanma!!!', 500)

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
    utc_now = datetime.datetime.now(pytz.utc)
    kwargs['date_created'] = utc_now

    kwargs['status_list'] = status_list

    kwargs['schedule_model'] = schedule_model
    kwargs['schedule_timing'] = schedule_timing
    kwargs['schedule_unit'] = schedule_unit

    kwargs['responsible'] = responsible
    kwargs['resources'] = resources
    kwargs['depends'] = depends

    kwargs['priority'] = priority

    if good_id:
        good = Good.query.filter_by(id=good_id).first()
        if good:
            logger.debug('Good is found with name : %s' % good.name)
            kwargs['good'] = good

    type_name = ''
    if entity_type == 'Asset':
        type_name = asset_type
    elif entity_type == 'Task':
        type_name = task_type
    kwargs['type'] = query_type(entity_type, type_name)

    if entity_type == 'Shot':
        if shot_sequence_id:
            sequence = Sequence.query.filter_by(id=shot_sequence_id).first()
            kwargs['sequences'] = [sequence]
        kwargs['cut_in'] = int(cut_in or 1)
        kwargs['cut_out'] = int(cut_out or 1)
        kwargs['fps'] = int(fps or 1)

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

    # invalidate all caches
    invalidate_all_caches()

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
    route_name='cleanup_task_new_reviews',
)
def cleanup_task_new_reviews(request):
    """works when task has at least one answered review
    """
    logger.debug('cleanup_task_new_reviews is starts')

    logged_in_user = get_logged_in_user(request)

    multi_permission_checker(request, ['Update_Task', 'Update_Review'])

    utc_now = datetime.datetime.now(pytz.utc)

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

    note = create_simple_note('%s has cleaned all unanswered reviews' % logged_in_user.name,
                              'Cleanup Reviews',
                              'red',
                              'cleanedup_reviews',
                              logged_in_user,
                              utc_now)

    task.notes.append(note)

    task.updated_by = logged_in_user
    task.date_updated = utc_now

    # invalidate all caches
    invalidate_all_caches()

    request.session.flash('success:Unanswered reviews are cleaned!')
    return Response('Successfully Unanswered reviews are cleaned!')


@view_config(
    route_name='review_sequence_dialog',
    renderer='templates/task/dialog/review_aalog.jinja2'
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
        'forced': forced,
        'review_type': review.type.name if review and review.type else ''
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

    # invalidate all caches
    invalidate_all_caches()

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
    """approves the given task

    :param request:
    :return:
    """

    task_id = request.matchdict.get('id', -1)
    task = Task.query.filter(Task.id == task_id).first()

    return approve_tasks(request, [task])


@view_config(
    route_name='approve_tasks'
)
def approve_tasks_view(request):
    """approves the given tasks

    :param request:
    :return:
    """
    from stalker import Task
    task_ids = get_multi_integer(request, 'task_ids', 'GET')
    logger.debug("approve tasks_ids: %s" % task_ids)
    tasks = Task.query.filter(Task.id.in_(task_ids)).all()
    return approve_tasks(request, tasks)


def approve_tasks(request, tasks):
    """approves the given tasks

    :param request: Request instance
    :param tasks: A list of Stalker tasks
    """
    logged_in_user = get_logged_in_user(request)

    task_ids = list(map(lambda x: x.id, tasks))
    logger.debug("inside approve_tasks task_ids: %s" % task_ids)

    send_email = request.params.get('send_email', 1)  # for testing purposes
    description = request.params.get('description', 1)
    forced = request.params.get('forced', None)

    logger.debug('forced: %s' % forced)

    utc_now = datetime.datetime.now(pytz.utc)
    status_new = Status.query.filter_by(code='NEW').first()

    reviews = []
    flash_messages = []
    response_messages = []

    if forced:
        has_permission = PermissionChecker(request)
        if has_permission('Create_Review'):
            review = forced_review(logged_in_user, tasks[0])
            review.date_created = utc_now
        else:
            return Response('You dont have permission', 500)
    else:
        reviews = Review.query\
            .filter(Review.reviewer_id == logged_in_user.id)\
            .filter(Review.task_id.in_(task_ids))\
            .filter(Review.status == status_new)\
            .all()

    logger.debug("reviews: %s" % reviews)

    if not reviews:
        transaction.abort()
        return Response('There is no review', 500)

    for review in reviews:
        if review.type and review.type.name == 'Extra Time':
            note = create_simple_note(
                description,
                'Rejected Extra Time Request',
                'red',
                'rejected',
                logged_in_user,
                utc_now
            )
        else:
            note = create_simple_note(
                description,
                'Approved',
                'green',
                'approved',
                logged_in_user,
                utc_now
            )

        task = review.task
        try:
            review.approve()
            review.description = \
                '%(resource_note)s<br/> <b>%(reviewer_name)s</b>: ' \
                '%(reviewer_note)s' % {
                    'resource_note': review.description,
                    'reviewer_name': logged_in_user.name,
                    'reviewer_note': note.content
                }

            review.date_updated = utc_now

            task.notes.append(note)
        except StatusError as e:
            return Response('StatusError: %s' % e, 500)
        finally:
            # fix task status
            task.update_status_with_dependent_statuses()
            task.update_status_with_children_statuses()
            task.update_schedule_info()
            check_task_status_by_schedule_model(task)
            fix_task_computed_time(task)

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

            for watcher in task.watchers:
                recipients.append(watcher.email)

            # also add other note owners to the list
            for note in task.notes:
                note_created_by = note.created_by
                if note_created_by:
                    recipients.append(note_created_by.email)

            # make the list unique
            recipients = list(set(recipients))

            task_full_path = get_task_full_path(task.id)

            if review.type and review.type.name == 'Extra Time':
                subject = 'Request Rejected: "%s"' % task_full_path

                description_temp = \
                    '%(user)s has rejected the Extra Time Request for' \
                    '%(task_full_path)s with the following ' \
                    'comment:%(spacing)s' \
                    '%(note)s'

            else:
                subject = 'Task Approved: "%s"' % task_full_path

                description_temp = \
                    '%(user)s has approved ' \
                    '%(task_full_path)s with the following ' \
                    'comment:%(spacing)s' \
                    '%(note)s'

            message = Message(
                subject=subject,
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
                    get_task_external_link(task.id),
                    note.content if note.content else '-- no notes --'
                )
            )

            try:
                mailer.send_to_queue(message)
            except ValueError:
                # no internet connection
                # or not a maildir
                pass

        if review.type and review.type.name == 'Extra Time':
            flash_message = 'success:Rejected Extra Time Request!'
            response_message = 'Successfully rejected extra time request'
        else:
            flash_message = 'success:Approved Task!'
            response_message = 'Successfully approved task'

        flash_messages.append(flash_message)
        response_messages.append(response_message)

    # invalidate all caches
    invalidate_all_caches()

    request.session.flash('<br>'.join(flash_messages))
    return Response('<br>'.join(response_messages))


def add_note_to_dependent_of_tasks(task, description, logged_in_user, utc_now):
    dependent_of_note = create_simple_note(
        'The task got a Revision due to the revision given to '
        '<a href="/tasks/%(task_id)s/view"><b>%(task_name)s</b></a>:<br/>'
        '%(description)s' % {
            'task_name': task.name,
            'task_id': task.id,
            'description': description
        },
        'Request Revision',
        'purple',
        'requested_revision',
        logged_in_user,
        utc_now
    )

    for tdep in walk_hierarchy(task, 'dependent_of'):
        logger.debug('tdep : %s' % tdep.name)
        if tdep != task:
            if tdep.status.code not in ['WFD','RTS']:
                if dependent_of_note not in tdep.notes:
                    tdep.notes.append(dependent_of_note)


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

    schedule_info = get_schedule_information(request)
    if schedule_info is Response:
        transaction.abort()
        return schedule_info

    schedule_timing = schedule_info[0]
    schedule_unit = schedule_info[1]
    schedule_model = schedule_info[2]

    logger.debug('schedule_timing: %s' % schedule_timing)
    logger.debug('schedule_unit  : %s' % schedule_unit)
    logger.debug('schedule_model : %s' % schedule_model)

    send_email = request.params.get('send_email', 1)  # for testing purposes
    description = request.params.get('description', 1)
    forced = request.params.get('forced', None)

    utc_now = datetime.datetime.now(pytz.utc)

    review = None

    if forced:
        has_permission = PermissionChecker(request)
        if has_permission('Create_Review')\
           or logged_in_user in task.responsible:
            # review = forced_review(logged_in_user, task);
            # review.date_created = utc_now

            note = create_simple_note(
                'Expanded the timing of the task by <b>'
                '%(schedule_timing)s %(schedule_unit)s</b>.<br/>'
                '%(description)s' % {
                    'schedule_timing': schedule_timing,
                    'schedule_unit': schedule_unit,
                    'description': description
                },
                'Request Revision',
                'purple',
                'requested_revision',
                logged_in_user,
                utc_now
            )

            task.request_revision(
                logged_in_user,
                note.content,
                schedule_timing,
                schedule_unit
            )

            add_note_to_dependent_of_tasks(task, description, logged_in_user, utc_now)

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
            content = 'Expanded the timing of the task by ' \
                '<b>%(schedule_timing)s %(schedule_unit)s</b>.<br/>%(description)s' % {
                'schedule_timing': schedule_timing,
                'schedule_unit': schedule_unit,
                'description': description
            }
            if review.type and review.type.name == 'Extra Time':
                note = create_simple_note(
                    content,
                    'Accepted Extra Time Request',
                    'green',
                    'accepted',
                    logged_in_user,
                    utc_now
                )
            else:
                note = create_simple_note(
                    content,
                    'Request Revision',
                    'purple',
                    'requested_revision',
                    logged_in_user,
                    utc_now
                )

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

            add_note_to_dependent_of_tasks(task,
                                           description,
                                           logged_in_user,
                                           utc_now)

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

        for watcher in task.watchers:
            recipients.append(watcher.email)

        # also add other note owners to the list
        for note in task.notes:
            note_created_by = note.created_by
            if note_created_by:
                recipients.append(note_created_by.email)

        # make the list unique
        recipients = list(set(recipients))

        task_full_path = get_task_full_path(task.id)

        if review and review.type and review.type.name == 'Extra Time':
            subject = 'Request Accepted: "%s"' % task_full_path

            description_temp = \
                '%(user)s has accepted the extra time request of ' \
                '%(task_full_path)s' \
                '. The following description is supplied:%(spacing)s' \
                '%(note)s'
        else:
            subject = 'Revision Requested: "%s"' % task_full_path

            description_temp = \
                '%(user)s has requested a revision to ' \
                '%(task_full_path)s' \
                '. The following description is supplied for the ' \
                'revision request:%(spacing)s' \
                '%(note)s'

        message = Message(
            subject=subject,
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
                get_task_external_link(task.id),
                note.content if note.content else '-- no notes --'
            )
        )

        try:
            mailer.send_to_queue(message)
        except ValueError:
            # no internet connection
            # or not a maildir
            pass

    # invalidate all caches
    invalidate_all_caches()

    if review and review.type and review.type.name == 'Extra Time':
        flash_message = 'success:Accepted Extra Time Request!'
        response_message = 'Successfully accepted extra time request!'
    else:
        flash_message = 'success:Requested a Revision for the task!'
        response_message = 'Successfully requested revision for the task!'

    request.session.flash(flash_message)

    return Response(response_message)


@view_config(
    route_name='approve_tasks_dialog',
    renderer='templates/task/dialog/approve_tasks_dialog.jinja2'
)
def approve_tasks_dialog(request):
    """deletes the department with the given id
    """
    logger.debug('approve_tasks_dialog starts')

    came_from = request.params.get('came_from', '/')

    selected_task_list = get_multi_integer(request, 'task_ids', 'GET')
    logger.debug('selected_task_list: %s' % selected_task_list)

    _query_buffer = []
    for task_id in selected_task_list:
        _query_buffer.append("""task_ids=%s""" % task_id)
    _query = '&'.join(_query_buffer)

    action = '/tasks/approve?%s' % (_query)

    logger.debug('action: %s' % action)

    return {
        'came_from': came_from,
        'action': action
    }


@view_config(
    route_name='request_revisions_dialog',
    renderer='templates/task/dialog/request_revisions_dialog.jinja2'
)
def request_revisions_dialog(request):
    """deletes the department with the given id
    """
    logger.debug('request_revisions_dialog is starts')

    came_from = request.params.get('came_from', '/')

    selected_task_list = get_multi_integer(request, 'task_ids', 'GET')
    logger.debug('selected_task_list: %s' % selected_task_list)

    _query_buffer = []
    for task_id in selected_task_list:
        _query_buffer.append("""task_ids=%s""" % task_id)
    _query = '&'.join(_query_buffer)

    action = '/tasks/request_revisions?%s' % (_query)

    logger.debug('action: %s' % action)

    return {
        'came_from': came_from,
        'action': action
    }


@view_config(
    route_name='request_revisions'
)
def request_revisions(request):
    """ request revision for selected tasks
    """

    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    selected_task_list = get_multi_integer(request, 'task_ids', 'GET')

    logger.debug("selected_task_list: %s" % selected_task_list)

    tasks = Task.query.filter(Task.id.in_(selected_task_list)).all()
    if not tasks:
        transaction.abort()
        return Response('Can not find any Task', 500)

    schedule_info = get_schedule_information(request)
    if schedule_info is Response:
        transaction.abort()
        return schedule_info

    schedule_timing = schedule_info[0]
    schedule_unit = schedule_info[1]
    schedule_model = schedule_info[2]

    description = request.params.get('description', 1)
    has_permission = PermissionChecker(request)

    if has_permission('Create_Review'):
        note = create_simple_note(
            'Expanded the timing of the task by <b>'
            '%(schedule_timing)s %(schedule_unit)s</b>.<br/>'
            '%(description)s' % {
                'schedule_timing': schedule_timing,
                'schedule_unit': schedule_unit,
                'description': description
            },
            'Request Revision',
            'purple',
            'requested_revision',
            logged_in_user,
            utc_now
        )
        result_message = []
        for task in tasks:
            if task.status.code not in ['CMPL', 'PREV']:
                result_message.append(
                    '%s/%s is  %s. You can not request revision!' % (task.parent.name, task.name, task.status.name)
                )
                continue

            task.request_revision(
                logged_in_user,
                note.content,
                schedule_timing,
                schedule_unit
            )
            task.notes.append(note)
            task.updated_by = logged_in_user
            task.date_updated = utc_now

            add_note_to_dependent_of_tasks(task, description, logged_in_user, utc_now)
    else:
        request.session.flash('error:You dont have permission!')
        return Response("You don't have permission", 500)

    flash_message = 'success:Requested revisions for all selected tasks!'
    if len(result_message) > 0:
        flash_message = 'warning: %s' % ',\n '.join(result_message)

    invalidate_all_caches()

    request.session.flash(flash_message)
    return Response(flash_message)


def get_schedule_information(req):

    schedule_timing = req.params.get('schedule_timing')
    schedule_unit = req.params.get('schedule_unit')
    schedule_model = req.params.get('schedule_model')

    if not schedule_timing:
        return Response('There are missing parameters: schedule_timing', 500)
    else:
        try:
            schedule_timing = float(schedule_timing)
        except ValueError:
            return Response('Please supply a float or integer value for '
                            'schedule_timing parameter', 500)

    if not schedule_unit:
        return Response('There are missing parameters: schedule_unit', 500)
    else:
        if schedule_unit not in ['min', 'h', 'd', 'w', 'm', 'y']:
            return Response(
                "schedule_unit parameter should be one of ['min','h', 'd', "
                "'w', 'm', 'y']", 500
            )

    if not schedule_model:
        return Response('There are missing parameters: schedule_model', 500)
    else:
        if schedule_model not in ['effort', 'duration', 'length']:
            return Response("schedule_model parameter should be on of "
                            "['effort', 'duration', 'length']", 500)

    return schedule_timing, schedule_unit, schedule_model


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
            # TODO: Add this to the config file / omitted
            # forced_publish_types = [
            #     'Look Development', 'Character Design', 'Model', 'Rig',
            #     'Previs', 'Layout', 'Lighting', 'Environment Design',
            #     'Matte Painting', 'Animation Bible',  'Camera', 'Simulation',
            #     'Postvis', 'Scene Assembly', 'Schematic', 'Comp', 'FX', 'Sketch',
            #     'Color Sketch', 'Groom'
            # ]
            forced_publish_types = []
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
        request.session.flash(
            'warning:You are not one of the resources nor the '
            'responsible of this task, so you can not request a '
            'review for this task'
        )

        return Response('You are not one of the resources nor the '
                        'responsible of this task, so you can not request a '
                        'review for this task', 500)

    # invalidate all caches
    invalidate_all_caches()

    send_email = request.params.get('send_email', 1)
    description = request.params.get('description', "")

    return request_review_action(request, task, logged_in_user, description, send_email, request_review_mode)

@view_config(
    route_name='request_reviews_dialog',
    renderer='templates/task/dialog/request_reviews_dialog.jinja2'
)
def request_reviews_dialog(request):
    """request_reviews_dialog
    """
    logger.debug('request_reviews_dialog is starts')

    came_from = request.params.get('came_from', '/')

    selected_task_list = get_multi_integer(request, 'task_ids', 'GET')
    logger.debug('selected_task_list: %s' % selected_task_list)

    _query_buffer = []
    for task_id in selected_task_list:
        _query_buffer.append("""task_ids=%s""" % task_id)
    _query = '&'.join(_query_buffer)

    action = '/tasks/request_reviews?%s' % (_query)

    logger.debug('action: %s' % action)

    return {
        'came_from': came_from,
        'action': action
    }

@view_config(
    route_name='request_reviews',
)
def request_reviews(request):
    """creates a new ticket and sends an email to the responsible
    """
    logger.debug('request_review method starts')
    # get logged in user as he review requester
    logged_in_user = get_logged_in_user(request)

    selected_task_list = get_multi_integer(request, 'task_ids', 'GET')
    tasks = Task.query.filter(Task.id.in_(selected_task_list)).all()
    if not tasks:
        selected_task_list = get_multi_integer(request, 'task_ids')
        tasks = Task.query.filter(Task.id.in_(selected_task_list)).all()
        if not tasks:
            transaction.abort()
            return Response('Can not find any Task', 500)

    request_review_mode = request.params.get('request_review_mode', 'Final')

    for task in tasks:
        # check if the user is one of the resources of this task or the responsible
        if logged_in_user not in task.resources and \
           logged_in_user not in task.responsible:
            request.session.flash(
                'warning:You are not one of the resources nor the '
                'responsible of this task, so you can not request a '
                'review for this task'
            )
        else:
            invalidate_all_caches()
            send_email = request.params.get('send_email', 1)
            description = request.params.get('description', "")
            request_review_action(request, task, logged_in_user, description, send_email, request_review_mode)
            # request_review_action(request, request_review_mode)

    return Response('Successfully requested reviews')

# def request_progress_review(request):
#     """runs when resource request final review"""
#
#     logger.debug('request_progress_review starts')
#
#     selected_responsible_ids = \
#         get_multi_integer(request, 'selected_responsible_ids')
#     selected_responsible_list = \
#         User.query.filter(User.id.in_(selected_responsible_ids)).all()
#
#     if not selected_responsible_list:
#         transaction.abort()
#         return Response('You did not select any responsible', 500)
#
#     logged_in_user = get_logged_in_user(request)
#
#     task_id = request.matchdict.get('id', -1)
#     task = Task.query.filter(Task.id == task_id).first()
#
#     note = request.params.get('note', 'No note')
#
#     utc_now = datetime.datetime.now(pytz.utc)
#
#     # Create ticket_type if it does not exist
#     ticket_type_name = 'In Progress-Review'
#     ticket_type = query_type('Ticket', ticket_type_name)
#
#     recipients = []
#
#     # Create tickets for selected responsible
#     user_link_internal = get_user_link_internal(request, logged_in_user)
#     task_full_path = get_task_full_path(task.id)
#     task_link_internal = request.route_path('view_task', id=task.id)
#
#     for responsible in selected_responsible_list:
#         logger.debug('responsible: %s' % responsible)
#         recipients.append(responsible.email)
#
#         request_review_ticket = Ticket(
#             project=task.project,
#             summary='In Progress Review Request: %s' % task_full_path,
#             description='%(sender)s has requested you to do <b>a progress '
#                         'review</b> for %(task)s' % {
#                             'sender': user_link_internal,
#                             'task': task_link_internal
#                         },
#             type=ticket_type,
#             created_by=logged_in_user,
#             date_created=utc_now,
#             date_updated=utc_now
#         )
#
#         request_review_ticket.reassign(logged_in_user, responsible)
#
#         # link the task to the review
#         request_review_ticket.links.append(task)
#         DBSession.add(request_review_ticket)
#
#         ticket_comment = create_simple_note(note,
#                                             'Ticket Comment',
#                                             'pink',
#                                             'ticket_comment',
#                                             logged_in_user,
#                                             utc_now)
#
#         request_review_ticket.comments.append(ticket_comment)
#         task.notes.append(ticket_comment)
#         task.updated_by = logged_in_user
#         task.date_updated = utc_now
#
#     # Send mail to
#     send_email = request.params.get('send_email', 1)  # for testing purposes
#
#     if send_email:
#         recipients.append(logged_in_user.email)
#         # recipients.extend(task.responsible)
#
#         for watcher in task.watchers:
#             recipients.append(watcher.email)
#
#         # also add other note owners to the list
#         for note in task.notes:
#             note_created_by = note.created_by
#             if note_created_by:
#                 recipients.append(note_created_by.email)
#
#         # make the list unique
#         recipients = list(set(recipients))
#
#         description_temp = \
#             '%(user)s has requested an in-progress review for ' \
#             '%(task_full_path)s with the following note:' \
#             '%(spacing)s' \
#             '%(note)s '
#
#         mailer = get_mailer(request)
#
#         message = Message(
#             subject='In Progress Review Request: "%s"' % task_full_path,
#             sender=dummy_email_address,
#             recipients=recipients,
#             body=get_description_text(
#                 description_temp,
#                 logged_in_user.name,
#                 task_full_path,
#                 note if note else '-- no notes --'
#             ),
#             html=get_description_html(
#                 description_temp,
#                 logged_in_user.name,
#                 get_task_external_link(task.id),
#                 note if note else '-- no notes --'
#             )
#         )
#
#         try:
#             mailer.send_to_queue(message)
#         except ValueError:
#             # no internet connection
#             # or not a maildir
#             pass
#
#     logger.debug(
#         'success:Your progress review request has been sent to responsible'
#     )
#
#     request.session.flash(
#         'success:Your progress review request has been sent to responsible'
#     )
#
#     # invalidate all caches
#     invalidate_all_caches()
#
#     return Response(
#         'Your progress review request has been sent to responsible'
#     )


def cut_schedule_timing(task):

    timing, unit = task.least_meaningful_time_unit(task.total_logged_seconds)
    task.schedule_timing = timing
    task.schedule_unit = unit
    logger.debug("cut_schedule_timing : %s" % task.schedule_timing)


def request_review_action(request, task, logged_in_user, desc, send_email, mode):
    """runs when resource request final review
    """

    logger.debug('request_final_review starts')

    # logged_in_user = get_logged_in_user(request)
    #
    # task_id = request.matchdict.get('id', -1)
    # task = Task.query.filter(Task.id == task_id).first()

    if mode == 'Final':
        cut_schedule_timing(task)

    note_str = desc
    # send_email = request.params.get('send_email', 1)  # for testing purposes

    utc_now = datetime.datetime.now(pytz.utc)

    note = create_simple_note( note_str,
                              'Request Review',
                              'orange',
                              'requested_review',
                              logged_in_user,
                              utc_now)

    request_type = Type.query.filter(Type.name == mode).first()
    if not request_type:
        request_type = Type(
            name=mode,
            code=mode,
            target_entity_type='Review'
        )

    task.notes.append(note)
    reviews = task.request_review()
    for review in reviews:
        review.type = request_type
        review.created_by = logged_in_user
        review.date_created = utc_now
        review.date_updated = utc_now
        review.description = "<br/><b>%(resource_name)s :<b> %(note)s" % {
            'resource_name': logged_in_user.name,
            'note': note.content
        }

    if send_email:
        # *******************************************************************
        # info message for responsible
        recipients = []

        for responsible in task.responsible:
            recipients.append(responsible.email)

        for watcher in task.watchers:
            recipients.append(watcher.email)

        # also add other note owners to the list
        for note in task.notes:
            note_created_by = note.created_by
            if note_created_by:
                recipients.append(note_created_by.email)

        # make the list unique
        recipients = list(set(recipients))
        logger.debug('recipients: %s' % recipients)

        task_full_path = get_task_full_path(task.id)
        description_temp = \
            '%(user)s has requested a final review for ' \
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
                get_task_external_link(task.id),
                note.content if note.content else '-- no notes --'
            )
        )

        try:
            mailer.send_to_queue(message)
        except ValueError:
            # no internet connection
            # or not a maildir
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
            subject='Review Request: "%s"' % task_full_path,
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
                                  get_task_external_link(task.id),
                "note": '<br/><br/> %s ' % note.content,
                "spacing": '<br><br>'
            }
        )

        try:
            mailer.send_to_queue(message)
        except ValueError:
            # no internet connection
            # or not a maildir
            pass

    # invalidate all caches
    invalidate_all_caches()

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

    schedule_info = get_schedule_information(request)
    if schedule_info is Response:
        transaction.abort()
        return schedule_info

    schedule_timing = schedule_info[0]
    schedule_unit = schedule_info[1]
    schedule_model = schedule_info[2]

    logger.debug('schedule_timing: %s' % schedule_timing)
    logger.debug('schedule_unit  : %s' % schedule_unit)
    logger.debug('schedule_model : %s' % schedule_model)

    send_email = request.params.get('send_email', 1)  # for testing purposes
    description = request.params.get('description', 'No comments')

    utc_now = datetime.datetime.now(pytz.utc)

    note = create_simple_note('<i class="icon-heart"></i> Requesting extra time <b>'
                                '%(schedule_timing)s %(schedule_unit)s</b>.<br/>'
                                '%(description)s' % {
                                    'schedule_timing': schedule_timing,
                                    'schedule_unit': schedule_unit,
                                    'description': description
                                },
                              'Request Extra Time',
                              'red2',
                              'requested_extra_time',
                              logged_in_user,
                              utc_now)
    task.notes.append(note)

    extra_time_type = Type.query.filter(Type.name == 'Extra Time').first()
    if not extra_time_type:
        extra_time_type = Type(
            name='Extra Time',
            code='ExtraTime',
            target_entity_type='Review'
        )
        DBSession.add(extra_time_type)

    reviews = task.request_review()
    for review in reviews:
        review.type = extra_time_type
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

        for watcher in task.watchers:
            recipients.append(watcher.email)

        # also add other note owners to the list
        for note in task.notes:
            note_created_by = note.created_by
            if note_created_by:
                recipients.append(note_created_by.email)

        # make the list unique
        recipients = list(set(recipients))

        task_full_path = get_task_full_path(task.id)

        description_temp = \
            '%(user)s has requested extra time for ' \
            '%(task_full_path)s with the following note:%(note)s'

        mailer = get_mailer(request)

        message = Message(
            subject='Extra Time Request: "%s"' % task_full_path,
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
                get_task_external_link(task.id),
                note.content if note.content else '-- no notes --'
            )
        )

        try:
            mailer.send_to_queue(message)
        except ValueError:
            # no internet connection
            # or not a maildir
            pass

    # invalidate all caches
    invalidate_all_caches()

    logger.debug(
        'success:Your extra time request has been sent to responsible'
    )

    request.session.flash(
        'success:Your extra time request has been sent to responsible'
    )

    return Response('Your extra time request has been sent to responsible')


def auto_extend_time(task, description, revision_type, logged_in_user):
    """creates sends an email to the responsible about the user has requested
    extra time
    """
    logger.debug('EXTEND TIMING OF TASK!')
    # get logged in user as he review requester
    utc_now = datetime.datetime.now(pytz.utc)

    exceeded_time_str = convert_seconds_to_time_range(
        task.total_logged_seconds - task.schedule_seconds
    )

    note = create_simple_note('Extending timing of the task <b>'
                                '%(exceeded_time_str)s</b>.<br/>'
                                '%(description)s' % {
                                    'exceeded_time_str': exceeded_time_str,
                                    'description': description
                                },
                              revision_type,
                              'red2',
                              'auto_extend_time',
                              logged_in_user,
                              utc_now)
    task.notes.append(note)
    cut_schedule_timing(task)

    # extra_time_type = Type.query.filter(Type.name == 'Extra Time').first()
    # if not extra_time_type:
    #     extra_time_type = Type(
    #         name='Extra Time',
    #         code='ExtraTime',
    #         target_entity_type='Review'
    #     )
    #     DBSession.add(extra_time_type)
    #
    # reviews = task.request_review()
    # for review in reviews:
    #     review.type = extra_time_type
    #     review.created_by = logged_in_user
    #     review.date_created = utc_now
    #     review.date_updated = utc_now
    #     review.description = "<b>%(resource_name)s</b>: %(note)s " % {
    #         'resource_name': logged_in_user.name,
    #         'note': note.content
    #     }

    # if send_email:
    #     #*******************************************************************
    #     # info message for responsible
    #     recipients = []
    #
    #     for responsible in task.responsible:
    #         recipients.append(responsible.email)
    #
    #     for watcher in task.watchers:
    #         recipients.append(watcher.email)
    #
    #     # also add other note owners to the list
    #     for note in task.notes:
    #         note_created_by = note.created_by
    #         if note_created_by:
    #             recipients.append(note_created_by.email)
    #
    #     # make the list unique
    #     recipients = list(set(recipients))
    #
    #     task_full_path = get_task_full_path(task.id)
    #
    #     description_temp = \
    #         '%(user)s has requested extra time for ' \
    #         '%(task_full_path)s with the following note:%(note)s'
    #
    #     mailer = get_mailer(request)
    #
    #     message = Message(
    #         subject='Extra Time Request: "%s"' % task_full_path,
    #         sender=dummy_email_address,
    #         recipients=recipients,
    #         body=get_description_text(
    #             description_temp,
    #             logged_in_user.name,
    #             task_full_path,
    #             note.content if note.content else '-- no notes --'
    #         ),
    #         html=get_description_html(
    #             description_temp,
    #             logged_in_user.name,
    #             get_task_external_link(task.id),
    #             note.content if note.content else '-- no notes --'
    #         )
    #     )
    #
    #     try:
    #         mailer.send_to_queue(message)
    #     except ValueError:
    #         # no internet connection
    #         # or not a maildir
    #         pass
    #
    # # invalidate all caches
    # invalidate_all_caches()



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
    logger.debug('delete_task_dialog is starts')

    selected_task_list = get_multi_integer(request, 'task_ids', 'GET')
    project_id = request.params.get('project_id', '-1')
    logger.debug('project_id : %s' % project_id)

    _query_buffer = ['project_id=%s' % project_id]

    for task_id in selected_task_list:
       _query_buffer.append("""&task_ids=%s""" % task_id)
    _query = ''.join(_query_buffer)

    logger.debug('_query : %s' % _query)

    action = '/tasks/delete?%s' % _query

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
    selected_task_list = get_multi_integer(request, 'task_ids', 'GET')
    logger.debug('selected_task_list : %s' % selected_task_list)

    tasks = Task.query.filter(Task.id.in_(selected_task_list)).all()
    logger.debug('tasks : %s' % tasks)

    if not tasks:
        transaction.abort()
        return Response('Can not find any Task', 500)

    try:
        for task in tasks:
            unbind_task_hierarchy_relations(task)
            unbind_task_relations(task)

            DBSession.delete(task)

            logger.debug(
                'Successfully deleted task: %s (%s)' % (task.name, task.id)
            )
    except Exception as e:
        transaction.abort()
        c = StdErrToHTMLConverter(e)
        transaction.abort()
        return Response(c.html(), 500)
    finally:
        # invalidate all caches
        invalidate_all_caches()

    return Response('Successfully deleted tasks!')

#
# @view_config(
#     route_name='delete_task',
#     permission='Delete_Task'
# )
# def delete_task(request):
#     """deletes the task with the given id
#     """
#     task_id = request.matchdict.get('id')
#     task = Task.query.get(task_id)
#
#     if not task:
#         transaction.abort()
#         return Response('Can not find a Task with id: %s' % task_id, 500)
#
#     try:
#         unbind_task_hierarchy_relations(task)
#         unbind_task_relations(task)
#
#         DBSession.delete(task)
#         #transaction.commit()
#
#         # invalidate all caches
#         invalidate_all_caches()
#
#         logger.debug(
#             'Successfully deleted task: %s (%s)' % (task.name, task_id)
#         )
#     except Exception as e:
#         transaction.abort()
#         c = StdErrToHTMLConverter(e)
#         transaction.abort()
#         return Response(c.html(), 500)
#
#     return Response('Successfully deleted task: %s' % task_id)
#


@view_config(
    route_name='get_task_children_tasks',
    renderer='json'
)
def get_task_children_tasks(request):
    """TODO: Add Docstring please
    """
    logger.debug('get_task_children_tasks is running')
    task_id = request.matchdict.get('id')
    task = Task.query.get(task_id)

    type_ids = get_multi_integer(request, 'type_ids', 'GET')
    types = Type.query.filter(Type.id.in_(type_ids)).all()

    if not task:
        transaction.abort()
        return Response('Can not find a Task with id: %s' % task_id, 500)

    children_tasks = []
    children_tasks.extend(get_task_children_tasks_action(task, types))
    return children_tasks


def get_task_children_tasks_action(task, types):
    """TODO: Add Docstring please
    """

    children_tasks = []
    if task.children:
        for child in task.children:
            children_tasks.extend(get_task_children_tasks_action(child, types))
    else:
        if task.type in types:
            children_tasks = [{'id': task.id, 'name': task.name}]

    return children_tasks


@view_config(
    route_name='get_task_children_task_types',
    renderer='json'
)
def get_task_children_task_types(request):
    """TODO: Add Docstring please
    """
    logger.debug('get_task_children_task_types is running')
    task_id = request.matchdict.get('id')
    task = Task.query.get(task_id)

    if not task:
        transaction.abort()
        return Response('Can not find a Task with id: %s' % task_id, 500)

    children_task_types = get_task_children_task_types_action(task)

    return children_task_types


def get_task_children_task_types_action(task):
    """TODO: Add Docstring please
    """

    children_task_types = []
    if task.children:
        for child in task.children:
            child_children_task_types = get_task_children_task_types_action(child)
            for type in child_children_task_types:
                if type not in children_task_types:
                    children_task_types.append(type)
    else:
        children_task_types = [{'id': task.type.id, 'name': task.type.name}]

    return children_task_types


@view_config(
    route_name='get_task_related_entities',
    renderer='json'
)
def get_task_related_entities(request):
    """TODO: Add Docstring please
    """
    logger.debug('get_task_related_entity is running')
    task_id = request.matchdict.get('id')
    task = Task.query.get(task_id)

    entity_type = request.matchdict.get('e_type')
    dep_type = request.matchdict.get('d_type')
    logger.debug('get_task_related_entity is running for %s ' % task.name)
    if not task:
        transaction.abort()
        return Response('Can not find a Task with id: %s' % task_id, 500)

    task_related_entities = []
    task_related_entities.extend(get_task_related_entities_action(task, entity_type, dep_type))
    return task_related_entities


def get_task_related_entities_action(task, entity_type, dep_type):
    """TODO: Add Docstring please
    """

    task_related_entities = []
    if task.children:
        for child in task.children:
            task_related_entities.extend(
                get_task_related_entities_action(child, entity_type, dep_type)
            )
    else:
        dep_tasks = []
        if dep_type == 'dependent_of':
            dep_tasks = task.dependent_of
        else:
            dep_tasks = task.depends
        for dep_task in dep_tasks:
            entity = get_task_parent(dep_task, entity_type)
            if entity:
                if entity not in task_related_entities:
                    task_related_entities.append({
                        'id': entity.id,
                        'name': entity.name,
                        'thumbnail_full_path': entity.thumbnail.full_path if entity.thumbnail else None,
                        'plural_class_name': entity.plural_class_name.lower()
                    })

    return task_related_entities


def get_task_parent(task, entity_type):
    parent = task.parent
    if parent:
        if parent.entity_type == entity_type:
            return parent
        else:
            return get_task_parent(parent, entity_type)
    else:
        if task.entity_type == entity_type:
            return task
        else:
            return


@view_config(
    route_name='get_task_events',
    renderer='json'
)
def get_task_events(request):
    if not multi_permission_checker(
            request, ['Read_User', 'Read_TimeLog', 'Read_Vacation']):
        return HTTPForbidden(headers=request.session)

    logger.debug('get_task_events is running')

    task_id = request.matchdict.get('id', -1)

    logger.debug('task_id: %s' % task_id)

    # first get the one individual task
    our_task = query_tasks(
        where_clause=generate_where_clause({'id': [task_id]})
    )

    # use its path to query all of its children
    # generate a second where condition
    all_tasks = query_tasks(
        where_clause=generate_where_clause({
            'path': [our_task[0]['path']]
        })
    )

    task_ids = [task['id'] for task in all_tasks]
    # logger.debug("task_ids %s" % task_ids)

    sql_query = """select
    "TimeLogs".id,
    'timelogs' as entity_type,
    "Resource_SimpleEntities".name as resource_name,
    "Task_SimpleEntities".name as task_name,
    (extract(epoch from "TimeLogs".start) * 1000)::bigint as start,
    (extract(epoch from "TimeLogs".end) * 1000)::bigint as end,
    'label-success', --className
    false, --allDay
    "Statuses".code as task_status
from "TimeLogs"
    join "Tasks" on "TimeLogs".task_id = "Tasks".id
    join "SimpleEntities" as "Task_SimpleEntities" on "Tasks".id = "Task_SimpleEntities".id
    join "SimpleEntities" as "Resource_SimpleEntities" on "TimeLogs".resource_id = "Resource_SimpleEntities".id
    join "Statuses" on "Tasks".status_id = "Statuses".id
where "TimeLogs".task_id in %s
    """ % str(task_ids).replace('[', '(').replace(']', ')')

    # logger.debug("sql_query %s" % sql_query)

    # now query all the time logs
    # to be able to use "%" sign use this function
    from sqlalchemy import text
    result = DBSession.connection().execute(text(sql_query))

    events = [
        {
            'id': r[0],
            'entity_type': r[1],
            'resource_name': r[2],
            'title': r[3],
            'start': r[4],
            'end': r[5],
            'className': r[6],
            'allDay': r[7],
            'status': r[8],
            'status_color': ''
        } for r in result.fetchall()
    ]

    return events


@view_config(
    route_name='get_task_dependency',
    renderer='json'
)
def get_task_dependency(request):
    if not multi_permission_checker(request, ['Read_User', 'Read_Task']):
        return HTTPForbidden(headers=request.session)

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
                'path': '%s (%s) (%s)' %
                        (dep_task.name,
                         dep_task.id,
                         '|'.join([p.name for p in dep_task.parents])),
                'status': dep_task.status.name,
                'status_color': dep_task.status.html_class,
                'percent_complete': dep_task.percent_complete,
                'total_logged_seconds': dep_task.total_logged_seconds,
                'schedule_seconds': dep_task.schedule_seconds,
                'schedule_unit': dep_task.schedule_unit,
                'resources': resources,
                'priority': dep_task.priority
            }
        )

    return list_of_dep_tasks_json


@view_config(
    route_name='force_task_status_dialog',
    renderer='templates/task/dialog/force_task_status_dialog.jinja2'
)
def force_task_status_dialog(request):
    """deletes the department with the given id
    """
    logger.debug('force_task_status_dialog is starts')

    task_id = request.matchdict.get('id')
    task = Task.query.filter_by(id=task_id).first()
    status_code = request.matchdict.get('status_code')
    logger.debug('status_code: %s' % status_code)
    came_from = request.params.get('came_from', '/')
    action = '/tasks/%s/force_status/%s' % (task_id, status_code)

    logger.debug('action: %s' % action)
    message = 'Task will be set as %s' \
              '<br><br>Are you sure?' % status_code

    version = get_last_version_of_task(request, is_published='t')

    logger.debug('action: %s' % action)

    return {
        'version': version,
        'task': task,
        'message': message,
        'came_from': came_from,
        'action': action
    }


@view_config(
    route_name='force_task_status'
)
def force_task_status(request):
    """Forces the task status to the status given with the status_code parameter.

    It needs task_id and status_code as a parameter in the request, with out
    them it will return a response with status_code of 500.

    It will work only for tasks with 'WIP' and 'HREV' statuses.
    """
    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    logger.debug("force_task_status starts")

    status_code = request.matchdict.get('status_code')
    status = Status.query.filter(Status.code == status_code).first()

    if not status:
        transaction.abort()
        return Response('Can not find a status with code: %s' % status_code, 500)

    if status.code not in ['CMPL', 'STOP', 'OH']:
        transaction.abort()
        return Response('Can not set status to: %s' % status_code, 500)

    task_id = request.matchdict.get('id')
    task = Task.query.get(task_id)

    if not task:
        transaction.abort()
        return Response('Can not find a Task with id: %s' % task_id, 500)

    if task.status.code not in ['WIP', 'HREV', 'PREV']:
        transaction.abort()
        return Response('Cannot force %s tasks' % task.status.code, 500)

    description = request.params.get('description', '')

    if description != '':
        description = 'with this note: <br/><b>%s</b>' % description

    content = '%s has changed this task status to %s %s' % (
        logged_in_user.name,
        status.name,
        description
    )

    note = create_simple_note(content,
                              'Forced Status',
                              'red',
                              'forced_status',
                              logged_in_user,
                              utc_now)

    set_task_status(task, status, note, logged_in_user, utc_now)
    # invalidate all caches
    invalidate_all_caches()

    flash_message = 'success:%s status is set to %s!' % (task.name, status.name)
    request.session.flash(flash_message)

    return Response('Success: %s status is set to %s' %
                    (task.name, status.name))


@view_config(
    route_name='force_tasks_status_dialog',
    renderer='templates/modals/confirm_dialog.jinja2'
)
def force_tasks_status_dialog(request):
    """deletes the department with the given id
    """
    logger.debug('force_task_status_dialog is starts')

    status_code = request.matchdict.get('status_code')
    logger.debug('status_code: %s' % status_code)
    came_from = request.params.get('came_from', '/')

    selected_task_list = get_multi_integer(request, 'task_ids', 'GET')
    logger.debug('selected_task_list: %s' % selected_task_list)

    _query_buffer = []
    for task_id in selected_task_list:
        _query_buffer.append("""task_ids=%s""" % task_id)
    _query = '&'.join(_query_buffer)

    action = '/tasks/force_status/%s?%s' % (status_code, _query)

    logger.debug('action: %s' % action)
    message = 'Tasks will be set as %s' \
              '<br><br>Are you sure?' % status_code


    logger.debug('action: %s' % action)

    return {
        'message': message,
        'came_from': came_from,
        'action': action
    }


@view_config(
    route_name='force_tasks_status'
)
def force_tasks_status(request):
    """Forces the tasks status to the status given with the status_code parameter.

    It needs task_ids and status_code as a parameter in the request, with out
    them it will return a response with status_code of 500.

    It will work only for tasks with 'WIP' and 'HREV' statuses.
    """
    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    status_code = request.matchdict.get('status_code')
    status = Status.query.filter(Status.code == status_code).first()

    if not status:
        transaction.abort()
        return Response('Can not find a status with code: %s' % status_code, 500)

    if status.code not in ['CMPL', 'STOP', 'OH']:
        transaction.abort()
        return Response('Can not set status to: %s' % status_code, 500)

    selected_task_list = get_multi_integer(request, 'task_ids')
    tasks = Task.query.filter(Task.id.in_(selected_task_list)).all()

    if not tasks:

        selected_task_list = get_multi_integer(request, 'task_ids', 'GET')
        tasks = Task.query.filter(Task.id.in_(selected_task_list)).all()

        if not tasks:
            transaction.abort()
            return Response('Can not find any task !!', 500)

    result_message =[]
    note_str = request.params.get('description', '')

    if note_str != '':
        note_str = 'with this note: <br/><b>%s</b>' % note_str

    content = '%s has changed this task status to %s %s' % (
        logged_in_user.name,
        status.name,
        note_str
    )
    note = create_simple_note(content, 'Forced Status', 'red', 'forced_status', logged_in_user, utc_now)

    for task in tasks:
        if task.status.code not in ['WIP', 'HREV', 'PREV']:
            result_message.append('%s/%s is  %s.  You can not force status!' % (task.parent.name, task.name, task.status.name))

            continue

        set_task_status(task, status, note, logged_in_user, utc_now)

    # invalidate all caches
    invalidate_all_caches()

    flash_message = 'success:Forced statuses %s for all selected tasks!' % status.name
    if len(result_message) > 0:
        flash_message = 'warning: %s' % ',\n '.join(result_message)
    request.session.flash(flash_message)
    return Response(flash_message)


def set_task_status(task, status, note, logged_in_user, utc_now):

    if task.status.code == 'PREV':
        review = forced_review(logged_in_user, task)
        review.date_created = utc_now
        review.date_updated = utc_now
        review.description = \
            '%(resource_note)s <br/> <b>%(reviewer_name)s</b>: ' \
            '%(reviewer_note)s' % {
                'resource_note': '',
                'reviewer_name': logged_in_user.name,
                'reviewer_note': note.content
            }
        review.approve()
    else:
        if status.code == 'STOP':
            task.stop()
            fix_task_computed_time(task)
        elif status.code == 'OH':
            task.hold()
            fix_task_computed_time(task)
        elif status.code == 'CMPL':
            cut_schedule_timing(task)
            task.status = status
            fix_task_computed_time(task)
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

    task.notes.append(note)
    task.updated_by = logged_in_user
    task.date_updated = utc_now


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
    utc_now = datetime.datetime.now(pytz.utc)

    note = create_simple_note('%s has changed this task status to %s' % (logged_in_user.name,
                                                           task.status.name),
                              'Resumed',
                              'red',
                              'resumed',
                              logged_in_user,
                              utc_now)

    task.notes.append(note)
    task.updated_by = logged_in_user
    task.date_updated = utc_now

    # invalidate all caches
    invalidate_all_caches()

    return Response('Success: %s is resumed' % task.name)


@view_config(
    route_name='get_task_resources',
    renderer='json'
)
def get_task_resources(request):
    """
    """

    logger.debug('***get_task_resources method starts ***')
    logged_in_user = get_logged_in_user(request)

    task_id = request.matchdict.get('id')
    task = Task.query.get(task_id)

    if not task:
        transaction.abort()
        return Response('Can not find a Task with id: %s' % task_id, 500)

    update_task_permission = PermissionChecker(request)('Update_Task')

    return [
        {
            'id': resource.id,
            'name': resource.name,
            'thumbnail_full_path': resource.thumbnail.full_path if resource.thumbnail else None,
            'description': '',
            'item_view_link': '/users/%s/view' % resource.id,
            'item_remove_link': '/tasks/%s/remove/resources/%s/dialog?came_from=%s'
                               % (task.id,
                                 resource.id,
                                 request.current_route_path())
            if (update_task_permission and (task.project in logged_in_user.projects)) else None
        }
        for resource in task.resources
    ]


@view_config(
    route_name='remove_task_user_dialog',
    renderer='templates/modals/confirm_dialog.jinja2'
)
def remove_task_user_dialog(request):
    """removes the user with the given id
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
    """removes the user with the given id
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

    if user_type == 'resources':
        task.resources.remove(user)
    elif user_type == 'responsible':
        task.responsible.remove(user)

    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    task.updated_by = logged_in_user
    task.date_updated = utc_now

    # invalidate all caches
    invalidate_all_caches()

    return Response('Success: %s is removed from %s resources' %
                    (user.name, task.name))


@view_config(
    route_name='remove_tasks_user_dialog',
    renderer='templates/modals/confirm_dialog.jinja2'
)
def remove_tasks_user_dialog(request):
    """removes the user with the given id
    """
    logger.debug('remove_tasks_user_dialog is starts')

    selected_task_list = get_multi_integer(request, 'task_ids', 'GET')
    user_id = request.matchdict.get('user_id')
    user_type = request.matchdict.get('user_type')

    user = User.query.filter(User.id == user_id).first()

    came_from = request.params.get('came_from', '/')

    _query_buffer = []
    for task_id in selected_task_list:
        _query_buffer.append("""task_ids=%s""" % task_id)
    _query = '&'.join(_query_buffer)

    action = '/tasks/remove/%s/%s?%s' % (user_type, user.id, _query)

    message = '%s will be removed from resources of selected tasks' \
              '<br><br>Are you sure?' % user.name

    logger.debug('action: %s' % action)

    return {
        'message': message,
        'came_from': came_from,
        'action': action
    }


@view_config(
    route_name='remove_tasks_user',
    permission='Update_Task'
)
def remove_tasks_user(request):
    """removes the user with the given id
    """

    user_id = request.matchdict.get('user_id')
    user = User.query.filter(User.id == user_id).first()
    user_type = request.matchdict.get('user_type')

    if not user:
        transaction.abort()
        return Response('Can not find a user with id: %s' % user_id, 500)

    selected_task_list = get_multi_integer(request, 'task_ids', 'GET')
    tasks = Task.query.filter(Task.id.in_(selected_task_list)).all()
    if not tasks:
        transaction.abort()
        return Response('Can not find any Task', 500)

    if not user_type:
        transaction.abort()
        return Response('Missing parameters', 500)

    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    description = request.params.get('description', 'No note')
    note = create_simple_note(
                                '%(resource_name)s is removed '
                                'from %(user_type)s list by %(logged_in_user)s '
                                'with the note:<br/> %(description)s' % {
                                                'user_type':user_type,
                                                'resource_name': user.name,
                                                'logged_in_user': logged_in_user.name,
                                                'description': description
                                        },
                                'Removed Resource',
                                'red',
                                'removed_resource',
                                logged_in_user,
                                utc_now)

    if user_type == 'resources':
        for task in tasks:
            task.resources.remove(user)
            task.updated_by = logged_in_user
            task.date_updated = utc_now
            task.notes.append(note)

    elif user_type == 'responsible':
        for task in tasks:
            task.responsible.remove(user)
            task.updated_by = logged_in_user
            task.date_updated = utc_now
            task.notes.append(note)

    # invalidate all caches
    invalidate_all_caches()

    return Response('Success: %s is removed from resources of the selected tasks' % (user.name))


@view_config(
    route_name='change_tasks_properties_dialog',
    renderer='templates/task/dialog/change_tasks_properties_dialog.jinja2'
)
def change_tasks_properties_dialog(request):
    """changes task properties with the given users dialog
    """
    logger.debug('change_tasks_properties_dialog started')

    selected_task_list = get_multi_integer(request, 'task_ids', 'GET')
    logger.debug('selected_task_list : %s' % selected_task_list)

    tasks = Task.query.filter(Task.id.in_(selected_task_list)).all()
    logger.debug('tasks : %s' % tasks)

    came_from = request.params.get('came_from', '/')
    default_action = request.params.get("default_action", None)
    reviewer_id = request.params.get("reviewer_id", None)

    logger.debug('change_tasks_properties_dialog ended')

    return {
        'tasks': tasks,
        'came_from': came_from,
        'default_action': default_action,
        'reviewer_id': reviewer_id
    }


@view_config(
    route_name='change_tasks_priority_dialog',
    renderer='templates/task/dialog/change_tasks_priority_dialog.jinja2'
)
@view_config(
    route_name='change_tasks_users_dialog',
    renderer='templates/task/dialog/change_tasks_users_dialog.jinja2'
)
def selected_task_dialog(request):
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
        'user_type': user_type,
        'came_from': came_from,
        'project_id': project_id
    }




@view_config(
    route_name='change_tasks_priority'
)
def change_tasks_priority(request):
    """changes task priority with the given users
    """

    priority = int(request.params.get('priority', 500))

    selected_task_list = get_multi_integer(request, 'task_ids[]')
    logger.debug('selected_task_list : %s' % selected_task_list)

    tasks = Task.query.filter(Task.id.in_(selected_task_list)).all()
    logger.debug('tasks : %s' % tasks)

    if not tasks:
        transaction.abort()
        return Response('Can not find any Task', 500)

    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    for task in tasks:
        task.priority = priority
        task.updated_by = logged_in_user
        task.date_updated = utc_now

        # also update all children
        for ct in task.walk_hierarchy():
            ct.priority = priority

    # invalidate all caches
    invalidate_all_caches()

    return Response('Success')


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
        'user_type': user_type,
        'came_from': came_from
    }


@view_config(
    route_name='set_task_start_end_date_dialog',
    renderer='templates/task/dialog/set_task_start_end_date_dialog.jinja2'
)
def set_task_start_end_date_dialog(request):
    """set_task_start_end_date_dialog
    """
    logger.debug('set_task_start_end_date_dialog is starts')

    came_from = request.params.get('came_from', '/')

    selected_task_list = get_multi_integer(request, 'task_ids', 'GET')
    logger.debug('selected_task_list: %s' % selected_task_list)

    _query_buffer = []
    for task_id in selected_task_list:
        _query_buffer.append("""task_ids=%s""" % task_id)
    _query = '&'.join(_query_buffer)

    action = '/tasks/set_start_end_date?%s' % (_query)

    logger.debug('action: %s' % action)

    return {
        'came_from': came_from,
        'action': action
    }


@view_config(
    route_name='set_task_start_end_date',
    permission='Update_Task'
)
def set_task_start_end_date(request):
    """sets task start end date with the data
    """
    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    selected_task_list = get_multi_integer(request, 'task_ids', 'GET')
    tasks = Task.query.filter(Task.id.in_(selected_task_list)).all()

    if not tasks:
        transaction.abort()
        return Response('Can not find any Task', 500)

    start_date = get_date(request, 'start')
    end_date = get_date(request, 'end')

    if not start_date:
        transaction.abort()
        return Response('Please supply date range', 500)

    for task in tasks:
        task.start = start_date
        task.end = end_date

        task.updated_by = logged_in_user
        task.date_updated = utc_now

    return Response('Success: New date range is set for selected tasks')


@view_config(
    route_name='change_task_users',
    permission='Update_Task'
)
def change_task_users(request):
    """changes task users with the given users
    """
    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

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
    if user_type == 'resources':
        task.resources = users
    elif user_type == 'responsible':
        task.responsible = users

    task.updated_by = logged_in_user
    task.date_updated = utc_now

    # invalidate all caches
    invalidate_all_caches()

    return Response('Success: %s are added to %s resources' % (user_type, task.name))


@view_config(
    route_name='change_tasks_users',
    permission='Update_Task'
)
def change_tasks_users(request):
    """changes task users with the given users
    """
    from stalker import User
    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    selected_list = get_multi_integer(request, 'user_ids')
    users = User.query.filter(User.id.in_(selected_list)).all()

    if not users:
        transaction.abort()
        return Response('Missing parameters', 500)

    selected_task_list = get_multi_integer(request, 'task_ids', 'GET')
    tasks = Task.query.filter(Task.id.in_(selected_task_list)).all()

    if not tasks:
        transaction.abort()
        return Response('Can not find any Task', 500)

    user_type = request.matchdict.get('user_type')
    logger.debug("user_type: %s" % user_type)

    if not user_type:
        transaction.abort()
        return Response('Missing parameters', 500)

    if user_type == 'resources':
        for task in tasks:
            task.resources = users
            task.updated_by = logged_in_user
            task.date_updated = utc_now
    elif user_type == 'responsible':
        for task in tasks:
            task.responsible = users
            task.updated_by = logged_in_user
            task.date_updated = utc_now
    elif user_type == 'resources_responsible':
        for task in tasks:
            task.resources = users
            task.responsible = users
            task.updated_by = logged_in_user
            task.date_updated = utc_now
    elif user_type == 'reviewer_responsible':
        original_reviewer_id = request.params.get("original_reviewer_id")
        if original_reviewer_id:
            from stalker import Review, Status
            original_reviewer = User.query.get(original_reviewer_id)
            new_status = Status.query.filter(Status.code == 'NEW').first()

            reviews = Review.query \
                .filter(Review.task_id.in_(selected_task_list)) \
                .filter(Review.status == new_status) \
                .filter(Review.reviewer == original_reviewer) \
                .all()
            logger.debug("reviews: %s" % reviews)
            # update reviewer
            for review in reviews:
                review.reviewer = users[0]

            import copy
            for task in tasks:
                # update the responsible
                logger.debug("Removing reviewer from: %s (%s)" % (task.name, task.id))
                task_responsible = copy.copy(task.responsible)
                if original_reviewer in task_responsible:
                    task_responsible.remove(original_reviewer)
                task_responsible.append(users[0])
                task.responsible = task_responsible

    # invalidate all caches
    invalidate_all_caches()

    return Response('Success: %s are added to selected tasks' % user_type)


@view_config(
    route_name='add_tasks_dependencies_dialog',
    renderer='templates/task/dialog/add_tasks_dependencies_dialog.jinja2'
)
def add_tasks_dependencies_dialog(request):
    """creates the add task dependency dialog
    """
    # get task ids and pass it to the dialog
    # also get the project id
    task_ids = get_multi_integer(request, 'task_ids', 'GET')
    project_id = request.params.get('project_id')

    logger.debug('task_ids: %s' % task_ids)

    return {
        'task_ids': task_ids,
        'project_id': project_id
    }


@view_config(
    route_name='add_tasks_dependencies',
    renderer='json'
)
def add_tasks_dependencies(request):
    """it will add the given dependencies to the given tasks without removing
    them
    """
    task_ids = get_multi_integer(request, 'task_ids[]')
    dep_ids = get_multi_integer(request, 'dependent_ids[]')

    logger.debug('task_ids: %s' % task_ids)
    logger.debug('dep_ids: %s' % dep_ids)

    # get each task
    tasks = Task.query.filter(Task.id.in_(task_ids)).all()
    deps = Task.query.filter(Task.id.in_(dep_ids)).all()

    from stalker.exceptions import CircularDependencyError, StatusError

    for t in tasks:
        for d in deps:
            if d not in t.depends:
                try:
                    t.depends.append(d)
                except (CircularDependencyError, StatusError):
                    pass

    # invalidate all caches
    invalidate_all_caches()

    return Response('Tasks updated successfully!')


@view_config(
    route_name='makedir_task'
)
def makedir_task(request):
    """add task to the logged in users watch list
    """
    logged_in_user = get_logged_in_user(request)

    task_id = request.matchdict.get('id')
    task = Task.query.get(task_id)

    children = find_leafs_in_hierarchy(task, [])

    for child in children:
        try:
            os.makedirs(child.absolute_path)
        except OSError:
                pass

    # invalidate all caches
    invalidate_all_caches()

    return Response('Task folders are created successfully')


@view_config(
    route_name='watch_task'
)
def watch_task(request):
    """add task to the logged in users watch list
    """
    logged_in_user = get_logged_in_user(request)
    task_id = request.matchdict.get('id')
    task = Task.query.get(task_id)

    if logged_in_user not in task.watchers:
        task.watchers.append(logged_in_user)

    # invalidate all caches
    invalidate_all_caches()

    return Response('Task successfully added to watch list')


@view_config(
    route_name='watch_tasks'
)
def watch_tasks(request):
    """add task to the logged in users watch list
    """
    logged_in_user = get_logged_in_user(request)
    selected_task_list = get_multi_integer(request, 'task_ids', 'GET')
    tasks = Task.query.filter(Task.id.in_(selected_task_list)).all()

    if not tasks:
        transaction.abort()
        return Response('Can not find any Task', 500)

    for task in tasks:
        if logged_in_user not in task.watchers:
            task.watchers.append(logged_in_user)

    # invalidate all caches
    invalidate_all_caches()

    return Response('Tasks successfully added to watch list')


@view_config(
    route_name='unwatch_task'
)
def unwatch_task(request):
    """remove task from the logged in users watch list
    """
    logged_in_user = get_logged_in_user(request)
    task_id = request.matchdict.get('id')
    task = Task.query.get(task_id)

    if logged_in_user in task.watchers:
        task.watchers.remove(logged_in_user)

    # invalidate all caches
    invalidate_all_caches()

    return Response('Task successfully removed from watch list')


@view_config(
    route_name='unwatch_tasks'
)
def unwatch_tasks(request):
    """remove task from the logged in users watch list
    """
    logged_in_user = get_logged_in_user(request)
    selected_task_list = get_multi_integer(request, 'task_ids', 'GET')
    tasks = Task.query.filter(Task.id.in_(selected_task_list)).all()

    if not tasks:
        transaction.abort()
        return Response('Can not find any Task', 500)

    for task in tasks:
        if logged_in_user in task.watchers:
            task.watchers.remove(logged_in_user)

    # invalidate all caches
    invalidate_all_caches()

    return Response('Tasks successfully removed from watch list')


def fix_task_computed_time(task):

    """Fix task's computed_start and computed_end time based on timelogs of the given task.

    :param task: The stalker task instance that the time log will be
      investigated.
    :type task: :class:`stalker.models.task.Task`
    :return: :class:`datetime.datetime`
    """
    invalidate_all_caches()
    if task.status.code not in ['CMPL', 'STOP', 'OH']:
        return

    else:
        start_time = get_actual_start_time(task)
        end_time = get_actual_end_time(task)

        task.computed_start = start_time
        task.computed_end = end_time

        logger.debug('Task computed time is fixed!')


def get_actual_start_time(task):
    """Returns the start time of the earliest time logs of the given task if it
    has any time logs, or it will return the task start_time.

    :param task: The stalker task instance that the time log will be
      investigated.
    :type task: :class:`stalker.models.task.Task`
    :return: :class:`datetime.datetime`
    """

    if not isinstance(task, Task):
        raise TypeError(
            'task should be an instance of stalker.models.task.Task, not %s' %
            task.__class__.__name__
        )

    first_time_log = TimeLog.query\
        .filter(TimeLog.task == task)\
        .order_by(TimeLog.start.asc())\
        .first()

    if first_time_log:
        return first_time_log.start
    else:
        if task.schedule_model == 'duration':
            start_time = task.project.start
            for tdep in task.depends:
                if tdep.computed_end > start_time:
                    start_time = tdep.computed_end
            return start_time

    return task.computed_start


def get_actual_end_time(task):
    """Returns the end time of the latest time logs of the given task if it
    has any time logs, or it will return the task end_time.

    :param task: The stalker task instance that the time log will be
      investigated.
    :type task: :class:`stalker.models.task.Task`
    :return: :class:`datetime.datetime`
    """

    if not isinstance(task, Task):
        raise TypeError(
            'task should be an instance of stalker.models.task.Task, not %s' %
            task.__class__.__name__
        )

    end_time_log = TimeLog.query\
        .filter(TimeLog.task == task)\
        .order_by(TimeLog.end.desc())\
        .first()

    if end_time_log:
        return end_time_log.end
    else:
        if task.schedule_model == 'duration':
            end_time = task.project.start
            for tdep in task.depends:
                if tdep.computed_end > end_time:
                    duration = datetime.timedelta(minutes=0)
                    if task.schedule_unit == 'min':
                         duration = datetime.timedelta(minutes=task.schedule_timing)
                    elif task.schedule_unit == 'h':
                         duration = datetime.timedelta(hours=task.schedule_timing)
                    elif task.schedule_unit == 'd':
                         duration = datetime.timedelta(days=task.schedule_timing)
                    elif task.schedule_unit == 'w':
                         duration = datetime.timedelta(weeks=task.schedule_timing)
                    elif task.schedule_unit == 'm':
                         duration = datetime.timedelta(weeks=4*task.schedule_timing)
                    end_time = tdep.computed_end + duration
            return end_time

    return task.computed_end


@view_config(
    route_name='get_task_absolute_full_path',
    renderer='json'
)
def get_task_absolute_full_path(request):

    task_id = request.matchdict.get('id')
    task = Task.query.filter(Task.id == task_id).first()

    if not task:
        transaction.abort()
        return Response('Can not find a Task with id: %s' % task_id, 500)

    version = Version.query.filter(Version.task == task).first()

    if not version:
        transaction.abort()
        return Response('Can not find a Version for task : %s' % task.name, 500)

    repo = task.project.repository
    user_os = get_user_os(request)

    if repo:
        if user_os == 'windows':
            return repo.to_windows_path(version.absolute_full_path)
        elif user_os == 'linux':
            return repo.to_linux_path(version.absolute_full_path)
        elif user_os == 'osx':
            return repo.to_osx_path(version.absolute_full_path)

    return version.absolute_full_path
