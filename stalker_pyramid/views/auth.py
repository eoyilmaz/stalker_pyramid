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
import datetime
# import colander
# from deform import widget
# import deform

from pyramid.httpexceptions import HTTPFound, HTTPOk, HTTPServerError
from pyramid.security import authenticated_userid, forget, remember
from pyramid.view import view_config, forbidden_view_config
from sqlalchemy import or_

import stalker_pyramid
from stalker import (defaults, User, Department, Group, Project, Entity,
                     Studio, Permission, EntityType, Task, Vacation)
from stalker.db import DBSession
from stalker_pyramid.views import (log_param, get_logged_in_user,
                                   PermissionChecker, get_multi_integer, get_tags, milliseconds_since_epoch)

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

        except BaseException as e:
            request.session.flash('error:' + e.message)
            HTTPFound(location=came_from)
    else:
        logger.debug('not all parameters are in request.params')
        log_param(request, 'name')
        log_param(request, 'login')
        log_param(request, 'email')
        log_param(request, 'password')
        HTTPServerError()

    return HTTPFound(
        location=came_from
    )


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
    route_name='get_users',
    renderer='json',
    permission='List_User'
)
def get_users(request):
    """returns all the users in database
    """
    # if there is a simple flag, just return ids and names and login
    simple = request.GET.get('simple')
    if simple:
        return [
            {
                'id': user.id,
                'name': user.name,
                'login': user.login,
            }
            for user in User.query.order_by(User.name.asc()).all()
        ]
    else:
        return [
            {
                'id': user.id,
                'name': user.name,
                'login': user.login,
                'email': user.email,
                'departments': [
                    {
                        'id': department.id,
                        'name': department.name
                    } for department in user.departments
                ],
                'groups': [
                    {
                        'id': group.id,
                        'name': group.name
                    } for group in user.groups
                ],
                'tasksCount': len(user.tasks),
                'ticketsCount': len(user.open_tickets),
                'thumbnail_path': user.thumbnail.full_path if user.thumbnail else None
            }
            for user in User.query.order_by(User.name.asc()).all()
        ]


# @view_config(
#     route_name='get_project_users',
#     renderer='json',
#     permission='List_User'
# )
# @view_config(
#     route_name='get_entity_users',
#     renderer='json',
#     permission='List_User'
# )
# def get_entity_users(request):
#     """returns all the Users of a given Entity
#     """
#     entity_id = request.matchdict.get('id', -1)
#     entity = Entity.query.filter_by(id=entity_id).first()
#
#     simple = request.GET.get('simple', False)
#
#     # works for Departments and Projects or any entity that has users attribute
#     if simple:
#         return [{
#             'id': user.id,
#             'name': user.name,
#             'login': user.login,
#         } for user in sorted(entity.users, key=lambda x: x.name.lower())]
#     return [{
#         'id': user.id,
#         'name': user.name,
#         'login': user.login,
#         'email': user.email,
#         'departments': [
#             {
#                 'id': department.id,
#                 'name': department.name
#             } for department in user.departments
#         ],
#         'groups': [
#             {
#                 'id': group.id,
#                 'name': group.name
#             } for group in user.groups
#         ],
#         'tasksCount': len(user.tasks),
#         'ticketsCount': len(user.open_tickets),
#         'thumbnail_path': user.thumbnail.full_path if user.thumbnail else None
#     } for user in sorted(entity.users, key=lambda x: x.name.lower())]
#
#
# @view_config(
#     route_name='get_entity_users_not',
#     renderer='json',
#     permission='List_User'
# )
# def get_users_not_in_entity(request):
#     """returns all the Users which are not related with the given Entity
#     """
#     entity_id = request.matchdict.get('id', -1)
#     entity = Entity.query.filter_by(id=entity_id).first()
#
#     entity_class = None
#     if entity.entity_type == 'Project':
#         entity_class = Project
#     elif entity.entity_type == 'Department':
#         entity_class = Department
#
#     logger.debug(User.query.filter(User.notin_(entity_class.users)).all())
#
#     # works for Departments and Projects or any entity that has users attribute
#     return [
#         {
#             'id': user.id,
#             'name': user.name,
#             'login': user.login,
#             'tasksCount': len(user.tasks),
#             'ticketsCount': len(user.open_tickets),
#             'thumbnail_path': user.thumbnail.full_path if user.thumbnail else None
#         }
#         for user in entity.users
#     ]
#

