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
import time
import datetime

from pyramid.httpexceptions import (HTTPFound, HTTPServerError)
from pyramid.response import Response
from pyramid.security import forget, remember
from pyramid.view import view_config, forbidden_view_config
from sqlalchemy import or_
import transaction

import stalker_pyramid
from stalker import (defaults, User, Department, Group, Project, Studio,
                     Permission, EntityType)
from stalker.db import DBSession
from stalker_pyramid.views import (log_param, get_logged_in_user,
                                   PermissionChecker, get_multi_integer,
                                   get_tags, milliseconds_since_epoch,
                                   StdErrToHTMLConverter)

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@view_config(
    route_name='create_user'
)
def create_user(request):
    """called when adding a User
    """

    logger.debug('***create user method starts ***')

    logged_in_user = get_logged_in_user(request)

    # get params
    came_from = request.params.get('came_from', '/')
    name = request.params.get('name', None)
    login = request.params.get('login', None)
    email = request.params.get('email', None)
    password = request.params.get('password', None)

    logger.debug('came_from : %s' % came_from)
    logger.debug('new user name : %s' % name)
    logger.debug('new user login : %s' % login)
    logger.debug('new user email : %s' % email)
    logger.debug('new user password : %s' % password)


    # create and add a new user
    if name and login and email and password:

        department_id = request.params.get('department_id', None)
        departments = []
        if department_id:
            department = Department.query.filter_by(id=department_id).first()
            departments = [department]
        else:
            # Departments
            if 'department_ids' in request.params:
                dep_ids = get_multi_integer(request, 'department_ids')
                departments = Department.query.filter(
                    Department.id.in_(dep_ids)).all()

        # Groups
        groups = []
        if 'group_ids' in request.params:
            grp_ids = get_multi_integer(request, 'group_ids')
            groups = Group.query.filter(
                Group.id.in_(grp_ids)).all()

        # Tags
        tags = get_tags(request)

        logger.debug('new user departments : %s' % departments)
        logger.debug('new user groups : %s' % groups)
        logger.debug('new user tags : %s' % tags)
        try:
            new_user = User(
                name=request.params['name'],
                login=request.params['login'],
                email=request.params['email'],
                password=request.params['password'],
                created_by=logged_in_user,
                departments=departments,
                groups=groups,
                tags=tags
            )

            DBSession.add(new_user)

            logger.debug('added new user successfully')

            request.session.flash(
                'success:User <strong>%s</strong> is created successfully' % name
            )

            logger.debug('***create user method ends ***')
            response = Response('User created successfully')
            response.status_int = 200
            return response

        except BaseException as e:
            # request.session.flash('error:' + e.message)
            # HTTPFound(location=came_from)
            transaction.abort()
            return Response('BaseException: %s' % e, 500)
    else:
        logger.debug('not all parameters are in request.params')
        log_param(request, 'name')
        log_param(request, 'login')
        log_param(request, 'email')
        log_param(request, 'password')

        response = Response('There are missing parameters: ')
        response.status_int = 500
        return response

    response = Response('User created successfully')
    response.status_int = 200
    return response