@view_config(
    route_name='append_users_to_entity_dialog',
    renderer='templates/auth/dialog_append_users_to_entity.jinja2'
)
def append_users_to_entity_dialog(request):
    """runs for append user dialog
    """
    logged_in_user = get_logged_in_user(request)

    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    return {
        'logged_in_user': logged_in_user,
        'has_permission': PermissionChecker(request),
        'entity': entity
    }


@view_config(
    route_name='append_users_to_entity'
)
def append_users_to_entity(request):
    """appends the given users o the given Project or Department
    """

    logger.debug('append_users_to_entity ')

    # users
    user_ids = get_multi_integer(request, 'user_ids')
    logger.debug('user_ids  : %s' % user_ids)
    users = User.query.filter(User.id.in_(user_ids)).all()

    # entity
    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter(Entity.id == entity_id).first()

    logger.debug('entity_id : %s' % entity_id)
    logger.debug('entity : %s' % entity)
    logger.debug('users  : %s' % users)

    if users and entity:
        entity.users = users
        DBSession.add(entity)
        DBSession.add_all(users)

    return HTTPOk()


@view_config(
    route_name='append_user_to_group'
)
@view_config(
    route_name='append_user_to_department'
)
def append_user_to_entity(request):
    """appends the given user to the given Project or Department or Group
    """
    # This is an unused method

    # user
    user_id = request.params.get('id', None)
    user = User.query.filter(User.id == user_id).first()

    # entity
    entity_id = request.params.get('entity_id', None)
    entity = Entity.query.filter(Entity.id == entity_id).first()

    if user and entity:
        entity.users.append(user)
        DBSession.add_all([entity, user])

    return HTTPOk()


@view_config(
    route_name='append_user_to_groups_dialog',
    renderer='templates/auth/dialog_append_user_to_groups.jinja2'
)
@view_config(
    route_name='append_user_to_departments_dialog',
    renderer='templates/department/dialog_append_user_to_departments.jinja2'
)
def append_user_to_entity_dialog(request):
    """runs for append user dialog
    """
    logged_in_user = get_logged_in_user(request)

    user_id = request.matchdict.get('id', -1)
    user = User.query.filter_by(id=user_id).first()

    return {
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'user': user
    }


@view_config(
    route_name='append_user_to_groups'
)
def append_user_to_groups(request):
    """appends the given group o the given user
    # """
    # groups
    groups_ids = get_multi_integer(request, 'group_ids')
    logger.debug('groups_ids : %s' % groups_ids)

    groups = Group.query.filter(Group.id.in_(groups_ids)).all()

    # user
    user_id = request.matchdict.get('id', None)
    user = User.query.filter(User.id == user_id).first()

    logger.debug('user : %s' % user)
    logger.debug('groups  : %s' % groups)

    if groups and user:
        user.groups = groups
        DBSession.add(user)
        DBSession.add_all(groups)

    return HTTPOk()


@view_config(
    route_name='append_user_to_departments'
)
def append_user_to_departments(request):
    """appends the given department to the given User
    """
    # departments

    logger.debug('append_user_to_departments')

    department_ids = get_multi_integer(request, 'department_ids')
    departments = Department.query.filter(
        Department.id.in_(department_ids)).all()

    # user
    user_id = request.matchdict.get('id', -1)
    user = Entity.query.filter(User.id == user_id).first()

    logger.debug('user : %s' % user)
    logger.debug('departments  : %s' % departments)

    if departments and user:
        user.departments = departments
        DBSession.add(user)
        DBSession.add_all(departments)

    return HTTPOk()


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
    # renderer='templates/auth/no_permission.jinja2'
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


# @forbidden_view_config(
#     renderer='templates/auth/no_permission.jinja2'
# )
# def forbidden(request):
#     """runs when user has no permission for the requested page
#     """
#     return {}