@view_config(
    route_name='update_user'
)
def update_user(request):
    """called when updating a User
    """

    logger.debug('***update user method starts ***')

    logged_in_user = get_logged_in_user(request)

    # get params
    came_from = request.params.get('came_from', '/')
    user_id = request.matchdict.get('id')
    user = User.query.filter(User.id == user_id).first()

    name = request.params.get('name')
    login = request.params.get('login')
    email = request.params.get('email')
    password = request.params.get('password')

    logger.debug('user : %s' % user)
    logger.debug('user new name : %s' % name)
    logger.debug('user new login : %s' % login)
    logger.debug('user new email : %s' % email)
    logger.debug('user new password : %s' % password)

    if user and name and login and email and password:
        # departments = []
        #
        # # Departments
        # if 'department_ids' in request.params:
        #     dep_ids = get_multi_integer(request, 'department_ids')
        #     departments = Department.query \
        #         .filter(Department.id.in_(dep_ids)).all()
        #
        # # Groups
        # groups = []
        # if 'group_ids' in request.params:
        #     grp_ids = get_multi_integer(request, 'group_ids')
        #     groups = Group.query \
        #         .filter(Group.id.in_(grp_ids)).all()

        # Tags
        tags = get_tags(request)

        user.name = name
        user.login = login
        user.email = email
        user.updated_by = logged_in_user
        user.date_updated = datetime.datetime.now()
        # user.departments = departments
        # user.groups = groups
        # user.tags = tags

        if password != 'DONTCHANGE':
            user.password = password

        DBSession.add(user)

        logger.debug('user is updated successfully')

        request.session.flash(
            'success:User <strong>%s</strong> is updated successfully' % name
        )
        logger.debug('***update user method ends ***')
    else:
        logger.debug('not all parameters are in request.params')
        log_param(request, 'user_id')
        log_param(request, 'name')
        log_param(request, 'login')
        log_param(request, 'email')
        log_param(request, 'password')
        HTTPServerError()

    return HTTPFound(
        location=came_from
    )


@view_config(
    route_name='get_entity_users_count',
    renderer='json',
    permission='List_User'
)
@view_config(
    route_name='get_project_users_count',
    renderer='json',
    permission='List_User'
)
@view_config(
    route_name='get_users_count',
    renderer='json',
    permission='List_User'
)
def get_users_count(request):
    """returns all users or one particular user from database
    """
    # if there is a simple flag, just return ids and names and login
    #simple = request.params.get('simple')

    # if there is an id it is probably a project
    entity_id = request.matchdict.get('id')

    entity_type = None
    if entity_id:
        sql_query = \
            'select entity_type from "SimpleEntities" where id=%s' % entity_id
        data = DBSession.connection().execute(sql_query).fetchone()
        entity_type = data[0] if data else None

    logger.debug('entity_id  : %s' % entity_id)
    logger.debug('entity_type: %s' % entity_type)

    if entity_id and entity_type not in ['Project', 'Department', 'Group', 'Task', 'User']:
        # there is no entity_type for that entity
        return []

    start = time.time()
    sql_query = """select
        count("Users".id)
    from "SimpleEntities"
    join "Users" on "SimpleEntities".id = "Users".id
    left outer join (
        select
            uid,
            array_agg(did) as dep_ids,
            array_agg(name) as dep_names
        from "User_Departments"
        join "SimpleEntities" on "User_Departments".did = "SimpleEntities".id
        group by uid
    ) as user_departments on user_departments.uid = "Users".id
    left outer join (
        select
            uid,
            array_agg(gid) as group_ids,
            array_agg(name) as group_names
        from "User_Groups"
        join "SimpleEntities" on "User_Groups".gid = "SimpleEntities".id
        group by uid
    ) as user_groups on user_groups.uid = "Users".id
    left outer join (
        select resource_id, count(task_id) as task_count from "Task_Resources" group by resource_id
    ) as tasks on tasks.resource_id = "Users".id
    left outer join (
        select
            owner_id,
            count("Tickets".id) as ticket_count
        from "Tickets"
        join "SimpleEntities" on "Tickets".status_id = "SimpleEntities".id
        where "SimpleEntities".name = 'New'
        group by owner_id, name
    ) as tickets on tickets.owner_id = "Users".id
    left outer join "Links" on "SimpleEntities".thumbnail_id = "Links".id
    """

    if entity_type == "Project":
        sql_query += """join "Project_Users" on "Users".id = "Project_Users".user_id
        where "Project_Users".project_id = %(id)s
        """ % {'id': entity_id}
    elif entity_type == "Department":
        sql_query += """join "User_Departments" on "Users".id = "User_Departments".uid
        where "User_Departments".did = %(id)s
        """ % {'id': entity_id}
    elif entity_type == "Group":
        sql_query += """join "User_Groups" on "Users".id = "User_Groups".uid
        where "User_Groups".gid = %(id)s
        """ % {'id': entity_id}
    elif entity_type == "Task":
        sql_query += """join "Task_Resources" on "Users".id = "Task_Resources".resource_id
        where "Task_Resources".task_id = %(id)s
        """ % {'id': entity_id}
    elif entity_type == "User":
        sql_query += 'where "Users".id = %s' % entity_id

    return DBSession.connection().execute(sql_query).fetchone()[0]


@view_config(
    route_name='get_entity_users',
    renderer='json',
    permission='List_User'
)
@view_config(
    route_name='get_project_users',
    renderer='json',
    permission='List_User'
)
@view_config(
    route_name='get_users',
    renderer='json',
    permission='List_User'
)
@view_config(
    route_name='get_user',
    renderer='json',
    permission='Read_User'
)
def get_users(request):
    """returns all users or one particular user from database
    """
    # if there is a simple flag, just return ids and names and login
    #simple = request.params.get('simple')

    # if there is an id it is probably a project
    entity_id = request.matchdict.get('id')

    entity_type = None


    update_user_permission = PermissionChecker(request)('Update_User')
    delete_user_permission = PermissionChecker(request)('Delete_User')

    delete_user_action ='/users/%(id)s/delete/dialog'


    if entity_id:
        sql_query = \
            'select entity_type from "SimpleEntities" where id=%s' % entity_id
        data = DBSession.connection().execute(sql_query).fetchone()
        entity_type = data[0] if data else None
        delete_user_action ='/entities/%(id)s/%(entity_id)s/remove/dialog'

    logger.debug('entity_id  : %s' % entity_id)
    logger.debug('entity_type: %s' % entity_type)

    if entity_id and entity_type not in ['Project', 'Department', 'Group', 'Task', 'User']:
        # there is no entity_type for that entity
        return []

    start = time.time()
    sql_query = """select
        "Users".id,
        "SimpleEntities".name,
        "Users".login,
        "Users".email,
        user_departments."dep_ids",
        user_departments."dep_names",
        user_groups."group_ids",
        user_groups."group_names",
        tasks.task_count,
        tickets.ticket_count,
        "Links".full_path
    from "SimpleEntities"
    join "Users" on "SimpleEntities".id = "Users".id
    left outer join (
        select
            uid,
            array_agg(did) as dep_ids,
            array_agg(name) as dep_names
        from "User_Departments"
        join "SimpleEntities" on "User_Departments".did = "SimpleEntities".id
        group by uid
    ) as user_departments on user_departments.uid = "Users".id
    left outer join (
        select
            uid,
            array_agg(gid) as group_ids,
            array_agg(name) as group_names
        from "User_Groups"
        join "SimpleEntities" on "User_Groups".gid = "SimpleEntities".id
        group by uid
    ) as user_groups on user_groups.uid = "Users".id
    left outer join (
        select resource_id, count(task_id) as task_count from "Task_Resources" group by resource_id
    ) as tasks on tasks.resource_id = "Users".id
    left outer join (
        select
            owner_id,
            count("Tickets".id) as ticket_count
        from "Tickets"
        join "SimpleEntities" on "Tickets".status_id = "SimpleEntities".id
        where "SimpleEntities".name = 'New'
        group by owner_id, name
    ) as tickets on tickets.owner_id = "Users".id
    left outer join "Links" on "SimpleEntities".thumbnail_id = "Links".id
    """

    if entity_type == "Project":
        sql_query += """join "Project_Users" on "Users".id = "Project_Users".user_id
        where "Project_Users".project_id = %(id)s
        """ % {'id': entity_id}
    elif entity_type == "Department":
        sql_query += """join "User_Departments" on "Users".id = "User_Departments".uid
        where "User_Departments".did = %(id)s
        """ % {'id': entity_id}
    elif entity_type == "Group":
        sql_query += """join "User_Groups" on "Users".id = "User_Groups".uid
        where "User_Groups".gid = %(id)s
        """ % {'id': entity_id}
    elif entity_type == "Task":
        sql_query += """join "Task_Resources" on "Users".id = "Task_Resources".resource_id
        where "Task_Resources".task_id = %(id)s
        """ % {'id': entity_id}
    elif entity_type == "User":
        sql_query += 'where "Users".id = %s' % entity_id

    sql_query += 'order by "SimpleEntities".name'

    result = DBSession.connection().execute(sql_query)
    data = [
        {
            'id': r[0],
            'name': r[1],
            'login': r[2],
            'email': r[3],
            'departments': [
                {
                    'id': r[4][i],
                    'name': r[5][i]
                } for i, a in enumerate(r[4])
            ] if r[4] else [],
            'groups': [
                {
                    'id': r[6],
                    'name': r[7]
                } for i in range(len(r[6]))
            ] if r[6] else [],
            'tasksCount': r[8] or 0,
            'ticketsCount': r[9] or 0,
            'thumbnail_full_path': r[10] if r[10] else None,
            'update_user_action':'/users/%s/update/dialog' % r[0] if update_user_permission else None,
            'delete_user_action':delete_user_action % {'id':r[0],'entity_id':entity_id} if delete_user_permission else None
        } for r in result.fetchall()
    ]

    end = time.time()
    logger.debug('get_users took : %s seconds for %s rows' %
                 ((end - start), len(data)))
    return data