@view_config(
    route_name='flash_message',
    renderer='templates/home.jinja2'
)
@view_config(
    route_name='home',
    renderer='templates/home.jinja2'
)
@view_config(
    route_name='me_menu',
    renderer='templates/auth/me_menu.jinja2'
)
def home(request):
    logged_in_user = get_logged_in_user(request)

    studio = Studio.query.first()
    projects = Project.query.all()

    today = datetime.date.today()
    start = datetime.time(0, 0)
    end = datetime.time(23, 59, 59)

    start_of_today = datetime.datetime.combine(today, start)
    end_of_today = datetime.datetime.combine(today, end)

    tasks_today = Task.query.join(User, Task.resources) \
        .filter(User.id == logged_in_user.id) \
        .filter(Task.computed_start < end_of_today) \
        .filter(Task.computed_end > start_of_today).all()

    flash_message = request.GET.get('flash')
    if flash_message:
        request.session.flash(flash_message)

    return {
        'stalker_pyramid': stalker_pyramid,
        'studio': studio,
        'logged_in_user': logged_in_user,
        'has_permission': PermissionChecker(request),
        'projects': projects,
        'entity': logged_in_user,
        'tasks_today': tasks_today
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
    route_name='get_user_events',
    renderer='json'
)
def get_user_events(request):

    logger.debug('get_user_events is running')
    user_id = request.matchdict.get('id', -1)
    user = User.query.filter_by(id=user_id).first()

    logger.debug('user_id : %s' % user_id)

    events = []

    # if user.time_logs:
    for time_log in user.time_logs:
        # logger.debug('time_log.task.id : %s' % time_log.task.id)
        # assert isinstance(time_log, TimeLog)
        events.append({
            'id': time_log.id,
            'entity_type':time_log.plural_class_name.lower(),
            'title': '%s (%s)' % (
                time_log.task.name,
                ' | '.join(reversed([parent.name for parent in time_log.task.parents]))),
            'start': milliseconds_since_epoch(time_log.start),
            'end': milliseconds_since_epoch(time_log.end),
            'className': 'label-success',
            'allDay': False,
            'status': time_log.task.status.name
            # 'hours_to_complete': time_log.hours_to_complete,
            # 'notes': time_log.notes
        })


    vacations = Vacation.query.filter(Vacation.user==None).all()
    if isinstance(user, User):
        vacations.extend(user.vacations)
    # if user.time_logs:
    for vacation in vacations:
        # logger.debug('time_log.task.id : %s' % time_log.task.id)
        # assert isinstance(time_log, TimeLog)
        events.append({
            'id': vacation.id,
            'entity_type':vacation.plural_class_name.lower(),
            'title': vacation.type.name,
            'start': milliseconds_since_epoch(vacation.start),
            'end': milliseconds_since_epoch(vacation.end),
            'className': 'label-yellow',
            'allDay': True,
            'status': ''
        })


    today = datetime.datetime.today()

    # if user.time_logs:
    for task in user.tasks:
        # logger.debug('time_log.task.id : %s' % time_log.task.id)
        # assert isinstance(time_log, TimeLog)

        if today < task.end:
            events.append({
                'id': task.id,
                'entity_type':task.plural_class_name.lower(),
                'title': '%s (%s)' % (
                    task.name,
                    ' | '.join(reversed([parent.name for parent in task.parents]))),
                'start': milliseconds_since_epoch(task.start),
                'end': milliseconds_since_epoch(task.end),
                'className': 'label',
                'allDay': False,
                'status': task.status.name
                # 'hours_to_complete': time_log.hours_to_complete,
                # 'notes': time_log.notes
            })

    return events


@view_config(
    route_name='get_user_efficiency_graphic',
    renderer='json'
)
def get_user_efficiency_graphic(request):

    logger.debug('get_user_efficiency_graphic is running')
    user_id = request.matchdict.get('id', -1)
    user = User.query.filter_by(id=user_id).first()

    logger.debug('user_id : %s' % user_id)

    efficiency_list = []


    return efficiency_list