def get_permissions_from_multi_dict(multi_dict):
    """returns the permission instances from the given multi_dict
    """
    permissions = []

    # gather all access, actions, and class_names
    all_class_names = [entity_type.name for entity_type in
                       EntityType.query.all()]
    all_actions = defaults.actions

    logger.debug(all_class_names)
    logger.debug(all_actions)

    for key in multi_dict.keys():
        access = multi_dict[key]
        action_and_class_name = key.split('_')

        try:
            action = action_and_class_name[0]
            class_name = action_and_class_name[1]

            logger.debug('access     : %s' % access)
            logger.debug('action     : %s' % action)
            logger.debug('class_name : %s' % class_name)

        except IndexError:
            continue

        else:

            if access in ['Allow', 'Deny'] and \
                            class_name in all_class_names and \
                            action in all_actions:

                # get permissions
                permission = Permission.query \
                    .filter_by(access=access) \
                    .filter_by(action=action) \
                    .filter_by(class_name=class_name) \
                    .first()

                if permission:
                    permissions.append(permission)

    logger.debug(permissions)
    return permissions


@view_config(
    route_name='logout'
)
def logout(request):
    headers = forget(request)
    return HTTPFound(
        location=request.route_url('login'),
        headers=headers
    )


@forbidden_view_config(
    renderer='templates/auth/login.jinja2'
)
@view_config(
    route_name='login',
    renderer='templates/auth/login.jinja2'
)
def login(request):
    """the login view
    """
    logger.debug('login start')
    login_url = request.route_url('login')
    referrer = request.url
    if referrer == login_url:
        referrer = '/'

    came_from = request.params.get('came_from', referrer)

    login = request.params.get('login', '')
    password = request.params.get('password', '')
    has_error = False

    if 'submit' in request.params:
        # get the user again (first got it in validation)
        user_obj = User.query \
            .filter(or_(User.login == login, User.email == login)).first()

        if user_obj:
            login = user_obj.login

        if user_obj and user_obj.check_password(password):
            headers = remember(request, login)
            # form submission succeeded
            return HTTPFound(
                location=came_from,
                headers=headers,
            )
        else:
            has_error = True

    return {
        'login': login,
        'password': password,
        'has_error': has_error,
        'came_from': came_from
    }


@view_config(
    route_name='flash_message',
    renderer='templates/home.jinja2'
)
@view_config(
    route_name='home',
    renderer='templates/auth/view/view_user.jinja2'
)
@view_config(
    route_name='me_menu',
    renderer='templates/auth/me_menu.jinja2'
)
def home(request):
    logged_in_user = get_logged_in_user(request)

    studio = Studio.query.first()
    projects = Project.query.all()

    flash_message = request.params.get('flash')
    if flash_message:
        request.session.flash(flash_message)

    return {
        'stalker_pyramid': stalker_pyramid,
        'studio': studio,
        'logged_in_user': logged_in_user,
        'has_permission': PermissionChecker(request),
        'milliseconds_since_epoch': milliseconds_since_epoch,
        'projects': projects,
        'entity': logged_in_user
    }


@view_config(
    route_name='check_login_availability',
    renderer='json'
)
def check_login_availability(request):
    """checks it the given login is available
    """
    login = request.matchdict['login']
    logger.debug('checking availability for: %s' % login)

    available = 1
    if login:
        user = User.query.filter(User.login == login).first()
        if user:
            available = 0

    return {
        'available': available
    }


@view_config(
    route_name='check_email_availability',
    renderer='json'
)
def check_email_availability(request):
    """checks it the given email is available
    """
    email = request.matchdict['email']
    logger.debug('checking availability for: %s' % email)

    available = 1
    if email:
        user = User.query.filter(User.email == email).first()
        if user:
            available = 0

    return {
        'available': available
    }


@view_config(
    route_name='get_entity_resources',
    permission='Read_User',
    renderer='json'
)
@view_config(
    route_name='get_resources',
    permission='Read_User',
    renderer='json'
)
@view_config(
    route_name='get_resource',
    permission='Read_User',
    renderer='json'
)
def get_resources(request):
    """returns Users for Resource View
    """
    # TODO: This is a very ugly function, please define the borders and use cases correctly and then clean it

    from stalker_pyramid.views.task import query_of_tasks_hierarchical_name_table

    start = time.time()
    # return users for now
    # /resources/
    # /resources/26/
    resource_id = request.matchdict.get('id')
    logger.debug('resource_id: %s' % resource_id)

    parent_id = request.params.get('parent_id')
    logger.debug('parent_id: %s' % parent_id)

    execute = DBSession.connection().execute

    entity_type = None
    if resource_id:
        # get the entity type of that resource
        data = execute('select entity_type from "SimpleEntities" where id=%s' %
                       resource_id).fetchone()
        if data:
            entity_type = data[0]
        else:
            return []
    else:
        # default to User
        entity_type = "User"
    logger.debug('entity_type : %s' % entity_type)

    # get resource details plus time logs
    if not parent_id:
        if entity_type == 'Department':
            resource_sql_query = """select
                "SimpleEntities".id,
                "SimpleEntities".name,
                "SimpleEntities".entity_type,
                count(*) as resource_count
            from "SimpleEntities"
            join "User_Departments" on "User_Departments".did = "SimpleEntities".id
            where "SimpleEntities".entity_type = '%s'
            """ % entity_type
        elif entity_type == 'User':
            resource_sql_query = """select
                "SimpleEntities".id,
                "SimpleEntities".name,
                "SimpleEntities".entity_type,
                1 as resource_count
            from "SimpleEntities"
            where "SimpleEntities".entity_type = '%s'
            """ % entity_type
        elif entity_type in ['Studio', 'Project']:
            resource_sql_query = """select
                "SimpleEntities".id,
                "SimpleEntities".name,
                "SimpleEntities".entity_type,
                count(*) as resource_count
            from "SimpleEntities"
            join "User_Departments" on "User_Departments".did = "SimpleEntities".id
            """

        if resource_id and entity_type not in ["Studio", "Project"]:
            resource_sql_query += "and id=%s group by id, name, entity_type order by name" % resource_id
        else:
            resource_sql_query += "group by id, name, entity_type order by name"

        # if the given entity is a Department return all the time logs of the
        # users of that department
        time_log_query = """select
            "TimeLogs".id,
            "TimeLogs".task_id,
            extract(epoch from "TimeLogs".start::timestamp AT TIME ZONE 'UTC') * 1000 as start,
            extract(epoch from "TimeLogs".end::timestamp AT TIME ZONE 'UTC') * 1000 as end
        from "TimeLogs"
        """

        tasks_query = """select
            tasks.id,
            tasks.full_path,
            extract(epoch from "Tasks".computed_start::timestamp AT TIME ZONE 'UTC') * 1000 as start,
            extract(epoch from "Tasks".computed_end::timestamp AT TIME ZONE 'UTC') * 1000 as end
        -- start with tasks (with full names)
        from (
            %(tasks_hierarchical_name_table)s
        ) as tasks
            join "Tasks" on tasks.id = "Tasks".id
        """ % {
            'tasks_hierarchical_name_table':
                query_of_tasks_hierarchical_name_table(ordered=False)
        }

        has_children = False

        if entity_type == "User":
            time_log_query += "where resource_id = %(id)s"

            tasks_query += """join "Task_Resources" on "Tasks".id = "Task_Resources".task_id
            where not (
                exists (
                    select 1
                    from "Tasks"
                    where "Tasks".parent_id = tasks.id
                )
            ) and resource_id = %(id)s
            """

            has_children = False
        elif entity_type in ["Department", "Studio"]:
            time_log_query += """
            join "User_Departments" on "User_Departments".uid = "TimeLogs".resource_id
            where did = %(id)s"""

            tasks_query += """join "Task_Resources" on "Tasks".id = "Task_Resources".task_id
            join "User_Departments" on "Task_Resources".resource_id = "User_Departments".uid
            join "SimpleEntities" as "Task_SimpleEntities" on "Tasks".id = "Task_SimpleEntities".id
            where not (
                exists (
                    select 1
                    from "Tasks"
                    where "Tasks".parent_id = tasks.id
                )
            )
            and did = %(id)s
            group by tasks.id, tasks.full_path, "Tasks".start, "Tasks".end, "Tasks".computed_start, "Tasks".computed_end
            order by start
            """

            has_children = True
        elif entity_type == "Project":
            # the resource is a Project return all the project tasks and
            # return all the time logs of the users in that project
            time_log_query += """
            join "User_Departments" on "User_Departments".uid = "TimeLogs".resource_id
            -- where did = %(id)s
            """

            tasks_query += """
            -- select all the leaf tasks of the users of a specific Project
            select
                "Tasks".id,
                "Task_SimpleEntities".name,
                extract(epoch from "Tasks".computed_start::timestamp AT TIME ZONE 'UTC') * 1000 as start,
                extract(epoch from "Tasks".computed_end::timestamp AT TIME ZONE 'UTC') * 1000 as end
            from "Tasks"
                join "SimpleEntities" as "Task_SimpleEntities" on "Tasks".id = "Task_SimpleEntities".id
                where not (
                    exists (
                        select 1
                        from "Tasks"
                        where "Tasks".parent_id = tasks.id
                    )
                ) and project_id = %(id)s
            group by id, "Task_SimpleEntities".name, start, "end", "Tasks".computed_start, "Tasks".computed_end
            order by start
            """

            has_children = True

    else:
        # return departments ??? should also return Groups, Project etc.
        # that contains users
        resource_sql_query = """select
            "Users".id,
            "SimpleEntities".name,
            "SimpleEntities".entity_type,
            1 as resource_count
        from "Users"
        join "SimpleEntities" on "SimpleEntities".id = "Users".id
        join "User_Departments" on "User_Departments".uid = "Users".id
        join "Departments" on "User_Departments".did = "Departments".id
        where "Departments".id = %(id)s
        order by name
        """ % {'id': parent_id}

        time_log_query = """select
            "TimeLogs".id,
            "TimeLogs".task_id,
            extract(epoch from "TimeLogs".start::timestamp AT TIME ZONE 'UTC') * 1000 as start,
            extract(epoch from "TimeLogs".end::timestamp AT TIME ZONE 'UTC') * 1000 as end
        from "TimeLogs"
        where resource_id = %(id)s
        """

        tasks_query = """select
            tasks.id,
            tasks.full_path,
            extract(epoch from "Tasks".computed_start::timestamp AT TIME ZONE 'UTC') * 1000 as start,
            extract(epoch from "Tasks".computed_end::timestamp AT TIME ZONE 'UTC') * 1000 as end
        from (
            %(tasks_hierarchical_name_table)s
        ) as tasks
            join "Tasks" on tasks.id = "Tasks".id
            join "Task_Resources" on tasks.id = "Task_Resources".task_id
        where
            not (
                exists (
                    select 1
                    from "Tasks"
                    where "Tasks".parent_id = tasks.id
                )
            ) and resource_id = %(id)s
        """

        has_children = False

    # logger.debug('resource_sql_query : %s' % resource_sql_query)
    # logger.debug('time_log_query : %s' % time_log_query)
    # logger.debug('tasks_sql_query : %s' % tasks_query)

    resources_result = execute(resource_sql_query).fetchall()

    # logger.debug('resources_result : %s' % resources_result)

    link = '/%s/%s/view' % (entity_type.lower(), '%s')
    data = [
        {
            'id': rr[0],
            'name': rr[1],
            'type': rr[2],
            'resource_count': rr[3],
            'hasChildren': has_children,
            'link': link % rr[0],
            'time_logs': [
                {
                    'id': tr[0],
                    'task_id': tr[1],
                    'start': tr[2],
                    'end': tr[3]
                } for tr in execute(
                    time_log_query % {
                        'id': rr[0]
                    }).fetchall()
            ],
            'tasks': [
                {
                    'id': tr[0],
                    'name': tr[1],
                    'start': tr[2],
                    'end': tr[3]
                } for tr in execute(
                    tasks_query % {
                        'tasks_hierarchical_name_table':
                            query_of_tasks_hierarchical_name_table(False),
                        'id': rr[0]
                    }
                ).fetchall()
            ]
        } for rr in resources_result
    ]

    end = time.time()
    logger.debug('get_resources took : %s seconds' % (end - start))

    data_count = len(data)
    content_range = '%s-%s/%s' % (0, data_count - 1, data_count)

    resp = Response(
        json_body=data
    )
    resp.content_range = content_range
    return resp


@view_config(
    route_name='delete_user_dialog',
    renderer='templates/modals/confirm_dialog.jinja2'
)
def delete_user_dialog(request):
    """deletes the user with the given id
    """
    logger.debug('delete_user_dialog is starts')

    user_id = request.matchdict.get('id')
    user = User.query.get(user_id)

    came_from = request.params.get('came_from', request.current_route_path())
    action = '/users/%s/delete?came_from=%s'% (user_id,came_from)


    message = 'Are you sure you want to <strong>delete User %s </strong>?'% (user.name)

    logger.debug('action: %s' % action)

    return {
            'came_from': came_from,
            'message': message,
            'action': action
        }


@view_config(
    route_name='delete_user',
    permission='Delete_User'
)
def delete_user(request):
    """deletes the user with the given id
    """
    user_id = request.matchdict.get('id')
    user = User.query.get(user_id)

    if not user:
        transaction.abort()
        return Response('Can not find a User with id: %s' % user_id, 500)

    try:
        DBSession.delete(user)

        transaction.commit()
        request.session.flash(
            'success: %s is deleted' % user.name
        )
    except Exception as e:
        transaction.abort()
        c = StdErrToHTMLConverter(e)
        transaction.abort()
        request.session.flash(
            c.html()
        )
        return Response(c.html(), 500)

    return Response('Successfully deleted user: %s' % user_id)
